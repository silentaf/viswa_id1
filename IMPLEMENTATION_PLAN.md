# VisionAid: Stage 2 Implementation Plan

**Team SVNIT** · Vishwakarma Awards 2026–27 · Track: Assistive Solutions & Inclusive Living
**Status: FINAL v1.1 · 8 Oct 2026** (scope corrected: Stage 2 = design-specification deck only). Changes only through the change log at the bottom.
**Deadline:** Stage 2 PPT through the Design Stage Form by **25 Oct 2026, 23:59**. Our own target is to **submit on 24 Oct**. Results are announced in October.

## What this round is

> *Design Specification Stage: shortlisted applicants submit a PPT of design specifications. No prototype video required.*

So Stage 2 is **design work, not a working prototype**. We submit:
- a corrected design (v2);
- target specifications;
- CAD + FEA;
- schematics;
- a sourced BOM;
- safety analysis;
- a roadmap.

All of it goes on the official 20-slide template. **Nothing has to be bought for this round.**

The plan has three parts, in order:
**A. Revise the Stage 1 design (v2)**, then **B. Produce the design files (CAD, FEA, KiCad, BOM, FPGA simulation)**, then **C. Build the PPT on the official template**.

---

## 0. Ground rules

1. **Specs are design targets and must be labelled "Target".** We have no measured results this round, and must not imply any. Every literature number carries a citation.
2. **The template's Maker Journey slide is still audited.** It asks for photos with ID badges, screenshots of CAD/KiCad/FEA work, and a Drive/GitHub link whose **file timestamps are checked**. So every design file goes into **one Git repo + one Drive folder from 8–9 Oct**, committed as work happens.
3. **No stock image is presented as our work.** Every borrowed image goes on the "Image Sources" slide.
4. **VisionAid complements the white cane; it does not replace it.**
5. **BOM prices are quotes** (seller link + date checked), not purchases, and are labelled that way.

---

## 1. Calendar

| Dates | Note |
|---|---|
| Thu 8 – Sat 10 Oct | Repo, Proposal v2, start CAD / KiCad / Verilog |
| **Sun 11 – Mon 19 Oct: Navratri** | Evenings light |
| **Tue 20 Oct: Dussehra** | Light day |
| Sat 24 Oct | **Our submission day** |
| Sun 25 Oct | Buffer only (official deadline 23:59) |

🔸 **Team:** add the SVNIT mid-semester exam dates.

---

## 2. Part A: What changes from Stage 1 → v2 (and why)

These become the **"Stage 1 → Stage 2 Engineering Iterations"** slide.

| # | Stage 1 said | v2 decision 🔒 | Why |
|---|---|---|---|
| C1 | PYNQ-Z2 (Zynq-7020) does everything | **Raspberry Pi 5 (AI path) + Sipeed Tang Nano 9K FPGA (safety island)** | The Zynq-7020's dual Cortex-A9 cores are too slow for object detection **and** OCR on CPU, which is what Stage 1 planned; the Pi 5 (4× Cortex-A76) is far faster. The PYNQ-Z2 doesn't fit the ₹30k grant. The split gives **fault independence**: if the AI computer crashes, the FPGA alert path keeps running. |
| C2 | FPGA also does image pre-processing | **FPGA = safety island only**: parallel ultrasonic + LiDAR timing, threshold/priority logic, haptic PWM, watchdog, sensor-fault detection | Routing the camera through the FPGA adds work with no clear gain at this scale; determinism matters most in the alert path. |
| C3 | Cover "<100 ms"; body "<10 ms reflex, <150 ms full" | **Per-stage latency targets** (§4) | Physics: an echo from 3 m takes ≈ 17.5 ms to return (sound ≈ 343 m/s), so "<10 ms end-to-end" is impossible. We specify the part we control: **echo received → motor on**. |
| C4 | "Hands-free unlike a cane"; obstacles "below chest height" | **Cane-complement:** covers **waist-to-head obstacles** and **drop-offs ahead**; the cane stays primary for the ground | Head-level collisions and falls are the documented gap (Manduchi & Kurniawan 2011). This is also the safe positioning. |
| C5 | Downward ultrasonic for drop-offs | **Downward ToF LiDAR (Benewake TF-Luna)** + IMU pitch compensation | The wide ultrasonic beam picks up ground clutter; a narrow LiDAR beam gives a clean distance-to-ground. |
| C6 | Wristband, two motors (L/R) | **L/R motors on the chest-harness straps, wired to the FPGA** | Motors a few cm apart on one wrist are hard to tell apart; wiring keeps radio latency out of the safety path. (L/R test planned for Stage 3.) |
| C7 | Custom bone-conduction driver | **Bluetooth bone-conduction headset** | The Pi 5 has no analog audio; speech is the information channel, haptics the safety channel. |
| C8 | Chest-clip, no mechanical detail | **Chest pod on a GoPro-style harness**; power bank in a pocket; **PETG** enclosure; IP54 target | Proven, cheap mount. PLA softens at Indian summer temperatures (Tg ≈ 60 °C); PETG doesn't (Tg ≈ 80 °C). |
| C9 | "<₹5,500 BOM" | **Prototype BOM from quotes (≈ ₹22–30k)** + a **production-intent BOM estimate** at 1k units | The ₹5,500 figure was impossible with a PYNQ-Z2 alone. |
| C10 | "250M+"; competitors "₹4–6 lakh" | **43.3 M blind + 295 M with moderate/severe impairment (2020)**; India: **1.99 % blindness among people aged 50+** (NBVIS 2015–19); OrCam MyEye 3 Pro ≈ US$4,250 (US retailer); Envision US$1,899–3,499; **SmartCane (IIT Delhi, ≈ ₹3,500) named as our closest Indian competitor** | Current, citable numbers, plus an honest public-search disclosure. |
| C11 | MEMS mic for horns/alarms | **Future scope** | Not core to the safety function. |
| C12 | Caregiver app | **Future scope** | Not core. |
| C13 | 10–15 pilot users via EnAble India / NAB | **Trials in Stage 3 after ethics approval**, with an O&M instructor; partners listed as "outreach in progress" unless they confirm | Honest scope. |
| C14 | Language not stated | **English + Hindi**, Gujarati as a goal | India-first. |
| C15 | Model/classes not stated | **COCO-pretrained YOLO-nano** now; **India-specific fine-tune** (auto-rickshaw, cow, pothole, open drain; IDD dataset) in Stage 3 | Realistic, with a clear novelty path. |

**Core innovation (one line, slide 1):**
*A chest-worn, fully offline navigation aid that adds head-level-obstacle and drop-off warnings to the white cane. Its alert latency is bounded by an FPGA "safety island" that keeps working even if the AI computer fails, and an on-device AI layer names the hazard and reads text aloud.*

---

## 3. v2 architecture

```
                     ┌──────────── CHEST POD (PETG, GoPro-style mount) ────────────┐
 3× ultrasonic ──────┤► Tang Nano 9K FPGA = SAFETY ISLAND                          │
 (fwd-L, fwd-R, head)│   trigger sequencer → echo timers → distance → zone compare │──► L/R haptic motors
 TF-Luna LiDAR (down)┤►  LiDAR UART parser → drop-off detector                     │    (MOSFET + PWM patterns)
 buttons ────────────┤►  priority encoder · pattern generator · watchdog · fault   │──► piezo buzzer ("check device")
                     │        ▲ UART (status 50 Hz / config) │ heartbeat            │
                     │        ▼                              ▼                      │
 Camera Module 3 ────┤► Raspberry Pi 5 = AI PATH                                   │
 IMU (I²C) ──────────┤►  YOLO-nano objects · OCR on button · alert manager · TTS   │──► BT bone-conduction headset
                     └──────────────────────────────▲──────────────────────────────┘
                                         USB-C 5 V power bank (pocket)
```

**Rule:** the FPGA drives the motors itself, and the Pi only *adds* information. If the Pi's heartbeat stops, the FPGA keeps the alerts running and gives an "AI offline" cue.

---

## 4. Target specifications (all TARGETS; how each is verified in Stage 3)

| Parameter | Target | Basis / Stage 3 verification |
|---|---|---|
| Obstacle range (waist–head height) | 0.3 – 3.0 m | Sensor datasheet; tape-measure test |
| Range error | ≤ ± 5 cm up to 2 m | Datasheet; 20 readings per step |
| **Alert latency** (echo edge → motor on) | ≤ 1 ms worst case | FPGA simulation now (B5); logic analyser later |
| Update period per direction (3 sensors sequenced) | ≤ 100 ms | Calculated from echo time + guard interval |
| Drop-off (≥ 15 cm step) detected ahead | ≥ 1.0 m before the step | Geometry (LiDAR angle, §B2 calc); stair test |
| Object label spoken | ≤ 1.0 s | Laptop benchmark now (optional); Pi 5 later |
| OCR read-aloud (short label) | ≤ 3 s | Same |
| Runtime on a 10,000 mAh bank | ≥ 4 h | **Power budget calculation** (B3) |
| Pi temperature in the closed pod | No throttling | Vent/cooler design; thermal test later |
| Chest pod mass | ≤ 250 g | CAD mass properties (B1) |
| Pi failure → "AI offline" cue | ≤ 1 s | Watchdog in FPGA simulation (B5) |

Some of these can be **backed by calculation or simulation this round**: alert latency, update period, drop-off geometry, runtime and mass. Say so on the slide ("simulated" / "calculated"), never "measured".

---

## 5. Part B: Design files to produce (8–21 Oct)

| ID | Deliverable | Tool | Owner | Due | Feeds slide |
|---|---|---|---|---|---|
| B0 | GitHub repo (`cad/ hw/ fpga/ sw/ docs/`) + Drive folder with **view access**; first commit today | GitHub | R1 | **8–9 Oct** | 12 |
| B1 | **3D CAD** of the chest pod: Pi 5, Tang Nano, camera, 3 ultrasonic windows, LiDAR angled down, vents + cooler, button layout, GoPro-style mount fingers, strap motor clips. Use official Pi 5 / sensor STEP files. Isometric + exploded renders; mass properties. | Fusion 360 (student licence) | R3 | 16 Oct | 7, 12 |
| B2 | **Sensor geometry calc**: mounting angles for the head-level sensor and the LiDAR, coverage cones vs body height (sketch + numbers) | Fusion / spreadsheet | R3 + Claude | 14 Oct | 6, 7 |
| B3 | **Power budget**: datasheet current per component → total W → runtime on 10,000 mAh | Spreadsheet | R2 + Claude | 15 Oct | 6, 9 |
| B4 | **FEA**: mount fingers + strap slot. Loads: 50 N strap tension; 0.3 kg × 10 g jolt ≈ 30 N. Target FoS ≥ 3 in PETG. Adaptive-mesh **convergence plot**. **At least one design iteration** (e.g. fillet / thickness change). Material comparison PLA vs PETG vs ASA. | Fusion Simulation | R3 | 19 Oct | 8, 12 |
| B5 | **FPGA design in simulation**: echo timer, trigger sequencer, zone compare, TF-Luna parser, drop-off detector, PWM patterns, watchdog. Testbench shows **echo → motor-on latency in clock cycles** and the watchdog timeout. Synthesis report for LUT/BRAM usage on the GW1NR-9. | Gowin EDA + Icarus Verilog / GTKWave | R1 | 18 Oct | 6, 12, 16 |
| B6 | **KiCad schematic** of the carrier board (Pi header, Tang Nano headers, sensor JST connectors, MOSFET motor drivers + flyback diodes, buzzer, buttons, 5 V/3.3 V power tree) + ERC | KiCad | R1 | 16 Oct | 9 |
| B7 | **KiCad PCB layout** + **DRC report** | KiCad | R1 | 20 Oct | 9, 12 |
| B8 | **BOM spreadsheet**: part number, qty, quoted price + link + date checked, local/imported, lead time; prototype total + production-intent estimate | Sheets/Excel | R2 + Claude | 20 Oct | 10 |
| B9 | **Software design**: flow chart of the AI path (camera → YOLO → alert manager → TTS; OCR button flow) and the alert-priority state machine. *Optional:* run YOLO/OCR on a laptop with sample images for indicative timings (labelled "laptop, not target hardware"). | draw.io / Python | R2 | 18 Oct | 5, 6 |
| B10 | **FMEA table + standards list** (§7) | Sheets | R2 + Claude | 20 Oct | 14 |
| B11 | **User-journey storyboards** (before/after) + quantified pain from literature. *Optional:* 2–3 phone interviews with blind users (with consent) via Blind People's Association Ahmedabad / NAB Gujarat | Slides / draw.io | R3 | 19 Oct | 3, 4 |
| B12 | **Maker-journey photos**: team **with ID badges** doing CAD, KiCad, simulation, plus a **review with the faculty guide/mentor** (photo or video-call screenshot) | Phone | R3 | 21 Oct | 11 |

**Part A task:**
- **A1, Proposal v2.** Revise the Stage 1 document with C1–C15. Owner: Claude, then team review. Due 11 Oct.

**Optional (only if the team wants stronger maker photos and has ~₹3–5k):** buy a Tang Nano 9K + 2 ultrasonic sensors + 1 motor and show a bench demo of the alert path. This is **not required** for this round. Everything else goes on the Stage 3 order.

---

## 6. Roles (🔸 team to confirm names)

**Update 8 Oct: Aman is working solo.** Claude generates first drafts of every design file (CAD script, KiCad schematic/PCB, Verilog + testbench, calculations, BOM, FMEA, slide text). Aman opens, reviews, modifies and screenshots each one personally, and must be able to explain every part to the judges.

| Who | Owns |
|---|---|
| **Aman** | Install tools; review and edit all files in KiCad / FreeCAD / GTKWave; screenshots; ID-badge photos + mentor review; repo commits; final PPT assembly and submission |
| **Claude** | Drafts of A1 and B1–B11; calculations; slide content; final number check |

---

## 7. Safety content (slide 14)

**FMEA seed:**

| Failure | Effect | Design response |
|---|---|---|
| Ultrasonic stuck / no echo | Missed obstacle | Timeout detector → buzzer "check device" pattern |
| Pi crash / hang | No object names or OCR | FPGA watchdog → "AI offline" cue; alert path unaffected |
| BT headset disconnects | No speech | Haptics continue; distinct cue |
| Harness tilt shifts the LiDAR baseline | False or missed drop-off | Stand-still calibration + IMU pitch check |
| Pi overheats | Throttling, slow AI | Active cooler + vents in the CAD |
| Power bank low | Device stops | Spoken warnings at 20 % / 10 % |
| Battery fire | Burn | Only a BIS-certified power bank; no loose Li-ion cells |
| Alert fatigue | User ignores alerts | Zone hysteresis + quiet mode |

**Standards considered in design (not "certified"):**
- IEC 62368-1 / IS 13252 (ICT equipment safety).
- IEC 62133-2 / IS 16046 (Li-ion batteries).
- IEC 60529 (IP54 target).
- ISO 10993-5/-10 (skin-contact materials).
- ISO 9999 (assistive product classification).
- WPC/ETA (pre-certified radio modules only).

---

## 8. Part C: PPT (21–24 Oct)

| ID | Task | Owner | Due |
|---|---|---|---|
| P1 | Freeze numbers: each one labelled target / calculated / simulated / cited, with its source in `docs/numbers.md` | Claude + all | 21 Oct |
| P2 | Draft content for every slide (map below) | Claude | 22 Oct |
| P3 | Build in a **copy of the official template**; delete the example slides | R3 | 23 Oct |
| P4 | Review against the checklist; fix | all + Claude | 23 Oct |
| P5 | Export PDF, test links in incognito, **submit** | Team lead | **24 Oct** |

**Slide map:**

| # | Template slide | Our content |
|---|---|---|
| 1 | Project overview | Application ID 🔸, Team ID 🔸, Track, one-line innovation |
| 2 | Problem statement | Cane gap; 43.3 M / 295 M; NBVIS India; SmartCane + premium devices disclosure |
| 3 | User journey: before | Storyboard + quantified pain (cited) |
| 4 | User journey: after | Storyboard + **target** gains |
| 5 | System block diagram | §3 diagram, drawn properly |
| 6 | Specs + hardware selection | §4 targets + basis; part choices + rationale (C1, C2, C5) |
| 7 | CAD renders | Isometric + exploded (B1); sensor cones (B2) |
| 8 | Materials + FEA | PETG vs PLA vs ASA; stress/FoS; iteration (B4) |
| 9 | Schematics + power | KiCad schematic + power tree + power budget (B3, B6, B7) |
| 10 | BOM + sourcing | Quotes, local/imported, lead times (B8) |
| 11 | Maker journey: photos | ID-badge photos, mentor review (B12) |
| 12 | Maker journey: evidence | Fusion feature tree, FEA convergence, KiCad DRC, FPGA sim waveform, repo link |
| 13 | Stage 1 → 2 iterations | Strongest 6–8 of C1–C15 |
| 14 | Safety | FMEA + standards (§7) |
| 15 | Roadmap + Stage 3 commitment | §9 |
| 16 | Technical challenges | Ultrasonic crosstalk, LiDAR in sunlight, Pi heat in a closed pod, harness tilt, alert fatigue |
| 17 | Mitigations | Matching design responses |
| 18 | References & image sources | All citations and image URLs |

**Checklist:**
- [ ] Every number is labelled target / calculated / simulated / cited
- [ ] Nothing says "measured" or "tested"
- [ ] No "<10 ms end-to-end", "<₹5,500" or "250M+" left from Stage 1
- [ ] SmartCane and the premium devices are named
- [ ] ID-badge photos + mentor review photo included
- [ ] Repo/Drive opens in incognito; native files present (`.f3d/.step`, `.kicad_sch/.kicad_pcb`, `.v`, BOM `.xlsx`); timestamps fall 8–24 Oct
- [ ] No embedded videos
- [ ] Template example slides removed
- [ ] Image sources complete
- [ ] PDF within the form's size limit 🔸

---

## 9. Gates

| Gate | Date | Pass | If it fails |
|---|---|---|---|
| G0 | 9 Oct | Repo live; roles assigned; Fusion/KiCad/Gowin installed | Fix the same day |
| G1 | 16 Oct | CAD v1, schematic v1, Proposal v2, power budget done | Drop PCB layout (B7); show the schematic only |
| G2 | 21 Oct | FEA, FPGA sim, BOM, FMEA, photos done | Cut optional items (B9 laptop run, interviews) |
| G3 | 23 Oct | Slides complete; checklist clean | 24 Oct is the fix day |

---

## 10. Stage 3 roadmap (4 months, slide 15)

| Month | Work |
|---|---|
| **Nov 2026** (Diwali 8 Nov) | Order parts; bring up the FPGA + sensors + Pi; carrier PCB fabrication; file the ethics application |
| **Dec 2026** | Integration; enclosure print; bench tests (range, latency, drop-off, power, thermal) |
| **Jan 2027** | India-class fine-tune; supervised trials (sighted blindfolded first, then blind volunteers with an O&M instructor, after approval) |
| **Feb 2027** | Fix the top issues; field-test-ready unit |

**Stage 3 commitment:** a wearable, battery-powered prototype ready for supervised functional field testing, with every §4 target measured.

**Stage 3 parts budget** (re-checked 9 Oct 2026; see `design/bom/VisionAid_BOM_Power.xlsx`): Pi 5 4 GB ₹12,600–14,500 (out of stock) · Camera Module 3 ₹3,158 · Tang Nano 9K ₹2,999 (out of stock) · TF-Luna ₹2,118 (out of stock) · rest estimated → **₹33,945 total, ₹3,945 over the grant**.

---

## 11. 🔸 Team inputs needed

| # | Input | Default |
|---|---|---|
| 1 | Application ID + Team ID | Placeholder |
| 2 | Names for R2 / R3 | — |
| 3 | SVNIT faculty guide + IIT Indore mentor | Needed for the review photo |
| 4 | Mid-semester exam dates | — |
| 5 | Optional bench demo (~₹3–5k)? | No |

---

## References (verified 8 Oct 2026)

- Bourne R. et al., Lancet Global Health 9(2):e130–e143, 2021. https://pubmed.ncbi.nlm.nih.gov/33275950/
- NBVIS India 2015–2019 (AIIMS / MoHFW). https://indiavisionatlasnpcb.aiims.edu/?p=358
- Manduchi R., Kurniawan S., Insight 4(2), 2011 (UCSC-SOE-10-24). https://tr.soe.ucsc.edu/research/technical-reports/UCSC-SOE-10-24
- SmartCane (IIT Delhi / Assistech). https://www.electronicsforu.com/electronics-startups/innovations-innovators/smartcane-indigenous-device-help-visually-impaired-2
- OrCam MyEye 3 Pro: https://www.orcam.com/en-us/orcam-myeye-lp-for-people-who-are-blind-or-visually-impaired · Envision: https://support.letsenvision.com/hc/en-us/articles/7602816580369
- Parts: https://probots.co.in/sipeed-tang-nano-9k-fpga-development-board.html · https://probots.co.in/benewake-tf-luna-lidar-distance-sensor-8m-uart.html · https://thingbits.in/products/raspberry-pi-camera-module-3

---

## Change log

| Date | Change | Reason |
|---|---|---|
| 8 Oct 2026 | v1.0 | Initial plan |
| 9 Oct 2026 | Numbers audit: every deck figure re-checked against logs/reports; prices re-quoted (BOM ₹33,945); citations re-verified | User: "everything real, verified, and correct" |
| 8 Oct 2026 | v1.1: scope cut to design-specification deck; no purchases or physical tests in Stage 2; specs as targets backed by calculation/simulation; build moved to the Stage 3 roadmap | Organisers: "PPT of design specifications… No prototype video required" |
