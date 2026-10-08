"""Take FreeCAD GUI screenshots (feature tree, spreadsheet, sketch, 3D) on a virtual X display.
Run: DISPLAY=:99 QT_QPA_PLATFORM=xcb tools/freecad.sh gui design/cad/scripts/gui_screenshots.py
"""
import os
import time
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtGui, QtCore

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.dirname(HERE)
SHOTS = os.path.join(CAD, '..', '..', 'docs', 'screenshots')
os.makedirs(SHOTS, exist_ok=True)


def settle(sec=2.0):
    end = time.time() + sec
    while time.time() < end:
        Gui.updateGui()
        QtCore.QCoreApplication.processEvents()
        time.sleep(0.05)


def snap(name):
    settle(1.5)
    mw = Gui.getMainWindow()
    mw.grab().save(os.path.join(SHOTS, name))
    print('shot', name, flush=True)


mw = Gui.getMainWindow()
mw.showMaximized()
settle(3)
Gui.activateWorkbench('PartDesignWorkbench')
doc = App.openDocument(os.path.join(CAD, 'VisionAid_Pod.FCStd'))
gdoc = Gui.getDocument(doc.Name)
settle(3)
view = gdoc.ActiveView

# 1. feature tree with the new fillet selected, rear view showing the mount
for name in ('FrontAssembly', 'Electronics'):
    gdoc.getObject(name).Visibility = False
for o in doc.getObject('Electronics').Group:
    gdoc.getObject(o.Name).Visibility = False
Gui.Selection.clearSelection()
Gui.Selection.addSelection(doc.getObject('FingerRootFillet'))
view.viewIsometric()
view.setCameraOrientation(App.Rotation(App.Vector(0, 0, 1), -35).multiply(App.Rotation(App.Vector(1, 0, 0), 70)))
view.fitAll()
snap('freecad_01_feature_tree_finger_fillet.png')

# 2. full assembly, isometric front
gdoc.getObject('FrontAssembly').Visibility = True
for o in doc.getObject('Electronics').Group:
    gdoc.getObject(o.Name).Visibility = True
Gui.Selection.clearSelection()
Gui.Selection.addSelection(doc.getObject('BaseShell'))
view.setCameraOrientation(App.Rotation(App.Vector(0, 0, 1), 155).multiply(App.Rotation(App.Vector(1, 0, 0), 70)))
view.fitAll()
snap('freecad_02_assembly_iso.png')

# 3. parameter spreadsheet
Gui.Selection.clearSelection()
gdoc.setEdit(doc.getObject('Params'))
snap('freecad_03_params_spreadsheet.png')
gdoc.resetEdit()
settle(1)

# 4. fully constrained profile sketch
gdoc.getObject('FrontAssembly').Visibility = False
gdoc.setEdit(doc.getObject('ShellProfile'))
snap('freecad_04_sketch_constraints.png')
gdoc.resetEdit()
settle(1)
os._exit(0)
