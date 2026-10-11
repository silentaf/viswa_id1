"""One-time conversion: RDD2020 India subset (PASCAL VOC XML) -> YOLO txt, pothole (D40) only.

Why: our pothole fine-tune was trained on a small (153 unique photo), mostly non-Indian, non-chest-height
public dataset. RDD2020 (Arya et al., "Global Road Damage Detection: State-of-the-art Solutions",
IEEE Big Data 2020) is a peer-reviewed benchmark of 26,336 real road photos from India, Japan and the
Czech Republic with PASCAL VOC annotations for 4 damage classes (D00/D10/D20/D40). Its India/ subset
alone has 7,706 real Indian road photos, 1,530 of them containing at least one pothole (D40) box -
roughly 10x the unique-photo count we had before, and the first real Indian road data in this pipeline.
(D44/D43/D50 are white-line-blur / crosswalk-blur / manhole-cover, NOT potholes - excluded on purpose.)

Source: downloaded tools/datasets/rdd2020_india_raw/India/{images,annotations/xmls} from
https://huggingface.co/datasets/ShixuanAn/RDD2020 (not in git - ~500 MB).
Writes tools/datasets/rdd2020_india_pothole/{images,labels}/ in YOLO format (flat, one class: pothole).
Run: tools/freecad-env/bin/python design/pi/training/prepare_rdd_india.py   (only needs stdlib + Pillow)
"""
import glob
import os
import shutil
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
SRC = os.path.join(ROOT, 'tools', 'datasets', 'rdd2020_india_raw', 'India')
OUT = os.path.join(ROOT, 'tools', 'datasets', 'rdd2020_india_pothole')

if os.path.exists(OUT):
    shutil.rmtree(OUT)
os.makedirs(os.path.join(OUT, 'images'))
os.makedirs(os.path.join(OUT, 'labels'))

kept, skipped, total_boxes = 0, 0, 0
for xml_path in sorted(glob.glob(os.path.join(SRC, 'annotations', 'xmls', '*.xml'))):
    root = ET.parse(xml_path).getroot()
    w = float(root.find('size/width').text)
    h = float(root.find('size/height').text)
    lines = []
    for obj in root.findall('object'):
        if obj.find('name').text != 'D40':      # D40 = pothole; other RDD classes are cracks/blur/manhole
            continue
        b = obj.find('bndbox')
        xmin, ymin = float(b.find('xmin').text), float(b.find('ymin').text)
        xmax, ymax = float(b.find('xmax').text), float(b.find('ymax').text)
        cx, cy = (xmin + xmax) / 2 / w, (ymin + ymax) / 2 / h
        bw, bh = (xmax - xmin) / w, (ymax - ymin) / h
        lines.append('0 %.6f %.6f %.6f %.6f' % (cx, cy, bw, bh))
    if not lines:
        skipped += 1
        continue
    stem = os.path.splitext(os.path.basename(xml_path))[0]
    img_src = os.path.join(SRC, 'images', stem + '.jpg')
    if not os.path.exists(img_src):
        skipped += 1
        continue
    shutil.copy(img_src, os.path.join(OUT, 'images', stem + '.jpg'))
    with open(os.path.join(OUT, 'labels', stem + '.txt'), 'w') as f:
        f.write('\n'.join(lines) + '\n')
    kept += 1
    total_boxes += len(lines)

print('RDD2020 India -> pothole-only YOLO set: %d images kept (%d pothole boxes), %d skipped (no D40 / missing file)'
      % (kept, total_boxes, skipped))
