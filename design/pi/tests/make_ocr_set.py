"""Synthetic OCR test set with KNOWN ground truth (labels / signs a blind user meets).
Each text is rendered in 2 fonts x 2 conditions (clean, degraded: blur + tilt + noise + low contrast + JPEG).
This is a controlled bench test - real-world photos are tested in Stage 3.
Run: tools/pi-env/bin/python design/pi/tests/make_ocr_set.py
"""
import os
import json
import random
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'test_data', 'ocr')
os.makedirs(OUT, exist_ok=True)
TEXTS = [
    'Paracetamol Tablets IP 500 mg', 'Take one tablet twice daily after food', 'EXP 08/2027  Batch B2341',
    'Store below 25 C away from light', 'Amoxicillin Capsules 250 mg', 'MRP Rs 32.50 incl. of all taxes',
    'PLATFORM NO 2', 'EXIT', 'LADIES TOILET', 'BUS STOP', 'PHARMACY', 'CAUTION WET FLOOR',
    'Room 204 Electronics Lab', 'Pull to open', 'Mind the step', 'Sardar Patel Road',
]
FONTS = ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
         '/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf']
random.seed(7)
np.random.seed(7)
meta = []
n = 0
for t in TEXTS:
    for fi, fpath in enumerate(FONTS):
        for cond in ('clean', 'degraded'):
            font = ImageFont.truetype(fpath, 44)
            w = int(font.getlength(t)) + 80
            img = Image.new('RGB', (w, 120), (245, 245, 238) if cond == 'clean' else (200, 196, 185))
            d = ImageDraw.Draw(img)
            d.text((40, 30), t, font=font, fill=(20, 20, 20) if cond == 'clean' else (85, 80, 75))
            if cond == 'degraded':
                img = img.rotate(random.uniform(-6, 6), expand=True, fillcolor=(200, 196, 185))
                img = img.filter(ImageFilter.GaussianBlur(1.4))
                a = np.asarray(img).astype(np.float32) + np.random.normal(0, 9, (img.size[1], img.size[0], 3))
                img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
            name = 'ocr_%02d.jpg' % n
            img.save(os.path.join(OUT, name), quality=60 if cond == 'degraded' else 92)
            meta.append({'file': name, 'text': t, 'font': os.path.basename(fpath), 'condition': cond})
            n += 1
json.dump(meta, open(os.path.join(OUT, 'ground_truth.json'), 'w'), indent=1)
print('wrote', n, 'images')
