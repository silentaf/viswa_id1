# VisionAid Raspberry Pi Software (AI path): Proof of Concept

**What this is:**
- The Python application that will run on the Raspberry Pi 5.
- It has been **run and measured on the development laptop** (Intel i7-14650HX, ONNX Runtime limited to 4 threads to match the Pi 5's 4 cores).
- **Speeds are laptop numbers, not Pi 5 numbers.** Expect the Pi 5 to be slower; it will be measured in Stage 3.
- **Accuracy numbers do not depend on the computer.**

| Module | File | Function |
|---|---|---|
| Protocol | `visionaid_pi/protocol.py` | FPGA ↔ Pi UART frames, matching `rtl/va_pilink.v` byte for byte |
| Floor baseline | `visionaid_pi/floor.py` | IMU pitch → expected LiDAR floor range → command to the FPGA (prevents walking-sway false alarms) |
| Vision | `visionaid_pi/vision.py` | YOLOv5n (COCO) on ONNX Runtime; only mobility hazards are named; left / ahead / right from box position |
| Speech | `visionaid_pi/speech.py` | RapidOCR (PP-OCR ONNX) text reading; Piper offline neural TTS (English, Hindi) |
| Alerts | `visionaid_pi/alerts.py` | Priorities: safety > hazard name + FPGA distance > text. The Pi never drives the motors. |
| App | `visionaid_pi/app.py` | Main loop: **event-triggered AI** (runs detection only when the FPGA reports < 3 m), heartbeat, replay mode |

## Measured results (`results/bench_results.json`, `results/detection_accuracy.json`)

| Check | Result | How |
|---|---|---|
| **FPGA ↔ Pi protocol** | **192 frames decoded, 0 bad**; drop-off and fault flags correct; **the Python-built command was accepted by the Verilog FPGA** | Bytes recorded from the Verilog testbench (`../fpga/sim/fpga_to_pi_bytes.hex`); the command bytes come from `protocol.build_command` |
| Detection speed | 28 ms per 640×640 frame (p95 29 ms) | 24 COCO images, laptop |
| **Detection accuracy** | mAP50 **0.41** over 12 hazard classes; **person: AP50 0.65, precision 0.85 and recall 0.54 overall; recall 0.82 for people larger than 96 × 96 px in the image**; weak on bench and truck | 200 COCO val2017 images vs human labels, IoU ≥ 0.5 |
| **OCR accuracy** | **1.9 %** character error (clean), **1.8 %** (blur + tilt + noise); 72–75 % of lines exactly right | 64 rendered labels with known text (synthetic bench test) |
| OCR speed | 1.2–1.4 s per label | laptop |
| TTS | English 150–270 ms, Hindi 85–150 ms to synthesise 1.6–3 s of speech | Piper, laptop |
| **End to end** | camera image → detection → alert → speech WAV ready: **211 ms** mean | laptop |
| Full loop replay | FPGA simulation bytes + images → "Step down ahead. Stop.", "Check device: head sensor.", "person, left, 1.6 metres" | `results/replay/` (log + WAV files) |

**A bug found by the tests and fixed:** OCR word order. Words on one line were sorted by box top, so "BUS STOP" came out as "STOP BUS". Character error went from 25.8 % to 1.9 % after the fix.

**Limitations (honest):**
- Synthetic OCR labels are cleaner than real photos.
- COCO has no Indian classes (auto-rickshaw, open drain).
- Hindi OCR needs a Devanagari model.

All three are Stage 3 work.

## Run

```
tools/pi-env/bin/python design/pi/bench.py               # benchmark
tools/pi-env/bin/python design/pi/eval_detection.py      # accuracy vs COCO
cd design/pi && ../../tools/pi-env/bin/python -m visionaid_pi.app --replay ../fpga/sim/fpga_to_pi_bytes.hex --images test_data/coco
```

**Test images:** `test_data/coco` is COCO val2017 (Flickr, Creative Commons; cocodataset.org).
