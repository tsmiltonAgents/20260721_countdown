"""Surgical routes for the last airwires the autorouters couldn't close.
Explicit polylines on the near-empty inner layers, verified by DRC.
Run with KiCad python. Coordinates in mm, board origin top-left.
"""
import os
import sys

import pcbnew

HW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "countdown")
PCB = os.path.join(HW, "countdown.kicad_pcb")

F, I1, I2, B = pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu

# net -> list of (layer, [(x,y), ...]) polylines and ("via", x, y) drops
ROUTES = {
    "BOOT0": [
        (B, [(2.60, 7.83), (5.6, 7.83)]),
        ("via", 5.6, 7.83),
        (I2, [(5.6, 7.83), (7.0, 6.4), (33.2, 6.4), (33.2, 2.45),
              (39.6, 2.45)]),
        ("via", 39.6, 2.45),
        (B, [(39.6, 2.45), (39.6, 3.46)]),
    ],
    "LSE_OUT": [
        (B, [(40.54, 4.9), (42.05, 4.9), (42.05, 2.45), (41.07, 2.45)]),
    ],
    # VDD pads 1 & 5: single stub+via each into the In2 VDD plane
    "VDD": [
        (B, [(40.54, 5.9), (41.6, 5.9)]),
        ("via", 41.6, 5.9),
        (B, [(40.60, 3.9), (41.5, 3.35)]),
        ("via", 41.5, 3.35),
    ],
    "SEG_F": [
        (F, [(17.68, 2.0), (17.68, 3.3)]),
        ("via", 17.68, 3.3),
        (I1, [(17.68, 3.3), (32.0, 3.3), (33.4, 4.7), (33.4, 8.6), (38.0, 8.6),
              (38.6, 8.0)]),
        ("via", 38.6, 8.0),
        (B, [(38.6, 8.0), (38.6, 7.34)]),
    ],
    "SEG_DP": [
        (F, [(20.18, 20.0), (20.18, 18.5)]),
        ("via", 20.18, 18.5),
        (I1, [(20.18, 18.5), (22.0, 16.5), (22.0, 9.0), (36.4, 9.0),
              (37.6, 8.4)]),
        ("via", 37.6, 8.4),
        (B, [(37.6, 8.4), (37.6, 7.34)]),
    ],
}


def main():
    board = pcbnew.LoadBoard(PCB)
    nets = board.GetNetsByName()
    n_items = 0
    for netname, steps in ROUTES.items():
        ni = nets[netname]
        for step in steps:
            if step[0] == "via":
                _, x, y = step
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(pcbnew.VECTOR2I_MM(x, y))
                v.SetWidth(pcbnew.FromMM(0.6))
                v.SetDrill(pcbnew.FromMM(0.3))
                v.SetViaType(pcbnew.VIATYPE_THROUGH)
                v.SetNet(ni)
                board.Add(v)
                n_items += 1
            else:
                layer, pts = step
                for a, b in zip(pts, pts[1:]):
                    t = pcbnew.PCB_TRACK(board)
                    t.SetStart(pcbnew.VECTOR2I_MM(*a))
                    t.SetEnd(pcbnew.VECTOR2I_MM(*b))
                    t.SetWidth(pcbnew.FromMM(0.2))
                    t.SetLayer(layer)
                    t.SetNet(ni)
                    board.Add(t)
                    n_items += 1
    pcbnew.SaveBoard(PCB, board)
    print(f"manual routes: {n_items} items for {list(ROUTES)}")


if __name__ == "__main__":
    main()
