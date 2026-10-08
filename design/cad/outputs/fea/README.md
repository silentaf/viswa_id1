# Chest-mount FEA (simulation, design stage)

**Tools:** FreeCAD FEM, Gmsh (2nd-order tetrahedra) and CalculiX. Script: `design/cad/scripts/fea_mount.py`. Plots: `plot_fea.py`.

**Model:** a GoPro-style 2-finger mount (3.0 mm fingers, 3.2 mm gap, M5 bolt) on a 30 × 30 mm piece of the 2.5 mm back wall.

**Material:** PETG, E = 2.0 GPa, ν = 0.38. Yield is about 50 MPa (typical datasheet value). Printed parts are weaker between layers, so we **require a factor of safety (FoS) ≥ 3**.

**Boundary conditions:** the bolt-hole faces are fixed (held by the harness buckle). The load is applied on the wall face.

**Load cases (design assumptions):**
- A: **50 N downward.** A ~0.3 kg pod at ~17 g, i.e. a bump or snag.
- B: **20 N sideways.** A side knock, which bends the thin fingers.

## Results (finest mesh that solved)

| Version | Load | Elements | Max von Mises (MPa) | Finger-root (MPa) | FoS on 50 MPa | Max deflection (mm) |
|---|---|---|---|---|---|---|
| v1 sharp roots | A 50 N down | 19,477 | 5.77 | 2.20 | 8.7 | 0.064 |
| v1 sharp roots | B 20 N side | 19,337 | 5.12 | 2.52 | 9.8 | 0.032 |
| v2 1.5 mm root fillet | A 50 N down | 13,572 | 5.74 | 1.76 | 8.7 | 0.062 |
| v2 1.5 mm root fillet | B 20 N side | 13,509 | 4.04 | 2.40 | 12.4 | 0.029 |

## What the convergence study shows (`fea_convergence.png`)

- **v1 (sharp roots):** the finger-root stress **keeps rising as the mesh is refined**: 1.59 → 2.20 MPa under load A and 1.62 → 2.52 MPa under load B. That is the signature of a **stress singularity at a sharp corner**. The true peak in a printed part is set by the corner radius, so the v1 result cannot be trusted.
- **v2 (1.5 mm root fillet):** the root stress **converges** to 1.76–1.82 MPa under A and 2.40–2.42 MPa under B, with < 3 % change across meshes.
- **Design iteration:** v1 → v2 adds 1.5 mm fillets at the finger roots. **To do:** add the same fillet to the finger roots in `VisionAid_Pod.FCStd` (a PartDesign Fillet). Good to do yourself in the GUI and screenshot as your own edit.
- **Where the peak sits:** the highest stress (~4–6 MPa) is at the bolt hole, where the rigid "fixed" support concentrates load. A real bolt spreads that load, so the peak is conservative.
- **Verdict:** every case has **FoS ≥ 8.7** against the ≥ 3 requirement.

## Honest limitations

- The two finest v2 meshes (h = 1.0 mm) **failed to produce a result** (Gmsh/CalculiX on the fillet geometry). The v2 numbers come from 3 mesh levels.
- This is a linear-elastic, isotropic model. Real FDM parts are anisotropic and can creep, so the print orientation should keep the fingers' layers along their length.
- These results are **not** a physical test. In Stage 3 we will do a pull test on a printed mount: hang a known weight and look for cracks.

**Figures:** `fea_convergence.png`, `fea_contour_<version>_<load>.png`.
