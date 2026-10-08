"""Headless renders of the VisionAid pod from outputs/pod_meshes.npz (matplotlib, flat shading).
Run: tools/freecad-env/bin/python design/cad/scripts/render_mpl.py
"""
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'outputs')
M = np.load(os.path.join(OUT, 'pod_meshes.npz'))
NAMES = sorted({k.split('__')[0] for k in M.files})
PI_PARTS = ('RPi5_PCB', 'RPi5_ActiveCooler', 'RPi5_USB_Ethernet')


def decimate(v, f, grid):
    """Vertex-clustering decimation (only used for the very detailed KiCad board)."""
    q = np.round(v / grid).astype(np.int64)
    _, idx, inv = np.unique(q, axis=0, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    nf = inv[f]
    ok = (nf[:, 0] != nf[:, 1]) & (nf[:, 1] != nf[:, 2]) & (nf[:, 0] != nf[:, 2])
    return v[idx], nf[ok]


def mesh(name, offset=(0, 0, 0)):
    v, f, c = M[name + '__v'], M[name + '__f'], M[name + '__c']
    if len(f) > 50000:
        v, f = decimate(v, f, 0.35)
    return v + np.array(offset, dtype=np.float32), f, c


def render(fname, parts, elev, azim, alpha=None, title=None, size=(12, 9)):
    fig = plt.figure(figsize=size, dpi=150)
    ax = fig.add_subplot(111, projection='3d')
    ax.set_proj_type('ortho')
    light = np.array([0.35, 0.55, 0.75])
    light /= np.linalg.norm(light)
    tris, cols = [], []
    for name, off in parts:
        v, f, c = mesh(name, off)
        t = v[f]
        n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
        shade = 0.45 + 0.55 * np.abs(n @ light)
        a = (alpha or {}).get(name, 1.0)
        col = np.concatenate([np.clip(c[None, :] * shade[:, None], 0, 1), np.full((len(f), 1), a)], axis=1)
        tris.append(t)
        cols.append(col)
    tris = np.concatenate(tris)
    cols = np.concatenate(cols)
    pc = Poly3DCollection(tris, facecolors=cols, edgecolors='none', linewidths=0)
    ax.add_collection3d(pc)
    allv = tris.reshape(-1, 3)
    lo, hi = allv.min(0), allv.max(0)
    mid, span = (lo + hi) / 2, (hi - lo).max() / 2
    ax.set_xlim(mid[0] - span, mid[0] + span)
    ax.set_ylim(mid[1] - span, mid[1] + span)
    ax.set_zlim(mid[2] - span, mid[2] + span)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    if title:
        ax.set_title(title, fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, fname), dpi=150, facecolor='white')
    plt.close(fig)
    print('saved', fname)


ALL = [(n, (0, 0, 0)) for n in NAMES]
# Y is forward (away from the chest); matplotlib azim 60 looks from front-right
render('pod_assembled_iso.png', ALL, elev=22, azim=62, title='VisionAid chest pod - assembled (CAD v1)')
render('pod_back_mount.png', ALL, elev=18, azim=-120, title='Back: GoPro-style 2-finger mount, vents, USB-C slot')
render('pod_front.png', ALL, elev=2, azim=90, title='Front: head-level, left/right ultrasonic, camera, LiDAR')
render('pod_xray_iso.png', ALL, elev=22, azim=62, alpha={'BaseShell': 0.18, 'FrontAssembly': 0.18},
       title='See-through: Pi 5 + 20 mm standoffs + carrier PCB + Tang Nano 9K + sensors')
ex = []
for n in NAMES:
    if n == 'FrontAssembly':
        dy = 80
    elif n.startswith(('US_', 'Camera_', 'TFLuna')):
        dy = 110
    elif n.startswith(('Carrier', 'TangNano')):
        dy = 40
    elif n.startswith('Standoff'):
        dy = 15
    else:
        dy = 0
    ex.append((n, (0, dy, 0)))
render('pod_exploded_iso.png', ex, elev=20, azim=50, size=(14, 9),
       title='Exploded: shell | Pi 5 | standoffs | carrier + Tang Nano | lid + housings | sensors')
