"""Autoroute the carrier PCB with FreeRouting, then add GND pours on both layers.
Steps: export Specctra DSN -> FreeRouting (headless) -> import SES -> GND zones -> fill -> save.
Run with: ../../../tools/kicad.sh python route_pcb.py
"""
import os
import subprocess
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
PCB = os.path.join(OUT, 'VisionAid_Carrier.kicad_pcb')
WORK = os.path.join(OUT, 'routing')
JAR = os.path.join(HERE, '..', '..', '..', 'tools', 'dl', 'freerouting.jar')
MM = pcbnew.FromMM


def add_gnd_zones(board):
    gnd = board.FindNet('GND')
    bb = board.GetBoardEdgesBoundingBox()
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(gnd)
        z.SetIsRuleArea(False)
        z.SetLocalClearance(MM(0.3))
        z.SetMinThickness(MM(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)   # solid: avoids starved thermals on small GND pads
        z.SetThermalReliefGap(MM(0.4))
        z.SetThermalReliefSpokeWidth(MM(0.4))
        z.SetZoneName('GND_' + ('TOP' if layer == pcbnew.F_Cu else 'BOT'))
        o = z.Outline()
        o.NewOutline()
        for x, y in ((bb.GetLeft(), bb.GetTop()), (bb.GetRight(), bb.GetTop()),
                     (bb.GetRight(), bb.GetBottom()), (bb.GetLeft(), bb.GetBottom())):
            o.Append(x, y)
        board.Add(z)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def main():
    os.makedirs(WORK, exist_ok=True)
    board = pcbnew.LoadBoard(PCB)
    # remove old tracks/zones so the script can be re-run
    for t in list(board.GetTracks()):
        board.Remove(t)
    for z in list(board.Zones()):
        board.Remove(z)
    dsn = os.path.join(WORK, 'VisionAid_Carrier.dsn')
    ses = os.path.join(WORK, 'VisionAid_Carrier.ses')
    if os.path.exists(ses):
        os.remove(ses)
    assert pcbnew.ExportSpecctraDSN(board, dsn), 'DSN export failed'
    log = open(os.path.join(WORK, 'freerouting.log'), 'w')
    subprocess.run(['java', '-Djava.awt.headless=true', '-jar', JAR, '-de', dsn, '-do', ses, '-mp', '30',
                    '--gui.enabled=false'], cwd=WORK, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
    assert os.path.exists(ses), 'FreeRouting produced no .ses (see routing/freerouting.log)'
    assert pcbnew.ImportSpecctraSES(board, ses), 'SES import failed'
    add_gnd_zones(board)
    board.Save(PCB)
    print('routed:', len(board.GetTracks()), 'track/via items')


if __name__ == '__main__':
    main()
