"""Simplified 3D model of the Sipeed Tang Nano 9K on two 8.5 mm female headers (for KiCad renders).
Coordinates follow KiCad's model convention: origin = footprint origin, model +Y = footprint -Y
(USB-C end), Z up from the carrier-board surface. Dimensions approximate (verify with calipers).
Run: tools/freecad.sh cmd design/electronics/scripts/make_tangnano_3d.py
"""
import os
import FreeCAD as App
import Part
import Import
V = App.Vector
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '3d')
doc = App.newDocument('TangNano9K')


def box(name, lx, ly, lz, cx, cy, z0, rgb):
    o = doc.addObject('Part::Feature', name)
    o.Shape = Part.makeBox(lx, ly, lz, V(cx - lx / 2, cy - ly / 2, z0))
    o.ViewObject if False else None
    o.addProperty('App::PropertyColor', 'Col').Col = rgb
    return o


parts = []
for s in (-1, 1):                                   # 1x24 female headers, 8.5 mm tall
    parts.append(box('Socket%d' % (s + 2), 2.54, 61.0, 8.5, s * 11.43, 0, 0, (0.08, 0.08, 0.08)))
parts.append(box('ModulePCB', 25.4, 65.0, 1.6, 0, 0, 8.5, (0.05, 0.05, 0.05)))
parts.append(box('FPGA_QFN88', 10.0, 10.0, 0.9, 0, 4.0, 10.1, (0.12, 0.12, 0.12)))
parts.append(box('USB_C', 9.0, 7.5, 3.2, 0, 32.5 - 3.4, 10.1, (0.75, 0.75, 0.78)))
parts.append(box('HDMI', 15.0, 11.0, 5.6, 0, -32.5 + 5.0, 10.1, (0.75, 0.75, 0.78)))
parts.append(box('LCD_FPC', 18.0, 5.0, 1.2, 0, -12.0, 10.1, (0.9, 0.9, 0.85)))
for i in range(6):
    parts.append(box('LED%d' % i, 1.6, 0.8, 0.5, -6 + 2.4 * i, 22.0, 10.1, (0.95, 0.95, 0.9)))
doc.recompute()
Import.export(parts, os.path.join(OUT, 'TangNano9K_Module.step'))
print('saved TangNano9K_Module.step')
