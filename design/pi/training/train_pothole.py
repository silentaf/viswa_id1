"""Fine-tune a small YOLO detector to find POTHOLES (a hazard the COCO model cannot name), then measure it.

Data:  1. public "Potholes" dataset (Roboflow export, re-hosted on Hugging Face as
          Ryukijano/Pothole-detection-Yolov8), downloaded to tools/datasets/pothole_ryukijano (not in git).
          Its original train split has only 53 unique source photos (100 images - Roboflow had already
          expanded it with augmented crops), which plateaued fine-tuning at recall 0.30 even with the full
          100-epoch budget (val mAP50 flat for the last ~20 epochs - a data-capacity ceiling, not an
          undertrained model). Its own 'valid' split (100 images, 100 unique photos, confirmed zero overlap
          with train or test) was only ever used to pick the best epoch and was barely exercised for that,
          since training never early-stopped. So train+valid are pooled (153 unique photos) and re-split
          85/15 BY UNIQUE SOURCE PHOTO (not by augmented file) - see _scene_pool() below.
       2. RDD2020 India subset (Arya et al., "Global Road Damage Detection: State-of-the-art Solutions",
          IEEE Big Data 2020), prepared by prepare_rdd_india.py into
          tools/datasets/rdd2020_india_pothole (not in git): 1,530 REAL INDIAN ROAD PHOTOS with pothole
          (D40) boxes - the first Indian data in this pipeline, and ~10x the unique-photo count of (1).
          Split 70/15/15 train/valid/test (each photo independent, no augmentation-duplication risk).
       The original Ryukijano 'test' split (88 unique photos, confirmed zero overlap with train/valid) is
       kept and the India test slice is ADDED to it (never subtracted from), so test is still never seen
       during training - just bigger and, for the first time, partly representative of actual Indian roads.
Model: Ultralytics YOLO11n, COCO-pretrained weights as the starting point (transfer learning).
Run:   tools/train-env/bin/python design/pi/training/train_pothole.py
Writes design/pi/training/results/ (metrics JSON, curves, ONNX model) - every number on the slide comes from there.
"""
import json, os, random, re, shutil, statistics as st, sys, time, glob

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
SRC_DATA = os.path.join(ROOT, 'tools', 'datasets', 'pothole_ryukijano')
RDD_INDIA = os.path.join(ROOT, 'tools', 'datasets', 'rdd2020_india_pothole')
DATA = os.path.join(ROOT, 'tools', 'train-runs', 'pothole_data_pooled')
RUNS = os.path.join(ROOT, 'tools', 'train-runs')
OUT = os.path.join(HERE, 'results')
os.makedirs(OUT, exist_ok=True)
os.makedirs(RUNS, exist_ok=True)

from ultralytics import YOLO
import torch


def _scene_id(path):
    """Roboflow source-photo id: strip the '.rf.<hash>.jpg' export suffix added per augmented crop."""
    b = os.path.basename(path)
    b = re.sub(r'\.rf\.[0-9a-f]+\.jpg$', '', b)
    return re.sub(r'_jpe?g_jpg$', '', b)


def _copy_pair(img, lab, sub):
    os.makedirs(os.path.join(DATA, sub, 'images'), exist_ok=True)
    os.makedirs(os.path.join(DATA, sub, 'labels'), exist_ok=True)
    shutil.copy(img, os.path.join(DATA, sub, 'images', os.path.basename(img)))
    shutil.copy(lab, os.path.join(DATA, sub, 'labels', os.path.basename(lab)))


def _scene_pool(valid_frac=0.15, india_valid_frac=0.15, india_test_frac=0.15, seed=0):
    """Pool Ryukijano train+valid (re-split 85/15 by unique scene) + RDD2020 India (split 70/15/15,
    train/valid folded into the pool, test ADDED to the untouched Ryukijano test). Idempotent."""
    if os.path.exists(DATA):
        shutil.rmtree(DATA)
    pairs = [(img, os.path.join(SRC_DATA, sp, 'labels', os.path.splitext(os.path.basename(img))[0] + '.txt'),
              _scene_id(img))
             for sp in ('train', 'valid') for img in glob.glob(os.path.join(SRC_DATA, sp, 'images', '*.jpg'))]
    scenes = sorted(set(p[2] for p in pairs))
    random.Random(seed).shuffle(scenes)
    valid_scenes = set(scenes[:max(1, round(len(scenes) * valid_frac))])
    for img, lab, scene in pairs:
        _copy_pair(img, lab, 'valid' if scene in valid_scenes else 'train')
    for img in glob.glob(os.path.join(SRC_DATA, 'test', 'images', '*.jpg')):
        lab = os.path.join(SRC_DATA, 'test', 'labels', os.path.splitext(os.path.basename(img))[0] + '.txt')
        _copy_pair(img, lab, 'test')

    india = sorted(glob.glob(os.path.join(RDD_INDIA, 'images', '*.jpg')))
    random.Random(seed + 1).shuffle(india)
    n_valid = round(len(india) * india_valid_frac)
    n_test = round(len(india) * india_test_frac)
    for i, img in enumerate(india):
        lab = os.path.join(RDD_INDIA, 'labels', os.path.splitext(os.path.basename(img))[0] + '.txt')
        sub = 'test' if i < n_test else ('valid' if i < n_test + n_valid else 'train')
        _copy_pair(img, lab, sub)


_scene_pool()

# dataset yaml with absolute paths (the Roboflow yaml uses relative ../ paths)
names = ['pothole']
yaml_path = os.path.join(RUNS, 'pothole_data.yaml')
with open(yaml_path, 'w') as f:
    f.write('path: %s\ntrain: train/images\nval: valid/images\ntest: test/images\nnames:\n  0: pothole\n' % DATA)

counts = {sp: {'images': len(glob.glob(os.path.join(DATA, sp, 'images', '*'))),
               'boxes': sum(1 for p in glob.glob(os.path.join(DATA, sp, 'labels', '*.txt'))
                            for line in open(p) if line.strip())}
          for sp in ('train', 'valid', 'test')}
print('dataset:', counts)

SEED, EPOCHS, IMGSZ = 0, 100, 640
model = YOLO('yolo11n.pt')
t0 = time.time()
model.train(data=yaml_path, epochs=EPOCHS, imgsz=IMGSZ, batch=16, seed=SEED, deterministic=True, patience=30,
            project=RUNS, name='pothole_yolo11n', exist_ok=True, device=0, workers=4, plots=True, verbose=False)
train_min = (time.time() - t0) / 60
run = os.path.join(RUNS, 'pothole_yolo11n')
best = YOLO(os.path.join(run, 'weights', 'best.pt'))

# final numbers: the held-out TEST split
m = best.val(data=yaml_path, split='test', imgsz=IMGSZ, device=0, plots=True, project=RUNS, name='pothole_test',
             exist_ok=True, verbose=False)
test = {'precision': float(m.box.mp), 'recall': float(m.box.mr), 'mAP50': float(m.box.map50),
        'mAP50_95': float(m.box.map)}
mv = best.val(data=yaml_path, split='val', imgsz=IMGSZ, device=0, plots=False, project=RUNS, name='pothole_val',
              exist_ok=True, verbose=False)
val = {'precision': float(mv.box.mp), 'recall': float(mv.box.mr), 'mAP50': float(mv.box.map50),
       'mAP50_95': float(mv.box.map)}

# ONNX export + CPU speed with the same settings as design/pi/bench.py (onnxruntime, 4 threads, 640 px)
onnx_path = best.export(format='onnx', imgsz=IMGSZ, opset=12, simplify=True)
import numpy as np, onnxruntime as ort, cv2
so = ort.SessionOptions(); so.intra_op_num_threads = 4
sess = ort.InferenceSession(onnx_path, so, providers=['CPUExecutionProvider'])
inp = sess.get_inputs()[0].name
imgs = sorted(glob.glob(os.path.join(DATA, 'test', 'images', '*')))
ts = []
for i, p in enumerate(imgs):
    x = cv2.resize(cv2.imread(p), (IMGSZ, IMGSZ))[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255
    t = time.perf_counter(); sess.run(None, {inp: x}); dt = (time.perf_counter() - t) * 1e3
    if i >= 3:          # first runs are warm-up
        ts.append(dt)

res = {
    'task': 'pothole detection (1 class) - fine-tuned, measured on the held-out test split',
    'dataset': {'source': 'Ryukijano/Pothole-detection-Yolov8 on Hugging Face (Roboflow "Potholes" export; '
                          'train+valid pooled and re-split 85/15 by unique source photo) '
                          '+ RDD2020 India subset (Arya et al. 2020, real Indian road photos, D40/pothole '
                          'only; split 70/15/15, test slice added to the Ryukijano test, never subtracted)',
                'splits': counts},
    'model': 'YOLO11n, COCO-pretrained start, fine-tuned',
    'train': {'epochs_max': EPOCHS, 'imgsz': IMGSZ, 'batch': 16, 'seed': SEED, 'patience': 30,
              'gpu': torch.cuda.get_device_name(0), 'minutes': round(train_min, 1)},
    'test_split': test, 'valid_split': val,
    'baseline_note': 'The COCO model used in the AI path has no pothole class, so before fine-tuning it cannot report potholes at all.',
    'cpu_speed_laptop': {'threads': 4, 'images': len(ts), 'mean_ms': st.mean(ts),
                         'note': 'onnxruntime on the development laptop, NOT a Pi 5'},
}
json.dump(res, open(os.path.join(OUT, 'pothole_metrics.json'), 'w'), indent=1)
shutil.copy(onnx_path, os.path.join(OUT, 'pothole_yolo11n.onnx'))
for f in ('results.csv', 'results.png'):
    if os.path.exists(os.path.join(run, f)):
        shutil.copy(os.path.join(run, f), os.path.join(OUT, f))
for f in glob.glob(os.path.join(RUNS, 'pothole_test', '*.png')) + glob.glob(os.path.join(RUNS, 'pothole_test', '*.jpg')):
    shutil.copy(f, os.path.join(OUT, 'test_' + os.path.basename(f)))
print(json.dumps(res, indent=1))
