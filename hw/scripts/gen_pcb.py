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

BOARD_W, BOARD_H, RAD = 44.0, 22.0, 3.0

# ref: (x, y, rot_deg, side)
PLACE = {
    "H1":  (4.0, 11.0, 0, "F"),
    "DS1": (21.35, 11.5, 0, "F"),
    "SW1": (39.4, 11.0, 90, "F"),
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
    "BT1": (19.4, 11.0, 0, "B"),  # (+) tab right, mouth toward hole (empirical)
    "U1":  (38.6, 5.0, 0, "B"),
    "Y1":  (37.1, 10.0, 90, "B"),
    "C7":  (35.2, 7.0, 90, "B"),   # LSE_IN load
    "C8":  (35.2, 11.4, 90, "B"),  # LSE_OUT load
    "C1":  (41.5, 8.8, 90, "B"),   # 100n VDD (near pin 17 side)
    "C2":  (36.0, 1.6, 0, "B"),    # 100n VDDA (near pin 5)
    "C3":  (41.5, 1.5, 0, "B"),    # 100n NRST
    "C4":  (38.6, 13.1, 0, "B"),   # 1u VDD
    "C5":  (4.6, 1.9, 0, "B"),     # 10u bulk
    "C6":  (4.6, 20.1, 0, "B"),    # 10u bulk
    "R9":  (2.6, 6.5, 90, "B"),    # BOOT0 10k
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
        x, y, rot, side = PLACE[ref]
        board.Add(fp)
        fp.SetPosition(pcbnew.VECTOR2I_MM(x, y))
        if side == "B":
            fp.Flip(fp.GetPosition(), True)
        fp.SetOrientationDegrees(rot)
        if lcsc:
            fp.SetField("LCSC", lcsc)
            fld = fp.GetField("LCSC")
            if fld is not None:
                fld.SetVisible(False)
                fld.SetLayer(pcbnew.F_Fab if side == "F" else pcbnew.B_Fab)
        for pad in fp.Pads():
            key = (ref, pad.GetNumber())
            if key in pin2net:
                pad.SetNet(netinfo[pin2net[key]])

    # drill/place origin at board bottom-left for JLC-friendly coords
    ds = board.GetDesignSettings()
    ds.SetAuxOrigin(pcbnew.VECTOR2I_MM(0, BOARD_H))

    pcbnew.SaveBoard(pcb_path, board)
    print("saved", pcb_path)

    # connectivity sanity: every net with >=2 pads should have a ratsnest
    board.BuildConnectivity()
    print("footprints:", len(board.GetFootprints()), "nets:", board.GetNetCount())

    ok = pcbnew.ExportSpecctraDSN(board, os.path.join(HW, "countdown.dsn"))
    print("DSN export:", ok)


if __name__ == "__main__":
    main()
