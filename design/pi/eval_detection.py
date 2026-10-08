"""Detection ACCURACY of the AI path against COCO val2017 ground truth (hardware-independent).

200 val2017 images that contain mobility-relevant classes are sampled with a fixed seed. For each class:
  AP50  - average precision at IoU >= 0.5 (all-point interpolation, detector run at conf 0.05)
  P / R - precision and recall at the operating threshold used on the device (conf 0.35)
  R_large - recall for LARGE objects (> 96 x 96 px, COCO definition): nearby obstacles look large
Run: tools/pi-env/bin/python design/pi/eval_detection.py
"""
import os
import sys
import json
import random
import urllib.request
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from visionaid_pi.vision import Detector, COCO          # noqa: E402

DS = '/tmp/visionaid-tools/datasets'
ANN = os.path.join(DS, 'annotations', 'instances_val2017.json')
IMG = os.path.join(DS, 'val2017_subset')
CLASSES = ['person', 'bicycle', 'car', 'motorcycle', 'bus', 'truck', 'dog', 'bench', 'chair', 'traffic light',
           'stop sign', 'cow']
N_IMAGES = 200
os.makedirs(IMG, exist_ok=True)

ann = json.load(open(ANN))
cat_name = {c['id']: c['name'] for c in ann['categories']}
by_img = {}
for a in ann['annotations']:
    by_img.setdefault(a['image_id'], []).append(a)
imgs = {i['id']: i for i in ann['images']}
cands = sorted(i for i, aa in by_img.items() if any(cat_name[a['category_id']] in CLASSES for a in aa))
random.seed(2026)
sel = random.sample(cands, N_IMAGES)

det = Detector('/tmp/visionaid-tools/models/yolov5n.onnx', conf=0.05, threads=8)


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter + 1e-9)


preds = {c: [] for c in CLASSES}      # (score, image_id, box)
gts = {c: {} for c in CLASSES}        # image_id -> list of [box, crowd, large, matched]
for k, iid in enumerate(sel):
    meta = imgs[iid]
    path = os.path.join(IMG, meta['file_name'])
    if not os.path.exists(path):
        urllib.request.urlretrieve(meta['coco_url'], path)
    im = cv2.imread(path)
    for a in by_img[iid]:
        n = cat_name[a['category_id']]
        if n in CLASSES:
            x, y, w, h = a['bbox']
            gts[n].setdefault(iid, []).append([(x, y, x + w, y + h), a['iscrowd'], a['area'] > 96 * 96, False])
    dets, _ = det.detect(im)
    for d in dets:
        if d['label'] in CLASSES:
            preds[d['label']].append((d['score'], iid, d['box']))
    if k % 50 == 0:
        print('image', k, flush=True)

res = {}
for c in CLASSES:
    n_gt = sum(1 for g in gts[c].values() for x in g if not x[1])
    n_large = sum(1 for g in gts[c].values() for x in g if not x[1] and x[2])
    if n_gt == 0:
        continue
    for g in gts[c].values():
        for x in g:
            x[3] = False
    tp, fp, scores, large_hit_035 = [], [], [], 0
    tp035 = fp035 = 0
    for s, iid, box in sorted(preds[c], key=lambda p: -p[0]):
        best, bj = 0.5, -1
        for j, g in enumerate(gts[c].get(iid, [])):
            o = iou(box, g[0])
            if o >= best and not g[3]:
                best, bj = o, j
        if bj >= 0 and not gts[c][iid][bj][1]:
            gts[c][iid][bj][3] = True
            tp.append(1); fp.append(0)
            if s >= 0.35:
                tp035 += 1
                large_hit_035 += gts[c][iid][bj][2]
        elif bj >= 0:                       # matched a crowd region: ignore
            continue
        else:
            tp.append(0); fp.append(1)
            if s >= 0.35:
                fp035 += 1
        scores.append(s)
    tpc, fpc = np.cumsum(tp), np.cumsum(fp)
    rec = tpc / n_gt
    prec = tpc / np.maximum(tpc + fpc, 1e-9)
    mrec = np.concatenate([[0], rec, [1]])
    mpre = np.concatenate([[0], prec, [0]])
    for i in range(len(mpre) - 2, -1, -1):
        mpre[i] = max(mpre[i], mpre[i + 1])
    ap = float(np.sum((mrec[1:] - mrec[:-1]) * mpre[1:]))
    res[c] = {'gt': n_gt, 'gt_large': n_large, 'AP50': ap,
              'precision_at_0.35': tp035 / max(1, tp035 + fp035), 'recall_at_0.35': tp035 / n_gt,
              'recall_large_at_0.35': large_hit_035 / max(1, n_large)}
summary = {'images': N_IMAGES, 'seed': 2026, 'model': 'YOLOv5n COCO ONNX, 640 px',
           'mAP50_hazard_classes': float(np.mean([r['AP50'] for r in res.values()])),
           'person': res.get('person'), 'per_class': res}
json.dump(summary, open(os.path.join(HERE, 'results', 'detection_accuracy.json'), 'w'), indent=1)
print(json.dumps({c: {k: round(v, 3) if isinstance(v, float) else v for k, v in r.items()} for c, r in res.items()},
                 indent=0))
print('mAP50 over hazard classes: %.3f' % summary['mAP50_hazard_classes'])
