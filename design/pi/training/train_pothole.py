"""Fine-tune a small YOLO detector to find POTHOLES (a hazard the COCO model cannot name), then measure it.

Data:  public "Potholes" dataset (Roboflow export, re-hosted on Hugging Face as Ryukijano/Pothole-detection-Yolov8),
       downloaded to tools/datasets/pothole_ryukijano (not in git). Its own train / valid / test split is used as-is:
       train = learning, valid = choosing the best epoch, test = the final numbers (never seen during training).
Model: Ultralytics YOLO11n, COCO-pretrained weights as the starting point (transfer learning).
Run:   tools/train-env/bin/python design/pi/training/train_pothole.py
Writes design/pi/training/results/ (metrics JSON, curves, ONNX model) - every number on the slide comes from there.
"""
import json, os, shutil, statistics as st, sys, time, glob

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
DATA = os.path.join(ROOT, 'tools', 'datasets', 'pothole_ryukijano')
RUNS = os.path.join(ROOT, 'tools', 'train-runs')
OUT = os.path.join(HERE, 'results')
os.makedirs(OUT, exist_ok=True)
os.makedirs(RUNS, exist_ok=True)

from ultralytics import YOLO
import torch

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
    'dataset': {'source': 'Ryukijano/Pothole-detection-Yolov8 on Hugging Face (Roboflow "Potholes" export)',
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
