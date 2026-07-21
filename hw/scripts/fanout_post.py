"""Post-route power fanout: give every GND/VDD pad a stub + via to the inner
planes, validated against the final routed copper (freerouting never sees
power — GND/VDD are empty-pinned in its network).

Run with KiCad python after stage-2 import, before zones.
"""
import math
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from repair_router import Obstacles, GRID, LAYERS, mm, compress

HW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "countdown")
PCB = os.path.join(HW, "countdown.kicad_pcb")

VIA_D, VIA_DRILL, STUB_W = 0.6, 0.3, 0.25


def stub_clear(obs, layer, x0, y0, x1, y1, skip=0.25):
    """Stub legality: sampled against the exact-clearance hard grid,
    ignoring the first `skip` mm (inside the pad itself)."""
    length = math.hypot(x1 - x0, y1 - y0)
    steps = max(2, int(length / 0.05))
    for k in range(steps + 1):
        t = k / steps
        if t * length < skip:
            continue
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        if (round(x / GRID), round(y / GRID)) in obs.hard[layer]:
            return False
    return True


def main():
    board = pcbnew.LoadBoard(PCB)
    netinfo = {n: board.GetNetsByName()[n] for n in ("GND", "VDD")}
    obs_cache = {}
    added, failed = 0, []
    placed_vias = []

    for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
        for pad in fp.Pads():
            net = pad.GetNetname()
            if net not in ("GND", "VDD"):
                continue
            px, py = mm(pad.GetPosition().x), mm(pad.GetPosition().y)
            layer = fp.GetLayer()  # SMD pad lives on its footprint's side
            already = False
            for t in board.GetTracks():
                if t.Type() == pcbnew.PCB_TRACE_T and t.GetNetname() == net:
                    for pt in (t.GetStart(), t.GetEnd()):
                        if abs(mm(pt.x) - px) < 0.01 and abs(mm(pt.y) - py) < 0.01:
                            already = True
            if already:
                continue
            if net not in obs_cache:
                obs = Obstacles(board, netinfo[net].GetNetCode())
                obs.build_grid()
                obs_cache[net] = obs
            obs = obs_cache[net]
            spot = None
            for dist in (0.9, 1.2, 1.6, 2.0, 2.5, 3.0, 3.6, 4.2, 4.8):
                for ang in range(0, 360, 10):
                    a = math.radians(ang)
                    vx = round((px + dist * math.cos(a)) / GRID) * GRID
                    vy = round((py + dist * math.sin(a)) / GRID) * GRID
                    if not obs.via_ok(vx, vy):
                        continue
                    if any(math.hypot(vx - ox, vy - oy) < 0.85
                           for ox, oy in placed_vias):
                        continue
                    if not stub_clear(obs, layer, px, py, vx, vy):
                        continue
                    spot = (vx, vy)
                    break
                if spot:
                    break
            if spot is None:
                path = _dijkstra_to_via(obs, px, py, layer, placed_vias)
                if path is None:
                    failed.append(f"{fp.GetReference()}.{pad.GetNumber()} ({net})")
                    continue
                pts = [(px, py, layer)] + [(x, y, layer) for x, y in path]
                pts = compress(pts)
                for i in range(len(pts) - 1):
                    tr = pcbnew.PCB_TRACK(board)
                    tr.SetStart(pcbnew.VECTOR2I_MM(pts[i][0], pts[i][1]))
                    tr.SetEnd(pcbnew.VECTOR2I_MM(pts[i+1][0], pts[i+1][1]))
                    tr.SetWidth(pcbnew.FromMM(0.2))
                    tr.SetLayer(layer)
                    tr.SetNet(netinfo[net])
                    board.Add(tr)
                vx, vy = path[-1]
                _via(board, netinfo[net], vx, vy)
                placed_vias.append((vx, vy))
                for oname, o in obs_cache.items():
                    if oname != net:
                        for i in range(len(pts) - 1):
                            _mark_new(o, pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1])
                added += 1
                continue
            vx, vy = spot
            _via(board, netinfo[net], vx, vy)
            tr = pcbnew.PCB_TRACK(board)
            tr.SetStart(pcbnew.VECTOR2I_MM(px, py))
            tr.SetEnd(pcbnew.VECTOR2I_MM(vx, vy))
            tr.SetWidth(pcbnew.FromMM(STUB_W))
            tr.SetLayer(layer)
            tr.SetNet(netinfo[net])
            board.Add(tr)
            placed_vias.append((vx, vy))
            # register new copper in cached obstacle grids of the OTHER net
            for oname, o in obs_cache.items():
                if oname != net:
                    _mark_new(o, px, py, vx, vy)
            added += 1

    pcbnew.SaveBoard(PCB, board)
    # snapshot all power wiring so it can be restored after SES imports
    # (KiCad's ImportSpecctraSES replaces the board's routing wholesale)
    import json
    snap = []
    for t in board.GetTracks():
        n = t.GetNetname()
        if n not in ("GND", "VDD"):
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            snap.append({"kind": "via", "net": n,
                         "x": mm(t.GetPosition().x), "y": mm(t.GetPosition().y)})
        else:
            snap.append({"kind": "trk", "net": n, "layer": int(t.GetLayer()),
                         "x1": mm(t.GetStart().x), "y1": mm(t.GetStart().y),
                         "x2": mm(t.GetEnd().x), "y2": mm(t.GetEnd().y),
                         "w": mm(t.GetWidth())})
    with open(os.path.join(HW, "power_wiring.json"), "w") as fh:
        json.dump(snap, fh)
    print(f"power fanout: {added} vias, failed: {failed if failed else 'none'}; snapshot {len(snap)} items")


def _dijkstra_to_via(obs, px, py, layer, placed_vias):
    """Single-layer flood from the pad to the nearest cell where a via fits;
    returns [(x, y)] path in mm or None."""
    import heapq
    s0 = (round(px / GRID), round(py / GRID))
    openq = [(0.0, s0, None)]
    came, seen = {}, set()
    DIRS = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
            (1, 1, 1.42), (1, -1, 1.42), (-1, 1, 1.42), (-1, -1, 1.42)]
    while openq:
        g, node, parent = heapq.heappop(openq)
        if node in seen:
            continue
        seen.add(node)
        came[node] = parent
        x, y = node[0] * GRID, node[1] * GRID
        if g > 0.6 and obs.via_ok(x, y) and                 all(math.hypot(x - ox, y - oy) >= 0.85 for ox, oy in placed_vias):
            path = []
            while node:
                path.append((node[0] * GRID, node[1] * GRID))
                node = came[node]
            return list(reversed(path))
        if g > 16.0 or len(seen) > 200000:
            return None
        for dx, dy, dc in DIRS:
            nxt = (node[0] + dx, node[1] + dy)
            if nxt in seen:
                continue
            nx_, ny_ = nxt[0] * GRID, nxt[1] * GRID
            near = max(abs(nxt[0] - s0[0]), abs(nxt[1] - s0[1])) <= 10
            if near:
                if (nxt[0], nxt[1]) in obs.hard[layer]:
                    continue
            elif obs.blocked(nx_, ny_, layer):
                continue
            heapq.heappush(openq, (g + dc * GRID, nxt, node))
    return None


def _via(board, net, x, y):
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(pcbnew.VECTOR2I_MM(x, y))
    via.SetWidth(pcbnew.FromMM(VIA_D))
    via.SetDrill(pcbnew.FromMM(VIA_DRILL))
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetNet(net)
    board.Add(via)


def _mark_new(obs, px, py, vx, vy):
    length = math.hypot(vx - px, vy - py) or 1e-9
    steps = max(1, int(length / (GRID / 2)))
    for k in range(steps + 1):
        t = k / steps
        x, y = px + (vx - px) * t, py + (vy - py) * t
        for l in LAYERS:
            for grid_, r in ((obs.cells[l], 0.4), (obs.hard[l], 0.38)):
                i0 = int((x - r) / GRID) - 1
                j0 = int((y - r) / GRID) - 1
                for i in range(i0, i0 + int(2 * r / GRID) + 3):
                    for j in range(j0, j0 + int(2 * r / GRID) + 3):
                        if (i * GRID - x) ** 2 + (j * GRID - y) ** 2 < r * r:
                            grid_.add((i, j))
        # via disc blocks via grid
    for l in LAYERS:
        pass


if __name__ == "__main__":
    main()
