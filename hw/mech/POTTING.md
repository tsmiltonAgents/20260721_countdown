# Potting the T-MINUS board — full both-sides encapsulation

Finished part: clear 52 × 29 × 14 mm rounded slab, display lens flush at
the front face, button in an open finger well, keyring hole cast-through,
battery sealed for life (fine: the mission ends 2026-10-10; cell budget
is ~2 years).

## Print

- `pot_mold.stl` — PETG or ASA, 0.2 mm layers, 4 perimeters, glossy bed
  face down. No supports. The cavity floor IS the front surface of your
  casting: print it on a smooth PEI/glass sheet for the best finish.
- `pot_button_plug.stl` — TPU (95A), 0.1 mm layers. One per pour (reusable).

## Resin

Water-clear, UV-stabilised **polyurethane casting resin**, low exotherm,
semi-rigid (Shore D 65-75) — e.g. Smooth-On Crystal Clear 202-class.
Epoxy works but yellows in sunlight within months. ~18 ml per casting.

## Process

1. **Flash the firmware first** (`cd fw && make flash`) — the TC2030 pads
   are buried forever. Insert a fresh CR2032, press the button, confirm
   the countdown. You should see the triple decimal-point "just seeded"
   flash on power-up.
2. Clean the board with IPA (PU hates fingerprint grease).
3. Seat the TPU plug in its floor recess. Wipe the mold with release
   spray (or paste wax, buffed).
4. Pour ~2 mm of resin. Lower the board in **display-down**, keyring hole
   over the pin, right edge onto the two level nubs. The display lens
   lands on the floor → flush window. Add a small weight (~100 g) on the
   board back so the lens stays pressed against the floor.
5. Fill slowly down the mold wall to the **groove line** (z = 14 mm).
   Pop surface bubbles with a heat-gun waft.
6. Cure per resin spec at room temperature (the display is only rated
   70 °C — no oven post-cure above 60 °C).
7. Flex the mold walls, push from the base, demold. Peel the TPU plug out
   of the button well. Trim the thin flash film over the button plunger
   (it cracks away on first press) and any edge flash with a deburr blade.

## Design notes (why it's shaped this way)

- The plug tops out 0.1 mm BELOW the switch plunger: if it pressed the
  button during the cure, the MCU would run the display for the whole
  cure and drain the sealed-in cell.
- The pin is Ø3.85 for a slip fit in the plated Ø4.0 ring; it also fixes
  board rotation (off-centre hole = only one way in). Display must face
  the FLOOR — if you can see the digits looking into the mold, it's
  upside down.
- 2° wall draft + rounded corners for demolding; thumb notches on both
  rims; fill groove marks the 14 mm casting height.
