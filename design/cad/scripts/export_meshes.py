"""Tessellate every visible part of VisionAid_Pod.FCStd into a compact .npz mesh file for rendering
(run with: tools/freecad.sh cmd design/cad/scripts/export_meshes.py)."""
import os
import numpy as np
import FreeCAD as App

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.dirname(HERE)
doc = App.openDocument(os.path.join(CAD, 'VisionAid_Pod.FCStd'))

parts = {'BaseShell': (0.93, 0.55, 0.15), 'FrontAssembly': (0.25, 0.48, 0.82)}
for o in doc.getObject('Electronics').Group:
    parts[o.Name] = tuple(o.RefColor)[:3] if hasattr(o, 'RefColor') else (0.55, 0.55, 0.6)
parts['CarrierPCB_from_KiCad'] = (0.13, 0.45, 0.25)

data = {}
for name, col in parts.items():
    sh = doc.getObject(name).Shape
    tol = 0.6 if name.startswith('Carrier') else 0.2
    v, f = sh.tessellate(tol)
    data[name + '__v'] = np.array([(p.x, p.y, p.z) for p in v], dtype=np.float32)
    data[name + '__f'] = np.array(f, dtype=np.int32)
    data[name + '__c'] = np.array(col, dtype=np.float32)
    print(name, len(f), 'triangles')
np.savez_compressed(os.path.join(CAD, 'outputs', 'pod_meshes.npz'), **data)
print('saved pod_meshes.npz')
