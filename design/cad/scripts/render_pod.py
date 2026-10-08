"""Render PNG views of VisionAid_Pod.FCStd (run with the FreeCAD GUI, offscreen):
   tools/freecad.sh offscreen design/cad/scripts/render_pod.py
"""
import os
import FreeCAD as App
import FreeCADGui as Gui

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.dirname(HERE)
OUT = os.path.join(CAD, 'outputs')

Gui.showMainWindow()
print("gui up", flush=True)
doc = App.openDocument(os.path.join(CAD, 'VisionAid_Pod.FCStd'))
Gui.updateGui()
print("doc open", flush=True)
gdoc = Gui.getDocument(doc.Name)

for o in doc.Objects:
    vo = gdoc.getObject(o.Name)
    if vo is None:
        continue
    vo.Visibility = False
show = {'BaseShell': ((0.93, 0.55, 0.15), 0), 'FrontAssembly': ((0.20, 0.45, 0.80), 0)}
for name, (col, tr) in show.items():
    vo = gdoc.getObject(name)
    vo.Visibility = True
    vo.ShapeColor = col
    vo.Transparency = tr
elec = [o for o in doc.getObject('Electronics').Group]
for o in elec:
    vo = gdoc.getObject(o.Name)
    vo.Visibility = True
    if hasattr(o, 'RefColor'):
        vo.ShapeColor = tuple(o.RefColor)[:3]
view = gdoc.ActiveView


def shot(fname, setup, w=1600, h=1200):
    setup()
    view.fitAll()
    Gui.updateGui()
    view.saveImage(os.path.join(OUT, fname), w, h, 'White')
    print('saved', fname)


def iso():
    view.viewIsometric()


def front():
    view.viewRear()          # FreeCAD 'rear' looks along -Y, i.e. at our front face (+Y)


def back():
    view.viewFront()


# 1. assembled, isometric from the front-right-top
def assembled_iso():
    view.setCameraOrientation(App.Rotation(App.Vector(0, 0, 1), 155).multiply(App.Rotation(App.Vector(1, 0, 0), 70)))


shot('pod_assembled_iso.png', assembled_iso)
shot('pod_front.png', front)
# 2. back view with the GoPro mount
shot('pod_back_mount.png', lambda: view.setCameraOrientation(
    App.Rotation(App.Vector(0, 0, 1), -25).multiply(App.Rotation(App.Vector(1, 0, 0), 75))))
# 3. see-through: shell transparent to show the stack
gdoc.getObject('BaseShell').Transparency = 70
gdoc.getObject('FrontAssembly').Transparency = 70
shot('pod_xray_iso.png', assembled_iso)
gdoc.getObject('BaseShell').Transparency = 0
gdoc.getObject('FrontAssembly').Transparency = 0
# 4. exploded view (temporary placement offsets, not saved)
moves = {'FrontAssembly': 75}
for o in elec:
    if o.Name.startswith(('US_', 'Camera_', 'TFLuna')):
        moves[o.Name] = 95
    elif o.Name.startswith(('Carrier', 'TangNano')):
        moves[o.Name] = 35
    elif o.Name.startswith('Standoff'):
        moves[o.Name] = 12
    else:
        moves[o.Name] = 0
for name, dy in moves.items():
    o = doc.getObject(name)
    o.Placement.Base.y += dy
doc.recompute()
shot('pod_exploded_iso.png', assembled_iso)
os._exit(0)   # closing the offscreen GUI can hang; all images are already written
