#!/bin/zsh
# Final composed flow: FR routes signals (2 stages, power emptied),
# fanout_post connects power to planes, A* repairs stragglers.
set -e
KP=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
KC=/Applications/KiCadCLI/Contents/MacOS/kicad-cli
HW=hw/countdown

STAGE1_NETS="SEG_A,SEG_B,SEG_C,SEG_D,SEG_E,SEG_F,SEG_G,SEG_DP,DIG_1,DIG_2,DIG_3,DIG_4,BTN,BOOT0,NRST,SWDIO,SWCLK,LSE_IN,LSE_OUT"

echo "== generate board =="
$KP hw/scripts/gen_pcb.py 2>/dev/null | tail -2

echo "== power fanout (empty board) =="
$KP hw/scripts/fanout_post.py 2>/dev/null
$KP - 2>/dev/null <<'PYEOF'
import pcbnew
b = pcbnew.LoadBoard("hw/countdown/countdown.kicad_pcb")
pcbnew.ExportSpecctraDSN(b, "hw/countdown/countdown.dsn")
PYEOF

echo "== stage 1: long signal nets =="
python3 hw/scripts/dsn_stage.py protect $HW/countdown.dsn $HW/countdown_p.dsn
python3 hw/scripts/dsn_stage.py stage1 $HW/countdown_p.dsn $HW/stage1a.dsn "$STAGE1_NETS,GND,VDD"
python3 hw/scripts/dsn_stage.py emptynets $HW/stage1a.dsn $HW/stage1.dsn "GND,VDD"
python3 hw/scripts/run_fr.py $HW/stage1.dsn $HW/stage1.ses 200 240
$KP hw/scripts/import_ses.py $HW/stage1.ses 2>/dev/null
$KP hw/scripts/restore_power.py 2>/dev/null

echo "== stage 2: remaining signals =="
$KP - 2>/dev/null <<'PYEOF'
import pcbnew
b = pcbnew.LoadBoard("hw/countdown/countdown.kicad_pcb")
pcbnew.ExportSpecctraDSN(b, "hw/countdown/stage2_raw.dsn")
PYEOF
python3 hw/scripts/dsn_stage.py protect $HW/stage2_raw.dsn $HW/stage2p.dsn
python3 hw/scripts/dsn_stage.py emptynets $HW/stage2p.dsn $HW/stage2.dsn "GND,VDD"
python3 hw/scripts/run_fr.py $HW/stage2.dsn $HW/stage2.ses 200 240
$KP hw/scripts/import_ses.py $HW/stage2.ses 2>/dev/null
$KP hw/scripts/restore_power.py 2>/dev/null

echo "== planes + silk (before repair so DRC sees power connected) =="
$KP hw/scripts/finish_pcb.py 2>/dev/null

echo "== A* repair =="
REPAIR_ITERS=20 $KP -u hw/scripts/repair_router.py 2>/dev/null

echo "== refill + final DRC =="
$KP hw/scripts/finish_pcb.py 2>/dev/null
$KC pcb drc --severity-error --schematic-parity -o $HW/drc_final.rpt $HW/countdown.kicad_pcb 2>/dev/null
grep "Found" $HW/drc_final.rpt
