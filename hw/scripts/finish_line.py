"""Close the last airwires. Two moves, looped under DRC:
1. Coincident F/B pair (same XY, different layers): drop a via at the
   nearest legal spot, joined by track if offset.
2. Pocketed long net: rip the signal nets whose copper crowds the stuck
   pad (within 0.8 mm), then A*-repair with the victim net first.
Run with KiCad python from repo root.
"""
import json
import math
import os
import subprocess
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from repair_router import Obstacles, GRID, mm

HW = "hw/countdown"
PCB = HW + "/countdown.kicad_pcb"
KICAD_CLI = "/Applications/KiCadCLI/Contents/MacOS/kicad-cli"
KP = sys.executable
POWER = ("GND", "VDD")


def drc():
    subprocess.run([KICAD_CLI, "pcb", "drc", "--severity-error", "--format",
                    "json", "-o", HW + "/drc.json", PCB], capture_output=True)
    d = json.load(open(HW + "/drc.json"))
    return d["violations"], d["unconnected_items"]


def netname_of(desc):
    if "[" in desc:
        return desc.split("[")[1].split("]")[0]
    return None


def fix_coincident(board, pair):
    a, b = pair["items"]
    ax, ay = a["pos"]["x"], a["pos"]["y"]
    net = netname_of(a["description"]) or netname_of(b["description"])
    ni = board.GetNetsByName()[net]
    obs = Obstacles(board, ni.GetNetCode())
    obs.build_grid()
    best = None
    for dist in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        steps = 1 if dist == 0 else 16
        for k in range(steps):
            ang = 2 * math.pi * k / steps
            x = round((ax + dist * math.cos(ang)) / GRID) * GRID
            y = round((ay + dist * math.sin(ang)) / GRID) * GRID
            if obs.via_ok(x, y):
                best = (x, y)
                break
        if best:
            break
    if not best:
        print(f"  coincident fix FAILED for {net} at ({ax:.2f},{ay:.2f})")
        return False
    x, y = best
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(pcbnew.VECTOR2I_MM(x, y))
    via.SetWidth(pcbnew.FromMM(0.6))
    via.SetDrill(pcbnew.FromMM(0.3))
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetNet(ni)
    board.Add(via)
    if (x, y) != (ax, ay):
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            tr = pcbnew.PCB_TRACK(board)
            tr.SetStart(pcbnew.VECTOR2I_MM(ax, ay))
            tr.SetEnd(pcbnew.VECTOR2I_MM(x, y))
            tr.SetWidth(pcbnew.FromMM(0.2))
            tr.SetLayer(layer)
            tr.SetNet(ni)
            board.Add(tr)
    print(f"  via-joined {net} at ({x:.2f},{y:.2f})")
    return True


def blockers_near(board, x, y, victim):
    names = set()
    for t in board.GetTracks():
        n = t.GetNetname()
        if n in POWER or n == victim or not n:
            continue
        if t.Type() == pcbnew.PCB_TRACE_T:
            x1, y1 = mm(t.GetStart().x), mm(t.GetStart().y)
            x2, y2 = mm(t.GetEnd().x), mm(t.GetEnd().y)
            dx, dy = x2 - x1, y2 - y1
            L2 = dx * dx + dy * dy
            tt = 0 if L2 == 0 else max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / L2))
            d = math.hypot(x - (x1 + tt * dx), y - (y1 + tt * dy))
        else:
            d = math.hypot(mm(t.GetPosition().x) - x, mm(t.GetPosition().y) - y)
        if d < 0.8:
            names.add(n)
    return names


def rip(board, nets):
    n = 0
    for t in list(board.GetTracks()):
        if t.GetNetname() in nets:
            board.Remove(t)
            n += 1
    print(f"  ripped {n} items of {sorted(nets)}")


def main():
    for attempt in range(8):
        viols, unc = drc()
        real_unc = [u for u in unc
                    if netname_of(u["items"][0]["description"]) not in POWER
                    or netname_of(u["items"][1]["description"]) not in POWER]
        print(f"attempt {attempt}: violations={len(viols)} unconnected={len(unc)}")
        if not viols and not unc:
            print("CLEAN")
            return 0
        board = pcbnew.LoadBoard(PCB)
        acted = False
        rip_sets = {}
        for u in unc:
            a, b = u["items"]
            ax, ay = a["pos"]["x"], a["pos"]["y"]
            bx, by = b["pos"]["x"], b["pos"]["y"]
            net = netname_of(a["description"]) or netname_of(b["description"])
            if net in POWER:
                continue
            if math.hypot(bx - ax, by - ay) < 0.2:
                acted |= fix_coincident(board, u)
            else:
                # pocketed: which end is near the QFN (dense)? rip around both
                blk = blockers_near(board, ax, ay, net) | \
                      blockers_near(board, bx, by, net)
                if blk:
                    rip_sets[net] = blk
        if rip_sets:
            allrip = set()
            # cap the rip radius: one victim + its blockers only (avoid
            # cascade storms that undo half the board)
            victim = list(rip_sets)[0]
            allrip = rip_sets[victim] | {victim}
            if len(allrip) > 4:
                allrip = set(list(allrip)[:4]) | {victim}
            rip(board, allrip)
            acted = True
        pcbnew.SaveBoard(PCB, board)
        if rip_sets:
            order = ",".join(rip_sets.keys())
            env = dict(os.environ, REPAIR_PRIORITY=list(rip_sets)[0],
                       REPAIR_ITERS="12")
            subprocess.run([KP, "-u", "hw/scripts/repair_router.py"],
                           env=env, capture_output=True)
            acted = True
        elif acted:
            pass
        else:
            print("no actionable items; stopping")
            return 1
    viols, unc = drc()
    print(f"final: violations={len(viols)} unconnected={len(unc)}")
    return 0 if not viols and not unc else 1


sys.exit(main())
