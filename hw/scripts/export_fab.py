"""Export JLCPCB fabrication files: gerbers+drill (zip), BOM csv, CPL csv.

Run with KiCad's bundled python (needs pcbnew) for the CPL; gerbers via
kicad-cli. Reads part metadata (LCSC number, JLC rotation offset) from
footprint fields set by gen_pcb.py.

Usage: kicad-python export_fab.py <board.kicad_pcb> <outdir>
"""
import csv
import os
import subprocess
import sys

import pcbnew

KICAD_CLI = "/Applications/KiCadCLI/Contents/MacOS/kicad-cli"


def export_gerbers(board_path, outdir):
    gdir = os.path.join(outdir, "gerbers")
    os.makedirs(gdir, exist_ok=True)
    layers = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"
    subprocess.run([KICAD_CLI, "pcb", "export", "gerbers",
                    "-l", layers, "--subtract-soldermask",
                    "--use-drill-file-origin",
                    "-o", gdir + "/", board_path],
                   check=True, capture_output=True)
    subprocess.run([KICAD_CLI, "pcb", "export", "drill",
                    "--format", "excellon", "--drill-origin", "plot",
                    "--excellon-units", "mm", "--generate-map",
                    "--map-format", "gerberx2",
                    "-o", gdir + "/", board_path],
                   check=True, capture_output=True)
    return gdir


def export_bom_cpl(board_path, outdir):
    board = pcbnew.LoadBoard(board_path)
    origin = board.GetDesignSettings().GetAuxOrigin()
    rows = {}
    cpl = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if fp.GetAttributes() & pcbnew.FP_EXCLUDE_FROM_BOM:
            continue
        lcsc = fp.GetFieldText("LCSC") if fp.HasField("LCSC") else ""
        if not lcsc:
            print(f"WARN: {ref} has no LCSC number; excluded from BOM/CPL")
            continue
        val = fp.GetValue()
        pkg = str(fp.GetFPID().GetLibItemName())
        rows.setdefault((val, pkg, lcsc), []).append(ref)

        pos = fp.GetPosition() - origin
        x_mm = pcbnew.ToMM(pos.x)
        y_mm = -pcbnew.ToMM(pos.y)  # JLC Y grows up; KiCad internal Y grows down
        rot = fp.GetOrientationDegrees()
        joff = float(fp.GetFieldText("JLCROT")) if fp.HasField("JLCROT") else 0.0
        layer = "Top" if fp.GetLayer() == pcbnew.F_Cu else "Bottom"
        if layer == "Bottom":
            # JLC expects rotation as seen from the bottom; KiCad reports
            # bottom parts with mirrored X. Standard correction: (180 - rot).
            rot = (180.0 - rot) % 360.0
        cpl.append([ref, f"{x_mm:.4f}mm", f"{y_mm:.4f}mm", layer,
                    f"{(rot + joff) % 360.0:.1f}"])

    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "bom.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (val, pkg, lcsc), refs in sorted(rows.items(), key=lambda kv: kv[1][0]):
            w.writerow([val, ",".join(sorted(refs)), pkg, lcsc])
    with open(os.path.join(outdir, "cpl.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for row in sorted(cpl):
            w.writerow(row)
    print(f"BOM: {len(rows)} line items; CPL: {len(cpl)} placements")


if __name__ == "__main__":
    board_path, outdir = sys.argv[1], sys.argv[2]
    export_gerbers(board_path, outdir)
    export_bom_cpl(board_path, outdir)
    print("fab export complete:", outdir)
