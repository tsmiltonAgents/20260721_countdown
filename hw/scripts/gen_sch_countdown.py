"""Generate the countdown keyring schematic (countdown.kicad_sch) + intended
netlist (intended.json). Run with system python3.

Circuit: CR2032 -> STM32L031G6U6 direct. LSE 32.768k crystal on PC14/PC15
(15 pF loads). 4-digit CC display: segments PA0-PA7 through 330R, digit
cathodes PB0/PB1/PA8/PA9. Button PB3->GND. SWD on TC2030-NL. BOOT0 10k down.
VDDA tied to VDD net (decoupled locally by C2).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from schgen import Schematic, load_symbol, make_symbol
from sexp import find, find_all

KLIB = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"
HWDIR = os.path.join(os.path.dirname(__file__), "..", "countdown")

FP_R = "Resistor_SMD:R_0603_1608Metric"
FP_C = "Capacitor_SMD:C_0603_1608Metric"

sch = Schematic("countdown", "Keyring countdown to 2026-10-10 12:00")


def load_resolved(libfile, name, new_id):
    """Load symbol; if it extends another, use the base's geometry."""
    sym = load_symbol(libfile, name)
    ext = find(sym, "extends")
    if ext:
        sym = load_symbol(libfile, str(ext[1]))
    sch.add_lib_symbol(new_id, sym)


load_resolved(f"{KLIB}/MCU_ST_STM32L0.kicad_sym", "STM32L031G6Ux", "countdown:STM32L031G6U6")
load_resolved(f"{KLIB}/Device.kicad_sym", "R", "Device:R")
load_resolved(f"{KLIB}/Device.kicad_sym", "C", "Device:C")
load_resolved(f"{KLIB}/Device.kicad_sym", "Crystal", "Device:Crystal")
load_resolved(f"{KLIB}/power.kicad_sym", "PWR_FLAG", "power:PWR_FLAG")
sch.add_lib_symbol("countdown:KEYRING_HOLE", make_symbol("KEYRING_HOLE", [
    ("1", "RING", "passive", "L", 0),
], "H"))

sch.add_lib_symbol("countdown:DISPLAY_4DIG", make_symbol("DISPLAY_4DIG", [
    ("11", "A", "passive", "L", 0),
    ("7", "B", "passive", "L", 1),
    ("4", "C", "passive", "L", 2),
    ("2", "D", "passive", "L", 3),
    ("1", "E", "passive", "L", 4),
    ("10", "F", "passive", "L", 5),
    ("5", "G", "passive", "L", 6),
    ("3", "DP", "passive", "L", 7),
    ("12", "DIG1", "passive", "R", 0),
    ("9", "DIG2", "passive", "R", 2),
    ("8", "DIG3", "passive", "R", 4),
    ("6", "DIG4", "passive", "R", 6),
], "DS"))

sch.add_lib_symbol("countdown:CR2032_BS08", make_symbol("CR2032_BS08", [
    ("1", "+", "passive", "R", 0),
    ("2", "-", "passive", "R", 1),
], "BT"))

sch.add_lib_symbol("countdown:SW_TACT4", make_symbol("SW_TACT4", [
    ("1", "A", "passive", "L", 0),
    ("3", "C", "passive", "L", 1),
    ("2", "B", "passive", "R", 0),
    ("4", "D", "passive", "R", 1),
], "SW"))

sch.add_lib_symbol("countdown:TC2030", make_symbol("TC2030", [
    ("1", "VDD", "passive", "L", 0),
    ("3", "NRST", "passive", "L", 1),
    ("5", "GND", "passive", "L", 2),
    ("2", "SWDIO", "passive", "R", 0),
    ("4", "SWCLK", "passive", "R", 1),
    ("6", "NC", "passive", "R", 2),
], "J"))

# ---------------- placements + nets ----------------
sch.place("countdown:STM32L031G6U6", "U1", "STM32L031G6U6", (100, 100), {
    "1": "VDD", "2": "LSE_IN", "3": "LSE_OUT", "4": "NRST", "5": "VDD",
    "6": "SEG_A", "7": "SEG_B", "8": "SEG_C", "9": "SEG_D", "10": "SEG_E",
    "11": "SEG_F", "12": "SEG_G", "13": "SEG_DP", "14": "DIG_1", "15": "DIG_2",
    "16": "GND", "17": "VDD", "18": "DIG_3", "19": "DIG_4",
    "21": "SWDIO", "22": "SWCLK", "24": "BTN", "27": "BOOT0", "28": "GND",
}, footprint="Package_DFN_QFN:QFN-28_4x4mm_P0.5mm", lcsc="C96514")

sch.place("countdown:DISPLAY_4DIG", "DS1", "XL-SA2401SRWC", (220, 120), {
    "11": "LED_A", "7": "LED_B", "4": "LED_C", "2": "LED_D", "1": "LED_E",
    "10": "LED_F", "5": "LED_G", "3": "LED_DP",
    "12": "DIG_1", "9": "DIG_2", "8": "DIG_3", "6": "DIG_4",
}, footprint="countdown:XL-SA2401SRWC", lcsc="C49652871")

SEGS = ["A", "B", "C", "D", "E", "F", "G", "DP"]
for i, sname in enumerate(SEGS):
    sch.place("Device:R", f"R{i+1}", "330R", (160 + (i % 4) * 25, 55 + (i // 4) * 25),
              {"1": f"SEG_{sname}", "2": f"LED_{sname}"},
              footprint=FP_R, lcsc="C23138")

sch.place("Device:R", "R9", "10k", (60, 130), {"1": "BOOT0", "2": "GND"},
          footprint=FP_R, lcsc="C25804")

sch.place("countdown:CR2032_BS08", "BT1", "BS-08-B2AA001", (40, 40),
          {"1": "VDD", "2": "GND"},
          footprint="countdown:BS-08-B2AA001", lcsc="C964777")

sch.place("Device:Crystal", "Y1", "32.768kHz", (60, 100),
          {"1": "LSE_IN", "2": "LSE_OUT"},
          footprint="Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm", lcsc="C32346")
sch.place("Device:C", "C7", "15pF", (35, 100), {"1": "LSE_IN", "2": "GND"},
          footprint=FP_C, lcsc="C1644")
sch.place("Device:C", "C8", "15pF", (82, 100), {"1": "LSE_OUT", "2": "GND"},
          footprint=FP_C, lcsc="C1644")

for ref, val, lcsc, x in (("C1", "100nF", "C14663", 60),
                          ("C2", "100nF", "C14663", 80),
                          ("C4", "1uF", "C15849", 100),
                          ("C5", "10uF", "C19702", 120),
                          ("C6", "10uF", "C19702", 140)):
    sch.place("Device:C", ref, val, (x, 40), {"1": "VDD", "2": "GND"},
              footprint=FP_C, lcsc=lcsc)
sch.place("Device:C", "C3", "100nF", (60, 70), {"1": "NRST", "2": "GND"},
          footprint=FP_C, lcsc="C14663")

# Diagonal wiring (pins 1 and 4 only): the TS-1187A internally commons its
# pads in pairs; a diagonal always spans the switch contact regardless of
# whether the pairing runs along the edges or the sides. Orientation-proof.
sch.place("countdown:SW_TACT4", "SW1", "TS-1187A-B-A-B", (160, 150), {
    "1": "BTN", "4": "GND",
}, footprint="countdown:SW_TS-1187A", lcsc="C318884")

sch.place("countdown:TC2030", "J1", "TC2030-SWD", (45, 150), {
    "1": "VDD", "2": "SWDIO", "3": "NRST", "4": "SWCLK", "5": "GND",
}, footprint="Connector:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical")

sch.place("countdown:KEYRING_HOLE", "H1", "KeyringHole", (20, 170),
          {"1": "GND"}, footprint="countdown:KeyringHole_4mm")

sch.place("power:PWR_FLAG", "#FLG01", "PWR_FLAG", (20, 190), {"1": "VDD"})
sch.place("power:PWR_FLAG", "#FLG02", "PWR_FLAG", (30, 190), {"1": "GND"})

sch.add_text("Keyring countdown -> 2026-10-10 12:00. CR2032 direct power.", 20, 15)

os.makedirs(HWDIR, exist_ok=True)
with open(os.path.join(HWDIR, "countdown.kicad_sch"), "w") as f:
    f.write(sch.emit())

# also emit the custom symbols as a real library so the 'countdown' lib
# reference resolves (removes lib_symbol_issues ERC warnings)
from sexp import Sym, dump
lib = [Sym("kicad_symbol_lib"), [Sym("version"), 20250114],
       [Sym("generator"), "gen_sch_countdown"]]
for lib_id, sym in sch.lib_symbols.items():
    if lib_id.startswith("countdown:"):
        s2 = [x for x in sym]
        s2[1] = lib_id.split(":")[1]
        base = lib_id.split(":")[1]
        for i, ch in enumerate(s2):
            if isinstance(ch, list) and ch and ch[0] == "symbol":
                pass  # child names already use the derived base
        lib.append(s2)
with open(os.path.join(HWDIR, "..", "lib", "countdown.kicad_sym"), "w") as f:
    f.write(dump(lib) + "\n")
with open(os.path.join(HWDIR, "intended.json"), "w") as f:
    json.dump({k: sorted(v) for k, v in sch.intended_nets().items()}, f, indent=1)
print("schematic + intended.json written")
