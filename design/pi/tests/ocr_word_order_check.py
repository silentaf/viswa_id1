"""Re-check of the OCR word-order bug: old ordering (sort all boxes by top edge) vs the fixed line grouping in
visionaid_pi/speech.py, on the same 64 labelled images. Run: tools/pi-env/bin/python design/pi/tests/ocr_word_order_check.py design/pi"""
import json, os, sys, statistics as st, cv2
PI = sys.argv[1]
from rapidocr_onnxruntime import RapidOCR
eng = RapidOCR()
def lev(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]
norm = lambda s: ' '.join(s.upper().replace('.', '').replace(',', '').split())
gt = json.load(open(os.path.join(PI, 'test_data/ocr/ground_truth.json')))
res = {'old_top_sort': {}, 'new_line_grouping': {}}
for g in gt:
    r, _ = eng(cv2.imread(os.path.join(PI, 'test_data/ocr', g['file'])))
    b = [{'top': min(p[1] for p in box), 'cy': (min(p[1] for p in box) + max(p[1] for p in box)) / 2,
          'h': max(p[1] for p in box) - min(p[1] for p in box), 'x': min(p[0] for p in box), 't': t}
         for box, t, sc in (r or []) if float(sc) >= 0.5]
    old = ' '.join(x['t'] for x in sorted(b, key=lambda x: x['top']))
    b.sort(key=lambda x: x['cy']); rows = []
    for x in b:
        if rows and abs(x['cy'] - rows[-1][-1]['cy']) < 0.5 * max(x['h'], rows[-1][-1]['h']): rows[-1].append(x)
        else: rows.append([x])
    new = ' '.join(' '.join(y['t'] for y in sorted(rw, key=lambda y: y['x'])) for rw in rows)
    ref = norm(g['text'])
    for k, hyp in (('old_top_sort', old), ('new_line_grouping', new)):
        res[k].setdefault(g['condition'], []).append(lev(ref, norm(hyp)) / max(1, len(ref)))
for k, v in res.items():
    print(k, {c: round(100 * st.mean(x), 2) for c, x in v.items()})
