"""Generate the VisionAid carrier-board schematic (KiCad 9) from a parts/netlist description.

Every connection is made with a short wire stub + net label (or power symbol) at the pin,
so the schematic stays readable and the netlist is exactly what is written below.
Run:  ../../../tools/kicad.sh python gen_schematic.py   (or plain python3)
"""
import os
import uuid
from sexpr import parse, dump, find, first, Sym as S

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
PROJECT = 'VisionAid_Carrier'
KICAD_SYMBOLS = os.path.join(HERE, '..', '..', '..', 'tools', 'kicad-root', 'usr', 'share', 'kicad', 'symbols')
LOCAL_LIB = os.path.join(OUT, 'VisionAid.kicad_sym')
NS = uuid.UUID('6f1c1b8e-2d5a-4f43-9a51-7a1e0c2b9d10')
ROOT = str(uuid.uuid5(NS, 'root'))
STUB = 2.54
POWER_NETS = {'+5V': 'power:+5V', '+3V3': 'power:+3V3', 'GND': 'power:GND'}

_uid = 0


def uid(tag=''):
    global _uid
    _uid += 1
    return str(uuid.uuid5(NS, f'{tag}-{_uid}'))


# ---------------------------------------------------------------- library symbols
_lib_cache = {}


def load_lib(name):
    if name not in _lib_cache:
        path = LOCAL_LIB if name == 'VisionAid' else os.path.join(KICAD_SYMBOLS, name + '.kicad_sym')
        tree = parse(open(path).read())
        _lib_cache[name] = {s[1]: s for s in find(tree, 'symbol')}
    return _lib_cache[name]


def flat_symbol(lib_id):
    """Return a flattened copy of a library symbol named 'Lib:Name' (resolves 'extends')."""
    lib, name = lib_id.split(':')
    syms = load_lib(lib)
    sym = syms[name]
    ext = first(sym, 'extends')
    if not ext:
        out = [S('symbol'), lib_id] + [c for c in sym[2:]]
        return out
    base = syms[ext[1]]
    derived_props = {p[1]: p for p in find(sym, 'property')}
    out = [S('symbol'), lib_id]
    for c in base[2:]:
        if isinstance(c, list) and c and c[0] == 'property':
            out.append(derived_props.pop(c[1], c))
        elif isinstance(c, list) and c and c[0] == 'symbol':
            sub = list(c)
            sub[1] = sub[1].replace(ext[1], name, 1)
            out.append(sub)
        else:
            out.append(c)
    # insert remaining derived-only properties right after the last property
    idx = max(i for i, c in enumerate(out) if isinstance(c, list) and c and c[0] == 'property') + 1
    for p in derived_props.values():
        out.insert(idx, p)
        idx += 1
    return out


def lib_pins(lib_id):
    pins = {}

    def walk(node):
        for c in node:
            if isinstance(c, list):
                if c and c[0] == 'pin':
                    at = first(c, 'at')
                    pins[first(c, 'number')[1]] = (float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0)
                else:
                    walk(c)
    walk(flat_symbol(lib_id))
    return pins


def lib_props(lib_id):
    return {p[1]: p for p in find(flat_symbol(lib_id), 'property')}


# ---------------------------------------------------------------- geometry
def xform(px, py, x, y, rot):
    """Library point (y up) -> schematic point (y down) for a symbol at (x, y) rotated rot deg CCW."""
    import math
    sx, sy = px, -py
    t = math.radians(rot)
    c, s = round(math.cos(t), 6), round(math.sin(t), 6)
    return round(x + sx * c + sy * s, 4), round(y - sx * s + sy * c, 4)


DIRV = {0: (1, 0), 90: (0, -1), 180: (-1, 0), 270: (0, 1)}


def outward(pin_angle, rot):
    return int((pin_angle + rot + 180) % 360)


# ---------------------------------------------------------------- schematic builder
items = []
used_lib_ids = set()
pwr_count = [0]


def font(size=1.27, bold=False):
    f = [S('font'), [S('size'), size, size]]
    if bold:
        f.append([S('bold'), S('yes')])
    return f


def prop(name, value, x, y, hide=False, justify=None, angle=0):
    eff = [S('effects'), font()]
    if justify:
        eff.append([S('justify'), S(justify)])
    if hide:
        eff.append([S('hide'), S('yes')])
    return [S('property'), name, value, [S('at'), x, y, angle], eff]


def snap(v, g=1.27):
    return round(round(v / g) * g, 4)


def place_symbol(lib_id, ref, value, x, y, rot=0, footprint='', extra=None, power=False, hide_value=False,
                 pos=None):
    x, y = snap(x), snap(y)
    used_lib_ids.add(lib_id)
    lp = lib_props(lib_id)
    pins = lib_pins(lib_id)
    props = []
    # Default text placement. Field angle = symbol rotation so the text stays horizontal on screen.
    auto = {}
    if len(pins) == 2 and not power:
        (ax1, ay1), (ax2, ay2) = [xform(px, py, x, y, rot) for px, py, _ in pins.values()]
        if abs(ax1 - ax2) < 0.01:   # vertical body -> text on the right
            auto = {'Reference': (x + 2.54, y - 1.27, 'left'), 'Value': (x + 2.54, y + 1.27, 'left')}
        else:                        # horizontal body -> text above / below
            auto = {'Reference': (x, y - 3.05, None), 'Value': (x, y + 3.3, None)}
    for key, val in (('Reference', ref), ('Value', value)):
        if pos and key in pos:
            ax, ay, just = pos[key]
        elif key in auto:
            ax, ay, just = auto[key]
        else:
            lx, ly = float(lp[key][3][1]), float(lp[key][3][2])
            ax, ay = xform(lx, ly, x, y, rot)
            dx = ax - x
            just = 'left' if dx > 0.5 else ('right' if dx < -0.5 else None)
        hide = (power and key == 'Reference') or (hide_value and key == 'Value')
        props.append(prop(key, val, ax, ay, hide=hide, justify=just, angle=rot if rot in (90, 270) else 0))
    props.append(prop('Footprint', footprint, x, y, hide=True, angle=rot))
    ds = lp.get('Datasheet')
    props.append(prop('Datasheet', ds[2] if ds else '~', x, y, hide=True, angle=rot))
    for k, v in (extra or {}).items():
        props.append(prop(k, v, x, y, hide=True, angle=rot))
    node = [S('symbol'), [S('lib_id'), lib_id], [S('at'), x, y, rot], [S('unit'), 1],
            [S('exclude_from_sim'), S('no')],
            [S('in_bom'), S('no' if power or ref.startswith(('H', 'TP')) else 'yes')],
            [S('on_board'), S('no' if power else 'yes')], [S('dnp'), S('no')], [S('uuid'), uid(ref)]]
    node += props
    for num in pins:
        node.append([S('pin'), num, [S('uuid'), uid(ref + num)]])
    node.append([S('instances'), [S('project'), PROJECT,
                                  [S('path'), '/' + ROOT, [S('reference'), ref], [S('unit'), 1]]]])
    items.append(node)


def wire(x1, y1, x2, y2):
    items.append([S('wire'), [S('pts'), [S('xy'), x1, y1], [S('xy'), x2, y2]],
                  [S('stroke'), [S('width'), 0], [S('type'), S('default')]], [S('uuid'), uid('w')]])


def label(net, x, y, ang):
    just = {0: 'left bottom', 90: 'left bottom', 180: 'right bottom', 270: 'right bottom'}[ang]
    items.append([S('label'), net, [S('at'), x, y, ang], [S('fields_autoplaced'), S('yes')],
                  [S('effects'), font(), [S('justify')] + [S(j) for j in just.split()]], [S('uuid'), uid('l')]])


def power_symbol(net, x, y, out_ang):
    lib_id = POWER_NETS.get(net, net)
    body = 270 if net == 'GND' else 90
    rot = int((out_ang - body) % 360)
    pwr_count[0] += 1
    place_symbol(lib_id, f'#PWR{pwr_count[0]:03d}', net if lib_id.startswith('power:') and net in POWER_NETS
                 else lib_id.split(':')[1], x, y, rot, power=True, hide_value=rot in (90, 270))


def pin_at(lib_id, x, y, rot, num):
    px, py, _ = lib_pins(lib_id)[num]
    return xform(px, py, snap(x), snap(y), rot)


def junction(x, y):
    items.append([S('junction'), [S('at'), x, y], [S('diameter'), 0], [S('color'), 0, 0, 0, 0], [S('uuid'), uid('j')]])


def no_connect(x, y):
    items.append([S('no_connect'), [S('at'), x, y], [S('uuid'), uid('nc')]])


def text(t, x, y, size=1.27, bold=False):
    items.append([S('text'), t, [S('exclude_from_sim'), S('no')], [S('at'), x, y, 0],
                  [S('effects'), font(size, bold), [S('justify'), S('left'), S('bottom')]], [S('uuid'), uid('t')]])


def part(lib_id, ref, value, x, y, nets, rot=0, footprint='', mpn='', nc=(), vpower=True, hide_value=False,
         pos=None):
    """Place a component and attach a label / power symbol to every listed pin.
    vpower: power pins that point sideways get an L-shaped stub so the power symbol stands upright."""
    x, y = snap(x), snap(y)
    place_symbol(lib_id, ref, value, x, y, rot, footprint, {'MPN': mpn} if mpn else None,
                 hide_value=hide_value, pos=pos)
    pins = lib_pins(lib_id)
    for num, (px, py, pa) in pins.items():
        ax, ay = xform(px, py, x, y, rot)
        if num in nets:
            net = nets[num]
            o = outward(pa, rot)
            vx, vy = DIRV[o]
            sx, sy = round(ax + vx * STUB, 4), round(ay + vy * STUB, 4)
            wire(ax, ay, sx, sy)
            if net in POWER_NETS and vpower and o in (0, 180):
                up = net != 'GND'
                ey = round(sy - STUB if up else sy + STUB, 4)
                wire(sx, sy, sx, ey)
                power_symbol(net, sx, ey, 90 if up else 270)
            elif net in POWER_NETS and net != 'GND' and o == 270 and vpower:
                wire(sx, sy, sx + 2.54, sy)
                wire(sx + 2.54, sy, sx + 2.54, sy - 2.54)
                power_symbol(net, sx + 2.54, sy - 2.54, 90)
            elif net in POWER_NETS:
                power_symbol(net, sx, sy, o)
            else:
                label(net, sx, sy, o)
        elif num in nc or nc == 'rest':
            no_connect(ax, ay)


def pwr_flag(net, x, y):
    """PWR_FLAG tells ERC that a net is externally powered (power bank via the Pi header)."""
    x, y = snap(x), snap(y)
    wire(x, y, x, y + STUB)
    pwr_count[0] += 1
    if net in POWER_NETS and net != 'GND':
        power_symbol(net, x, y, 90)
        place_symbol('power:PWR_FLAG', f'#FLG{pwr_count[0]:03d}', 'PWR_FLAG', x, y + STUB, 180, power=True)
        return
    place_symbol('power:PWR_FLAG', f'#FLG{pwr_count[0]:03d}', 'PWR_FLAG', x, y, 0, power=True)
    if net in POWER_NETS:
        power_symbol(net, x, y + STUB, 270)
    else:
        label(net, x, y + STUB, 270)


# ---------------------------------------------------------------- footprints / parts
FP = {
    'R': 'Resistor_SMD:R_0603_1608Metric', 'C': 'Capacitor_SMD:C_0603_1608Metric',
    'C0805': 'Capacitor_SMD:C_0805_2012Metric', 'CP': 'Capacitor_SMD:CP_Elec_6.3x5.8',
    'TANT': 'Capacitor_Tantalum_SMD:CP_EIA-3528-21_Kemet-B', 'SOT223': 'Package_TO_SOT_SMD:SOT-223-3_TabPin2',
    'SOT23': 'Package_TO_SOT_SMD:SOT-23', 'SMA': 'Diode_SMD:D_SMA', 'SOD123': 'Diode_SMD:D_SOD-123',
    'LED': 'LED_SMD:LED_0603_1608Metric', 'PTC': 'Fuse:Fuse_1206_3216Metric',
    'XH4': 'Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical',
    'XH2': 'Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical',
    'PI': 'Connector_PinHeader_2.54mm:PinHeader_2x20_P2.54mm_Vertical',
    'BUZ': 'Buzzer_Beeper:Buzzer_12x9.5RM7.6', 'TP': 'TestPoint:TestPoint_Pad_D1.5mm',
    'HOLE': 'MountingHole:MountingHole_2.7mm_M2.5', 'TN9K': 'VisionAid:TangNano9K_Module',
}


def build():
    # ---------------- POWER
    text('POWER', 20, 30, 2.54, True)
    text('Pi 5 is powered by a USB-C power bank; this board takes 5 V from the Pi 40-pin header (pins 2/4)', 20, 34)
    text('through a 500 mA PTC (protects the Pi 5 V rail). AMS1117 makes +3V3 for sensors, motors, IMU, buttons.', 20, 37)
    part('Device:Polyfuse', 'F1', '500mA PTC', 30, 52, {'1': '+5V', '2': 'PI_5V'}, footprint=FP['PTC'],
         mpn='1206L050 / equivalent')
    part('Device:C', 'C1', '22uF 10V X5R', 52, 52, {'1': '+5V', '2': 'GND'}, footprint='Capacitor_SMD:C_1206_3216Metric')
    part('Device:C', 'C2', '10uF 10V', 72, 52, {'1': '+5V', '2': 'GND'}, footprint=FP['C0805'])
    part('Regulator_Linear:AMS1117-3.3', 'U2', 'AMS1117-3.3', 100, 52, {'3': '+5V', '2': '+3V3', '1': 'GND'},
         footprint=FP['SOT223'], mpn='AMS1117-3.3',
         pos={'Reference': (95, 44.45, 'left'), 'Value': (95, 46.99, 'left')})
    part('Device:C_Polarized', 'C3', '22uF tant', 125, 52, {'1': '+3V3', '2': 'GND'}, footprint=FP['TANT'])
    part('Device:C', 'C4', '100nF', 145, 52, {'1': '+3V3', '2': 'GND'}, footprint=FP['C'])
    text('D1 feeds the Tang Nano 9K 5 V pin and blocks back-feed when its own USB-C is plugged in for programming.', 165, 41)
    part('Device:D_Schottky', 'D1', 'SS14', 172, 50, {'1': 'TN_5V', '2': '+5V'}, footprint=FP['SMA'], mpn='SS14')
    part('Device:C', 'C5', '10uF 10V', 190, 52, {'1': 'TN_5V', '2': 'GND'}, footprint=FP['C0805'])
    part('Device:R', 'R18', '1k', 210, 52, {'1': '+3V3', '2': 'LED_A'}, footprint=FP['R'])
    part('Device:LED', 'D5', 'PWR green', 228, 62, {'1': 'GND', '2': 'LED_A'}, footprint=FP['LED'])
    pwr_flag('+5V', 250, 50)
    pwr_flag('GND', 262, 50)
    pwr_flag('PI_5V', 274, 50)
    pwr_flag('TN_5V', 286, 50)

    # ---------------- RASPBERRY PI HEADER
    text('J1  RASPBERRY PI 5 40-PIN HEADER', 20, 100, 2.54, True)
    text('2x20 pin header + 40-way IDC ribbon to the Pi GPIO header. Board = Pi 5 outline (85 x 56 mm), same', 20, 104)
    text('mounting holes, stacked on 20 mm standoffs above the Pi (clears USB/Ethernet jacks and the active cooler).', 20, 110)
    text('Pi 3V3 (pins 1, 17) intentionally NOT connected: this board has its own 3.3 V regulator.', 20, 113)
    pi = {'2': 'PI_5V', '4': 'PI_5V', '3': 'I2C_SDA', '5': 'I2C_SCL', '8': 'PI_TXD', '10': 'PI_RXD',
          '11': 'PI_HB', '13': 'FPGA_FAULT_N'}
    for g in ('6', '9', '14', '20', '25', '30', '34', '39'):
        pi[g] = 'GND'
    part('Connector_Generic:Conn_02x20_Odd_Even', 'J1', 'RPi5_GPIO_40pin', 45, 150, pi, footprint=FP['PI'], nc='rest',
         vpower=False)
    text('GPIO2=SDA  GPIO3=SCL  GPIO14=TXD  GPIO15=RXD  GPIO17=heartbeat  GPIO27=fault-in', 20, 182)

    # ---------------- FPGA
    text('U1  FPGA SAFETY ISLAND (Sipeed Tang Nano 9K)', 165, 108, 2.54, True)
    text('Only 3.3 V-bank pins of the left header are used. *_1V8 pins are on a 1.8 V bank: unused.', 165, 112)
    left = ['', '', '', '', 'US_L_TRIG', 'US_L_ECHO', 'US_R_TRIG', 'US_R_ECHO', 'US_H_TRIG', 'US_H_ECHO',
            'LIDAR_TX', 'LIDAR_RX', 'PI_TXD', 'PI_RXD', 'PI_HB', 'FPGA_FAULT_N', 'MOT_L_PWM', 'MOT_R_PWM',
            'BUZZ_EN', 'BTN_READ', 'BTN_MODE', 'BTN_QUIET', '', '']
    fn = {str(i + 1): n for i, n in enumerate(left) if n}
    fn['31'] = 'TN_5V'
    fn['26'] = 'GND'
    part('VisionAid:TangNano9K', 'U1', 'Tang Nano 9K', 205, 150, fn, footprint=FP['TN9K'], nc='rest',
         mpn='Sipeed Tang Nano 9K')

    # ---------------- SENSORS
    text('SENSORS (off-board, JST-XH)', 290, 30, 2.54, True)
    text('100R series resistors limit fault current and ringing on the sensor cables.', 290, 34)
    rn = 7
    for j, (code, title, y0) in enumerate((('L', 'forward-left', 50), ('R', 'forward-right', 80),
                                           ('H', 'head-level', 110))):
        text(f'J{2 + j}: RCWL-1601 ultrasonic, {title}', 290, y0 - 9)
        part('Device:R', f'R{rn}', '100R', 330, y0 - 6, {'1': f'US_{code}_TRIG', '2': f'US_{code}_TRIG_C'}, rot=90,
             footprint=FP['R'])
        part('Device:R', f'R{rn + 1}', '100R', 330, y0 + 6, {'1': f'US_{code}_ECHO', '2': f'US_{code}_ECHO_C'}, rot=90,
             footprint=FP['R'])
        rn += 2
        part('Connector_Generic:Conn_01x04', f'J{2 + j}', f'US_{code}', 390, y0,
             {'1': '+3V3', '2': f'US_{code}_TRIG_C', '3': f'US_{code}_ECHO_C', '4': 'GND'}, footprint=FP['XH4'],
             mpn='JST B4B-XH-A')
    y0 = 140
    text('J5: Benewake TF-Luna LiDAR (UART 115200, 3.3 V logic, 5 V supply), pointing down', 290, y0 - 9)
    part('Device:R', f'R{rn}', '100R', 330, y0 - 6, {'1': 'LIDAR_TX', '2': 'LIDAR_TX_C'}, rot=90, footprint=FP['R'])
    part('Device:R', f'R{rn + 1}', '100R', 330, y0 + 6, {'1': 'LIDAR_RX', '2': 'LIDAR_RX_C'}, rot=90, footprint=FP['R'])
    part('Connector_Generic:Conn_01x04', 'J5', 'TF-Luna', 390, y0,
         {'1': '+5V', '2': 'LIDAR_TX_C', '3': 'LIDAR_RX_C', '4': 'GND'}, footprint=FP['XH4'], mpn='JST B4B-XH-A')
    text('J5 pin 2 -> TF-Luna RXD, pin 3 <- TF-Luna TXD (TF-Luna pin 5 left open = UART mode)', 290, y0 + 17)
    y0 = 172
    text('J8: MPU-6050 IMU module (I2C to the Pi)', 290, y0 - 9)
    part('Connector_Generic:Conn_01x04', 'J8', 'IMU', 390, y0,
         {'1': '+3V3', '2': 'I2C_SDA', '3': 'I2C_SCL', '4': 'GND'}, footprint=FP['XH4'], mpn='JST B4B-XH-A')
    part('Device:C', 'C6', '100nF', 360, y0 + 2, {'1': '+3V3', '2': 'GND'}, footprint=FP['C'])

    # ---------------- HAPTICS & BUZZER
    text('HAPTICS & BUZZER', 20, 200, 2.54, True)
    text('AO3400A logic-level N-MOSFETs (Vgs(th) <= 1.45 V) switched by FPGA 3.3 V PWM. 100k gate pull-downs keep', 20, 204)
    text('outputs OFF while the FPGA boots. 1N4148W diodes clamp motor/buzzer flyback. 3 V coin ERMs run from +3V3.', 20, 207)
    def driver(bx, pwm, gate, drain, supply, rg, rpd, q, d, load_ref, load_lib, load_val, load_fp, load_mpn):
        part('Device:R', rg, '100R', bx + 12, 240, {'1': pwm}, rot=90, footprint=FP['R'])
        part('Transistor_FET:AO3400A', q, 'AO3400A', bx + 45, 240, {'1': gate, '3': drain, '2': 'GND'},
             footprint=FP['SOT23'], mpn='AO3400A')
        rx, ry = pin_at('Device:R', bx + 12, 240, 90, '2')
        gx, gy = pin_at('Transistor_FET:AO3400A', bx + 45, 240, 0, '1')
        jx = snap((rx + gx) / 2 - STUB)
        wire(rx, ry, jx, ry)                      # split at the junction so every segment ends on a node
        wire(jx, ry, snap(gx - STUB), gy)
        part('Device:R', rpd, '100k', jx, ry + 7.62, {'2': 'GND'}, footprint=FP['R'])
        px, py = pin_at('Device:R', jx, ry + 7.62, 0, '1')
        wire(jx, ry, px, py)
        junction(jx, ry)
        part('Device:D', d, '1N4148W', bx + 60, 222, {'1': supply, '2': drain}, footprint=FP['SOD123'],
             mpn='1N4148W')
        part(load_lib, load_ref, load_val, bx + 72, 240, {'1': supply, '2': drain}, footprint=load_fp, mpn=load_mpn)

    driver(15, 'MOT_L_PWM', 'MOT_L_G', 'MOT_L_D', '+3V3', 'R1', 'R4', 'Q1', 'D2', 'J6',
           'Connector_Generic:Conn_01x02', 'Motor_L', FP['XH2'], 'JST B2B-XH-A')
    driver(110, 'MOT_R_PWM', 'MOT_R_G', 'MOT_R_D', '+3V3', 'R2', 'R5', 'Q2', 'D3', 'J7',
           'Connector_Generic:Conn_01x02', 'Motor_R', FP['XH2'], 'JST B2B-XH-A')
    driver(205, 'BUZZ_EN', 'BUZZ_G', 'BUZZ_D', '+5V', 'R3', 'R6', 'Q3', 'D4', 'BZ1',
           'Device:Buzzer', '5V active buzzer', FP['BUZ'], '12 mm 5 V active buzzer')
    text('J6/J7 go to the coin motors on the left/right harness straps; BZ1 sounds the \"check device\" alarm.', 20, 262)

    # ---------------- BUTTONS
    text('BUTTONS (READ = OCR, MODE, QUIET)', 305, 190, 2.54, True)
    text('10k pull-up + 100nF = 1 ms RC filter; FPGA also debounces digitally.', 305, 194)
    for i, (b, bx) in enumerate((('READ', 312), ('MODE', 332), ('QUIET', 352))):
        part('Device:R', f'R{15 + i}', '10k', bx, 207, {'1': '+3V3', '2': f'BTN_{b}'}, footprint=FP['R'])
        part('Device:C', f'C{7 + i}', '100nF', bx + 8, 236, {'1': f'BTN_{b}', '2': 'GND'}, footprint=FP['C'])
    part('Connector_Generic:Conn_01x04', 'J9', 'Buttons', 395, 215,
         {'1': 'BTN_READ', '2': 'BTN_MODE', '3': 'BTN_QUIET', '4': 'GND'}, footprint=FP['XH4'],
         mpn='JST B4B-XH-A')

    # ---------------- TEST POINTS & MOUNTING
    text('TEST POINTS (latency / power measurements)', 165, 186, 1.8, True)
    for i, net in enumerate(('+5V', '+3V3', 'GND', 'US_L_ECHO', 'MOT_L_G', 'PI_HB')):
        part('Connector:TestPoint', f'TP{i + 1}', net, 170 + i * 20, 200, {'1': net}, footprint=FP['TP'],
             hide_value=True, rot=180 if net in ('+5V', '+3V3') else 0)
    for i in range(4):
        place_symbol('Mechanical:MountingHole', f'H{i + 1}', 'M2.5', 200 + i * 12, 280, 0, FP['HOLE'])


def main():
    build()
    lib_symbols = [S('lib_symbols')] + [flat_symbol(l) for l in sorted(used_lib_ids)]
    sch = [S('kicad_sch'), [S('version'), 20250114], [S('generator'), 'eeschema'], [S('generator_version'), '9.0'],
           [S('uuid'), ROOT], [S('paper'), 'A3'],
           [S('title_block'), [S('title'), 'VisionAid Carrier Board (stacks on Raspberry Pi 5, 40-pin ribbon)'],
            [S('date'), '2026-10-08'], [S('rev'), 'v0.1'], [S('company'), 'Team SVNIT - Vishwakarma Awards 2026-27'],
            [S('comment'), 1, 'FPGA safety island (Tang Nano 9K) + sensor / haptic interface for the Pi 5 AI path'],
            [S('comment'), 2, 'Design stage - not yet fabricated. Verify Tang Nano 9K row spacing before ordering.']],
           lib_symbols] + items + [[S('sheet_instances'), [S('path'), '/', [S('page'), '1']]],
                                   [S('embedded_fonts'), S('no')]]
    with open(os.path.join(OUT, PROJECT + '.kicad_sch'), 'w') as f:
        f.write(dump(sch) + '\n')
    print('schematic written:', len(items), 'items')


if __name__ == '__main__':
    main()
