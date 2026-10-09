# VisionAid: Stage 2 Design Files (index)

**Everything here is design-stage work.** It contains no hardware measurements. Each number is labelled **simulated**, **calculated**, **estimate** or **target**.

| Folder | What | Key result | Feeds slide |
|---|---|---|---|
| `electronics/` | KiCad 9 carrier board: schematic, PCB, Gerbers, BOM, 3D STEP | ERC 0 · DRC 0 · 0 unconnected · parity 0 · 100 % routed | 5, 9, 10, 12 |
| `fpga/` | Verilog safety island, testbench, waveform plots, Yosys utilisation | ALL TESTS PASSED; echo → motor 136 ns on the waveform, ≤ 214 ns testbench bound (simulated); P&R: LUT 17 %, FF 8 %, Fmax 67.9 MHz | 5, 6, 12, 16 |
| `cad/` | FreeCAD parametric pod (`VisionAid_Pod.FCStd`), STEP/STL, renders, mount FEA | 0 mm³ interference; FEA convergence + v1 → v2 iteration | 7, 8, 12 |
| `bom/` | `VisionAid_BOM_Power.xlsx`: prototype BOM + power budget | ₹33,945 at 9 Oct 2026 quotes (₹3,945 over the grant; budget rule inside); 7.2 W → 4.3 h assuming ~50 % AI duty (calculated) | 6, 10 |
| `../VisionAid_Proposal_v2.md` | Corrected Stage 1 document | 15 documented changes | 1–4, 13 |
| `../IMPLEMENTATION_PLAN.md` | Plan, gates, slide map, checklist | — | all |

## Tools (installed locally in `../tools/`, no root needed)

| Tool | Launcher | Used for |
|---|---|---|
| KiCad 9.0.8 | `tools/kicad.sh kicad design/electronics/VisionAid_Carrier.kicad_pro` | Schematic / PCB GUI |
| FreeCAD (conda-forge) | `tools/freecad.sh gui design/cad/VisionAid_Pod.FCStd` | CAD GUI, feature tree, FEM |
| Icarus Verilog, GTKWave, Yosys | `tools/eda.sh <tool>` | Simulation, waveforms, synthesis |
| FreeRouting 2.5 | used by `electronics/scripts/route_pcb.py` | PCB autorouting |

## What YOU must do yourself (judges check authenticity)

1. **Open every design in the GUI and make at least one real edit of your own.** For example: tidy silkscreen in KiCad, change a fillet in FreeCAD, add a comment in the Verilog. Save, then commit.
2. **Take your own screenshots:**
   - FreeCAD with the **feature tree** (BaseShell → ShellProfile sketch, ShellPad, CornerFillet, Hollow, …) and the Params spreadsheet;
   - KiCad PCB editor + 3D viewer + the DRC dialog showing 0 errors;
   - GTKWave with the latency signals;
   - the FreeCAD FEM result.
3. **Photos with your SVNIT ID badge on:** you at the laptop doing CAD / KiCad / simulation, and a review with your faculty guide (photo or video-call screenshot).
4. **Git:** put this `design/` folder in a GitHub repo and commit regularly until 24 Oct. File dates are audited, so do not upload everything on the last day.
5. **Be able to explain every block.** Read `electronics/README.md` and `fpga/README.md`, and the "why" column of the plan.
