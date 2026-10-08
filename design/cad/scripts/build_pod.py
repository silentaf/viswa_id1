"""VisionAid chest pod - parametric FreeCAD model (design stage, v1).

Builds VisionAid_Pod.FCStd with:
  Params          spreadsheet - every key dimension (edit a cell -> whole model updates)
  BaseShell       PartDesign body: rounded box, 2.5 mm wall, vents, Pi 5 bosses, lid posts,
                  USB-C cable slot, GoPro-style 2-finger mount on the back
  FrontLid        PartDesign body: lid plate, screw holes, cable windows
  Housings        angled sensor housings (Part CSG): head-level ultrasonic (+25 deg pitch),
                  left/right ultrasonics (+/-15 deg yaw), camera, TF-Luna LiDAR (-35 deg pitch)
  Electronics     reference geometry: Raspberry Pi 5 (simplified), carrier PCB (KiCad STEP),
                  Tang Nano 9K, sensors (simplified blocks)
Coordinates: X = across the chest, Y = forward (away from the body), Z = up. Units mm.
Run:  tools/freecad.sh cmd design/cad/scripts/build_pod.py
"""
import os
import math
import FreeCAD as App
import Part
import Sketcher

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.dirname(HERE)
OUT = os.path.join(CAD, 'outputs')
PCB_STEP = os.path.join(CAD, '..', 'electronics', 'outputs', 'VisionAid_Carrier.step')
V = App.Vector

PARAMS = [  # alias, value, unit/comment
    ('PodW', 112, 'outer width (X)'), ('PodH', 84, 'outer height (Z)'), ('BaseD', 48, 'base shell depth (Y); 44 -> 48 after the Tang Nano 3D model showed an HDMI-connector clash'),
    ('WallT', 2.5, 'wall thickness'), ('CornerR', 8, 'corner radius'), ('LidT', 3, 'lid thickness'),
    ('PiBoss', 4, 'Pi standoff boss height'), ('StandH', 20, 'Pi -> carrier standoff'),
    ('SensW', 48, 'ultrasonic housing width'), ('SensH', 26, 'ultrasonic housing height'),
    ('SensD', 20, 'ultrasonic housing depth'), ('YawLR', 15, 'left/right sensor yaw (deg)'),
    ('PitchHead', 25, 'head sensor pitch up (deg)'), ('PitchLidar', 35, 'LiDAR pitch down (deg)'),
    ('FingerT', 3.0, 'GoPro finger thickness'), ('FingerGap', 3.2, 'GoPro finger gap'),
    ('FingerL', 10, 'GoPro finger length'), ('FingerR', 7.5, 'GoPro finger tip radius'),
    ('BoltD', 5.2, 'GoPro bolt hole (M5)'),
]


def origin_feature(body, role):
    for f in body.Origin.OriginFeatures:
        if getattr(f, 'Role', '') == role or f.Name.startswith(role):
            return f
    raise RuntimeError(role)


def rot_y_axis():
    """Rotation that turns a primitive's +Z axis into +Y."""
    return App.Rotation(V(1, 0, 0), -90)


def rect_sketch(body, name, plane, w_alias, h_alias, w, h):
    """Fully constrained centred rectangle; width/height driven by spreadsheet aliases."""
    sk = body.newObject('Sketcher::SketchObject', name)
    sk.AttachmentSupport = (origin_feature(body, plane), [''])
    sk.MapMode = 'FlatFace'
    p = [V(-w / 2, -h / 2, 0), V(w / 2, -h / 2, 0), V(w / 2, h / 2, 0), V(-w / 2, h / 2, 0)]
    for i in range(4):
        sk.addGeometry(Part.LineSegment(p[i], p[(i + 1) % 4]), False)
    for i in range(4):
        sk.addConstraint(Sketcher.Constraint('Coincident', i, 2, (i + 1) % 4, 1))
    sk.addConstraint(Sketcher.Constraint('Horizontal', 0))
    sk.addConstraint(Sketcher.Constraint('Horizontal', 2))
    sk.addConstraint(Sketcher.Constraint('Vertical', 1))
    sk.addConstraint(Sketcher.Constraint('Vertical', 3))
    sk.addConstraint(Sketcher.Constraint('Symmetric', 0, 1, 1, 2, -1, 1))   # centred on origin
    iw = sk.addConstraint(Sketcher.Constraint('DistanceX', 0, 1, 0, 2, w))
    ih = sk.addConstraint(Sketcher.Constraint('DistanceY', 1, 1, 1, 2, h))
    sk.renameConstraint(iw, 'width')
    sk.renameConstraint(ih, 'height')
    sk.setExpression('Constraints.width', 'Params.' + w_alias)
    sk.setExpression('Constraints.height', 'Params.' + h_alias)
    return sk


def edges_parallel_to(shape, axis, at=None):
    names = []
    for i, e in enumerate(shape.Edges):
        if len(e.Vertexes) != 2:
            continue
        d = e.Vertexes[1].Point - e.Vertexes[0].Point
        if d.Length < 1e-6:
            continue
        d.normalize()
        if abs(d.dot(axis)) > 0.999:
            names.append('Edge%d' % (i + 1))
    return names


def face_at(shape, axis, value, tol=0.01):
    for i, f in enumerate(shape.Faces):
        c = f.CenterOfMass
        if abs(c.dot(axis) - value) < tol and f.Surface.__class__.__name__ == 'Plane':
            n = f.normalAt(0, 0)
            if abs(abs(n.dot(axis)) - 1) < 1e-6:
                return 'Face%d' % (i + 1)
    raise RuntimeError('face not found')


def prim(body, kind, name, **props):
    o = body.newObject('PartDesign::' + kind, name)
    for k, v in props.items():
        setattr(o, k, v)
    return o


def build():
    doc = App.newDocument('VisionAid_Pod')
    P = {a: v for a, v, _ in PARAMS}

    # ------------------------------------------------ parameters
    ss = doc.addObject('Spreadsheet::Sheet', 'Params')
    ss.set('A1', 'Parameter'); ss.set('B1', 'Value (mm / deg)'); ss.set('C1', 'Meaning')
    for r, (a, v, c) in enumerate(PARAMS, start=2):
        ss.set('A%d' % r, a); ss.set('B%d' % r, str(v)); ss.set('C%d' % r, c)
        ss.setAlias('B%d' % r, a)
    doc.recompute()

    W, H, D, t = P['PodW'], P['PodH'], P['BaseD'], P['WallT']

    # ------------------------------------------------ base shell
    body = doc.addObject('PartDesign::Body', 'BaseShell')
    sk = rect_sketch(body, 'ShellProfile', 'XZ_Plane', 'PodW', 'PodH', W, H)
    pad = body.newObject('PartDesign::Pad', 'ShellPad')
    pad.Profile = sk
    pad.Length = D
    pad.setExpression('Length', 'Params.BaseD')
    doc.recompute()
    bb = pad.Shape.BoundBox
    if bb.YMin < -0.1:                       # XZ sketch normal is -Y in FreeCAD: pad forward instead
        pad.Reversed = True
        doc.recompute()
    fil = body.newObject('PartDesign::Fillet', 'CornerFillet')
    fil.Base = (pad, edges_parallel_to(pad.Shape, V(0, 1, 0)))
    fil.Radius = P['CornerR']
    fil.setExpression('Radius', 'Params.CornerR')
    doc.recompute()
    shell = body.newObject('PartDesign::Thickness', 'Hollow')
    shell.Base = (fil, [face_at(fil.Shape, V(0, 1, 0), D)])      # open the front face
    shell.Value = t
    shell.setExpression('Value', 'Params.WallT')
    shell.Reversed = True                                        # wall grows inward
    shell.Join = 'Intersection'
    doc.recompute()

    # Pi 5 mounting bosses (Pi hole pattern 58 x 49 mm) with 3.6 mm heat-set insert holes
    for i, (x, z) in enumerate([(-39.0, 24.5), (19.0, 24.5), (-39.0, -24.5), (19.0, -24.5)]):
        b = prim(body, 'AdditiveCylinder', 'PiBoss%d' % (i + 1), Radius=3.25, Height=P['PiBoss'] + 0.5)
        b.Placement = App.Placement(V(x, t - 0.5, z), rot_y_axis())
        b.setExpression('Height', 'Params.PiBoss + 0.5')
        h = prim(body, 'SubtractiveCylinder', 'PiInsert%d' % (i + 1), Radius=1.8, Height=P['PiBoss'])
        h.Placement = App.Placement(V(x, t + 0.5, z), rot_y_axis())
    # lid screw posts in the four corners, M3 heat-set insert holes from the front
    px, pz = W / 2 - 7.0, H / 2 - 7.0
    for i, (x, z) in enumerate([(-px, pz), (px, pz), (-px, -pz), (px, -pz)]):
        b = prim(body, 'AdditiveCylinder', 'LidPost%d' % (i + 1), Radius=3.5, Height=D - t + 0.5)
        b.Placement = App.Placement(V(x, t - 0.5, z), rot_y_axis())
        h = prim(body, 'SubtractiveCylinder', 'LidInsert%d' % (i + 1), Radius=2.0, Height=7)
        h.Placement = App.Placement(V(x, D - 7, z), rot_y_axis())
    doc.recompute()

    # ventilation: side slots (through both side walls) and top/bottom slots for the Pi active cooler
    vs = prim(body, 'SubtractiveBox', 'SideVents', Length=W + 10, Width=3, Height=30)
    vs.Placement = App.Placement(V(-W / 2 - 5, 16, -15), App.Rotation())
    for i in range(1, 5):
        v = prim(body, 'SubtractiveBox', 'SideVent%d' % (i + 1), Length=W + 10, Width=3, Height=30)
        v.Placement = App.Placement(V(-W / 2 - 5, 16 + 6 * i, -15), App.Rotation())
    for i in range(6):
        v = prim(body, 'SubtractiveBox', 'TopVent%d' % (i + 1), Length=3, Width=18, Height=H + 10)
        v.Placement = App.Placement(V(-22 + 8 * i, 14, -H / 2 - 5), App.Rotation())
    # USB-C power cable slot in the bottom wall, under the Pi 5 USB-C port (x = -42.5 + 11.2)
    usb = prim(body, 'SubtractiveBox', 'USBCSlot', Length=14, Width=10, Height=t + 4)
    usb.Placement = App.Placement(V(-31.3 - 7, t + P['PiBoss'] - 3, -H / 2 - 2), App.Rotation())

    # GoPro-style 2-finger mount on the back (fits a standard 3-finger chest-harness buckle, M5 bolt)
    T, G, L, R = P['FingerT'], P['FingerGap'], P['FingerL'], P['FingerR']
    zc = 12.0
    for i, s in enumerate((-1, 1)):
        xf = s * (G / 2 + T / 2) - T / 2
        f = prim(body, 'AdditiveBox', 'Finger%d' % (i + 1), Length=T, Width=L + 0.5, Height=2 * R)
        f.Placement = App.Placement(V(xf, -L, zc - R), App.Rotation())
        tip = prim(body, 'AdditiveCylinder', 'FingerTip%d' % (i + 1), Radius=R, Height=T)
        tip.Placement = App.Placement(V(xf, -L, zc), App.Rotation(V(0, 1, 0), 90))
    bolt = prim(body, 'SubtractiveCylinder', 'BoltHole', Radius=P['BoltD'] / 2, Height=4 * (T + G))
    bolt.Placement = App.Placement(V(-2 * (T + G), -L, zc), App.Rotation(V(0, 1, 0), 90))
    doc.recompute()
    # FEA iteration v1 -> v2: 1.5 mm fillet where the fingers meet the back wall (removes the sharp-corner
    # stress singularity found in the mesh-convergence study, see outputs/fea/README.md)
    root = [('Edge%d' % (i + 1)) for i, e in enumerate(bolt.Shape.Edges)
            if all(abs(v.Point.y) < 1e-6 for v in e.Vertexes)
            and max(abs(v.Point.x) for v in e.Vertexes) <= G / 2 + T + 1e-6
            and max(abs(v.Point.z - zc) for v in e.Vertexes) <= R + 1e-6]
    ff = body.newObject('PartDesign::Fillet', 'FingerRootFillet')
    ff.Base = (bolt, root)
    ff.Radius = 1.5
    doc.recompute()
    print('finger-root fillet on %d edges, valid=%s' % (len(root), ff.Shape.isValid()))

    # ------------------------------------------------ front lid
    lid = doc.addObject('PartDesign::Body', 'FrontLid')
    lb = prim(lid, 'AdditiveBox', 'LidPlate', Length=W, Width=P['LidT'], Height=H)
    lb.Placement = App.Placement(V(-W / 2, D, -H / 2), App.Rotation())
    doc.recompute()
    lf = lid.newObject('PartDesign::Fillet', 'LidCorners')
    lf.Base = (lb, edges_parallel_to(lb.Shape, V(0, 1, 0)))
    lf.Radius = P['CornerR']
    lf.setExpression('Radius', 'Params.CornerR')
    doc.recompute()
    for i, (x, z) in enumerate([(-px, pz), (px, pz), (-px, -pz), (px, -pz)]):
        h = prim(lid, 'SubtractiveCylinder', 'LidScrew%d' % (i + 1), Radius=1.6, Height=P['LidT'] + 2)
        h.Placement = App.Placement(V(x, D - 1, z), rot_y_axis())
        cb = prim(lid, 'SubtractiveCylinder', 'LidCounterbore%d' % (i + 1), Radius=2.9, Height=2)
        cb.Placement = App.Placement(V(x, D + P['LidT'] - 1.5, z), rot_y_axis())

    # housing layout on the lid (x, z of the housing centre)
    lay = {'Head': (0, 27), 'Left': (-29.5, 2), 'Right': (29.5, 2), 'Camera': (-22, -26), 'Lidar': (20, -25)}
    win = {'Head': (34, 14), 'Left': (34, 14), 'Right': (34, 14), 'Camera': (20, 14), 'Lidar': (26, 10)}
    for k, (x, z) in lay.items():
        ww, wh = win[k]
        c = prim(lid, 'SubtractiveBox', 'Window' + k, Length=ww, Width=P['LidT'] + 2, Height=wh)
        c.Placement = App.Placement(V(x - ww / 2, D - 1, z - wh / 2), App.Rotation())
    doc.recompute()

    # ------------------------------------------------ angled sensor housings (Part CSG, parametric)
    yl = D + P['LidT']

    def housing(name, x, z, w, h, d, rot, holes):
        outer = doc.addObject('Part::Box', name + '_Outer')
        outer.Length, outer.Width, outer.Height = w, d + 8, h
        outer.Placement = App.Placement(V(-w / 2, -8, -h / 2), App.Rotation())
        inner = doc.addObject('Part::Box', name + '_Cavity')
        inner.Length, inner.Width, inner.Height = w - 4, d + 8 - 2 + 0.5, h - 4      # 2 mm front wall
        inner.Placement = App.Placement(V(-w / 2 + 2, -8.5, -h / 2 + 2), App.Rotation())
        cut = doc.addObject('Part::Cut', name + '_Shell')
        cut.Base, cut.Tool = outer, inner
        tools = []
        for i, (hx, hz, r, kind) in enumerate(holes):
            if kind == 'round':
                c = doc.addObject('Part::Cylinder', '%s_Hole%d' % (name, i + 1))
                c.Radius, c.Height = r, 6
                c.Placement = App.Placement(V(hx, d - 3, hz), rot_y_axis())
            else:
                c = doc.addObject('Part::Box', '%s_Hole%d' % (name, i + 1))
                c.Length, c.Width, c.Height = r[0], 6, r[1]
                c.Placement = App.Placement(V(hx - r[0] / 2, d - 3, hz - r[1] / 2), App.Rotation())
            tools.append(c)
        if len(tools) == 1:
            fused_tools = tools[0]
        else:
            fused_tools = doc.addObject('Part::MultiFuse', name + '_Openings')
            fused_tools.Shapes = tools
        h_obj = doc.addObject('Part::Cut', name + 'Housing')
        h_obj.Base, h_obj.Tool = cut, fused_tools
        h_obj.Placement = App.Placement(V(x, yl, z), rot)
        # lid-side cut so the housing does not poke through the lid backwards
        clip = doc.addObject('Part::Box', name + '_Clip')
        clip.Length, clip.Width, clip.Height = 200, 40, 200
        clip.Placement = App.Placement(V(-100, D - 40, -100), App.Rotation())
        final = doc.addObject('Part::Cut', name + 'HousingFinal')
        final.Base, final.Tool = h_obj, clip
        final.addProperty('App::PropertyPlacement', 'MountPlacement').MountPlacement = App.Placement(V(x, yl, z), rot)
        return final

    us_holes = [(-13, 0, 8.3, 'round'), (13, 0, 8.3, 'round')]   # 16 mm transducers, 26 mm apart
    hs = [
        housing('Head', *lay['Head'], P['SensW'], P['SensH'], P['SensD'],
                App.Rotation(V(1, 0, 0), P['PitchHead']), us_holes),
        housing('Left', *lay['Left'], P['SensW'], P['SensH'], P['SensD'],
                App.Rotation(V(0, 0, 1), P['YawLR']), us_holes),
        housing('Right', *lay['Right'], P['SensW'], P['SensH'], P['SensD'],
                App.Rotation(V(0, 0, 1), -P['YawLR']), us_holes),
        housing('Camera', *lay['Camera'], 30, 30, 14, App.Rotation(), [(0, 2, 5.5, 'round')]),
        housing('Lidar', *lay['Lidar'], 40, 26, 27, App.Rotation(V(1, 0, 0), -P['PitchLidar']),
                [(0, 0, (30, 14), 'rect')]),
    ]
    front = doc.addObject('Part::MultiFuse', 'FrontAssembly')
    front.Shapes = [lid] + hs
    doc.recompute()

    # ------------------------------------------------ electronics (reference geometry, simplified)
    elec = doc.addObject('App::DocumentObjectGroup', 'Electronics')
    ypi = t + P['PiBoss']

    def block(name, x0, y0, z0, lx, ly, lz, color):
        b = doc.addObject('Part::Box', name)
        b.Length, b.Width, b.Height = lx, ly, lz
        b.Placement = App.Placement(V(x0, y0, z0), App.Rotation())
        elec.addObject(b)
        b.addProperty('App::PropertyColor', 'RefColor').RefColor = color
        return b

    block('RPi5_PCB', -42.5, ypi, -28, 85, 1.6, 56, (0.1, 0.5, 0.1))
    block('RPi5_ActiveCooler', -26, ypi + 1.6, -10, 36, 9, 32, (0.6, 0.6, 0.65))
    block('RPi5_USB_Ethernet', 21.5, ypi + 1.6, -26, 21, 16, 52, (0.75, 0.75, 0.75))
    yc = ypi + 1.6 + P['StandH']
    if os.path.exists(PCB_STEP):
        sh = Part.read(PCB_STEP)
        m = App.Matrix(-1, 0, 0, 0,   0, 0, 1, 0,   0, 1, 0, 0,   0, 0, 0, 1)   # x->-x, y->z, z->y
        sh = sh.transformGeometry(m)
        bb = sh.BoundBox
        board_back = bb.YMin
        sh.translate(V(-(bb.XMin + bb.XMax) / 2, yc - board_back, -(bb.ZMin + bb.ZMax) / 2))
        pcb = doc.addObject('Part::Feature', 'CarrierPCB_from_KiCad')
        pcb.Shape = sh
        elec.addObject(pcb)
    # Tang Nano 9K on 8.5 mm sockets (module footprint centre at board x=52.2, y=30 -> pod coords)
    # (the Tang Nano 9K module + its sockets are now part of the KiCad STEP via 3d/TangNano9K_Module.step)
    for i in range(4):
        st = doc.addObject('Part::Cylinder', 'Standoff%d' % (i + 1))
        st.Radius, st.Height = 2.5, P['StandH']
        x, z = [(-39.0, 24.5), (19.0, 24.5), (-39.0, -24.5), (19.0, -24.5)][i]
        st.Placement = App.Placement(V(x, ypi + 1.6, z), rot_y_axis())
        elec.addObject(st)
    # sensors inside the housings (simplified: PCB + transducers / lens), same placement as housing
    def sensor_part(name, housing_obj, shapes, color):
        sh = Part.makeCompound(shapes)
        sh.Placement = housing_obj.MountPlacement
        o = doc.addObject('Part::Feature', name)
        o.Shape = sh
        o.addProperty('App::PropertyColor', 'RefColor').RefColor = color
        elec.addObject(o)

    d = P['SensD']
    for nm, hobj in (('US_Head', hs[0]), ('US_Left', hs[1]), ('US_Right', hs[2])):
        pcb = Part.makeBox(43.5, 1.6, 20, V(-21.75, d - 14.1, -10))   # RCWL-1601 board (approx.)
        t1 = Part.makeCylinder(8, 12, V(-13, d - 12.5, 0), V(0, 1, 0))
        t2 = Part.makeCylinder(8, 12, V(13, d - 12.5, 0), V(0, 1, 0))
        sensor_part(nm + '_RCWL1601', hobj, [pcb, t1, t2], (0.1, 0.3, 0.7))
    cam_pcb = Part.makeBox(25, 1.0, 24, V(-12.5, 14 - 2 - 7 - 1, -12))
    cam_lens = Part.makeCylinder(4.5, 7, V(0, 14 - 2 - 7, 2), V(0, 1, 0))
    sensor_part('Camera_Module3', hs[3], [cam_pcb, cam_lens], (0.1, 0.5, 0.1))
    sensor_part('TFLuna_LiDAR', hs[4], [Part.makeBox(35, 13.5, 21.25, V(-17.5, 27 - 2.2 - 13.5, -10.6))],
                (0.2, 0.2, 0.2))
    doc.recompute()
    return doc


def report(doc):
    lines = []
    for name in ('BaseShell', 'FrontAssembly'):
        o = doc.getObject(name)
        s = o.Shape
        bb = s.BoundBox
        lines.append('%-14s valid=%s volume=%.1f cm3  bbox X %.1f..%.1f Y %.1f..%.1f Z %.1f..%.1f' % (
            name, s.isValid(), s.Volume / 1000, bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))
    # interference check: electronics vs printed parts
    printed = doc.getObject('BaseShell').Shape.fuse(doc.getObject('FrontAssembly').Shape)
    for o in doc.getObject('Electronics').Group:
        if o.TypeId == 'Part::Cylinder':
            continue
        common = o.Shape.common(printed).Volume
        lines.append('interference %-24s %.2f mm3' % (o.Name, common))
    return '\n'.join(lines)


if __name__ == '__main__' or True:
    os.makedirs(OUT, exist_ok=True)
    d = build()
    txt = report(d)
    print(txt)
    open(os.path.join(OUT, 'model_report.txt'), 'w').write(txt + '\n')
    d.saveAs(os.path.join(CAD, 'VisionAid_Pod.FCStd'))
    import Import
    Import.export([d.getObject('BaseShell')], os.path.join(OUT, 'BaseShell.step'))
    Import.export([d.getObject('FrontAssembly')], os.path.join(OUT, 'FrontLid_with_housings.step'))
    import Mesh
    Mesh.export([d.getObject('BaseShell')], os.path.join(OUT, 'BaseShell.stl'))
    Mesh.export([d.getObject('FrontAssembly')], os.path.join(OUT, 'FrontLid_with_housings.stl'))
    print('saved VisionAid_Pod.FCStd + STEP/STL')
