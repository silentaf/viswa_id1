"""Prediction-grid figure for the pothole slide, using real Indian held-out test photos (RDD2020 India).

Why its own script: Ultralytics only saves the first few validation batches during train_pothole.py's
val() call, and those happen to be the alphabetically-first files in the pooled test set - which are all
the (non-Indian) Ryukijano images, since 'India_*.jpg' sorts after digit-prefixed filenames. That default
grid would silently misrepresent the dataset now that most of the test set is real Indian road photos.
This script explicitly samples from the India_*.jpg test images so the figure matches what's claimed.
Run (after train_pothole.py has produced tools/train-runs/pothole_yolo11n/weights/best.pt):
  tools/train-env/bin/python design/pi/training/make_india_test_grid.py
Writes design/pi/training/results/india_test_pred.jpg (16-tile grid) - copy into ppt/assets/pothole_test_pred.png.
"""
import glob
import os
import random

import cv2
import numpy as np
from ultralytics import YOLO

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
WEIGHTS = os.path.join(ROOT, 'tools', 'train-runs', 'pothole_yolo11n', 'weights', 'best.pt')
TEST_DIR = os.path.join(ROOT, 'tools', 'train-runs', 'pothole_data_pooled', 'test', 'images')
OUT = os.path.join(HERE, 'results', 'india_test_pred.jpg')

india_imgs = sorted(glob.glob(os.path.join(TEST_DIR, 'India_*.jpg')))
pick = india_imgs[:]
random.Random(3).shuffle(pick)
pick = pick[:16]

model = YOLO(WEIGHTS)
results = model.predict(pick, imgsz=640, conf=0.25, save=False, verbose=False)

tiles = [cv2.resize(r.plot(line_width=2, font_size=10), (480, 480)) for r in results]
rows = [np.hstack(tiles[i:i + 4]) for i in range(0, 16, 4)]
grid = np.vstack(rows)
cv2.imwrite(OUT, grid)
print('saved', OUT, grid.shape, '(%d India test images available)' % len(india_imgs))
