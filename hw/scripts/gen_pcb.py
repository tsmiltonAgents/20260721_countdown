"""Build countdown.kicad_pcb from the exported netlist + placement table.
Run with KiCad's bundled python (pcbnew).

Layout (mm, origin = board top-left; board 44 x 22, corner R3):
- FRONT: keyring hole (4.6, 11); display centered (21.35, 11.5); 8 segment
  resistors in the top/bottom silk bands; button right edge (39.4, 11).
- BACK: CR2032 holder (19, 11) mouth facing left; MCU column x~36-43:
  QFN28 (38.6, 5), crystal + loads below it, TC2030 (38.8, 16.6) vertical.
Note: pcbnew mirrors X for bottom-side footprints when flipping; the
placement table below gives *top-view* coordinates for every part; for
back parts we flip in place, which keeps the position and mirrors the
footprint about its own origin — verified by the rendered views.
"""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp import parse, find, find_all

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
HW = os.path.join(ROOT, "hw", "countdown")
KFP = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
LIBMAP = {
    "Resistor_SMD": f"{KFP}/Resistor_SMD.pretty",
    "Capacitor_SMD": f"{KFP}/Capacitor_SMD.pretty",
    "Package_DFN_QFN": f"{KFP}/Package_DFN_QFN.pretty",
    "Crystal": f"{KFP}/Crystal.pretty",
    "Connector": f"{KFP}/Connector.pretty",
    "countdown": os.path.join(ROOT, "hw", "lib", "countdown.pretty"),
}

BOARD_W, BOARD_H, RAD = 44.0, 23.0, 3.0

# ref: (x, y, rot_deg, side)
PLACE = {
    "H1":  (4.0, 11.5, 0, "F"),
    "DS1": (21.35, 12.0, 0, "F"),
    "SW1": (39.4, 11.5, 90, "F"),
    # segment resistors: R1..R8 = A B C D E F G DP
    # bottom-row display pins (y+): 1=E 2=D 3=DP 4=C 5=G -> R5,R4,R8,R3,R7 below
    "R5": (14.0, 20.0, 0, "F"),   # E   (DS pin 1 at x=15.0)
    "R4": (17.5, 20.0, 0, "F"),   # D   (pin 2 at 17.54)
    "R8": (21.0, 20.0, 0, "F"),   # DP  (pin 3 at 20.08)
    "R3": (24.5, 20.0, 0, "F"),   # C   (pin 4 at 22.62)
    "R7": (28.0, 20.0, 0, "F"),   # G   (pin 5 at 25.16)
    # top-row display pins (y-): 7=B 10=F 11=A -> R2,R6,R1 above
    "R2": (26.5, 2.0, 0, "F"),    # B   (pin 7 at 27.7)
    "R6": (18.5, 2.0, 0, "F"),    # F   (pin 10 at 20.08)
    "R1": (14.5, 2.0, 0, "F"),    # A   (pin 11 at 17.54)
    # BACK
    "BT1": (19.4, 11.5, 0, "B"),  # (+) tab right, mouth toward hole (empirical)
    "U1":  (38.6, 5.0, 0, "B"),
    "Y1":  (34.4, 5.6, 90, "B"),
    "C7":  (33.0, 1.9, 90, "B"),   # LSE_IN load
    "C8":  (34.9, 2.0, 90, "B"),  # LSE_OUT load
    "C1":  (41.5, 8.8, 90, "B"),   # 100n VDD (near pin 17 side)
    "C2":  (35.8, 9.6, 0, "B"),   # clear of the QFN south escape field    # 100n VDDA (near pin 5)
    "C3":  (33.6, 18.6, 0, "B"),    # 100n NRST
    "C4":  (8.0, 1.6, 0, "B"),   # 1u VDD
    "C5":  (4.6, 2.0, 0, "B"),     # 10u bulk
    "C6":  (4.6, 21.0, 0, "B"),    # 10u bulk
    "R9":  (2.6, 7.0, 90, "B"),    # BOOT0 10k
    "J1":  (38.8, 18.5, 90, "B"),  # TC2030
}


def read_netlist(path):
    doc = parse(open(path).read())
    comps = {}
    for c in find_all(find(doc, "components"), "comp"):
        ref = str(find(c, "ref")[1])
        fp = str(find(c, "footprint")[1])
        val = str(find(c, "value")[1])
        lcsc = ""
        fields = find(c, "fields")
        if fields:
            for f in find_all(fields, "field"):
                if str(f[1][1]) == "LCSC":
                    lcsc = str(f[2]) if len(f) > 2 else ""
        comps[ref] = (fp, val, lcsc)
    nets = {}
    for n in find_all(find(doc, "nets"), "net"):
        name = str(find(n, "name")[1])
        for nd in find_all(n, "node"):
            ref = str(find(nd, "ref")[1])
            pin = str(find(nd, "pin")[1])
            nets.setdefault(name, []).append((ref, pin))
    return comps, nets


def rounded_rect(board, w, h, r):
    L = pcbnew.Edge_Cuts
    def seg(x1, y1, x2, y2):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pcbnew.VECTOR2I_MM(x1, y1))
        s.SetEnd(pcbnew.VECTOR2I_MM(x2, y2))
        s.SetLayer(L); s.SetWidth(pcbnew.FromMM(0.1))
        board.Add(s)
    def arc(cx, cy, sx, sy, angle_deg):
        a = pcbnew.PCB_SHAPE(board)
        a.SetShape(pcbnew.SHAPE_T_ARC)
        a.SetCenter(pcbnew.VECTOR2I_MM(cx, cy))
        a.SetStart(pcbnew.VECTOR2I_MM(sx, sy))
        a.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(angle_deg, pcbnew.DEGREES_T), False)
        a.SetLayer(L); a.SetWidth(pcbnew.FromMM(0.1))
        board.Add(a)
    seg(r, 0, w - r, 0)
    seg(w, r, w, h - r)
    seg(w - r, h, r, h)
    seg(0, h - r, 0, r)
    # corners: KiCad Y grows down; +angle sweeps clockwise on screen
    arc(r, r, 0, r, 90)                # top-left: (0,r) -> (r,0)
    arc(w - r, r, w - r, 0, 90)        # top-right: (w-r,0) -> (w,r)
    arc(w - r, h - r, w, h - r, 90)    # bottom-right: (w,h-r) -> (w-r,h)
    arc(r, h - r, r, h, 90)            # bottom-left: (r,h) -> (0,h-r)


U1_POWER_VIAS = {
    # pad: (via_x, via_y) — verified >=0.58 mm from all other-net pad copper
    "1": (36.1, 7.6),    # VDD  (spot legal vs C7/SW1/pad28 on the bare board)
    "28": (37.1, 9.5),   # GND  (clears SW1 F pads and Y1)
}


def add_u1_power_vias(board, netinfo):
    u1 = board.FindFootprintByReference("U1")
    for padnum, (vx, vy) in U1_POWER_VIAS.items():
        pad = u1.FindPadByNumber(padnum)
        net = pad.GetNetname()
        px, py = pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y)
        via = pcbnew.PCB_VIA(board)
        via.SetPosition(pcbnew.VECTOR2I_MM(vx, vy))
        via.SetWidth(pcbnew.FromMM(0.6))
        via.SetDrill(pcbnew.FromMM(0.3))
        via.SetViaType(pcbnew.VIATYPE_THROUGH)
        via.SetNet(netinfo[net])
        board.Add(via)
        tr = pcbnew.PCB_TRACK(board)
        tr.SetStart(pcbnew.VECTOR2I_MM(px, py))
        tr.SetEnd(pcbnew.VECTOR2I_MM(vx, vy))
        tr.SetWidth(pcbnew.FromMM(0.25))
        tr.SetLayer(u1.GetLayer())  # SMD pad lives on the footprint's side
        tr.SetNet(netinfo[net])
        board.Add(tr)
    print("U1 power vias:", len(U1_POWER_VIAS))


def add_power_fanout(board, netinfo):
    import math
    VIA_D, VIA_DRILL, STUB_W = 0.6, 0.3, 0.3
    placed = []  # (x, y, netname)
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            placed.append((pcbnew.ToMM(t.GetPosition().x),
                           pcbnew.ToMM(t.GetPosition().y), t.GetNetname()))
    obstacles = []  # (x, y, halfw, halfh, netname) pad boxes
    # no-fly bboxes: courtyards of dense/sensitive parts (QFN escape lanes,
    # display underside mold marks, switch, tag-connect field)
    nofly = []
    for r in ("DS1", "J1"):
        f = board.FindFootprintByReference(r)
        bb = f.GetBoundingBox(False)
        box = (pcbnew.ToMM(bb.GetLeft()) - 0.15, pcbnew.ToMM(bb.GetTop()) - 0.15,
               pcbnew.ToMM(bb.GetRight()) + 0.15, pcbnew.ToMM(bb.GetBottom()) + 0.15)
        nofly.append(box)
        print(f"nofly {r}: {[round(v,1) for v in box]}")
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            obstacles.append((pcbnew.ToMM(bb.GetCenter().x),
                              pcbnew.ToMM(bb.GetCenter().y),
                              pcbnew.ToMM(bb.GetWidth()) / 2,
                              pcbnew.ToMM(bb.GetHeight()) / 2,
                              pad.GetNetname()))
    hx, hy = PLACE["H1"][0], PLACE["H1"][1]

    def ok_spot(x, y, netname):
        if not (1.2 <= x <= BOARD_W - 1.2 and 1.2 <= y <= BOARD_H - 1.2):
            return False
        if math.hypot(x - hx, y - hy) < 3.4 + 0.35:
            return False
        for x1, y1, x2, y2 in nofly:
            if x1 <= x <= x2 and y1 <= y <= y2:
                return False
        for vx, vy, vn in placed:
            need = 0.65 if vn == netname else 0.85
            if math.hypot(x - vx, y - vy) < need:
                return False
        for ox, oy, hw, hh, on in obstacles:
            if on == netname:
                continue
            dx = max(abs(x - ox) - hw, 0)
            dy = max(abs(y - oy) - hh, 0)
            if math.hypot(dx, dy) < 0.3 + 0.2:  # via radius + clearance
                return False
        return True

    n_vias = 0
    for fp in board.GetFootprints():
        cx = pcbnew.ToMM(fp.GetPosition().x)
        cy = pcbnew.ToMM(fp.GetPosition().y)
        if fp.GetReference() == "U1":
            continue  # freerouting fans out the QFN power pins to the planes
        for pad in fp.Pads():
            net = pad.GetNetname()
            if net not in ("GND", "VDD"):
                continue
            if fp.GetReference() == "BT1":
                # huge mechanical tabs: via-in-pad is standard practice here
                px = pcbnew.ToMM(pad.GetPosition().x)
                py = pcbnew.ToMM(pad.GetPosition().y)
                via = pcbnew.PCB_VIA(board)
                via.SetPosition(pad.GetPosition())
                via.SetWidth(pcbnew.FromMM(VIA_D))
                via.SetDrill(pcbnew.FromMM(VIA_DRILL))
                via.SetViaType(pcbnew.VIATYPE_THROUGH)
                via.SetNet(netinfo[net])
                board.Add(via)
                placed.append((px, py, net))
                n_vias += 1
                continue
            px = pcbnew.ToMM(pad.GetPosition().x)
            py = pcbnew.ToMM(pad.GetPosition().y)
            dx, dy = px - cx, py - cy
            norm = math.hypot(dx, dy) or 1.0
            ux, uy = dx / norm, dy / norm
            cands = []
            for dist in (1.0, 1.4, 1.9, 2.4):
                for rot in (0, 35, -35, 70, -70, 110, -110, 180):
                    a = math.radians(rot)
                    rx = ux * math.cos(a) - uy * math.sin(a)
                    ry = ux * math.sin(a) + uy * math.cos(a)
                    cands.append((px + rx * dist, py + ry * dist))
            spot = next(((x, y) for x, y in cands if ok_spot(x, y, net)), None)
            if spot is None:
                print(f"WARN: no fanout spot for {fp.GetReference()} pad {pad.GetNumber()} ({net})")
                continue
            vx, vy = spot
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(pcbnew.VECTOR2I_MM(vx, vy))
            via.SetWidth(pcbnew.FromMM(VIA_D))
            via.SetDrill(pcbnew.FromMM(VIA_DRILL))
            via.SetViaType(pcbnew.VIATYPE_THROUGH)
            via.SetNet(netinfo[net])
            board.Add(via)
            tr = pcbnew.PCB_TRACK(board)
            tr.SetStart(pcbnew.VECTOR2I_MM(px, py))
            tr.SetEnd(pcbnew.VECTOR2I_MM(vx, vy))
            tr.SetWidth(pcbnew.FromMM(STUB_W))
            tr.SetLayer(pad.GetLayer())
            tr.SetNet(netinfo[net])
            board.Add(tr)
            placed.append((vx, vy, net))
            n_vias += 1
    print("fanout vias:", n_vias)


def main():
    comps, nets = read_netlist(os.path.join(HW, "countdown.net"))
    missing = set(comps) - set(PLACE)
    extra = set(PLACE) - set(comps)
    if missing or extra:
        raise SystemExit(f"placement table mismatch: missing={missing} extra={extra}")

    pcb_path = os.path.join(HW, "countdown.kicad_pcb")
    if os.path.exists(pcb_path):
        os.remove(pcb_path)
    board = pcbnew.NewBoard(pcb_path)
    board.SetCopperLayerCount(4)

    rounded_rect(board, BOARD_W, BOARD_H, RAD)

    netinfo = {}
    for name in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni
    pin2net = {}
    for name, nodes in nets.items():
        for ref, pin in nodes:
            pin2net[(ref, pin)] = name

    for ref, (fpid, val, lcsc) in sorted(comps.items()):
        libname, fpname = fpid.split(":")
        fp = pcbnew.FootprintLoad(LIBMAP[libname], fpname)
        if fp is None:
            raise SystemExit(f"footprint not found: {fpid}")
        fp.SetReference(ref)
        fp.SetValue(val)
        if ref == "U1":
            # UFQFPN28 exposed die pad is VSS-bonded (DocID027063): add it as
            # GND copper, mask-opened, NO paste (assembly unchanged). Also
            # physically blocks the autorouter from parking vias under it.
            ep = pcbnew.PAD(fp)
            ep.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
            ep.SetShape(pcbnew.PAD_SHAPE_RECT)
            ep.SetSize(pcbnew.VECTOR2I_MM(2.7, 2.7))
            ep.SetPosition(fp.GetPosition())
            ep.SetNumber("16")  # same net as VSS pin 16
            ls = pcbnew.LSET()
            ls.AddLayer(pcbnew.F_Cu)
            ls.AddLayer(pcbnew.F_Mask)
            ep.SetLayerSet(ls)
            fp.Add(ep)
        x, y, rot, side = PLACE[ref]
        board.Add(fp)
        fp.SetPosition(pcbnew.VECTOR2I_MM(x, y))
        if side == "B":
            fp.Flip(fp.GetPosition(), True)
        fp.SetOrientationDegrees(rot)
        if ref == "U1":
            # JLC tape orientation for QFN: +270 vs KiCad (matthewlai/Bouni/
            # KiBot consensus) — MUST be eyeballed in the JLC placement
            # preview before payment
            fp.SetField("JLCROT", "270")
            f2 = fp.GetField("JLCROT")
            if f2 is not None:
                f2.SetVisible(False)
                f2.SetLayer(pcbnew.B_Fab)
        if lcsc:
            fp.SetField("LCSC", lcsc)
            fld = fp.GetField("LCSC")
            if fld is not None:
                fld.SetVisible(False)
                fld.SetLayer(pcbnew.F_Fab if side == "F" else pcbnew.B_Fab)
        fp.Reference().SetVisible(False)  # bare-board look; CPL drives placement
        for pad in fp.Pads():
            key = (ref, pad.GetNumber())
            if key in pin2net:
                pad.SetNet(netinfo[pin2net[key]])

    # drill/place origin at board bottom-left for JLC-friendly coords
    ds = board.GetDesignSettings()
    ds.SetAuxOrigin(pcbnew.VECTOR2I_MM(0, BOARD_H))

    # ---- power planes (In1 = GND, In2 = VDD): added post-route by
    # finish_pcb.py — freerouting 2.2.4 silently drops nets when it sees
    # planes/keepouts, so its DSN input must stay plain (empirical)
    for layer, netname in () if os.environ.get("ZONES") != "1" else (
            (pcbnew.In1_Cu, "GND"), (pcbnew.In2_Cu, "VDD")):
        zone = pcbnew.ZONE(board)
        zone.SetLayer(layer)
        zone.SetNetCode(netinfo[netname].GetNetCode())
        zone.Outline().NewOutline()
        for zx, zy in ((-1, -1), (BOARD_W + 1, -1), (BOARD_W + 1, BOARD_H + 1),
                       (-1, BOARD_H + 1)):
            zone.Outline().Append(pcbnew.VECTOR2I_MM(zx, zy))
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        zone.SetMinThickness(pcbnew.FromMM(0.2))
        zone.SetLocalClearance(pcbnew.FromMM(0.25))
        board.Add(zone)

    # copper keepout ring around the keyring hole (both outer layers) so the
    # split ring can never scratch into live copper
    def add_keepout(pts):
        z = pcbnew.ZONE(board)
        z.SetIsRuleArea(True)
        z.SetDoNotAllowTracks(True)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowZoneFills(False)
        try:
            z.SetDoNotAllowPads(False)
            z.SetDoNotAllowFootprints(False)
        except AttributeError:
            pass
        z.SetLayerSet(pcbnew.LSET.AllCuMask(4))
        z.Outline().NewOutline()
        for px, py in pts:
            z.Outline().Append(pcbnew.VECTOR2I_MM(px, py))
        board.Add(z)

    # (border keepout strips removed: freerouting mishandles them; edge
    # violations are fixed deterministically post-import instead)

    # (keyring hole is now a plated GND pad — its own copper clearance rules
    # keep other nets away; no rule area needed)

    # power fanout happens post-route (fanout_post.py); only the two
    # QFN-corner power pins are pre-fanned here (their pocket gets walled in
    # by signal escapes otherwise)

    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(pcb_path, board)
    print("saved", pcb_path)

    # connectivity sanity: every net with >=2 pads should have a ratsnest
    board.BuildConnectivity()
    print("footprints:", len(board.GetFootprints()), "nets:", board.GetNetCount())

    dsn_path = os.path.join(HW, "countdown.dsn")
    ok = pcbnew.ExportSpecctraDSN(board, dsn_path)
    print("DSN export:", ok)
    # mark inner layers as power planes so freerouting keeps signals off them
    txt = open(dsn_path).read()
    if os.environ.get("POWER_LAYERS", "0") == "1":
        for lname in ("In1.Cu", "In2.Cu"):
            txt = txt.replace(f'(layer {lname}\n      (type signal)',
                              f'(layer {lname}\n      (type power)')
    open(dsn_path, "w").write(txt)
    print("DSN inner layers set to power:", txt.count("(type power)"))


if __name__ == "__main__":
    main()
