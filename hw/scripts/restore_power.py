"""Re-add snapshotted GND/VDD wiring lost to ImportSpecctraSES (which
replaces the whole board's routing). Idempotent: skips items already present.
Run with KiCad python."""
import json
import math
import os

import pcbnew

HW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "countdown")
PCB = os.path.join(HW, "countdown.kicad_pcb")

board = pcbnew.LoadBoard(PCB)
snap = json.load(open(os.path.join(HW, "power_wiring.json")))
nets = board.GetNetsByName()

have_vias = set()
have_trks = set()
for t in board.GetTracks():
    if t.GetNetname() not in ("GND", "VDD"):
        continue
    if t.Type() == pcbnew.PCB_VIA_T:
        have_vias.add((round(pcbnew.ToMM(t.GetPosition().x), 3),
                       round(pcbnew.ToMM(t.GetPosition().y), 3)))
    else:
        have_trks.add((round(pcbnew.ToMM(t.GetStart().x), 3),
                       round(pcbnew.ToMM(t.GetStart().y), 3),
                       round(pcbnew.ToMM(t.GetEnd().x), 3),
                       round(pcbnew.ToMM(t.GetEnd().y), 3)))

added = 0
for it in snap:
    net = nets[it["net"]]
    if it["kind"] == "via":
        if (round(it["x"], 3), round(it["y"], 3)) in have_vias:
            continue
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I_MM(it["x"], it["y"]))
        v.SetWidth(pcbnew.FromMM(0.6))
        v.SetDrill(pcbnew.FromMM(0.3))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetNet(net)
        board.Add(v)
        added += 1
    else:
        key = (round(it["x1"], 3), round(it["y1"], 3),
               round(it["x2"], 3), round(it["y2"], 3))
        if key in have_trks:
            continue
        tr = pcbnew.PCB_TRACK(board)
        tr.SetStart(pcbnew.VECTOR2I_MM(it["x1"], it["y1"]))
        tr.SetEnd(pcbnew.VECTOR2I_MM(it["x2"], it["y2"]))
        tr.SetWidth(pcbnew.FromMM(it["w"]))
        tr.SetLayer(it["layer"])
        tr.SetNet(net)
        board.Add(tr)
        added += 1
pcbnew.SaveBoard(PCB, board)
print(f"restored {added} power items")
