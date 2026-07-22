"""Final board dressing (run after routing + repair):
- In1.Cu GND plane + In2.Cu VDD plane, filled
- silkscreen art
Run with KiCad python.
"""
import os

import pcbnew

HW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "countdown")
PCB = os.path.join(HW, "countdown.kicad_pcb")


def add_zone(board, layer, netname):
    net = board.GetNetsByName()[netname]
    zone = pcbnew.ZONE(board)
    zone.SetLayer(layer)
    zone.SetNetCode(net.GetNetCode())
    zone.Outline().NewOutline()
    for x, y in ((-1, -1), (45, -1), (45, 24), (-1, 24)):
        zone.Outline().Append(pcbnew.VECTOR2I_MM(x, y))
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    zone.SetMinThickness(pcbnew.FromMM(0.2))
    zone.SetLocalClearance(pcbnew.FromMM(0.25))
    board.Add(zone)


def add_text(board, txt, x, y, layer, size=1.2, thick=0.2, mirror=False, bold=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(txt)
    t.SetPosition(pcbnew.VECTOR2I_MM(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I_MM(size, size))
    t.SetTextThickness(pcbnew.FromMM(thick))
    t.SetBold(bold)
    if mirror:
        t.SetMirrored(True)
    board.Add(t)


def main():
    board = pcbnew.LoadBoard(PCB)
    have = {z.GetNetname() for z in board.Zones()}
    if "GND" not in have:
        add_zone(board, pcbnew.In1_Cu, "GND")
    if "VDD" not in have:
        add_zone(board, pcbnew.In2_Cu, "VDD")

    texts = [pcbnew.ToMM(t.GetPosition().x) for t in board.GetDrawings()
             if isinstance(t, pcbnew.PCB_TEXT)]
    if not texts:
        add_text(board, "T-MINUS", 21.35, 18.1, pcbnew.F_SilkS, 1.4, 0.24, bold=True)
        add_text(board, "2026-10-10 12:00", 21.35, 4.6, pcbnew.F_SilkS, 0.9, 0.15)
        add_text(board, "COUNTDOWN v1 2026", 21.0, 21.3, pcbnew.B_SilkS, 0.9,
                 0.15, mirror=True)

    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(PCB, board)
    print("finished: zones:", len(board.Zones()), "tracks:", len(board.GetTracks()))


if __name__ == "__main__":
    main()
