"""Sensor coverage and drop-off geometry for the chest pod (calculation + simple simulation).

Inputs (from the CAD spreadsheet and datasheets):
  pod height on the chest          H   = 1.30 m   (assumption: adult ~1.70 m tall; varies with user)
  ultrasonic half-beam angle       15 deg         (HC-SR04-class datasheet 'measuring angle 15 deg')
  head sensor pitch                +25 deg (CAD PitchHead);  side sensors yaw +/-15 deg (CAD YawLR)
  LiDAR pitch                      -35 deg (CAD PitchLidar); TF-Luna FOV 2 deg
  drop-off threshold               15 cm for 3 frames (FPGA va_lidar DROP_CM / DROP_FRAMES)
Outputs: coverage figure, drop-off warning distance, and a walking-sway simulation that checks whether
the fixed-baseline drop-off detector would false-alarm, with and without IMU pitch compensation.
Run: tools/pi-env/bin/python design/analysis/sensor_geometry.py
"""
import os
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
H, HALF, HEAD, YAW, LID = 1.30, 15.0, 25.0, 15.0, 35.0
DROP_CM = 0.15
R = {}

# ---------------- drop-off warning distance (flat floor, then a step down of 15 cm)
t = np.radians(LID)
D0 = H / np.tan(t)                     # where the beam meets the floor ahead
r0 = H / np.sin(t)                     # LiDAR range on flat floor
dr = DROP_CM / np.sin(t)               # range increase when the beam passes a 15 cm step
R['dropoff'] = {'beam_hits_floor_ahead_m': D0, 'flat_range_m': r0, 'range_jump_for_15cm_step_m': dr,
                'warning_distance_m': D0, 'warning_time_s_at_1.2mps': D0 / 1.2,
                'note': 'detected when the step edge is ~%.2f m ahead (beam passes the edge)' % D0}

# ---------------- walking sway: does pitch wobble alone exceed the 15 cm threshold?
fs, T = 100.0, 20.0                    # TF-Luna 100 Hz, 20 s walk
tt = np.arange(0, T, 1 / fs)
rng = np.random.default_rng(1)
sway = 3.0 * np.sin(2 * np.pi * 1.8 * tt) + rng.normal(0, 0.7, tt.size)   # deg: +/-3 deg at step rate (assumption)
bounce = 0.02 * np.sin(2 * np.pi * 1.8 * tt + 0.5)                          # m: +/-2 cm vertical bob (assumption)
rng_meas = (H + bounce) / np.sin(np.radians(LID + sway)) + rng.normal(0, 0.01, tt.size)   # 1 cm sensor noise
base_fixed = r0
imu_pitch = sway + rng.normal(0, 0.5, tt.size)                               # IMU pitch estimate, 0.5 deg error
base_comp = H / np.sin(np.radians(LID + imu_pitch))


def alarms(r, base):
    over = (r - base) > DROP_CM
    run, n = 0, 0
    for o in over:
        run = run + 1 if o else 0
        if run == 3:
            n += 1
    return n


R['walking_sway_sim'] = {
    'assumptions': '+/-3 deg pitch sway at 1.8 Hz + 0.7 deg jitter, +/-2 cm bob, 1 cm LiDAR noise, flat floor, 20 s',
    'max_range_excursion_m': float((rng_meas - r0).max()),
    'false_alarms_fixed_baseline': alarms(rng_meas, base_fixed),
    'false_alarms_imu_compensated': alarms(rng_meas, base_comp),
    'margin_left_with_imu_m': float(DROP_CM - (rng_meas - base_comp).max())}

# ---------------- ultrasonic coverage (side view, head sensor and forward sensors)
d = np.linspace(0.3, 3.0, 50)
head_lo, head_hi = H + d * np.tan(np.radians(HEAD - HALF)), H + d * np.tan(np.radians(HEAD + HALF))
fw_lo, fw_hi = H - d * np.tan(np.radians(HALF)), H + d * np.tan(np.radians(HALF))
R['coverage'] = {'head_sensor_band_at_1m_m': [float(H + np.tan(np.radians(HEAD - HALF))),
                                              float(H + np.tan(np.radians(HEAD + HALF)))],
                 'forward_band_at_1m_m': [float(H - np.tan(np.radians(HALF))), float(H + np.tan(np.radians(HALF)))],
                 'forward_band_at_2m_m': [float(H - 2 * np.tan(np.radians(HALF))), float(H + 2 * np.tan(np.radians(HALF)))],
                 'side_sensors_horizontal_deg': [-(YAW + HALF), -(YAW - HALF), YAW - HALF, YAW + HALF],
                 'cane_covers_height_m': [0.0, 0.3]}

fig, axs = plt.subplots(1, 3, figsize=(16, 4.8))
ax = axs[0]
ax.fill_between(d, fw_lo, fw_hi, color='#5B6BA8', alpha=0.35, label='forward L/R sensors (+/-15 deg beam)')
ax.fill_between(d, head_lo, np.minimum(head_hi, 2.4), color='#8CC63F', alpha=0.45, label='head-level sensor (+25 deg)')
ax.plot([0, D0], [H, 0], color='#B3261E', lw=2, label='LiDAR beam (-35 deg)')
ax.axhspan(0, 0.3, color='grey', alpha=0.15, label='white cane zone (ground)')
ax.axhline(1.75, color='k', ls=':', lw=1)
ax.text(2.2, 1.78, 'head of a 1.75 m adult', fontsize=8)
ax.plot([0], [H], 'ks')
ax.set_xlim(0, 3.0); ax.set_ylim(0, 2.4)
ax.set_xlabel('distance ahead (m)'); ax.set_ylabel('height (m)')
ax.set_title('Side view: what each sensor covers (calculated)', fontsize=10)
ax.legend(fontsize=7, loc='upper left')
ax = axs[1]
for yaw, col, lab in ((YAW, '#25325F', 'left sensor'), (-YAW, '#5B6BA8', 'right sensor')):
    a1, a2 = np.radians(90 + yaw - HALF), np.radians(90 + yaw + HALF)
    ang = np.linspace(a1, a2, 30)
    xs = np.concatenate([[0], 3 * np.cos(ang), [0]])
    ys = np.concatenate([[0], 3 * np.sin(ang), [0]])
    ax.fill(xs, ys, color=col, alpha=0.35, label=lab)
ax.plot([0], [0], 'ks')
ax.set_aspect('equal'); ax.set_xlim(-2, 2); ax.set_ylim(0, 3.1)
ax.set_xlabel('left (-) / right (+) (m)'); ax.set_ylabel('ahead (m)')
ax.set_title('Top view: left / right beams (+/-15 deg yaw)', fontsize=10)
ax.legend(fontsize=8)
ax = axs[2]
ax.plot(tt[:600], (rng_meas - base_fixed)[:600] * 100, color='#B3261E', lw=1, label='fixed baseline')
ax.plot(tt[:600], (rng_meas - base_comp)[:600] * 100, color='#3F6E12', lw=1, label='IMU-compensated baseline')
ax.axhline(DROP_CM * 100, color='k', ls='--', lw=1, label='15 cm drop-off threshold')
ax.set_xlabel('time (s)'); ax.set_ylabel('LiDAR range - baseline (cm)')
ax.set_title('Walking sway on a flat floor (simulated)', fontsize=10)
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(HERE, 'sensor_geometry.png'), dpi=150)
json.dump(R, open(os.path.join(HERE, 'sensor_geometry.json'), 'w'), indent=1)
print(json.dumps(R, indent=1))
