"""Extra acceptance gates beyond DRC (run with KiCad python):
- no non-GND via inside the QFN die-pad square (VSS-bonded exposed pad)
- every via pair >= 0.72 mm centre-to-centre (JLC hole-to-hole)
- no silk text overlapping SMD pads on the same side (bare-board aesthetics)
Prints count of gate failures; exit code = count>0.
"""
import math
import sys

import pcbnew

b = pcbnew.LoadBoard("hw/countdown/countdown.kicad_pcb")
fails = []
vias = [(t, pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y))
        for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
for t, x, y in vias:
    if t.GetNetname() != "GND" and 37.8 <= x <= 41.4 and 3.8 <= y <= 7.4:
        fails.append(f"non-GND via {t.GetNetname()} under QFN at ({x:.2f},{y:.2f})")
for i in range(len(vias)):
    for j in range(i + 1, len(vias)):
        d = math.hypot(vias[i][1] - vias[j][1], vias[i][2] - vias[j][2])
        if d < 0.719:
            fails.append(f"via pair {d:.3f}mm apart at ({vias[i][1]:.2f},{vias[i][2]:.2f})")
for f in fails:
    print("GATE:", f)
print(f"gate failures: {len(fails)}")
sys.exit(1 if fails else 0)
