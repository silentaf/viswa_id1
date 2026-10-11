"""Headless, properly z-buffered renders of the VisionAid pod from outputs/pod_meshes.npz.

Why: the matplotlib renderer (render_mpl.py) draws each part as a flat Poly3DCollection and lets
matplotlib's approximate painter's-algorithm sort the triangles. That sort is only an average-depth
heuristic and visibly breaks on this model's overlapping/concave geometry (sensor bores cut into the
housings, the shell around the carrier PCB) - stray dark triangles and mis-ordered faces show up in
pod_assembled_iso.png, pod_front.png and pod_xray_iso.png. VTK renders with a real GPU/Mesa z-buffer
(plus depth peeling for the translucent x-ray view), so every face is drawn in the correct order.
Same input (outputs/pod_meshes.npz), same 5 views/angles/titles/colors/explode offsets as render_mpl.py,
so this is a drop-in replacement - only the renderer changed, not any geometry or design data.
Run: tools/freecad-env/bin/python design/cad/scripts/render_vtk.py
"""
import os
import numpy as np
import vtk
from vtk.util import numpy_support as vnp

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'outputs')
M = np.load(os.path.join(OUT, 'pod_meshes.npz'))
NAMES = sorted({k.split('__')[0] for k in M.files})


def part_actor(name, offset, alpha):
    v, f, c = M[name + '__v'], M[name + '__f'], M[name + '__c']
    v = v + np.asarray(offset, dtype=np.float64)
    pts = vtk.vtkPoints()
    pts.SetData(vnp.numpy_to_vtk(v, deep=True))
    cells = vtk.vtkCellArray()
    conn = np.hstack([np.full((len(f), 1), 3, dtype=np.int64), f.astype(np.int64)]).ravel()
    cells.SetCells(len(f), vnp.numpy_to_vtkIdTypeArray(conn, deep=True))
    poly = vtk.vtkPolyData()
    poly.SetPoints(pts)
    poly.SetPolys(cells)
    norms = vtk.vtkPolyDataNormals()
    norms.SetInputData(poly)
    norms.ConsistencyOn()
    norms.SplittingOff()
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(norms.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    p = actor.GetProperty()
    p.SetColor(*[float(x) for x in c])
    p.SetAmbient(0.35)
    p.SetDiffuse(0.75)
    p.SetSpecular(0.15)
    p.SetSpecularPower(25)
    p.SetOpacity(alpha)
    return actor, poly


def render(fname, parts, elev, azim, alpha=None, title=None, size=(1800, 1350)):
    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)
    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    win.AddRenderer(ren)
    win.SetSize(*size)
    has_translucent = any((alpha or {}).get(n, 1.0) < 1.0 for n, _ in parts)
    if has_translucent:
        win.SetAlphaBitPlanes(1)
        win.SetMultiSamples(0)
        ren.SetUseDepthPeeling(1)
        ren.SetMaximumNumberOfPeels(64)
        ren.SetOcclusionRatio(0.0)

    all_pts = []
    for name, off in parts:
        a = (alpha or {}).get(name, 1.0)
        actor, poly = part_actor(name, off, a)
        ren.AddActor(actor)
        all_pts.append(np.asarray(poly.GetPoints().GetData()))
    allv = np.concatenate(all_pts)
    lo, hi = allv.min(0), allv.max(0)
    mid, span = (lo + hi) / 2, (hi - lo).max() / 2

    elev_r, azim_r = np.radians(elev), np.radians(azim)
    direction = np.array([np.cos(elev_r) * np.cos(azim_r), np.cos(elev_r) * np.sin(azim_r), np.sin(elev_r)])
    cam = ren.GetActiveCamera()
    cam.SetFocalPoint(*mid)
    cam.SetPosition(*(mid + direction * span * 6))
    cam.SetViewUp(0, 0, 1)
    cam.ParallelProjectionOn()
    cam.SetParallelScale(span * 1.08 * (size[1] / min(size)))
    ren.ResetCameraClippingRange()

    if title:
        txt = vtk.vtkTextActor()
        txt.SetInput(title)
        txt.GetTextProperty().SetColor(0, 0, 0)
        txt.GetTextProperty().SetFontSize(22)
        txt.GetTextProperty().SetFontFamilyToArial()
        txt.SetPosition(18, size[1] - 36)
        ren.AddViewProp(txt)

    win.Render()
    w2if = vtk.vtkWindowToImageFilter()
    w2if.SetInput(win)
    if has_translucent:
        w2if.SetInputBufferTypeToRGBA()
    else:
        w2if.SetInputBufferTypeToRGB()
    w2if.Update()
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(os.path.join(OUT, fname))
    writer.SetInputConnection(w2if.GetOutputPort())
    writer.Write()
    print('saved', fname)


ALL = [(n, (0, 0, 0)) for n in NAMES]
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
render('pod_exploded_iso.png', ex, elev=20, azim=50, size=(2100, 1350),
       title='Exploded: shell · Pi 5 · standoffs · carrier + Tang Nano · lid + housings · sensors')
