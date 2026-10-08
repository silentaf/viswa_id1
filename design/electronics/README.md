# VisionAid Carrier Board: Electronics Design (v0.1, design stage)

**Status (8 Oct 2026):**
- **Designed and verified in KiCad 9:** ERC 0 violations; DRC 0 violations; 0 unconnected; schematic ↔ PCB parity 0 issues.
- **Not fabricated or tested yet.** Every number below is a design value or target, not a measurement.

## What this board does

It is the **interface and safety-island board** that sits on top of the Raspberry Pi 5 in the chest pod.

| Block | Parts | Why it is designed this way |
|---|---|---|
| **FPGA safety island** | U1 Sipeed Tang Nano 9K (GW1NR-9, 27 MHz) on 2 × 24 sockets | Times all 3 ultrasonic echoes **in parallel** and drives the motors **without the Pi**. If Linux or the AI crashes, obstacle alerts continue (watchdog on `PI_HB`). Only **3.3 V-bank pins** on the left header are used; the right-header pins marked `_1V8` are on a 1.8 V bank and are unused. |
| **Pi link** | J1 2 × 20 header → 40-way IDC ribbon → Pi GPIO | UART (GPIO14/15) for status and config, GPIO17 = heartbeat to the FPGA, GPIO27 = fault from the FPGA, I²C (GPIO2/3) for the IMU. |
| **Power** | F1 500 mA PTC, U2 AMS1117-3.3, C1–C5, D1 SS14 | 5 V comes from the Pi header (the Pi is powered by a BIS-certified USB-C power bank). The PTC protects the Pi's 5 V rail if this board shorts. A separate 3.3 V regulator means the Pi's 3.3 V pins (1, 17) are deliberately **not** used. D1 stops back-feed when the Tang Nano's own USB-C is plugged in for programming. |
| **Sensors** | J2–J4 RCWL-1601 ultrasonic (left, right, head-level), J5 TF-Luna LiDAR (drop-offs), J8 MPU-6050 IMU | RCWL-1601 works at 3.3 V, so there is no level shifting. The TF-Luna takes 5 V but has 3.3 V UART logic. 100 Ω series resistors (R7–R14) limit fault current and ringing on the cables. |
| **Haptics and alarm** | Q1–Q3 AO3400A, R1–R6, D2–D4, J6/J7 coin motors, BZ1 buzzer | Logic-level MOSFETs (V_GS(th) ≤ 1.45 V) are switched directly by the FPGA's 3.3 V PWM. 100 kΩ pull-downs keep the motors off while the FPGA boots. Flyback diodes protect the MOSFETs. The motors (3 V coin ERMs) run from +3V3. |
| **Buttons** | J9 (READ = OCR, MODE, QUIET), R15–R17 10 k pull-ups, C7–C9 100 nF | 10 k × 100 nF ≈ 1 ms RC filter, plus digital debounce in the FPGA. |
| **Test points** | TP1–TP6 (+5V, +3V3, GND, US_L_ECHO, MOT_L_G, PI_HB) | For the Stage 3 logic-analyser measurement of **echo → motor-on latency** and for power checks. |

## FPGA pin map (Tang Nano 9K, 3.3 V banks only)

| Signal | FPGA pin | Signal | FPGA pin |
|---|---|---|---|
| US_L_TRIG / ECHO | 25 / 26 | PI_TXD (FPGA RX) / PI_RXD (FPGA TX) | 40 / 35 |
| US_R_TRIG / ECHO | 27 / 28 | PI_HB (heartbeat in) | 41 |
| US_H_TRIG / ECHO | 29 / 30 | FPGA_FAULT_N (out to Pi) | 42 |
| LIDAR_TX / LIDAR_RX | 33 / 34 | MOT_L_PWM / MOT_R_PWM / BUZZ_EN | 51 / 53 / 54 |
| Clock 27 MHz (on module) | 52 | BTN_READ / MODE / QUIET | 55 / 56 / 57 |

Source: the Sipeed Tang Nano 9K official pin map (wiki.sipeed.com).

## PCB

- **Outline:** 85 × 56 mm, 2 layers, 1.6 mm FR-4. It has the **same outline and M2.5 mounting holes as the Raspberry Pi 5**, and is stacked above the Pi on **20 mm standoffs**. Those clear the Pi's USB/Ethernet jacks and the active cooler; a standard HAT would hit them.
- **Layout:**
  - The Tang Nano sits on 8.5 mm sockets, with its USB-C flush at the right edge for programming.
  - Low-profile SMD parts sit **under** the module, between the socket rows.
  - Sensor connectors are on the bottom edge (cables exit downward towards the sensor windows). Buttons, IMU and motor connectors are on the left edge.
- **Track rules:**
  - 5 V and GND: 0.5 mm.
  - +3V3: 0.3 mm (about 250 mA total load).
  - Signals: 0.25 mm (minimum 0.15 mm, where the router necks down at pads).
  - Clearance 0.2 mm; vias 0.6/0.3 mm.
  - GND pours on both layers.
- **Routing:** FreeRouting v2.5.0 completed 100 %, with 0 violations.

## How the files are produced (reproducible)

All files are generated from scripts so every design decision is written down:

```
tools/kicad.sh python design/electronics/scripts/gen_library.py    # Tang Nano symbol + footprint
python3 design/electronics/scripts/gen_schematic.py                # schematic (.kicad_sch)
tools/kicad.sh kicad-cli sch export netlist -o design/electronics/VisionAid_Carrier.net design/electronics/VisionAid_Carrier.kicad_sch
tools/kicad.sh python design/electronics/scripts/gen_pcb.py        # outline, placement, nets
tools/kicad.sh python design/electronics/scripts/route_pcb.py      # FreeRouting + GND pours
```

Open the project in the KiCad GUI with `tools/kicad.sh kicad design/electronics/VisionAid_Carrier.kicad_pro`.

## Outputs (`outputs/`)

| File | Contents |
|---|---|
| `VisionAid_Carrier_schematic.pdf` / `.svg` | Schematic |
| `VisionAid_Carrier_pcb_top.pdf` / `_bottom.pdf` | Copper and silkscreen plots |
| `gerbers/` | Fabrication files (Gerber X2 + Excellon drill + drill map) |
| `VisionAid_Carrier_BOM.csv` | Bill of materials (on-board parts) |
| `VisionAid_Carrier_pos.csv` | Pick-and-place positions |
| `VisionAid_Carrier.step` | 3D model for the enclosure CAD |
| `pcb_3d_top.png` / `pcb_3d_iso.png` | Board renders with component 3D models (Tang Nano 9K: simplified model in `3d/`) |
| `ERC_report.txt` / `DRC_report.txt` | Verification reports |

## Not on the PCB BOM (buy separately in Stage 3)

- 2 × 1×24 female headers (2.54 mm, 8.5 mm tall) for the Tang Nano.
- 40-way IDC ribbon cable with 2 sockets (≈ 10 cm).
- 4 × M2.5 × 20 mm standoffs and screws.
- JST-XH housings and crimps.
- The sensors, motors and buttons themselves (see the implementation plan, §5).

## Open items before fabrication (Stage 3)

1. **Measure the Tang Nano 9K header row spacing with calipers.** The footprint uses 22.86 mm (0.9″), taken from a community footprint, not an official drawing.
2. Confirm the ribbon length and the standoff height against the enclosure CAD.
3. Check the AMS1117 dropout and temperature at the real load: 5 V → 3.3 V at ~250 mA ≈ 0.43 W in SOT-223.
4. Review the board in the KiCad GUI: tidy silkscreen, then re-run DRC.
