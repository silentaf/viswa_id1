"""Summary figure of the measured AI-path results (laptop) for the PPT. Run with tools/pi-env python."""
import json, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__))
b = json.load(open(os.path.join(HERE, 'results', 'bench_results.json')))
a = json.load(open(os.path.join(HERE, 'results', 'detection_accuracy.json')))
fig, axs = plt.subplots(1, 3, figsize=(16, 4.6))
ax = axs[0]
names = ['Detect', 'Image file ->\nspeech WAV', 'TTS\nEnglish', 'TTS\nHindi', 'OCR\nlabel']
vals = [b['detection_speed']['mean_ms'], b['end_to_end']['mean_ms'],
        sum(x['synth_ms'] for x in b['tts']['en']) / len(b['tts']['en']),
        sum(x['synth_ms'] for x in b['tts']['hi']) / len(b['tts']['hi']),
        b['ocr']['clean']['mean_ms']]
bars = ax.bar(names, vals, color=['#25325F', '#3F6E12', '#5B6BA8', '#5B6BA8', '#8CC63F'])
for r, v in zip(bars, vals):
    ax.text(r.get_x() + r.get_width() / 2, v * 1.03, '%.0f ms' % v, ha='center', fontsize=9)
ax.set_ylabel('time (ms)'); ax.set_title('Measured on laptop (%s), 4 threads - NOT Pi 5' % b['machine']['cpu'].split(' ')[2] if len(b['machine']['cpu'].split(' ')) > 2 else 'laptop', fontsize=9)
ax = axs[1]
pc = a['per_class']
cls = sorted(pc, key=lambda c: -pc[c]['AP50'])
lab = ['%s (n=%d)' % (c, pc[c]['gt']) for c in cls]
ax.barh(lab, [pc[c]['AP50'] for c in cls], color='#5B6BA8', label='AP50 (all sizes)')
# recall on objects that are large in the image (> 96 x 96 px, COCO definition); only where >= 5 such objects
big = [pc[c]['recall_large_at_0.35'] if pc[c]['gt_large'] >= 5 else 0 for c in cls]
ax.barh(lab, big, color='#3F6E12', alpha=0.85, height=0.4, label='recall, objects > 96x96 px (only if >= 5 of them)')
ax.invert_yaxis(); ax.set_xlim(0, 1); ax.legend(fontsize=8, loc='lower right')
ax.set_title('Detection accuracy vs COCO ground truth (200 images)\nmAP50 = %.2f over 12 hazard classes' % a['mAP50_hazard_classes'], fontsize=9)
ax = axs[2]
o = b['ocr']
x = ['clean', 'degraded']
ax.bar([0, 1], [o['clean']['mean_cer_pct'], o['degraded']['mean_cer_pct']], color='#25325F', width=0.35, label='char. error %')
ax.bar([0.38, 1.38], [100 - o['clean']['exact_match_pct'], 100 - o['degraded']['exact_match_pct']], color='#B3261E', width=0.35, label='lines not exactly right %')
for i, c in enumerate(x):
    ax.text(i, o[c]['mean_cer_pct'] + 1, '%.1f%%' % o[c]['mean_cer_pct'], ha='center', fontsize=9)
ax.set_xticks([0.19, 1.19]); ax.set_xticklabels(['clean labels', 'blur+tilt+noise'])
ax.set_ylabel('%'); ax.legend(fontsize=8)
ax.set_title('OCR on 64 labels with known text (RapidOCR, English)', fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(HERE, 'results', 'ai_path_results.png'), dpi=150)
print('saved')
