"""Remove GND/VDD tracks/vias that are NOT in the fanout snapshot — the
planes carry power; anything extra (freerouting echoes on inner layers,
repair-router excursions) is redundant and can only cause trouble."""
import json
import os

import pcbnew

HW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "countdown")
PCB = os.path.join(HW, "countdown.kicad_pcb")

board = pcbnew.LoadBoard(PCB)
snap = json.load(open(os.path.join(HW, "power_wiring.json")))
vias = {(round(i["x"], 2), round(i["y"], 2)) for i in snap if i["kind"] == "via"}
trks = {(round(i["x1"], 2), round(i["y1"], 2), round(i["x2"], 2), round(i["y2"], 2))
        for i in snap if i["kind"] == "trk"}
removed = 0
for t in list(board.GetTracks()):
    if t.GetNetname() not in ("GND", "VDD"):
        continue
    if t.Type() == pcbnew.PCB_VIA_T:
        k = (round(pcbnew.ToMM(t.GetPosition().x), 2),
             round(pcbnew.ToMM(t.GetPosition().y), 2))
        if k not in vias:
            board.Remove(t)
            removed += 1
    else:
        k = (round(pcbnew.ToMM(t.GetStart().x), 2), round(pcbnew.ToMM(t.GetStart().y), 2),
             round(pcbnew.ToMM(t.GetEnd().x), 2), round(pcbnew.ToMM(t.GetEnd().y), 2))
        kr = (k[2], k[3], k[0], k[1])
        if k not in trks and kr not in trks:
            board.Remove(t)
            removed += 1
filler = pcbnew.ZONE_FILLER(board)
filler.Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
print(f"cleanup: removed {removed} non-snapshot power items")
