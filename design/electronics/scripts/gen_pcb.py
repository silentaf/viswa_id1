"""Build the VisionAid carrier PCB (KiCad 9) from the schematic netlist: outline, placement, nets.
Routing is done afterwards by FreeRouting (see route_pcb.sh), then GND pours are added by finish_pcb.py.

Board = Raspberry Pi 5 outline: 85 x 56 mm, 3 mm corner radius, same 4 mounting holes (M2.5),
stacked above the Pi on 20 mm standoffs and linked by a 40-way IDC ribbon.
Run with: ../../../tools/kicad.sh python gen_pcb.py
"""
import os
import pcbnew
from sexpr import parse, find, first

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
FPDIR = os.path.join(HERE, '..', '..', '..', 'tools', 'kicad-root', 'usr', 'share', 'kicad', 'footprints')
LOCAL = {'VisionAid': os.path.join(OUT, 'VisionAid.pretty')}
OX, OY = 100.0, 100.0          # board origin on the KiCad canvas (mm)
W, H, R = 85.0, 56.0, 3.0      # Pi 5 outline
HOLES = [(3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)]
MM = pcbnew.FromMM


def P(x, y):
    return pcbnew.VECTOR2I(MM(OX + x), MM(OY + y))


# ---------------------------------------------------------------- placement (board coordinates, mm)
# (x, y, rotation_deg) - x to the right, y down, origin = board top-left corner (GPIO-header edge).
PLACE = {
    # 40-pin header: pin 1 at the same spot as on the Pi (odd row inboard, 5 V pins on the edge row)
    'J1': (8.37, 4.77, 90),
    # Tang Nano 9K: long axis along X, USB-C flush with the right edge for programming access
    'U1': (52.2, 30.0, -90),
    'BZ1': (66.5, 9.5, 0),
    # bottom edge: sensor connectors (JST-XH 4-pin), cable exits downward
    'J2': (11.0, 47.5, 0), 'J3': (27.0, 47.5, 0), 'J4': (43.0, 47.5, 0), 'J5': (68.5, 47.5, 0),
    # left edge: buttons, IMU, motors
    'J9': (4.5, 10.0, -90), 'J8': (4.5, 24.0, -90), 'J6': (4.5, 38.0, -90), 'J7': (13.3, 10.0, -90),
    'D5': (13.3, 21.5, 90), 'R18': (13.3, 25.5, 90),
    'H1': (3.5, 3.5, 0), 'H2': (61.5, 3.5, 0), 'H3': (3.5, 52.5, 0), 'H4': (61.5, 52.5, 0),
}
# groups of small SMD parts placed in a grid under the Tang Nano (between its two socket rows)
GROUPS = [
    # (x0, y0, x1, refs)
    (21.5, 22.0, 41.0, ['U2', 'F1', 'C1', 'C2', 'C3', 'C4', 'D1', 'C5']),
    (42.5, 22.0, 62.5, ['Q1', 'Q2', 'Q3', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'D2', 'D3', 'D4']),
    (64.0, 22.0, 82.5, ['R7', 'R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15', 'R16', 'R17',
                        'C7', 'C8', 'C9', 'C6']),
]
TEST_POINTS = ['TP1', 'TP2', 'TP3', 'TP4', 'TP5', 'TP6']   # row in the strip between header and module
SILK_LABELS = [  # (text, x, y, size, layer)
    ('J2 US-L', 11.0 + 3.75, 52.9, 1.0, 'F'), ('J3 US-R', 27.0 + 3.75, 52.9, 1.0, 'F'),
    ('J4 US-H', 43.0 + 3.75, 52.9, 1.0, 'F'), ('J5 LIDAR', 68.5 + 3.75, 52.9, 1.0, 'F'),
    ('J9 BTN', 8.5, 13.5, 0.8, 'F90'), ('J8 IMU', 8.5, 27.5, 0.8, 'F90'), ('J6 MOT-L', 8.5, 41.0, 0.8, 'F90'),
    ('J7 MOT-R', 13.3, 17.4, 0.8, 'F'), ('PWR LED', 13.3, 28.6, 0.8, 'F'),
    ('J1 GPIO ribbon, pin 1 = square pad', 32.5, 8.3, 0.8, 'F'),
    ('VisionAid carrier v0.1', 42.5, 26.0, 2.0, 'B'), ('Team SVNIT - Vishwakarma Awards 2026-27', 42.5, 30.0, 1.2, 'B'),
    ('FPGA safety island + sensor/haptic I/O for Raspberry Pi 5', 42.5, 33.0, 1.0, 'B'),
]


def load_netlist(path):
    t = parse(open(path).read())
    comps = {}
    for c in find(first(t, 'components'), 'comp'):
        comps[first(c, 'ref')[1]] = (first(c, 'value')[1], first(c, 'footprint')[1])
    nets = []
    for n in find(first(t, 'nets'), 'net'):
        nodes = [(first(nd, 'ref')[1], first(nd, 'pin')[1]) for nd in find(n, 'node')]
        nets.append((first(n, 'name')[1], nodes))
    return comps, nets


def load_fp(fpid):
    lib, name = fpid.split(':')
    path = LOCAL.get(lib, os.path.join(FPDIR, lib + '.pretty'))
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise RuntimeError('footprint not found: ' + fpid)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def courtyard_size(fp):
    bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
    if bb.GetWidth() == 0:
        bb = fp.GetBoundingBox(False)
    return pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())


def edge(board, shape, **kw):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(shape)
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(MM(0.1))
    if shape == pcbnew.SHAPE_T_SEGMENT:
        s.SetStart(kw['a'])
        s.SetEnd(kw['b'])
    else:
        s.SetArcGeometry(kw['a'], kw['m'], kw['b'])
    board.Add(s)


def outline(board):
    import math
    k = R * (1 - math.cos(math.radians(45)))
    edge(board, pcbnew.SHAPE_T_SEGMENT, a=P(R, 0), b=P(W - R, 0))
    edge(board, pcbnew.SHAPE_T_SEGMENT, a=P(W, R), b=P(W, H - R))
    edge(board, pcbnew.SHAPE_T_SEGMENT, a=P(W - R, H), b=P(R, H))
    edge(board, pcbnew.SHAPE_T_SEGMENT, a=P(0, H - R), b=P(0, R))
    edge(board, pcbnew.SHAPE_T_ARC, a=P(0, R), m=P(k, k), b=P(R, 0))
    edge(board, pcbnew.SHAPE_T_ARC, a=P(W - R, 0), m=P(W - k, k), b=P(W, R))
    edge(board, pcbnew.SHAPE_T_ARC, a=P(W, H - R), m=P(W - k, H - k), b=P(W - R, H))
    edge(board, pcbnew.SHAPE_T_ARC, a=P(R, H), m=P(k, H - k), b=P(0, H - R))


def silk_text(board, txt, x, y, size, side='F'):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(txt)
    t.SetPosition(P(x, y))
    t.SetLayer(pcbnew.B_SilkS if side == 'B' else pcbnew.F_SilkS)
    if side == 'F90':
        t.SetTextAngle(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T))
    if side == 'B':
        t.SetMirrored(True)
    t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
    t.SetTextThickness(MM(size * 0.15))
    board.Add(t)


def setup_rules(board):
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    ns = ds.m_NetSettings
    dflt = ns.GetDefaultNetclass()
    dflt.SetTrackWidth(MM(0.25))
    dflt.SetClearance(MM(0.2))
    dflt.SetViaDiameter(MM(0.6))
    dflt.SetViaDrill(MM(0.3))
    try:
        pw = pcbnew.NETCLASS('Power')
        # 5 V path carries Pi-side current (<= 500 mA PTC): 0.5 mm. 3.3 V loads total ~250 mA: 0.3 mm.
        pw.SetTrackWidth(MM(0.5))
        pw.SetClearance(MM(0.2))
        pw.SetViaDiameter(MM(0.8))
        pw.SetViaDrill(MM(0.4))
        ns.SetNetclass('Power', pw)
        p3 = pcbnew.NETCLASS('Power3V3')
        p3.SetTrackWidth(MM(0.3))
        p3.SetClearance(MM(0.2))
        p3.SetViaDiameter(MM(0.6))
        p3.SetViaDrill(MM(0.3))
        ns.SetNetclass('Power3V3', p3)
        for n in ('+5V', 'GND', '/PI_5V', '/TN_5V'):
            ns.SetNetclassPatternAssignment(n, 'Power')
        ns.SetNetclassPatternAssignment('+3V3', 'Power3V3')
        print('netclasses: Power 0.5 mm, Power3V3 0.3 mm, default 0.25 mm')
    except Exception as e:  # API differences between KiCad versions
        print('netclass setup skipped:', e)
    ds.m_MinClearance = MM(0.2)
    ds.m_TrackMinWidth = MM(0.15)   # FreeRouting necks down at fine pads; 6 mil is standard fab capability
    ds.m_ViasMinSize = MM(0.6)
    ds.m_MinThroughDrill = MM(0.3)
    ds.m_CopperEdgeClearance = MM(0.3)


def main():
    comps, nets = load_netlist(os.path.join(OUT, 'VisionAid_Carrier.net'))
    board = pcbnew.BOARD()
    setup_rules(board)
    outline(board)

    fps = {}
    for ref, (value, fpid) in sorted(comps.items()):
        fp = load_fp(fpid)
        fp.SetReference(ref)
        fp.SetValue(value)
        board.Add(fp)
        fps[ref] = fp

    def put(ref, x, y, rot):
        fp = fps[ref]
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(P(x, y))

    for ref, (x, y, rot) in PLACE.items():
        put(ref, x, y, rot)

    # grid placement of small parts: anchor each part by its courtyard so nothing overlaps
    for x0, y0, x1, refs in GROUPS:
        x, y, row_h = x0, y0, 0.0
        for ref in refs:
            w, h = courtyard_size(fps[ref])
            if x + w > x1:
                x, y, row_h = x0, y + row_h + 0.3, 0.0
            fp = fps[ref]
            fp.SetPosition(P(0, 0))
            bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
            dx = pcbnew.ToMM(fp.GetPosition().x - bb.GetLeft())
            dy = pcbnew.ToMM(fp.GetPosition().y - bb.GetTop())
            put(ref, x + dx, y + dy, 0)
            x += w + 0.3
            row_h = max(row_h, h)
        if y + row_h > 39.5:
            print(f'WARNING: group starting {refs[0]} overflows under-module area (bottom {y + row_h:.1f} mm)')

    for i, ref in enumerate(TEST_POINTS):
        put(ref, 22.0 + i * 6.0, 12.5, 0)

    # nets
    for name, nodes in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        for ref, pin in nodes:
            for pad in fps[ref].Pads():
                if pad.GetNumber() == pin:
                    pad.SetNet(ni)

    for txt, x, y, size, side in SILK_LABELS:
        silk_text(board, txt, x, y, size, side)

    # Reference text: parts under the module and labelled connectors keep their reference on F.Fab only
    fab_only = {r for _, _, _, refs in GROUPS for r in refs}
    fab_only |= {'J1', 'J2', 'J3', 'J4', 'J5', 'J6', 'J7', 'J8', 'J9', 'D5', 'R18', 'H1', 'H2', 'H3', 'H4'}
    for ref in fab_only:
        fps[ref].Reference().SetLayer(pcbnew.F_Fab)
    for fp in fps.values():
        fp.Value().SetVisible(False)

    tb = board.GetTitleBlock()
    tb.SetTitle('VisionAid Carrier Board')
    tb.SetRevision('v0.1')
    tb.SetDate('2026-10-08')
    tb.SetCompany('Team SVNIT - Vishwakarma Awards 2026-27')
    path = os.path.join(OUT, 'VisionAid_Carrier.kicad_pcb')
    board.Save(path)
    print('saved', path, len(fps), 'footprints')


if __name__ == '__main__':
    main()
