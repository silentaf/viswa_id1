# VisionAid: Session Notes (where we are, as of 9 Oct 2026)

**Goal:** Vishwakarma Awards 2026–27 **Stage 2** submission. This is a design-specification PPT on the official template, submitted via the Design Stage Form.
- **Deadline:** 25 Oct 2026, 23:59.
- **Our own target:** submit on 24 Oct.

**Repo:** https://github.com/silentaf/viswa_id1. Push after every change.

## Status right now

**9 Oct: full numbers audit done.** Every deck figure was re-checked against the logs/reports, the citations against their sources, and prices against live listings. Fixes: BOM ₹33,945 (₹3,945 over; Pi 5 / Tang Nano / TF-Luna out of stock), runtime 4.3 h (assumes ~50 % AI duty), latency 136 ns waveform vs ≤ 214 ns testbench bound, Manduchi survey stats, OrCam US$4,250, detection-chart labels. New evidence files: `design/cad/outputs/interference_check_44mm.txt`, `design/electronics/outputs/DRC_ERC_parity_recheck.txt`, `design/pi/results/ocr_word_order_check.txt`. **Next:** user fills IDs + photos, then exports the PDF.

### Done

| Area | Files | Key result |
|---|---|---|
| Plan + corrected proposal | `IMPLEMENTATION_PLAN.md`, `VisionAid_Proposal_v2.md` | 15 changes from Stage 1, with reasons |
| Electronics (KiCad 9) | `design/electronics/` | Carrier board 85×56 mm, ERC 0, DRC 0, parity 0, Gerbers, STEP; Tang Nano 9K 3D model in `3d/` |
| FPGA (Verilog) | `design/fpga/` | Simulation **all pass**; echo → motor 136 ns (waveform), ≤ 214 ns (testbench bound); **real P&R on GW1NR-9: Fmax 67.9 MHz, LUT 17 %, FF 8 %, bitstream `impl/visionaid.fs`**; Vivado xc7z020: WNS +30.2 ns |
| FPGA ↔ Pi cross-check | `design/fpga/tb`, `design/pi` | Python-built command accepted by the Verilog FPGA; Python decodes 192/192 frames |
| Pi software (AI path) | `design/pi/` | YOLOv5n 28 ms/frame, mAP50 0.41 (person: precision 0.85, recall 0.54 overall, 0.82 for people > 96 px); OCR 1.9 % character error; Piper TTS in English and Hindi; end to end 211 ms. **All measured on the laptop (i7-14650HX), NOT a Pi 5.** Event-triggered AI; IMU floor baseline. |
| Analyses | `design/analysis/` | Drop-off warned 1.86 m ahead; sway: 25 false alarms → 0 with IMU; waist-height gap under 1 m (fix: forward sensors −10°, CAD v2); battery 3.1 / **4.3** (~50 % AI duty, assumed) / 7.2 h |
| CAD (FreeCAD) | `design/cad/` | Parametric pod 112×84×48 mm; 0 mm³ interference; FEA v2 worst safety factor 8.7 (all runs ≥ 8.6); 1.5 mm finger-root fillet |
| BOM | `design/bom/VisionAid_BOM_Power.xlsx` | ₹33,945 at 9 Oct quotes, **₹3,945 over the grant**. Pi 5 must be ≤ ₹10,555 to fit; re-quote at order time. |
| Screenshots | `docs/screenshots/` | FreeCAD tree/sketch, KiCad DRC/ERC/3D, GTKWave |
| **PPT** | `ppt/VisionAid_Stage2_Design_Deck.pptx` (20 slides, editable), built by `node ppt/build_deck.js` | Validated and checked visually |

### Pending from the user

1. Application ID + Team ID (slide 1, shown in red).
2. Photos: ID-badge work photo + faculty-guide review (slide 14 placeholders).
3. Their own edits in KiCad/FreeCAD + regular commits until 24 Oct (authenticity).
4. PPT feedback, then export the final PDF (the user does this at the end).

### Open technical items (Stage 3, not now)

- Pi 5 real timings, power and thermal.
- Measure the Tang Nano header spacing with calipers before ordering the PCB.
- CAD v2: forward sensors −10°, weight reduction.
- RISC-V (PicoRV32) + tiny SNN: research extension only.

## How to run things (no root needed; tools live in `tools/`, which is not in git)

- **KiCad:** `tools/kicad.sh kicad design/electronics/VisionAid_Carrier.kicad_pro`. libkicommon is patched so 3D plugins load via `/tmp/vakicad_lib_x86_64gn`.
- **FreeCAD:** `tools/freecad.sh gui|cmd|offscreen <script>`.
- **EDA:** `tools/eda.sh iverilog|vvp|gtkwave|yosys|nextpnr-himbaechel-gowin`.
- **FPGA:**
  - `design/fpga/run_sim.sh` (~10 min)
  - `design/fpga/run_impl.sh` (P&R + bitstream)
  - Vivado: `/opt/Xilinx/2026.1/2026.1/Vivado/bin/vivado -mode batch -source design/fpga/vivado/vivado_crosscheck.tcl`
- **Pi software:**
  - `tools/pi-env/bin/python design/pi/bench.py`
  - `eval_detection.py`
  - `python -m visionaid_pi.app --replay ...`
  - Models live in `/tmp/visionaid-tools/models` (= `tools/models`).
- **Deck:** `node ppt/build_deck.js` (pptxgenjs in `tools/node`). Validate with the pptx skill's `validate.py`, using `tools/freecad-env/bin/python`.
- **Virtual display for GUI screenshots:** `tools/vshot.sh start|grab|xdo|windows` (Xvfb :99).

## User preferences

- Strictly no shortcuts and no faked numbers; label everything as simulated, calculated, measured or cited.
- Work only inside this `submission` folder.
- Keep the PPT editable (PPTX); the PDF comes at the end.
- Keep GitHub updated.
