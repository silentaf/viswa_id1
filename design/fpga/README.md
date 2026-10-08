# VisionAid FPGA Safety Island (Tang Nano 9K, Verilog)

**Status (8 Oct 2026):**
- Simulation only, so all numbers here are **simulated**, not hardware measurements.
- `run_sim.sh` reports **ALL TESTS PASSED**.

## What it does

| Module | File | Function |
|---|---|---|
| `va_ultrasonic` | `rtl/va_ultrasonic.v` | Fires 3 RCWL-1601 sensors **one at a time** (no crosstalk), 33 ms slots (99 ms per direction). Times the echo in µs and converts it to mm with `(t × 11239) >> 16` = t × 0.1715. Flags a dead or unplugged sensor after 3 missed responses. |
| `va_zone` | `rtl/va_alerts.v` | Distance → zone (info < 3 m, warn < 2 m, urgent < 1 m). Escalates **immediately**; de-escalates with 50 mm hysteresis. |
| `va_haptic` | `rtl/va_alerts.v` | Pulse rate encodes distance: urgent = continuous, warn = 5 Hz, info = 2 Hz. The pattern restarts in its ON phase when the zone escalates, so the motor turns on in the same clock cycle. PWM limits the 3 V motors. |
| `va_lidar` | `rtl/va_alerts.v` | TF-Luna 9-byte frame parser (checksum + signal-strength check). Drop-off = floor reading ≥ 15 cm beyond the calibrated baseline for 3 frames. |
| `va_watchdog` | `rtl/va_alerts.v` | No Pi heartbeat edge for 750 ms → "AI offline" chirp. **Alerts keep working.** |
| `va_pilink` | `rtl/va_pilink.v` | 115200-baud link: status frame to the Pi every 20 ms; commands from the Pi with **clamped** limits (the Pi cannot disable alerts). |
| `visionaid_top` | `rtl/visionaid_top.v` | Ties the blocks together: synchronisers, debouncing, quiet mode (silences only the "info" level), buzzer patterns, LEDs. |

## Simulated results (`sim/sim_results.log`)

| Check | Result |
|---|---|
| Distance 1500 / 2500 mm | 1499 / 2499 mm |
| **Echo edge → motor on** | **max 214 ns = 5.8 clock cycles** (4 events; target ≤ 1 ms) |
| Status frames to the Pi | 45 OK, 0 bad |
| Drop-off alert | 22.3 ms after the floor reading changed |
| Pi heartbeat lost | AI offline flagged at 666 ms; the obstacle alert still worked |
| Unplugged sensor | fault flag + FAULT_N low |

Figures: `sim/waveform_overview.png`, `sim/waveform_latency_zoom.png` (made by `plot_waveforms.py`).

## Resource estimate (Yosys `synth_gowin`, before place-and-route)

About **2,255 LUT4 equivalents (26 % of 8,640)** and **568 flip-flops (9 % of 6,480)**. See `synth/yosys_utilization.txt`. Confirm the real figures with Gowin EDA when the board arrives.

## Run

```
./run_sim.sh                                                   # ~10 min: simulates 3.9 s of operation
../../tools/eda.sh gtkwave sim/visionaid.vcd                   # waveforms (screenshot for the PPT)
python3 plot_waveforms.py                                      # PNG figures
```

Pin constraints: `constraints/visionaid_tangnano9k.cst`. They match the carrier-board schematic.
