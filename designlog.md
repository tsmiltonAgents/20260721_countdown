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
