# Ordering from JLCPCB — step by step

Files in this directory:
- `gerbers.zip` — upload this as the Gerber file
- `bom.csv` — BOM (Comment / Designator / Footprint / LCSC Part #)
- `cpl.csv` — pick-and-place (Designator / Mid X / Mid Y / Layer / Rotation)

## PCB options (jlcpcb.com → "Add gerber file")

| Option | Value | Why |
|---|---|---|
| Layers | 4 (auto-detected) | stackup JLC04161H-7628, default |
| Dimensions | 44 × 23 mm (auto) | |
| PCB Qty | 5 (minimum) | you'll assemble 2 |
| Thickness | 1.6 mm | |
| Solder mask | **Black** | the look; green is fine if lead time matters |
| Silkscreen | White | |
| Surface finish | **ENIG** (~+$13) | flat pads under the display + gold TC2030 pads; LeadFree HASL works if you want it cheaper |
| Via covering | Tented | default |
| Remove order number | "Specify a location" | free; the JLC order text lands on the back silk |

## Assembly options

- **PCB Assembly: ON** → **Standard** service (the battery holder is on the
  back and the display on the front → double-sided assembly; Economic is
  single-sided only).
- Assembly side: **Both sides**. Qty: 2.
- Upload `bom.csv` + `cpl.csv` when prompted.
- Part matching: 10 line items, 3 Extended (U1 MCU, DS1 display, BT1 battery
  holder → ~$3 loading fee each), rest Basic. J1/H1 have no part — that is
  correct (Tag-Connect pads and the keyring hole), confirm them as
  "Do not place".
- **CRITICAL — placement preview**: on the "Review Parts Placement" step,
  check with your eyes:
  1. **U1** (STM32, QFN28): the orientation dot must sit at the pin-1 corner
     (the CPL already applies the +270° tape correction — but JLC has
     changed conventions before; the preview is the ground truth).
  2. **DS1** (display): digits upright, decimal points at the bottom-right
     of each digit, pin 1 bottom-left.
  3. **BT1** (battery holder): "+" tab on the right (toward the MCU end),
     insertion mouth toward the keyring hole.
  4. **SW1**: square 4-pad switch, any 0/180° is fine, 90° is also
     electrically fine here (pads are symmetric) — just confirm it sits on
     its pads.
  The editor lets you rotate parts in-browser before paying — use it if
  anything looks off, and note the correction in designlog.md.

## After the boards arrive

1. `cd fw && make && make flash` (needs `arm-none-eabi-gcc`, `pyocd`, an
   ST-Link/CMSIS-DAP probe and a Tag-Connect TC2030-IDC-NL cable — or hold
   pogo pins / solder fine wires to the 6 pads).
   Flash **right after** building: the RTC is seeded with the build
   timestamp at first power-up.
2. Insert a CR2032 (+ side up/outward), press the button: hours remaining
   to 2026-10-10 12:00 light up.
3. Split ring through the Ø4 hole. Done.

Battery notes: display brightness tracks the cell voltage (it dims as the
cell ages — that's your battery gauge). Expect ~2 years typical use.
