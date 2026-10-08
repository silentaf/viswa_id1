# Design Analyses (calculation and simulation, not hardware measurements)

## `sensor_geometry.py` → `sensor_geometry.png`, `sensor_geometry.json`

**Assumptions:**
- pod height 1.30 m (adult);
- ultrasonic half-beam angle 15°;
- angles taken from the CAD: head sensor +25°, sides ±15°, LiDAR −35°.

**Drop-off warning:**
- The LiDAR meets the floor **1.86 m ahead**.
- A 15 cm step raises the range by 26 cm, so the step is flagged when its edge is about **1.86 m ahead** (≈ 1.5 s at 1.2 m/s).
- **The ≥ 1 m target is met (calculated).**

**Walking sway (simulated):**
- With ±3° chest sway, the floor range swings by up to 30 cm.
- **With a fixed floor baseline there were 25 false alarms in 20 s. With an IMU-compensated baseline there were 0.**
- → Implemented in `design/pi/visionaid_pi/floor.py`. The IMU is required, not optional.

**Coverage gap found:**
- Close to the user (< 1 m ahead), heights **0.3–1.0 m** (waist level) are not covered: the cane covers < 0.3 m and the forward beams reach down to only about 1.0 m there.
- **Fix for CAD v2:** tilt the forward sensors down by 10°.
- Until then, the camera can name such objects but the FPGA reflex path will not catch them.

## `power_range.py` → `power_range.json`

Uses the **published** Pi 5 figures: ≈ 3.0 W idle and ≈ 8.8 W full load (raspberry.tips, 2026). The rest of the system is ≈ 1.3 W (datasheet-level estimates), on a 37 Wh bank at 85 % efficiency.

| Mode | Total | Runtime |
|---|---|---|
| AI running continuously | 10.1 W | **3.1 h** |
| **Event-triggered AI (design choice)** | 7.2 W | **4.4 h** |
| AI mostly idle | 4.3 W | 7.3 h |

**Conclusion:** the ≥ 4 h target needs event-triggered AI. This is implemented in `design/pi/visionaid_pi/app.py`.
