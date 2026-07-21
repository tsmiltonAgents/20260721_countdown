"""Import a SES into the board and report per-net connectivity via DRC.
Usage: kicad-python import_ses.py <ses-file>
"""
import json
import os
import subprocess
import sys

import pcbnew

HW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "countdown")
PCB = os.path.join(HW, "countdown.kicad_pcb")
KICAD_CLI = "/Applications/KiCadCLI/Contents/MacOS/kicad-cli"

board = pcbnew.LoadBoard(PCB)
before = len(board.GetTracks())
ok = pcbnew.ImportSpecctraSES(board, sys.argv[1])
after = len(board.GetTracks())
print(f"import {ok}: tracks {before} -> {after}")
pcbnew.SaveBoard(PCB, board)

subprocess.run([KICAD_CLI, "pcb", "drc", "--severity-error", "--format", "json",
                "-o", os.path.join(HW, "drc.json"), PCB], capture_output=True)
d = json.load(open(os.path.join(HW, "drc.json")))
unc = d.get("unconnected_items", [])
nets = set()
for u in unc:
    for i in u["items"]:
        m = i["description"].split("[")
        if len(m) > 1:
            nets.add(m[1].split("]")[0])
print("violations:", len(d.get("violations", [])),
      "unconnected:", len(unc), "nets:", sorted(nets))
