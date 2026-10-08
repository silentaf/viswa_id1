"""Object detection for the AI path: YOLOv5n (COCO, ONNX) on onnxruntime CPU.
Only classes that matter to a walking blind user are spoken; the rest are ignored.
"""
import time
import numpy as np
import cv2
import onnxruntime as ort

COCO = ['person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat', 'traffic light',
        'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
        'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
        'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard',
        'tennis racket', 'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
        'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
        'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote', 'keyboard',
        'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book', 'clock', 'vase', 'scissors',
        'teddy bear', 'hair drier', 'toothbrush']
# Spoken names for hazards / landmarks relevant to mobility (others are not announced)
HAZARDS = {'person': 'person', 'bicycle': 'bicycle', 'car': 'car', 'motorcycle': 'motorbike', 'bus': 'bus',
           'truck': 'truck', 'train': 'train', 'traffic light': 'traffic light', 'fire hydrant': 'hydrant',
           'stop sign': 'stop sign', 'bench': 'bench', 'dog': 'dog', 'cow': 'cow', 'horse': 'horse',
           'chair': 'chair', 'potted plant': 'plant pot', 'dining table': 'table', 'suitcase': 'suitcase',
           'umbrella': 'umbrella'}


class Detector:
    def __init__(self, model_path, size=640, conf=0.35, iou=0.45, threads=4):
        so = ort.SessionOptions()
        so.intra_op_num_threads = threads          # Raspberry Pi 5 has 4 cores
        self.sess = ort.InferenceSession(model_path, so, providers=['CPUExecutionProvider'])
        self.inp = self.sess.get_inputs()[0].name
        self.dtype = np.float16 if 'float16' in self.sess.get_inputs()[0].type else np.float32   # release ONNX is FP16
        self.size, self.conf, self.iou = size, conf, iou

    def _letterbox(self, img):
        h, w = img.shape[:2]
        r = self.size / max(h, w)
        nh, nw = int(round(h * r)), int(round(w * r))
        canvas = np.full((self.size, self.size, 3), 114, np.uint8)
        top, left = (self.size - nh) // 2, (self.size - nw) // 2
        canvas[top:top + nh, left:left + nw] = cv2.resize(img, (nw, nh))
        return canvas, r, left, top

    def detect(self, bgr):
        """Returns (detections, timings). detection = dict(label, score, box=(x1,y1,x2,y2), side)."""
        t0 = time.perf_counter()
        img, r, dx, dy = self._letterbox(bgr)
        x = img[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255.0
        t1 = time.perf_counter()
        out = self.sess.run(None, {self.inp: np.ascontiguousarray(x.astype(self.dtype))})[0][0].astype(np.float32)
        t2 = time.perf_counter()
        obj = out[:, 4]
        cls = out[:, 5:].argmax(1)
        score = obj * out[np.arange(len(out)), 5 + cls]
        keep = score > self.conf
        out, cls, score = out[keep], cls[keep], score[keep]
        boxes = []
        for (cx, cy, w, h) in out[:, :4]:
            boxes.append([(cx - w / 2 - dx) / r, (cy - h / 2 - dy) / r, w / r, h / r])
        idx = cv2.dnn.NMSBoxes(boxes, score.tolist(), self.conf, self.iou) if boxes else []
        W = bgr.shape[1]
        dets = []
        for i in np.array(idx).reshape(-1):
            bx, by, bw, bh = boxes[i]
            cxn = (bx + bw / 2) / W
            side = 'left' if cxn < 1 / 3 else ('right' if cxn > 2 / 3 else 'ahead')
            dets.append({'label': COCO[int(cls[i])], 'score': float(score[i]),
                         'box': (int(bx), int(by), int(bx + bw), int(by + bh)), 'side': side,
                         'area': float(bw * bh) / (bgr.shape[0] * W)})
        t3 = time.perf_counter()
        return dets, {'pre_ms': (t1 - t0) * 1e3, 'infer_ms': (t2 - t1) * 1e3, 'post_ms': (t3 - t2) * 1e3,
                      'total_ms': (t3 - t0) * 1e3}


def hazards(dets):
    """Only mobility-relevant detections, largest (closest-looking) first."""
    h = [dict(d, spoken=HAZARDS[d['label']]) for d in dets if d['label'] in HAZARDS]
    return sorted(h, key=lambda d: -d['area'])
