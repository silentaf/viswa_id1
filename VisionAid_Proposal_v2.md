# VisionAid: Design Specification v2

**Vishwakarma Awards 2026–27 · Stage 2 (Design Development)**
**Team SVNIT:** Jayant Kumawat (lead), Sneha Ahir, Aman Gupta · SVNIT Surat · Mentor institute: IIT Indore
**Track:** Assistive Solutions & Inclusive Living · **Date:** 8 Oct 2026 · **Status:** design stage, nothing fabricated yet

> **How to read the numbers in this document:**
> - **Target** = a design goal.
> - **Simulated** = from our own simulation files.
> - **Calculated** = from datasheets and arithmetic.
> - **Cited** = from a published source.
>
> Nothing here is a hardware measurement. Hardware testing is planned for Stage 3.

---

## 1. Title

**VisionAid**: a chest-worn, fully offline navigation aid that adds head-level-obstacle and drop-off warnings to the white cane. An FPGA "safety island" guarantees the alert path even if the AI computer fails, and an on-device AI layer names the hazard and reads text aloud.

## 2. Problem

- In 2020, about **43.3 million people were blind** and **295 million had moderate or severe vision impairment** worldwide *(cited: Bourne et al., Lancet Global Health 2021)*.
- In India, blindness affects **1.99 % of people aged 50 and over** *(cited: National Blindness & Visual Impairment Survey 2015–19)*.
- The white cane only detects what it touches at ground level. **Head-level collisions and falls** are the injuries that blind travellers report most often *(cited: Manduchi & Kurniawan, 2011, a survey of 300+ people)*.

**What exists today, and the gap:**

| Product | What it does | Price | Gap |
|---|---|---|---|
| **SmartCane (IIT Delhi / Assistech)** | Ultrasonic, above-knee obstacles, vibration on the cane handle | ≈ ₹3,500 | No drop-off detection, does not identify objects, no text reading |
| OrCam MyEye 3 Pro | Camera on glasses: reading, faces, products | ≈ US$3,700–4,490 | Not a mobility aid; expensive |
| Envision Glasses | AI reading and scene description | ≈ US$1,899–3,499 | Not a mobility aid; expensive; some features need the cloud |
| Phone apps (Lookout, RBI MANI, Seeing AI) | Reading and identification | free | Need a hand and a pointed phone; no continuous obstacle warning |

Nothing affordable combines head-level and drop-off warnings with a **bounded alert latency**, on-device object naming and text reading, and fully offline operation, in a form that is worn rather than held.

## 3. Solution (v2)

**Use model:** VisionAid **complements the cane; it does not replace it.** The cane covers the ground at the user's feet. VisionAid covers:
1. obstacles from **waist to head height**, 0.3–3 m ahead (target);
2. **drop-offs** (steps down, kerbs, pits) about 1 m ahead (target);
3. **naming** what is ahead ("person", "car", "dog") and **reading** text when a button is pressed.

### Architecture: two independent paths

```
 3 ultrasonic (left, right, head) ┐                     ┌─► left / right vibration motors (chest straps)
 TF-Luna LiDAR (floor, -35°)      ├─► FPGA SAFETY ISLAND ┤
 buttons                          ┘   Tang Nano 9K       └─► buzzer ("check device")
                                        ▲ UART + heartbeat
 Camera Module 3 ─► RASPBERRY PI 5 (AI path): YOLO-nano objects · OCR · text-to-speech ─► Bluetooth bone-conduction headset
                    power: BIS-certified USB-C power bank
```

- **Safety island (FPGA):**
  - times the three ultrasonic echoes in parallel;
  - reads the LiDAR;
  - classifies distance into zones (info < 3 m, warn < 2 m, urgent < 1 m);
  - drives the motors directly.
  
  **The Pi can tune thresholds but cannot switch alerts off.** If the Pi stops its heartbeat, alerts continue and an "AI offline" chirp sounds.
- **AI path (Pi 5):**
  - names objects (COCO-pretrained YOLO-nano; India-specific classes such as auto-rickshaw, cow, pothole and open drain in Stage 3);
  - OCR on a button press;
  - speech in English and Hindi, with Gujarati as a goal.
- **Feedback:**
  - Haptics are the *safety* channel: wired, so no radio latency. The pulse rate encodes the distance.
  - Speech is the *information* channel, through a bone-conduction headset so the ears stay open to traffic.

## 4. What changed from Stage 1 (and why)

| Stage 1 | v2 | Reason |
|---|---|---|
| PYNQ-Z2 does everything | Pi 5 (AI) + Tang Nano 9K FPGA (safety island) | The Zynq-7020's dual Cortex-A9 cores are too slow for detection plus OCR. The PYNQ-Z2 does not fit the ₹30k grant. Splitting the work isolates faults. |
| "<10 ms" reflex, "<100 ms" on the cover | Per-stage latency specs | An echo from 3 m takes ≈ 17.5 ms to return, so "<10 ms end-to-end" is physically impossible. We specify the part we control: echo → motor. |
| FPGA image pre-processing | FPGA = timing, decision and actuation only | That is where determinism matters. |
| Downward ultrasonic | Downward TF-Luna LiDAR + IMU | A narrow beam gives a clean floor-distance signal. |
| Wristband with 2 motors | Left/right motors on the harness straps | Two motors on one wrist are hard to tell apart. A user test is planned for Stage 3. |
| Custom bone-conduction driver | Bluetooth bone-conduction headset | The Pi 5 has no analog audio. |
| "<₹5,500 BOM" | Prototype BOM ≈ ₹24–31k (quotes + estimates); production estimate in Stage 3 | ₹5,500 was impossible with the Stage 1 hardware. |
| "250M+", "₹4–6 lakh" competitors | Updated cited figures; SmartCane named | Accuracy, and an honest public-search disclosure. |
| 10–15 pilot users | Stage 3, after ethics approval, with an O&M instructor | Honest scope. |
| Mic, caregiver app | Future scope | Not core to safety. |

## 5. Target specifications

| Parameter | Target | Design evidence so far |
|---|---|---|
| Obstacle range (waist–head) | 0.3–3.0 m | Sensor class rating; housings angled: head +25°, sides ±15° (CAD) |
| Distance resolution | ≤ ±5 cm to 2 m | 1 µs echo timing = 0.17 mm resolution *(simulated: 1500 mm → 1499 mm)* |
| **Alert latency (echo edge → motor on)** | ≤ 1 ms | **Simulated: 136–214 ns (4–6 clock cycles at 27 MHz)** |
| Update period per direction | ≤ 100 ms | 3 sequenced 33 ms slots = 99 ms *(by design; simulated)* |
| Drop-off warning | ≥ 1.0 m ahead of the step | LiDAR at −35° from chest height; *simulated: alert 22 ms after the floor reading changes* |
| AI offline detection | ≤ 1 s, alerts unaffected | *Simulated: 666 ms; obstacle alert still worked with the Pi offline* |
| Object name spoken | ≤ 1.0 s | Stage 3 measurement |
| OCR read-aloud | ≤ 3 s | Stage 3 measurement |
| Runtime | ≥ 4 h | *Calculated: 7.3 W average → 4.3 h on a 10,000 mAh bank* (to be measured) |
| Pod mass | ≤ 250 g | *Estimated: ≈ 140 g of PETG for the enclosure (solid volume 118 cm³) plus electronics*. Likely over the target; a v2 weight reduction is planned. |

## 6. Hardware (see `design/` for every file)

- **Carrier PCB** (KiCad 9):
  - Pi 5 outline, 85 × 56 mm, 2 layers;
  - FPGA + sensor connectors + MOSFET motor drivers + 3.3 V regulator + 500 mA PTC + test points;
  - **ERC 0 · DRC 0 · 0 unconnected · schematic ↔ PCB parity 0**; Gerbers generated.
- **FPGA logic** (Verilog):
  - **ALL TESTS PASSED** in simulation;
  - **≈ 26 % of the LUTs and 9 % of the flip-flops** of the GW1NR-9 *(Yosys synthesis estimate)*.
- **Enclosure** (FreeCAD, parametric):
  - 112 × 84 × 44 mm PETG shell, angled sensor housings, GoPro-style mount, vents;
  - **0 mm³ interference** with the electronics *(CAD check)*.
- **Mount FEA** (FreeCAD FEM + CalculiX, PETG; *simulated*):
  - 50 N down and 20 N sideways, worst **factor of safety 8.7** (requirement ≥ 3).
  - The convergence study showed a **stress singularity at the sharp finger roots in v1**; v2 adds **1.5 mm root fillets** and converges.
  - Details: `design/cad/outputs/fea/README.md`.

## 7. Safety

- **The alert path is independent of the AI computer**, with a watchdog.
- Sensor faults produce a distinct alarm.
- Quiet mode can only silence the "info" level.
- **No loose lithium cells:** power comes from a BIS-certified power bank.
- A PTC fuse protects the Pi.
- Standards considered in the design (not certification): IEC 62368-1 / IS 13252, IEC 62133-2 / IS 16046, IEC 60529 (IP54 target), ISO 10993 (skin contact), ISO 9999.

## 8. Plan to Stage 3 (4 months)

| Month | Work |
|---|---|
| Nov | Parts and PCB order; FPGA + sensor bring-up; bench tests of range, latency (logic analyser at TP4/TP5) and power |
| Dec | Integration; enclosure print and fit; thermal test; India-class dataset |
| Jan | Ethics approval → supervised trials (sighted blindfolded first, then blind volunteers with an O&M instructor) |
| Feb | Fixes; field-test-ready unit |

## References

1. Bourne R. et al., *Lancet Global Health* 9(2):e130–e143, 2021.
2. National Blindness & Visual Impairment Survey India 2015–19, AIIMS / MoHFW.
3. Manduchi R., Kurniawan S., *Insight* 4(2), 2011 (UCSC-SOE-10-24).
4. SmartCane, IIT Delhi / Assistech (product information).
5. OrCam MyEye 3 Pro and Envision Glasses (vendor pricing pages, 2026).
6. Sipeed Tang Nano 9K wiki and pin map; Benewake TF-Luna datasheet; Raspberry Pi 5 product brief.
