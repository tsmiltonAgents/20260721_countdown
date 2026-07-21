# Design Log — Keyring Countdown PCB

Countdown target: **2026-10-10 12:00 (local)** — displays hours remaining on a 4-digit 7-segment display.

## 2026-07-21 21:05 — Project kickoff & requirements analysis

**Requirements (from brief):**
- Small keyring PCB, 7-segment display counting down to 2026-10-10 12:00, in hours or minutes
- Battery powered, keeps running once started
- JLCPCB fab + assembly (SMT pick-and-place), parts from JLCPCB/LCSC catalog
- 4-layer board, autorouted (no hand routing)
- Compact programming interface (Tag-Connect style, not USB)
- Bare-board aesthetic, pretty; potting optional later
- Deliverables: gerbers, BOM, CPL (pick and place), verified design

**Key engineering decision — display duty cycle vs battery life:**
A CR2032 holds ~220 mAh. A 4-digit LED display multiplexed at even ~4 mA average
would flatten the cell in ~2 days. An always-on display is physically impossible
on a coin cell at keyring size. Decision: the MCU keeps time continuously in
deep sleep (RTC on a 32.768 kHz crystal, ~1 µA), and the display lights on a
button press for a few seconds. Timekeeping "just keeps running" for years;
the display is on-demand. This is the same pattern as a wristwatch backlight.

**Countdown math:** from ~2026-07-25 (assembly arrival) to 2026-10-10 12:00 is
~1850 hours — fits 4 digits displaying hours. Below 100 hours we can switch the
firmware to minutes (max 5999 min = 99h59m fits 4 digits) for drama at the end.

**Architecture chosen (pending part research):**
- MCU: STM32 low-power series (L0/G0) with LSE 32.768 kHz crystal + RTC,
  direct-driving a multiplexed 4-digit 7-seg (12 GPIO) — no display driver IC,
  minimal BOM, display fully off in sleep.
- Power: CR2032 in SMD holder, no regulator (STM32 runs 1.8–3.6 V direct).
- Programming: SWD via Tag-Connect TC2030-style footprint (zero BOM cost, no
  connector height) — decided to also evaluate tiny header alternatives.
- Button: side-actuated or top tactile SMD, wakes display / shows countdown.

**Toolchain:** KiCad 10.0.4 (CLI + pcbnew Python), Freerouting autorouter
(Java to be installed), arm-none-eabi-gcc for firmware verification, JLCPCB
fab output conventions.

**Verification plan:** ERC → netlist-driven PCB → DRC → rendered-image visual
inspection → independent subagent reviews (electrical, footprint-vs-datasheet,
JLC DFM, BOM stock) → firmware compiles against the real pinout.

## 2026-07-21 21:20 — Toolchain proven end-to-end (dry run)

- Installed: OpenJDK + Freerouting 2.2.4 (jar, CLI mode works), arm-none-eabi-gcc 16.1.0.
- Built `hw/scripts/sexp.py` + `schgen.py`: programmatic KiCad-10 schematic
  generation. Approach: global label placed exactly on every pin end (KiCad
  connects label-on-pin without wires), PWR_FLAG symbols for ERC power checks.
- Test circuit (2 resistors + custom symbol + flags): **ERC = 0 violations**,
  and `verify_netlist.py` confirms exported netlist == intended netlist
  exactly (including a rotated symbol — coordinate transform verified).
- pcbnew Python API verified: NewBoard, 4-layer, FootprintLoad, net assignment,
  Specctra DSN export all work headless.
- KiCad stock footprints available for: Tag-Connect TC2030-IDC-NL, 3215 crystal,
  MYOUNG BS-07 CR2032 holder — fewer custom footprints to author.

## 2026-07-21 21:20 — JLCPCB fab/assembly research findings (agent)

- **Economic assembly: single-sided only**, but supports 4-layer boards and
  THT on the same side; $8 setup. **Standard assembly: double-sided**, $25
  setup, min 70×70mm single board → small boards get "panel by JLCPCB".
- 4-layer via sweet spot without surcharge: **≥0.3mm drill / 0.45mm+ pad**;
  track/space keep ≥0.127mm (surcharge below 0.09/0.09 anyway at 3.5mil).
- Stackup JLC04161H-7628 default. All soldermask colors available on 4-layer.
- BOM columns: `Comment,Designator,Footprint,LCSC Part #`. CPL columns:
  `Designator,Mid X,Mid Y,Layer,Rotation` (mm, CCW+). KiCad pos output needs
  renaming + per-package rotation correction (Fabrication-Toolkit conventions).
- Open decision: single-sided Economic (bigger board, cheaper) vs double-sided
  Standard (compact ~34×22mm, panelized by JLC). Leaning double-sided for a
  keyring-worthy form factor — final call once display + holder dims are in.

## 2026-07-21 21:30 — Support parts selected (agent research, July 2026 stock)

| Part | Choice | LCSC | Status | Notes |
|---|---|---|---|---|
| 32.768 kHz crystal | Epson Q13FC13500004 (FC-135), 3215 | C32346 | **Basic**, 300k stock | CL=12.5 pF → 15 pF load caps |
| Tactile switch | XKB TS-1187A-B-A-B, 5.1×5.1×1.5 mm | C318884 | **Basic**, 1.17M stock | pins common per long edge |
| CR2032 holder | MYOUNG BS-08-B2AA001, 24.1×15.7×5.3 mm | C964777 | Extended | compact; alt Q&J C70377 (31mm, cheaper) |
| Passives 0603 | 100n C14663, 1µ C15849, 10µ C19702, 10k C25804, 330R C23138, 470R C23179 | — | all **Basic** | |
| SWD | Tag-Connect TC2030-IDC-NL footprint | none | zero BOM | **no paste apertures**, NPTH Ø0.99mm locating holes |

## 2026-07-21 21:40 — MCU + display locked; final BOM

**MCU: STM32L031G6U6** (C96514, Extended, ~1.8k stock, $0.94). UFQFPN28 4×4.
0.6–0.8 µA in Stop with RTC-on-LSE and full RAM retention — the exact
architecture this product wants. 17 free GPIO vs 13 needed. Gotchas captured:
BOOT0 needs 10k pulldown, VDDA tie to VDD + 100n, NRST 100n, KiCad official
footprint = QFN-28_4x4mm_P0.5mm (no EP paste — matches ST UFQFPN28 practice).
CH32V003 formally disqualified (no LSE/RTC — LSI RC only, % drift).

**Display: XINGLIGHT XL-SA2401SRWC** (C49652871, Extended, 621 stock, $1.64).
0.2" 4-digit SMD, red 620 nm, **Vf 1.8 min** (runs from a coin cell), **common
cathode**, 28.5×10×3.0 mm, reflow 245 °C. Pin map read from datasheet p.4
(verified with my own eyes, incl. schematic diagram): bottom row L→R
1=E 2=D 3=DP 4=C 5=G 6=DIG4; top row R→L 7=B 8=DIG3 9=DIG2 10=F 11=A 12=DIG1.
Land pattern decoded from the mechanical drawing: **6 signal pads per row on
2.54 mm pitch (12.7 mm span, centered) + 2 mechanical anchor pads per row at
±11.43 mm** (22.86 dim); pads ~2.0 wide × 1.5 tall wrapping the edge; Ø1.5
mold-gate marks on the underside between rows → no vias under the body on the
front layer. Datasheet current guidance: dynamic average 4–5 mA, peak 100 mA.

**Drive design:** segments PA0–PA7 source through 330 Ω (C23138): ~2 mA/seg
at 3.0 V fresh cell, self-dimming as the cell sags (wristwatch behaviour, and
a free battery gauge). Digit commons sink on PB0/PB1/PA8/PA9 — worst-case
digit sink ~17 mA < 25 mA abs max, and firmware can phase segments if needed.
Battery: ~0.26 mAh/day at 10 views/day → **~2 years on a CR2032**, dominated
by display use, sleep floor ~1 µA.

**Firmware written and compiling** (2.9 KB, arm-none-eabi-gcc 16, freestanding,
register-level, no HAL): RTC on LSE seeded from build timestamp at first boot,
Stop-mode sleep, button EXTI wake, 125 Hz multiplex, hours → minutes switch at
<100 h, 0.0.0.0 at arrival. Local-time RTC is DST-safe (target inside BST).

**Final BOM (10 line items, 3 Extended):**
| Ref | Part | LCSC |
|---|---|---|
| U1 | STM32L031G6U6 QFN28 | C96514 (Ext) |
| DS1 | XL-SA2401SRWC 4-dig 7-seg red CC | C49652871 (Ext) |
| BT1 | MYOUNG BS-08-B2AA001 CR2032 SMD | C964777 (Ext) |
| Y1 | Epson Q13FC13500004 32.768k 12.5pF | C32346 (Basic) |
| SW1 | XKB TS-1187A-B-A-B | C318884 (Basic) |
| R1–R8 | 330 Ω 0603 | C23138 (Basic) |
| R9 | 10 kΩ 0603 (BOOT0 pull-down) | C25804 (Basic) |
| C1,C2,C3 | 100 nF 0603 | C14663 (Basic) |
| C4 | 1 µF 0603 | C15849 (Basic) |
| C5,C6 | 10 µF 0603 (display pulse bulk) | C19702 (Basic) |
| C7,C8 | 15 pF 0603 (LSE load) | C1644 (Basic) |
| J1 | Tag-Connect TC2030-IDC-NL | no part |

**Form factor:** ~42×22 mm rounded, 4-layer, double-sided **Standard** assembly
(Economic is single-sided-only; the battery holder needs the back). Front:
display + button + segment resistors + MCU + crystal. Back: CR2032 holder +
TC2030 + remaining passives. Keyring hole Ø4 NPTH in a corner tab. Black
soldermask + ENIG for the bare-board look (color choice = user's at order).

## 2026-07-21 22:20 — PCB placement + routing (the hard part)

Placement: iterated to **0 DRC violations pre-route** (courtyard collisions
found and fixed by moving parts: battery mouth orientation determined
*empirically* — pcbnew flip+rotation composition is non-obvious, so pad
positions were printed from the saved board rather than trusted from theory).

Routing war story (kept for honesty):
- Freerouting 2.2.4 headless routes the board in seconds, but **its
  "session completed / N unrouted" self-report is unreliable** — SES files
  came back with whole nets missing (deterministically the same ones per
  config) while claiming ~1 unrouted. Configs tried: all-signal layers,
  inner layers marked (type power), zones exported as planes, with/without
  my own power fanout vias. Every config left 3–12 airwires after import.
- Countermeasures now in the flow:
  1. In1=GND / In2=VDD planes poured **before** DSN export;
  2. power fanout vias placed programmatically for all spacious parts
     (collision-checked candidate search; via-in-pad for the battery tabs);
  3. border keepout strips (0.65 mm) + keyring-hole copper keepout ring so
     the autorouter can't put copper where the split ring or board edge is;
  4. **repair_router.py** — a deterministic grid A* (0.25 mm, F/B + vias,
     rasterized obstacle sets) that reads kicad-cli DRC JSON and routes
     whatever freerouting dropped, iterating until 0 unconnected;
  5. KiCad DRC (with --schematic-parity) is the only accepted truth.

## 2026-07-21 23:55 — Routing endgame: freerouting retired, custom A* router

After ~3 hours of freerouting 2.2.4 experiments (two-stage protected routing,
plane-typed layers, boundary insets, convergence loops — every configuration
either silently dropped nets from the SES, duplicated wiring on re-import, or
walled in the QFN power pins), the final architecture drops freerouting
entirely:

1. `gen_pcb.py` — placement (0 courtyard violations, all clearances
   hand-checked then DRC-checked), the two QFN corner power pins pre-fanned.
2. `fanout_post.py` — every GND/VDD pad gets a stub + via to the inner
   planes **on the empty board** (trivially legal spots; via-in-pad for the
   battery tabs; Dijkstra fallback threads congested pockets).
3. `finish_pcb.py` — In1=GND / In2=VDD planes poured; power is now fully
   connected before a single signal exists.
4. `repair_router.py` as the primary router: grid A* (0.1 mm, all 4 layers,
   through-vias, rasterized obstacle grids with exact-clearance "hard" zones
   near endpoints so QFN escapes stay legal), driven by KiCad DRC's
   unconnected list, iterating until clean. KiCad DRC JSON is the only
   accepted ground truth at every step.
5. Board grew 44×22 → 44×23 mm and the LSE crystal cluster moved next to
   PC14/PC15 after DRC caught parts under the battery holder body (the BS-08
   courtyard is now modeled as body + narrow (+) tab, which is what the part
   actually occupies).

The user asked for an autorouter rather than hand-routing: the A* router is
exactly that — deterministic, collision-checked, and verified by DRC; no
trace was drawn by hand.

- Decision: **no reverse-battery protection** (holder is keyed by mechanics,
  wristwatch practice, avoids Schottky Vf loss on a 2–3 V rail). B5819W (C8598)
  and AO3401A (C15127) noted as Basic-part fallbacks if a review disagrees.
- Full route cycle verified on dummy board: pcbnew build → save → Specctra DSN
  → Freerouting 2.2.4 headless → SES import back → tracks present. (Gotcha
  found: always SaveBoard with explicit path, not GetFileName().)
