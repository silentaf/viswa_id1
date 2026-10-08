"""Generate the project-local KiCad library for the VisionAid carrier board:
  - VisionAid.kicad_sym : symbol for the Sipeed Tang Nano 9K module (2 x 24 header)
  - VisionAid.pretty/TangNano9K_Module.kicad_mod : matching footprint

Pin data comes from the official Sipeed pinmap (wiki.sipeed.com, Tang Nano 9K "Pinmap").
Header row spacing 22.86 mm (0.9 in) and pitch 2.54 mm. VERIFY ROW SPACING WITH CALIPERS
on the real board before ordering a PCB.
"""
import os
from sexpr import dump, Sym as S

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)

# Header pins, viewed from the top with the USB-C connector at the top.
# Values are FPGA package pin numbers (GW1NR-LV9QN88P), or power names.
LEFT = ['38', '37', '36', '39', '25', '26', '27', '28', '29', '30', '33', '34',
        '40', '35', '41', '42', '51', '53', '54', '55', '56', '57', '68', '69']
RIGHT = ['63', '86', '85', '84', '83', '82', '81', '80', '79', '77', '76', '75',
         '74', '73', '72', '71', '70', '5V', '48', '49', '31', '32', 'GND', '3V3']
BANK3_1V8 = {'63', '86', '85', '84', '83', '82', '81', '80', '79'}  # 1.8 V I/O: do not use with 3.3 V signals
ROW_SPACING = 22.86
PITCH = 2.54


def pad_number(side, pos):
    """DIP numbering: left column 1..24 top->bottom, right column 25..48 bottom->top."""
    return pos + 1 if side == 'L' else 48 - pos


def pin_name(p):
    if p in ('5V', 'GND', '3V3'):
        return p
    return f'P{p}_1V8' if p in BANK3_1V8 else f'P{p}'


def font(size=1.27):
    return [S('effects'), [S('font'), [S('size'), size, size]]]


def hidden(size=1.27):
    return [S('effects'), [S('font'), [S('size'), size, size]], [S('hide'), S('yes')]]


def symbol():
    pins = []
    for side, col in (('L', LEFT), ('R', RIGHT)):
        for i, p in enumerate(col):
            x = -17.78 if side == 'L' else 17.78
            ang = 0 if side == 'L' else 180
            y = 30.48 - i * PITCH
            etype = {'5V': 'power_in', 'GND': 'power_in', '3V3': 'power_out'}.get(p, 'bidirectional')
            pins.append([S('pin'), S(etype), S('line'), [S('at'), x, y, ang], [S('length'), 5.08],
                         [S('name'), pin_name(p), font()], [S('number'), str(pad_number(side, i)), font()]])
    return [S('symbol'), 'TangNano9K', [S('pin_names'), [S('offset'), 1.016]],
            [S('exclude_from_sim'), S('no')], [S('in_bom'), S('yes')], [S('on_board'), S('yes')],
            [S('property'), 'Reference', 'U', [S('at'), 0, 35.56, 0], font()],
            [S('property'), 'Value', 'TangNano9K', [S('at'), 0, -31.75, 0], font()],
            [S('property'), 'Footprint', 'VisionAid:TangNano9K_Module', [S('at'), 0, -34.29, 0], hidden()],
            [S('property'), 'Datasheet', 'https://wiki.sipeed.com/hardware/en/tang/Tang-Nano-9K/Nano-9K.html',
             [S('at'), 0, -36.83, 0], hidden()],
            [S('property'), 'Description',
             'Sipeed Tang Nano 9K FPGA module (GW1NR-9, 27 MHz), 2x24 headers, 0.9 in row spacing. '
             'Pins named P<n> = FPGA package pin n; *_1V8 pins are on the 1.8 V bank.',
             [S('at'), 0, -39.37, 0], hidden()],
            [S('symbol'), 'TangNano9K_0_1',
             [S('rectangle'), [S('start'), -12.7, 31.75], [S('end'), 12.7, -29.21],
              [S('stroke'), [S('width'), 0.254], [S('type'), S('default')]], [S('fill'), [S('type'), S('background')]]],
             [S('text'), 'USB-C end', [S('at'), 0, 32.766, 0], font(1.0)]],
            [S('symbol'), 'TangNano9K_1_1', *pins],
            [S('embedded_fonts'), S('no')]]


def footprint():
    lines = lambda layer, w, x0, y0, x1, y1: [S('fp_rect'), [S('start'), x0, y0], [S('end'), x1, y1],
                                               [S('stroke'), [S('width'), w], [S('type'), S('solid')]],
                                               [S('fill'), S('no')], [S('layer'), layer]]
    fp = [S('footprint'), 'TangNano9K_Module', [S('version'), 20241229], [S('generator'), 'visionaid_gen'],
          [S('layer'), 'F.Cu'],
          [S('descr'), 'Sipeed Tang Nano 9K on 2x24 female headers, 2.54 mm pitch, 22.86 mm row spacing '
                       '(verify with calipers). Board approx 65 x 23 mm, USB-C towards -Y.'],
          [S('tags'), 'FPGA Gowin GW1NR-9 Sipeed module'],
          [S('property'), 'Reference', 'REF**', [S('at'), 0, -34.0, 0], [S('layer'), 'F.SilkS'],
           [S('effects'), [S('font'), [S('size'), 1, 1], [S('thickness'), 0.15]]]],
          [S('property'), 'Value', 'TangNano9K_Module', [S('at'), 0, 34.0, 0], [S('layer'), 'F.Fab'],
           [S('effects'), [S('font'), [S('size'), 1, 1], [S('thickness'), 0.15]]]],
          [S('attr'), S('through_hole')],
          lines('F.SilkS', 0.12, -12.95, -32.3, 12.95, 32.3),
          lines('F.Fab', 0.1, -12.7, -32.25, 12.7, 32.25),
          # Courtyard only around the two socket rows: the module sits on 8.5 mm female headers,
          # so low-profile SMD parts (< 2 mm) may be placed underneath it.
          lines('F.CrtYd', 0.05, -ROW_SPACING / 2 - 1.6, -30.6, -ROW_SPACING / 2 + 1.6, 30.6),
          lines('F.CrtYd', 0.05, ROW_SPACING / 2 - 1.6, -30.6, ROW_SPACING / 2 + 1.6, 30.6),
          [S('fp_text'), S('user'), 'Tang Nano 9K on 8.5 mm sockets - SMD parts underneath', [S('at'), 0, 33.0, 0],
           [S('layer'), 'F.Fab'], [S('effects'), [S('font'), [S('size'), 0.8, 0.8], [S('thickness'), 0.1]]]],
          [S('fp_text'), S('user'), 'USB-C', [S('at'), 0, -30.6, 0], [S('layer'), 'F.SilkS'],
           [S('effects'), [S('font'), [S('size'), 1, 1], [S('thickness'), 0.15]]]],
          [S('fp_text'), S('user'), '${REFERENCE}', [S('at'), 0, 0, 90], [S('layer'), 'F.Fab'],
           [S('effects'), [S('font'), [S('size'), 1, 1], [S('thickness'), 0.15]]]]]
    for side, col in (('L', LEFT), ('R', RIGHT)):
        for i, _ in enumerate(col):
            n = pad_number(side, i)
            x = -ROW_SPACING / 2 if side == 'L' else ROW_SPACING / 2
            y = -29.21 + i * PITCH
            shape = S('rect') if n == 1 else S('oval')
            fp.append([S('pad'), str(n), S('thru_hole'), shape, [S('at'), round(x, 3), round(y, 3)],
                       [S('size'), 1.7, 1.7], [S('drill'), 1.0], [S('layers'), '*.Cu', '*.Mask']])
    fp.append([S('model'), '${KIPRJMOD}/3d/TangNano9K_Module.wrl',
               [S('offset'), [S('xyz'), 0, 0, 0]], [S('scale'), [S('xyz'), 1, 1, 1]], [S('rotate'), [S('xyz'), 0, 0, 0]]])
    fp.append([S('embedded_fonts'), S('no')])
    return fp


def main():
    lib = [S('kicad_symbol_lib'), [S('version'), 20241209], [S('generator'), 'visionaid_gen'],
           [S('generator_version'), '9.0'], symbol()]
    with open(os.path.join(OUT, 'VisionAid.kicad_sym'), 'w') as f:
        f.write(dump(lib) + '\n')
    os.makedirs(os.path.join(OUT, 'VisionAid.pretty'), exist_ok=True)
    with open(os.path.join(OUT, 'VisionAid.pretty', 'TangNano9K_Module.kicad_mod'), 'w') as f:
        f.write(dump(footprint()) + '\n')
    print('library written')


if __name__ == '__main__':
    main()
