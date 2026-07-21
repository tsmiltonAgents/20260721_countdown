#!/bin/zsh
# Full routing flow with convergence loop. Run from repo root.
set -e
KP=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
KC=/Applications/KiCadCLI/Contents/MacOS/kicad-cli
HW=hw/countdown

STAGE1_NETS="SEG_A,SEG_B,SEG_C,SEG_D,SEG_E,SEG_F,SEG_G,SEG_DP,DIG_1,DIG_2,DIG_3,DIG_4,BTN,BOOT0,NRST,SWDIO,SWCLK,LSE_IN,LSE_OUT"

echo "== generate board =="
$KP hw/scripts/gen_pcb.py 2>/dev/null | tail -3

echo "== stage 1: long nets =="
python3 hw/scripts/dsn_stage.py protect $HW/countdown.dsn $HW/countdown_p.dsn
python3 hw/scripts/dsn_stage.py stage1 $HW/countdown_p.dsn $HW/stage1a.dsn "$STAGE1_NETS,GND,VDD"
python3 hw/scripts/dsn_stage.py emptynets $HW/stage1a.dsn $HW/stage1.dsn "GND,VDD"
python3 hw/scripts/run_fr.py $HW/stage1.dsn $HW/stage1.ses 60 240
$KP hw/scripts/import_ses.py $HW/stage1.ses 2>/dev/null

for round in 1 2 3 4 5 6; do
  echo "== routing round $round =="
  $KP - 2>/dev/null <<'PYEOF'
import pcbnew
b = pcbnew.LoadBoard("hw/countdown/countdown.kicad_pcb")
pcbnew.ExportSpecctraDSN(b, "hw/countdown/round_raw.dsn")
PYEOF
  python3 hw/scripts/dsn_stage.py protect $HW/round_raw.dsn $HW/round_p.dsn
  python3 hw/scripts/dsn_stage.py emptynets $HW/round_p.dsn $HW/round.dsn "GND,VDD"
  python3 hw/scripts/run_fr.py $HW/round.dsn $HW/round.ses 60 240
  $KP hw/scripts/import_ses.py $HW/round.ses 2>/dev/null
  echo "-- fanout --"
  $KP hw/scripts/fanout_post.py 2>/dev/null
  echo "-- repair --"
  $KP -u hw/scripts/repair_router.py 2>/dev/null | tail -4
  $KC pcb drc --severity-error --format json -o $HW/drc_check.json $HW/countdown.kicad_pcb 2>/dev/null >/dev/null
  UNC=$(python3 -c "import json;d=json.load(open('$HW/drc_check.json'));print(len(d['unconnected_items'])+len(d['violations']))")
  echo "round $round: open issues = $UNC"
  if [ "$UNC" = "0" ]; then
    echo "CONVERGED"
    break
  fi
done

echo "== finish: planes, silk, refill =="
$KP hw/scripts/finish_pcb.py 2>/dev/null

echo "== final DRC =="
$KC pcb drc --severity-error --schematic-parity -o $HW/drc_final.rpt $HW/countdown.kicad_pcb 2>/dev/null
grep "Found" $HW/drc_final.rpt
