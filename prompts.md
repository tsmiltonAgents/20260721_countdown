# Prompts Log

All prompts given during this project, verbatim, with timestamps.

## 2026-07-21 21:01 — Initial brief (user)

> i want to have a small pcb on my keyring with a countdown to a specific date. this key ring should countdown to the date of 10th of october 2026 midday. it can have digitial electronics and a micro and be programmable, but i want it to me nice and small and simple, a simple 7 segment display, counting down in hours or minuts to this time. it should just keep running once going so needs a battery. i am ultimately going to order the board from JLC pCB and want the gerbers and pick and place and bOM. Make sure the parts come from there and can be pick and place assembled by them. i think it;ll be cool to be a bare board, but we might also want to pot it. if you need to do ANY mechanical design use this github repo https://github.com/earthtojake/text-to-cad. As you work maintain a prompts.md with all the prompts and a designlog.md with the design process and reviews etc. Then make this folder a github repo called 20260721_countdown and commit and push regularly, at least every time you do an interesting design. i want you to make sure the PCB really works, dont do routing yourself, use an autorouter, and make it a four layer board at least to make it easy for yourself. bear in mind it being small (e.g. maybe use a quickconnect jtag programmer thing or headers or something not a usb thing, then also make it wonderful for the user and pretty. keep going until you're done, and make sure you run verification loops to check (and look using your eyes) that this all really does work and then tell me to order it. i expect to wake up tomorrow to this working, but i'd prefer rigour and to wait longer than for you to fail completing it and me to waste my money on ordering PCBs that don't work

## Agent prompts (Claude → subagents / tools)

### 2026-07-21 21:15 — Four parallel research agents launched

1. **MCU research**: "Find the best microcontroller for an ultra-low-power coin-cell (CR2032, 2.0–3.0V) countdown keyring... runs 1.8–3.6V direct, RTC on external 32.768 kHz crystal, ~1 µA deep sleep keeping time, ≥13 GPIO + SWD, LQFP32/TSSOP20/QFN28-32, IN STOCK at JLCPCB parts library, Basic/Extended status... candidates STM32L031/G031/L011, PY32F002B, CH32V003 (verify it lacks LSE)... report LCSC C-numbers, stock, price, sleep current, gotchas (BOOT0, NRST, VDDA)."
2. **Display research**: "Find a 4-digit 7-segment LED display, as SMALL as practical (digit 0.2–0.4 inch, under ~42x15mm), JLC-assemblable, SMD preferred... RED (Vf ~1.8–2.0V) REQUIRED for 2.0–3.0V coin cell, disqualify blue/white/green... report full pin map, mechanical dims, LCSC number, stock, common anode/cathode... backups: 2-digit or smallest THT 4-digit."
3. **Support parts**: "CR2032 SMD holder, 32.768 kHz 3215 crystal (report CL and load caps), small SMD tactile switch, 0402/0603 Basic passives (100nF/1uF/10uF, 150–470R, 10k), optional Schottky + P-FET, Tag-Connect TC2030-NL footprint geometry + JLC-stocked 1.27mm SWD header alternative... LCSC numbers, Basic/Extended, stock."
4. **JLC fab/assembly rules**: "4-layer capabilities (track/space, via, stackup, colors), Economic vs Standard assembly (THT? both sides? fees), exact BOM/CPL file formats and column names, KiCad→JLC rotation corrections, gerber layer requirements, min board size for ~40x20mm board."

(Full verbatim agent prompts preserved in the session; condensed here for readability.)

### 2026-07-21 22:45 — JLC CPL rotation research agent

"Research JLCPCB pick-and-place rotation conventions... QFN-28 for STM32L031
(consensus of matthewlai/Bouni/KiBot databases vs Fabrication-Toolkit),
bottom-side formula from Fabrication-Toolkit process.py source, verify JLC
placement preview exists as pre-payment safety net." → Result: +270° for QFN,
bottom = (180 − rot + offset) mod 360, preview editable before payment.

### 2026-07-21 23:58 — Independent review agents (design frozen)

1. **Electrical review**: adversarial check of netlist vs STM32L031 UFQFPN28
   pinout, SWD/TC2030 pin order, display current budget vs GPIO ratings,
   CC multiplex logic vs firmware pin map, LSE loading, blank-chip first
   flash, EXTI vector, VDDA tie, RTC math. Findings ranked
   BLOCKER/MAJOR/MINOR/NIT with evidence.
2. **Firmware review**: RM0377-level check of RCC/PWR/RTC init order,
   LSEDRV-before-LSEON, shadow register staleness after Stop wake (RSF),
   EXTI config arithmetic, BSRR patterns vs SWD pins, vector table, linker,
   freestanding-libc pitfalls, calendar math transcription, DST/timezone
   seeding, Stop-mode leakage paths.
