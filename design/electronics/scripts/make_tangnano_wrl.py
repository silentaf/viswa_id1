"""Coloured VRML twin of 3d/TangNano9K_Module.step for KiCad renders (same geometry, in KiCad's
VRML unit of 0.1 inch = 2.54 mm). Run: python3 design/electronics/scripts/make_tangnano_wrl.py"""
import os
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '3d', 'TangNano9K_Module.wrl')
U = 2.54
BOXES = [  # lx, ly, lz, cx, cy, z0, rgb  (mm, same as make_tangnano_3d.py)
    (2.54, 61.0, 8.5, -11.43, 0, 0, (0.08, 0.08, 0.08)), (2.54, 61.0, 8.5, 11.43, 0, 0, (0.08, 0.08, 0.08)),
    (25.4, 65.0, 1.6, 0, 0, 8.5, (0.06, 0.06, 0.07)), (10.0, 10.0, 0.9, 0, 4.0, 10.1, (0.15, 0.15, 0.15)),
    (9.0, 7.5, 3.2, 0, 29.1, 10.1, (0.8, 0.8, 0.82)), (15.0, 11.0, 5.6, 0, -27.5, 10.1, (0.8, 0.8, 0.82)),
    (18.0, 5.0, 1.2, 0, -12.0, 10.1, (0.92, 0.9, 0.82)),
] + [(1.6, 0.8, 0.5, -6 + 2.4 * i, 22.0, 10.1, (0.95, 0.95, 0.9)) for i in range(6)]
with open(OUT, 'w') as f:
    f.write('#VRML V2.0 utf8\n# Sipeed Tang Nano 9K on 8.5 mm sockets - simplified (VisionAid)\n')
    for lx, ly, lz, cx, cy, z0, (r, g, b) in BOXES:
        f.write('Transform { translation %.4f %.4f %.4f children [ Shape { appearance Appearance { material '
                'Material { diffuseColor %.2f %.2f %.2f specularColor 0.2 0.2 0.2 shininess 0.3 } } '
                'geometry Box { size %.4f %.4f %.4f } } ] }\n' % (cx / U, cy / U, (z0 + lz / 2) / U, r, g, b,
                                                                 lx / U, ly / U, lz / U))
print('saved', OUT)
