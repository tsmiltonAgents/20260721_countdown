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

- Decision: **no reverse-battery protection** (holder is keyed by mechanics,
  wristwatch practice, avoids Schottky Vf loss on a 2–3 V rail). B5819W (C8598)
  and AO3401A (C15127) noted as Basic-part fallbacks if a review disagrees.
- Full route cycle verified on dummy board: pcbnew build → save → Specctra DSN
  → Freerouting 2.2.4 headless → SES import back → tracks present. (Gotcha
  found: always SaveBoard with explicit path, not GetFileName().)
