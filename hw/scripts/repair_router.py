"""Deterministic repair router: finds unconnected net islands on the board
and routes them with grid A* on F.Cu/B.Cu (through-vias allowed), then lets
KiCad DRC verify. Used after freerouting to finish nets it dropped.

Run with KiCad python. Approach:
- build per-layer obstacle sets from pads/tracks/vias of OTHER nets,
  rule areas, NPTH holes and the board edge
- for each unconnected pad pair (from kicad-cli DRC json), A* over a 0.25 mm
  grid; touching same-net copper is allowed (free), via cost discourages
  layer hops; vias forbidden inside part bodies (display mold marks etc.)
- emit 0.2 mm tracks / 0.6-0.3 vias, save
"""
import heapq
import json
import math
import os
import subprocess
import sys

import pcbnew

HW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "countdown")
PCB = os.path.join(HW, "countdown.kicad_pcb")
KICAD_CLI = "/Applications/KiCadCLI/Contents/MacOS/kicad-cli"

GRID = 0.1
TRACK_W = 0.2
CLEAR = 0.27        # centreline to other-net copper edge (0.1+0.15 margin)
VIA_D, VIA_DRILL = 0.6, 0.3
VIA_CLEAR = 0.48    # via centre to other-net copper edge margin
BOARD_W, BOARD_H = 44.0, 23.0
EDGE = 0.75         # centreline to board edge
LAYERS = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)


def mm(v):
    return pcbnew.ToMM(v)


class Obstacles:
    """Per-layer segments/circles/boxes of other-net copper."""

    def __init__(self, board, netcode):
        self.segs = {l: [] for l in LAYERS}   # (x1,y1,x2,y2,halfw)
        self.circles = {l: [] for l in LAYERS}  # (x,y,r)
        self.all_circles = []  # NPTH & holes blocking all layers (x,y,r)
        self.novia_boxes = []
        self.boxes = {l: [] for l in LAYERS}   # other-net pad bboxes
        self.all_boxes = []                     # through obstacles (NPTH/PTH)
        for fp in board.GetFootprints():
            bb = fp.GetBoundingBox(False)
            if fp.GetReference() in ("DS1", "J1"):  # mold marks / TC2030 seat
                self.novia_boxes.append((mm(bb.GetLeft()), mm(bb.GetTop()),
                                         mm(bb.GetRight()), mm(bb.GetBottom())))
            for pad in fp.Pads():
                pb = pad.GetBoundingBox()
                box = (mm(pb.GetLeft()), mm(pb.GetTop()),
                       mm(pb.GetRight()), mm(pb.GetBottom()))
                if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                    self.all_boxes.append(box)
                    continue
                if pad.GetNetCode() == netcode:
                    continue
                if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                    self.all_boxes.append(box)
                else:
                    for l in LAYERS:
                        if pad.IsOnLayer(l):
                            self.boxes[l].append(box)
        for t in board.GetTracks():
            if t.GetNetCode() == netcode:
                continue
            if t.Type() == pcbnew.PCB_VIA_T:
                self.all_circles.append((mm(t.GetPosition().x),
                                         mm(t.GetPosition().y),
                                         mm(t.GetWidth(pcbnew.F_Cu)) / 2))
            elif t.Type() == pcbnew.PCB_TRACE_T and t.GetLayer() in LAYERS:
                self.segs[t.GetLayer()].append(
                    (mm(t.GetStart().x), mm(t.GetStart().y),
                     mm(t.GetEnd().x), mm(t.GetEnd().y), mm(t.GetWidth()) / 2))
        # keyring hole keepout ring + border handled by EDGE margin checks
        self.all_circles.append((4.0, 11.5, 3.5))

    def build_grid(self):
        """Rasterize obstacles once: blocked cell sets per layer + via grid."""
        self.cells = {l: set() for l in LAYERS}
        nx = int(BOARD_W / GRID) + 1
        ny = int(BOARD_H / GRID) + 1

        def mark(cellset, cx, cy, r):
            i0 = max(0, int((cx - r) / GRID) - 1)
            i1 = min(nx, int((cx + r) / GRID) + 2)
            j0 = max(0, int((cy - r) / GRID) - 1)
            j1 = min(ny, int((cy + r) / GRID) + 2)
            r2 = r * r
            for i in range(i0, i1):
                for j in range(j0, j1):
                    if (i * GRID - cx) ** 2 + (j * GRID - cy) ** 2 < r2:
                        cellset.add((i, j))

        def mark_seg(cellset, x1, y1, x2, y2, r):
            length = math.hypot(x2 - x1, y2 - y1)
            steps = max(1, int(length / (GRID / 2)))
            for k in range(steps + 1):
                t = k / steps
                mark(cellset, x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, r)

        def mark_box(cellset, x1, y1, x2, y2, inflate):
            i0 = max(0, int((x1 - inflate) / GRID) - 1)
            i1 = min(nx, int((x2 + inflate) / GRID) + 2)
            j0 = max(0, int((y1 - inflate) / GRID) - 1)
            j1 = min(ny, int((y2 + inflate) / GRID) + 2)
            for i in range(i0, i1):
                for j in range(j0, j1):
                    if (x1 - inflate < i * GRID < x2 + inflate and
                            y1 - inflate < j * GRID < y2 + inflate):
                        cellset.add((i, j))

        for l in LAYERS:
            for cx, cy, r in self.all_circles:
                mark(self.cells[l], cx, cy, r + CLEAR)
            for bx in self.all_boxes + self.boxes[l]:
                mark_box(self.cells[l], *bx, CLEAR)
            for x1, y1, x2, y2, hw in self.segs[l]:
                mark_seg(self.cells[l], x1, y1, x2, y2, hw + CLEAR)
        # hard cells: exact-minimum clearance obstacles (pad/track copper +
        # 0.25/0.35) used inside endpoint exemption zones — a legal escape
        # lane stays open there while shorts/clearance breaks stay blocked
        self.hard = {l: set() for l in LAYERS}
        for l in LAYERS:
            for bx in self.all_boxes:
                mark_box(self.hard[l], *bx, 0.36)  # holes: 0.25 rule + width
            for bx in self.boxes[l]:
                mark_box(self.hard[l], *bx, 0.26)
            for cx, cy, r in self.all_circles:
                mark(self.hard[l], cx, cy, r + 0.26)
            for x1, y1, x2, y2, hw in self.segs[l]:
                mark_seg(self.hard[l], x1, y1, x2, y2, hw + 0.26)
        # via legality grid: blocked on either layer with via clearance
        self.via_cells = set()
        for l in LAYERS:
            for cx, cy, r in self.all_circles:
                mark(self.via_cells, cx, cy, r + VIA_CLEAR)
            for bx in self.all_boxes + self.boxes[l]:
                mark_box(self.via_cells, *bx, VIA_CLEAR)
            for x1, y1, x2, y2, hw in self.segs[l]:
                mark_seg(self.via_cells, x1, y1, x2, y2, hw + VIA_CLEAR)
        for bx1, by1, bx2, by2 in self.novia_boxes:
            i0 = max(0, int((bx1 - 0.3) / GRID) - 1)
            i1 = min(nx, int((bx2 + 0.3) / GRID) + 2)
            j0 = max(0, int((by1 - 0.3) / GRID) - 1)
            j1 = min(ny, int((by2 + 0.3) / GRID) + 2)
            for i in range(i0, i1):
                for j in range(j0, j1):
                    self.via_cells.add((i, j))

    def blocked(self, x, y, layer, clear=None):
        if not (EDGE <= x <= BOARD_W - EDGE and EDGE <= y <= BOARD_H - EDGE):
            return True
        return (round(x / GRID), round(y / GRID)) in self.cells[layer]

    def via_ok(self, x, y):
        if not (EDGE <= x <= BOARD_W - EDGE and EDGE <= y <= BOARD_H - EDGE):
            return False
        return (round(x / GRID), round(y / GRID)) not in self.via_cells


def _seg_dist2(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    ln2 = dx * dx + dy * dy
    if ln2 == 0:
        return (px - x1) ** 2 + (py - y1) ** 2
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / ln2))
    cx, cy = x1 + t * dx, y1 + t * dy
    return (px - cx) ** 2 + (py - cy) ** 2


def astar(obs, start, goal, start_layer, goal_layer):
    """start/goal in mm. Returns [(x, y, layer)] or None."""
    def snap(v):
        return round(v / GRID) * GRID

    sx, sy = snap(start[0]), snap(start[1])
    gx, gy = snap(goal[0]), snap(goal[1])
    layers = LAYERS
    li = {l: i for i, l in enumerate(layers)}
    s = (round(sx / GRID), round(sy / GRID), li[start_layer])
    g = (round(gx / GRID), round(gy / GRID), li[goal_layer])

    def h(n):
        return math.hypot((n[0] - g[0]), (n[1] - g[1])) * GRID + \
            (0.5 if n[2] != g[2] else 0)

    openq = [(h(s), 0.0, s, None)]
    came, cost = {}, {s: 0.0}
    DIRS = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
            (1, 1, 1.42), (1, -1, 1.42), (-1, 1, 1.42), (-1, -1, 1.42)]
    visited = set()
    steps = 0
    while openq:
        steps += 1
        if steps > 2000000:
            return None
        f, gcost, node, parent = heapq.heappop(openq)
        if node in visited:
            continue
        visited.add(node)
        came[node] = parent
        if node == g:
            path = []
            while node:
                path.append((node[0] * GRID, node[1] * GRID, layers[node[2]]))
                node = came[node]
            return list(reversed(path))
        nx0, ny0, nl = node
        for dx, dy, dc in DIRS:
            nxt = (nx0 + dx, ny0 + dy, nl)
            if nxt in visited:
                continue
            x, y = nxt[0] * GRID, nxt[1] * GRID
            near_goal = max(abs(nxt[0] - g[0]), abs(nxt[1] - g[1])) <= 10 and nl == g[2]
            near_start = max(abs(nxt[0] - s[0]), abs(nxt[1] - s[1])) <= 10 and nl == s[2]
            if near_goal or near_start:
                if (nxt[0], nxt[1]) in obs.hard[layers[nl]]:
                    continue
            elif obs.blocked(x, y, layers[nl], CLEAR):
                continue
            ng = gcost + dc * GRID
            if ng < cost.get(nxt, 1e9):
                cost[nxt] = ng
                heapq.heappush(openq, (ng + h(nxt), ng, nxt, node))
        # layer change (through-via reaches every layer)
        x, y = nx0 * GRID, ny0 * GRID
        if obs.via_ok(x, y):
            for other in range(len(layers)):
                if other == nl:
                    continue
                nxt = (nx0, ny0, other)
                if nxt in visited:
                    continue
                ng = gcost + 1.4  # via cost
                if ng < cost.get(nxt, 1e9):
                    cost[nxt] = ng
                    heapq.heappush(openq, (ng + h(nxt), ng, nxt, node))
    return None


def drc_unconnected():
    subprocess.run([KICAD_CLI, "pcb", "drc", "--severity-error", "--format",
                    "json", "-o", os.path.join(HW, "drc.json"), PCB],
                   capture_output=True)
    data = json.load(open(os.path.join(HW, "drc.json")))
    pairs = []
    for u in data.get("unconnected_items", []):
        items = u.get("items", [])
        if len(items) != 2:
            continue
        a, b = items
        def lay(d):
            if "on F.Cu" in d["description"]:
                return pcbnew.F_Cu
            if "on B.Cu" in d["description"]:
                return pcbnew.B_Cu
            return None
        pairs.append(((a["pos"]["x"], a["pos"]["y"]),
                      (b["pos"]["x"], b["pos"]["y"]),
                      lay(a), lay(b),
                      a["description"] + b["description"]))
    return pairs, data.get("violations", [])


def item_layer(board, x, y, netcode):
    """Find which routable layer has this net's copper at (x,y)."""
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() != netcode:
                continue
            if abs(mm(pad.GetPosition().x) - x) < 0.01 and \
               abs(mm(pad.GetPosition().y) - y) < 0.01:
                for l in LAYERS:
                    if pad.IsOnLayer(l):
                        return l
    for t in board.GetTracks():
        if t.GetNetCode() != netcode:
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            if abs(mm(t.GetPosition().x) - x) < 0.05 and \
               abs(mm(t.GetPosition().y) - y) < 0.05:
                return pcbnew.B_Cu
        elif t.GetLayer() in LAYERS:
            for pt in (t.GetStart(), t.GetEnd()):
                if abs(mm(pt.x) - x) < 0.05 and abs(mm(pt.y) - y) < 0.05:
                    return t.GetLayer()
    return None


def netcode_at(board, x, y):
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if abs(mm(pad.GetPosition().x) - x) < 0.01 and \
               abs(mm(pad.GetPosition().y) - y) < 0.01:
                return pad.GetNetCode(), pad.GetNetname()
    for t in board.GetTracks():
        for pt in ((t.GetStart()), (t.GetEnd())):
            if abs(mm(pt.x) - x) < 0.05 and abs(mm(pt.y) - y) < 0.05:
                return t.GetNetCode(), t.GetNetname()
    return None, None


def compress(path):
    """Merge consecutive collinear same-layer steps into single segments."""
    if len(path) < 3:
        return path
    out = [path[0]]
    for i in range(1, len(path) - 1):
        x0, y0, l0 = out[-1]
        x1, y1, l1 = path[i]
        x2, y2, l2 = path[i + 1]
        if l0 == l1 == l2:
            v1 = (x1 - x0, y1 - y0)
            v2 = (x2 - x1, y2 - y1)
            if abs(v1[0] * v2[1] - v1[1] * v2[0]) < 1e-9:
                continue  # collinear: skip middle point
        out.append(path[i])
    out.append(path[-1])
    return out


def add_path(board, path, netinfo):
    path = compress(path)
    for i in range(len(path) - 1):
        (x1, y1, l1), (x2, y2, l2) = path[i], path[i + 1]
        if l1 != l2:
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(pcbnew.VECTOR2I_MM(x1, y1))
            via.SetWidth(pcbnew.FromMM(VIA_D))
            via.SetDrill(pcbnew.FromMM(VIA_DRILL))
            via.SetViaType(pcbnew.VIATYPE_THROUGH)
            via.SetNet(netinfo)
            board.Add(via)
        else:
            if (x1, y1) == (x2, y2):
                continue
            tr = pcbnew.PCB_TRACK(board)
            tr.SetStart(pcbnew.VECTOR2I_MM(x1, y1))
            tr.SetEnd(pcbnew.VECTOR2I_MM(x2, y2))
            tr.SetWidth(pcbnew.FromMM(TRACK_W))
            tr.SetLayer(l1)
            tr.SetNet(netinfo)
            board.Add(tr)


def fix_edge_vias(board):
    """Nudge vias violating copper-edge clearance back inside, moving
    coincident track endpoints with them."""
    moved = 0
    for t in list(board.GetTracks()):
        if t.Type() != pcbnew.PCB_VIA_T:
            continue
        x, y = mm(t.GetPosition().x), mm(t.GetPosition().y)
        r = mm(t.GetWidth(pcbnew.F_Cu)) / 2
        need = r + 0.35
        nxp = min(max(x, need), BOARD_W - need)
        nyp = min(max(y, need), BOARD_H - need)
        if (nxp, nyp) == (x, y):
            continue
        old = t.GetPosition()
        newpos = pcbnew.VECTOR2I_MM(nxp, nyp)
        for tr in board.GetTracks():
            if tr.Type() == pcbnew.PCB_TRACE_T:
                if tr.GetStart() == old:
                    tr.SetStart(newpos)
                if tr.GetEnd() == old:
                    tr.SetEnd(newpos)
        t.SetPosition(newpos)
        moved += 1
    print(f"edge vias nudged: {moved}")
    return moved


def main():
    import os as _os
    for it in range(int(_os.environ.get('REPAIR_ITERS', '8'))):
        pairs, _ = drc_unconnected()
        if not pairs:
            print("repair: no unconnected items remain")
            return
        prio = _os.environ.get("REPAIR_PRIORITY", "")
        if prio:
            pairs.sort(key=lambda pr: 0 if f"[{prio}]" in pr[4] else 1)
        print(f"repair iteration {it}: {len(pairs)} unconnected pairs")
        board = pcbnew.LoadBoard(PCB)
        progress = fix_edge_vias(board)
        done_nets = set()
        for (ax, ay), (bx, by), la_hint, lb_hint, _desc in pairs:
            ncode, nname = netcode_at(board, ax, ay)
            if ncode is None:
                ncode, nname = netcode_at(board, bx, by)
            if ncode is None or nname in done_nets:
                continue
            if nname in ("GND", "VDD"):
                # power lives on the planes + fanout vias; a disconnected
                # power pad is a fanout/fill problem, not a routing one
                print(f"  SKIP power pair {nname} ({ax:.2f},{ay:.2f})")
                continue
            la = la_hint or item_layer(board, ax, ay, ncode) or pcbnew.B_Cu
            lb = lb_hint or item_layer(board, bx, by, ncode) or pcbnew.B_Cu
            if (la_hint is not None and la_hint == lb_hint and
                    0.05 < math.hypot(bx - ax, by - ay) < 1.2):
                ni = board.FindNet(ncode)
                add_path(board, [(ax, ay, la), (bx, by, lb)], ni)
                print(f"  stitched {nname} ({ax:.2f},{ay:.2f})~({bx:.2f},{by:.2f})")
                done_nets.add(nname)
                progress += 1
                continue
            obs = Obstacles(board, ncode)
            obs.build_grid()
            path = astar(obs, (ax, ay), (bx, by), la, lb)
            if path is None:
                print(f"  FAIL {nname}: ({ax:.2f},{ay:.2f})->({bx:.2f},{by:.2f})")
                continue
            # stitch exact endpoints to the snapped path ends
            full = [(ax, ay, la)] + path + [(bx, by, lb)]
            add_path(board, full, board.FindNet(ncode))
            print(f"  routed {nname} ({len(path)} nodes)")
            done_nets.add(nname)
            progress += 1
        if progress == 0:
            print("repair: no progress, stopping")
            return
        # refill zones and save
        filler = pcbnew.ZONE_FILLER(board)
        filler.Fill(board.Zones())
        pcbnew.SaveBoard(PCB, board)


if __name__ == "__main__":
    main()
