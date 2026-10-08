"""Plots for the mount FEA (simulation results, not physical tests):
  fea_convergence.png  - max von Mises and finger-root stress vs number of elements (both versions, both loads)
  fea_contour_<case>.png - von Mises stress mapped on the part surface (finest mesh)
  fea_summary.md       - table for the PPT
Run: tools/freecad.sh cmd design/cad/scripts/plot_fea.py
"""
import os
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = os.path.dirname(os.path.abspath(__file__))
FEA = os.path.join(os.path.dirname(HERE), 'outputs', 'fea')
res = json.load(open(os.path.join(FEA, 'fea_results.json')))
YIELD = 50.0

# ---------------- convergence
fig, axs = plt.subplots(1, 2, figsize=(13, 4.8))
for ax, load, title in ((axs[0], 'down50N', 'Load case A: 50 N downward (bump / snag)'),
                        (axs[1], 'side20N', 'Load case B: 20 N sideways (knock)')):
    for ver, col in (('v1_sharp', '#c0392b'), ('v2_fillet1p5', '#1f5fa8')):
        rs = sorted([r for r in res if r['version'] == ver and r.get('load') == load], key=lambda r: r['elements'])
        if not rs:
            continue
        n = [r['elements'] for r in rs]
        ax.plot(n, [r['max_vonmises_MPa'] for r in rs], 'o-', color=col, label=ver + ' : max anywhere')
        ax.plot(n, [r['root_vonmises_MPa'] for r in rs], 's--', color=col, alpha=0.7, label=ver + ' : finger root')
    ax.set_xscale('log')
    ax.set_xlabel('number of elements (2nd-order tetrahedra)')
    ax.set_ylabel('von Mises stress (MPa)')
    ax.set_title(title, fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
fig.suptitle('Mount FEA mesh-convergence study (FreeCAD FEM + Gmsh + CalculiX, PETG E = 2 GPa) - simulated', fontsize=11)
fig.tight_layout()
fig.savefig(os.path.join(FEA, 'fea_convergence.png'), dpi=150)

# ---------------- contour on surface (nearest FE node -> surface vertex)
import FreeCAD as App
import Part
contour = json.load(open(os.path.join(FEA, 'fea_contour_finest.json')))
for case, d in contour.items():
    ver = case.rsplit('_', 1)[0] if case.endswith(('down50N', 'side20N')) else case
    ver = '_'.join(case.split('_')[:2])
    shape = Part.read(os.path.join(FEA, 'mount_%s.step' % ver))
    v, f = shape.tessellate(0.15)
    sv = np.array([(p.x, p.y, p.z) for p in v])
    nodes = np.array(d['nodes'])
    vm = np.array(d['vm'])
    idx = np.empty(len(sv), dtype=int)
    for i in range(0, len(sv), 500):
        dd = ((sv[i:i + 500, None, :] - nodes[None, :, :]) ** 2).sum(-1)
        idx[i:i + 500] = dd.argmin(1)
    sval = vm[idx]
    tri = sv[np.array(f)]
    fv = sval[np.array(f)].mean(1)
    vmax = float(vm.max())
    fig = plt.figure(figsize=(8, 7), dpi=150)
    ax = fig.add_subplot(111, projection='3d')
    ax.set_proj_type('ortho')
    cmap = plt.get_cmap('jet')
    pc = Poly3DCollection(tri, facecolors=cmap(fv / vmax), edgecolors='none')
    ax.add_collection3d(pc)
    lo, hi = sv.min(0), sv.max(0)
    mid, span = (lo + hi) / 2, (hi - lo).max() / 2
    ax.set_xlim(mid[0] - span, mid[0] + span); ax.set_ylim(mid[1] - span, mid[1] + span)
    ax.set_zlim(mid[2] - span, mid[2] + span)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=25, azim=-55)
    ax.set_axis_off()
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, vmax))
    fig.colorbar(sm, ax=ax, shrink=0.6, label='von Mises (MPa)')
    ax.set_title('%s - max %.1f MPa, FoS %.1f vs 50 MPa yield (simulated)' % (case, vmax, YIELD / vmax), fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(FEA, 'fea_contour_%s.png' % case), dpi=150)
    plt.close(fig)

# ---------------- summary table (finest mesh per case)
lines = ['| Version | Load | Elements | Max von Mises (MPa) | Finger-root (MPa) | FoS on 50 MPa | Max deflection (mm) |',
         '|---|---|---|---|---|---|---|']
for ver in ('v1_sharp', 'v2_fillet1p5'):
    for load in ('down50N', 'side20N'):
        rs = [r for r in res if r['version'] == ver and r.get('load') == load]
        if not rs:
            continue
        r = max(rs, key=lambda r: r['elements'])
        lines.append('| %s | %s | %d | %.2f | %.2f | %.1f | %.4f |' % (
            ver, load, r['elements'], r['max_vonmises_MPa'], r['root_vonmises_MPa'], r['FoS'], r['max_disp_mm']))
open(os.path.join(FEA, 'fea_summary.md'), 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
