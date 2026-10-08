"""Plot waveforms from sim/visionaid.vcd (simulation, not hardware):
  1. a 120 ms window: ultrasonic triggers, echo pulses, left-motor drive, left zone
  2. a 1.2 us zoom at the moment an obstacle enters the urgent zone: echo edge -> motor on
Run: python3 design/fpga/plot_waveforms.py
"""
import os
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
VCD = os.path.join(HERE, 'sim', 'visionaid.vcd')
WANT = {('tb_visionaid', 'trig'), ('tb_visionaid', 'echo'), ('tb_visionaid', 'mot_l'), ('tb_visionaid', 'clk'),
        ('dut', 'zl'), ('dut', 'd0')}


def read_vcd(path):
    ids, scope, t = {}, [], 0
    sig = {}
    with open(path) as f:
        for line in f:
            if line.startswith('$scope'):
                scope.append(line.split()[2])
            elif line.startswith('$upscope'):
                scope.pop()
            elif line.startswith('$var'):
                p = line.split()
                key = (scope[-1], p[4])
                if key in WANT and key not in [v for v in ids.values()]:
                    ids[p[3]] = key
                    sig[key] = []
            elif line.startswith('$enddefinitions'):
                break
        for line in f:
            if line[0] == '#':
                t = int(line[1:])
            elif line[0] in '01xz' and line[1:].strip() in ids:
                sig[ids[line[1:].strip()]].append((t, line[0]))
            elif line[0] == 'b':
                v, i = line[1:].split()
                if i in ids:
                    sig[ids[i]].append((t, v))
    return sig


def to_int(v):
    try:
        return int(v, 2)
    except ValueError:
        return 0


def step(series, t0, t1, bit=None, scale=1.0):
    xs, ys, last = [], [], None
    for t, v in series:
        val = to_int(v) if bit is None else (to_int(v) >> bit) & 1
        if t < t0:
            last = val
            continue
        if t > t1:
            break
        if last is not None:
            xs.append(t)
            ys.append(last)
        xs.append(t)
        ys.append(val)
        last = val
    if last is not None:
        xs.append(t1)
        ys.append(last)
    return [(x - t0) * scale for x in xs], ys


sig = read_vcd(VCD)
echo = sig[('tb_visionaid', 'echo')]
times = [t for t, _ in echo]
t_start = min(times)
# find the urgent-zone entry inside the dumped window
zl = sig[('dut', 'zl')]
t_urg = next(t for t, v in zl if to_int(v) == 3 and t > t_start)
mot = sig[('tb_visionaid', 'mot_l')]
t_mot = next(t for t, v in mot if v == '1' and t >= t_urg)
t_fall = max(t for t, v in echo if t <= t_urg and (to_int(v) & 1) == 0)

# ---- figure 1: 120 ms overview
t_end = max(t for t, _ in sig[('tb_visionaid', 'clk')])
t0, t1 = t_start, min(t_start + 120_000_000_000, t_end)   # ps; VCD only covers a 100 ms window
fig, axs = plt.subplots(5, 1, figsize=(12, 7), sharex=True)
rows = [('TRIG L', sig[('tb_visionaid', 'trig')], 0), ('TRIG R', sig[('tb_visionaid', 'trig')], 1),
        ('ECHO L', echo, 0), ('ECHO R', echo, 1), ('MOTOR L', mot, None)]
for ax, (name, s, b) in zip(axs, rows):
    x, y = step(s, t0, t1, b, 1e-9)
    ax.plot(x, y, drawstyle='steps-post', lw=1.2, color='#1f5fa8' if 'MOTOR' not in name else '#c0392b')
    ax.set_ylabel(name, rotation=0, ha='right', va='center', fontsize=9)
    ax.set_yticks([])
    ax.set_ylim(-0.2, 1.2)
axs[-1].set_xlabel('time (ms) - simulated, 27 MHz clock')
fig.suptitle('VisionAid FPGA safety island (simulation, 100 ms recorded window): sequenced pings; obstacle at 0.75 m -> left motor ON', fontsize=11)
fig.tight_layout()
fig.savefig(os.path.join(HERE, 'sim', 'waveform_overview.png'), dpi=150)

# ---- figure 2: latency zoom
t0, t1 = t_fall - 200_000, t_fall + 1_000_000            # ps window: -0.2 us .. +1.0 us
fig, axs = plt.subplots(4, 1, figsize=(12, 5.5), sharex=True)
rows = [('CLK 27 MHz', sig[('tb_visionaid', 'clk')], None), ('ECHO L', echo, 0),
        ('ZONE L (3 = urgent)', zl, None), ('MOTOR L', mot, None)]
for ax, (name, s, b) in zip(axs, rows):
    x, y = step(s, t0, t1, b, 1e-3)                       # ns
    ax.plot(x, y, drawstyle='steps-post', lw=1.2)
    ax.set_ylabel(name, rotation=0, ha='right', va='center', fontsize=9)
    ax.set_yticks([])
lat_ns = (t_mot - t_fall) / 1000
for ax in axs:
    ax.axvline((t_fall - t0) / 1000, color='grey', ls='--', lw=0.8)
    ax.axvline((t_mot - t0) / 1000, color='red', ls='--', lw=0.8)
axs[-1].set_xlabel('time (ns)')
fig.suptitle('Echo falling edge -> motor ON: %.0f ns (%.1f clock cycles) - simulated' % (lat_ns, lat_ns / 37.037),
             fontsize=11)
fig.tight_layout()
fig.savefig(os.path.join(HERE, 'sim', 'waveform_latency_zoom.png'), dpi=150)
print('latency in plotted event: %.1f ns' % lat_ns)
