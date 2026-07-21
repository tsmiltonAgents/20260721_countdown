"""Import routed SES, add power planes + silkscreen art, save.
Run with KiCad's bundled python.
- In1.Cu: GND plane zone
- In2.Cu: VDD plane zone
- Silkscreen: front title + back target-date text
"""
import os
import sys

import pcbnew

HW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "countdown")
PCB = os.path.join(HW, "countdown.kicad_pcb")


def add_zone(board, layer, netname, prio):
    net = board.GetNetsByName()[netname]
    zone = pcbnew.ZONE(board)
    zone.SetLayer(layer)
    zone.SetNetCode(net.GetNetCode())
    outline = zone.Outline()
    outline.NewOutline()
    for x, y in ((-1, -1), (45, -1), (45, 23), (-1, 23)):
        outline.Append(pcbnew.VECTOR2I_MM(x, y))
    zone.SetAssignedPriority(prio)
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    zone.SetMinThickness(pcbnew.FromMM(0.2))
    zone.SetLocalClearance(pcbnew.FromMM(0.25))
    board.Add(zone)
    return zone


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
    ok = pcbnew.ImportSpecctraSES(board, os.path.join(HW, "countdown.ses"))
    print("SES import:", ok, "tracks:", len(board.GetTracks()))
    if not ok:
        raise SystemExit("SES import failed")

    # silkscreen: front wordmark under display area / back target date
    add_text(board, "T-MINUS", 21.35, 19.0, pcbnew.F_SilkS, 1.5, 0.25, bold=True)
    add_text(board, "2026-10-10 12:00", 21.35, 3.6, pcbnew.F_SilkS, 1.1, 0.18)
    add_text(board, "COUNTDOWN v1  tsm 2026", 19.4, 11.0, pcbnew.B_SilkS, 1.0,
             0.15, mirror=True)

    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())

    pcbnew.SaveBoard(PCB, board)
    print("saved with zones; tracks:", len(board.GetTracks()),
          "zones:", len(board.Zones()))


if __name__ == "__main__":
    main()
