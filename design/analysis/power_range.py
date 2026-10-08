"""Battery-life range using PUBLISHED Raspberry Pi 5 power figures (calculation, not a measurement).
Pi 5: ~3.0 W idle (headless, Wi-Fi), ~8.8 W all 4 cores at full load (raspberry.tips, 2026 comparison).
Rest of the system (camera 0.25 W, FPGA board 0.4 W, LiDAR 0.35 W, ultrasonics/IMU 0.04 W, motors 0.17 W avg,
regulator loss 0.11 W) = 1.32 W (datasheet-level estimates, see design/bom).
Power bank 10,000 mAh x 3.7 V = 37 Wh, 85 % conversion efficiency (assumption).
Run: python3 design/analysis/power_range.py
"""
import json, os
REST = 0.25 + 0.4 + 0.35 + 0.04 + 0.17 + 0.11
E = 37 * 0.85
cases = {
    'AI continuous (all cores busy, worst)': 8.8,
    'AI event-triggered (detect only when FPGA sees < 3 m; ~50 % duty)': (8.8 + 3.0) / 2,
    'AI mostly idle (FPGA alerts only, OCR on demand)': 3.0,
}
out = {k: {'pi_W': v, 'total_W': round(v + REST, 2), 'runtime_h': round(E / (v + REST), 2)} for k, v in cases.items()}
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'power_range.json'), 'w'), indent=1)
for k, v in out.items():
    print('%-68s %5.2f W  -> %.1f h' % (k, v['total_W'], v['runtime_h']))
