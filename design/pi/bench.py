"""VisionAid AI-path proof of concept and benchmark (runs the real Pi software on the dev laptop).

Measures, with real data:
  1. FPGA<->Pi protocol cross-check: decode the bytes the Verilog FPGA transmitted in simulation
  2. Object detection speed (YOLOv5n ONNX, 4 CPU threads like the Pi 5's 4 cores)
  3. OCR accuracy (character error rate) and speed on the synthetic label set with known text
  4. Text-to-speech (Piper) synthesis time, English and Hindi
  5. End-to-end: FPGA status + camera image -> spoken phrase -> WAV file
IMPORTANT: speeds are measured on THIS laptop, not on a Raspberry Pi 5 (expect the Pi to be slower).
Accuracy numbers do not depend on the computer.
Run: tools/pi-env/bin/python design/pi/bench.py
"""
import os
import sys
import json
import glob
import time
import platform
import statistics as st

import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from visionaid_pi.protocol import StatusParser, Status, build_command, encode_status   # noqa: E402
from visionaid_pi.vision import Detector, hazards                                    # noqa: E402
from visionaid_pi.speech import Reader, Speaker                                      # noqa: E402
from visionaid_pi.alerts import AlertManager                                         # noqa: E402

MODELS = '/tmp/visionaid-tools/models'
RES = os.path.join(HERE, 'results')
SIM_BYTES = os.path.join(HERE, '..', 'fpga', 'sim', 'fpga_to_pi_bytes.hex')
os.makedirs(RES, exist_ok=True)


def cpu_name():
    try:
        for line in open('/proc/cpuinfo'):
            if line.startswith('model name'):
                return line.split(':', 1)[1].strip()
    except OSError:
        pass
    return platform.processor()


def lev(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def norm(s):
    return ' '.join(s.upper().replace('.', '').replace(',', '').split())


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


R = {'machine': {'cpu': cpu_name(), 'python': platform.python_version(), 'threads_used': 4,
                 'note': 'Speeds measured on the development laptop, NOT on a Raspberry Pi 5.'}}

# ------------------------------------------------------------------ 1. protocol cross-check
if os.path.exists(SIM_BYTES):
    data = bytes(int(x, 16) for x in open(SIM_BYTES).read().split())
    p = StatusParser()
    frames = p.feed(data)
    R['protocol'] = {'bytes_from_verilog': len(data), 'frames_decoded': p.good, 'bad_frames': p.bad,
                     'first': frames[0].__dict__ if frames else None, 'last': frames[-1].__dict__ if frames else None,
                     'drop_off_frames': sum(f.drop_off for f in frames),
                     'fault_frames': sum(f.any_fault() for f in frames),
                     'command_sent_to_verilog_hex': build_command(4, 150).hex()}
    # self-consistency: encoder <-> parser round trip
    rt = StatusParser().feed(encode_status(Status(1499, 2499, 0xFFFF, 150, 0x10)))
    R['protocol']['roundtrip_ok'] = bool(rt and rt[0].left_mm == 1499 and rt[0].drop_off)
    print('protocol:', R['protocol']['frames_decoded'], 'frames decoded,', p.bad, 'bad')

# ------------------------------------------------------------------ 2. detection speed
det = Detector(os.path.join(MODELS, 'yolov5n.onnx'), threads=4)
imgs = sorted(glob.glob(os.path.join(HERE, 'test_data', 'coco', '*.jpg')))
for f in imgs[:3]:
    det.detect(cv2.imread(f))                                   # warm-up
times, infer, found = [], [], {}
for f in imgs:
    d, t = det.detect(cv2.imread(f))
    times.append(t['total_ms'])
    infer.append(t['infer_ms'])
    for h in hazards(d):
        found[h['label']] = found.get(h['label'], 0) + 1
R['detection_speed'] = {'images': len(imgs), 'input': '640x640', 'model': 'YOLOv5n (COCO) ONNX, onnxruntime CPU',
                        'mean_ms': st.mean(times), 'p95_ms': pct(times, 95), 'mean_infer_ms': st.mean(infer),
                        'fps_equiv': 1000 / st.mean(times), 'hazard_classes_seen': found}
print('detection: %.1f ms mean, p95 %.1f ms' % (st.mean(times), pct(times, 95)))

# ------------------------------------------------------------------ 3. OCR
reader = Reader()
gt = json.load(open(os.path.join(HERE, 'test_data', 'ocr', 'ground_truth.json')))
reader.read(cv2.imread(os.path.join(HERE, 'test_data', 'ocr', gt[0]['file'])))   # warm-up
rows = []
for g in gt:
    text, ms = reader.read(cv2.imread(os.path.join(HERE, 'test_data', 'ocr', g['file'])))
    ref, hyp = norm(g['text']), norm(text)
    rows.append({**g, 'read': text, 'ms': ms, 'cer': lev(ref, hyp) / max(1, len(ref)), 'exact': ref == hyp})
ocr = {}
for cond in ('clean', 'degraded'):
    rs = [r for r in rows if r['condition'] == cond]
    ocr[cond] = {'images': len(rs), 'mean_cer_pct': 100 * st.mean(r['cer'] for r in rs),
                 'exact_match_pct': 100 * sum(r['exact'] for r in rs) / len(rs),
                 'mean_ms': st.mean(r['ms'] for r in rs), 'p95_ms': pct([r['ms'] for r in rs], 95)}
R['ocr'] = {'engine': 'RapidOCR (PP-OCR ONNX), English', **ocr,
            'worst': sorted(rows, key=lambda r: -r['cer'])[:3]}
json.dump(rows, open(os.path.join(RES, 'ocr_details.json'), 'w'), indent=1)
print('ocr:', {k: round(v['mean_cer_pct'], 2) for k, v in ocr.items()})

# ------------------------------------------------------------------ 4. TTS
tts = {}
for lang, model, phrases in (
        ('en', 'en_US-lessac-medium.onnx', ['Step down ahead. Stop.', 'Car, left, 1.4 metres',
                                             'Paracetamol Tablets I P 500 milligram']),
        ('hi', 'hi_IN-pratham-medium.onnx', ['आगे सीढ़ी है, रुकिए।', 'बाईं ओर कार, डेढ़ मीटर'])):
    sp = Speaker(os.path.join(MODELS, model))
    sp.synth(phrases[0], os.path.join(RES, 'warmup.wav'))
    res = []
    for i, ph in enumerate(phrases):
        ms, dur = sp.synth(ph, os.path.join(RES, 'tts_%s_%d.wav' % (lang, i)))
        res.append({'text': ph, 'synth_ms': ms, 'audio_s': dur, 'rtf': ms / 1000 / dur})
    tts[lang] = res
os.remove(os.path.join(RES, 'warmup.wav'))
R['tts'] = {'engine': 'Piper (offline neural TTS)', **tts}
print('tts:', {k: [round(r['synth_ms']) for r in v] for k, v in tts.items()})

# ------------------------------------------------------------------ 5. end-to-end demo
am = AlertManager()
en = Speaker(os.path.join(MODELS, 'en_US-lessac-medium.onnx'))
demo = []
for f in imgs:
    t0 = time.perf_counter()
    d, _ = det.detect(cv2.imread(f))
    hz = hazards(d)
    if not hz:
        continue
    side = hz[0]['side']
    status = Status(1400 if side in ('left', 'ahead') else 3500, 1400 if side in ('right', 'ahead') else 3500,
                    0xFFFF, 150, 0)                         # FPGA reports something at 1.4 m on that side
    msgs = am.update(status, hz)
    if not msgs:
        continue
    phrase = msgs[0][1]
    wav = os.path.join(RES, 'e2e_%s.wav' % os.path.basename(f)[:-4])
    synth_ms, dur = en.synth(phrase, wav)
    total = (time.perf_counter() - t0) * 1e3
    demo.append({'image': os.path.basename(f), 'phrase': phrase, 'total_ms_to_audio_ready': total})
    if len(demo) >= 6:
        break
R['end_to_end'] = {'description': 'camera image -> YOLO -> alert manager (+FPGA distance) -> Piper WAV ready',
                   'runs': demo, 'mean_ms': st.mean(x['total_ms_to_audio_ready'] for x in demo) if demo else None}
for f in glob.glob(os.path.join(RES, 'e2e_*.wav'))[3:]:
    os.remove(f)                                            # keep only a few audio samples
print('e2e:', [(x['phrase'], round(x['total_ms_to_audio_ready'])) for x in demo])
json.dump(R, open(os.path.join(RES, 'bench_results.json'), 'w'), indent=1, ensure_ascii=False)
print('saved results/bench_results.json')
