#!/bin/zsh
# v10: single-stage freerouting (full network incl power), clean inset
# boundary, best-of-N attempts, then repair machinery + planes + gates.
set -e
KP=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
KC=/Applications/KiCadCLI/Contents/MacOS/kicad-cli
HW=hw/countdown

echo "== generate board =="
$KP hw/scripts/gen_pcb.py 2>/dev/null | tail -2
python3 hw/scripts/dsn_stage.py protect $HW/countdown.dsn $HW/full.dsn
cp $HW/countdown.kicad_pcb $HW/base.kicad_pcb

BEST=999
for try in 1 2 3 4 5 6; do
  echo "== FR attempt $try =="
  cp $HW/base.kicad_pcb $HW/countdown.kicad_pcb
  python3 hw/scripts/run_fr.py $HW/full.dsn $HW/full.ses 300 300 | tail -1
  $KP hw/scripts/import_ses.py $HW/full.ses 2>/dev/null | tail -1
  $KC pcb drc --severity-error --format json -o $HW/drc_try.json $HW/countdown.kicad_pcb 2>/dev/null >/dev/null
  N=$(python3 -c "import json;d=json.load(open('$HW/drc_try.json'));print(len(d['unconnected_items'])+len(d['violations']))")
  echo "attempt $try: issues = $N"
  if [ "$N" -lt "$BEST" ]; then
    BEST=$N
    cp $HW/countdown.kicad_pcb $HW/best.kicad_pcb
  fi
  if [ "$BEST" -le "1" ]; then break; fi
done
cp $HW/best.kicad_pcb $HW/countdown.kicad_pcb
echo "== best FR result: $BEST issues; repairing =="
$KP hw/scripts/finish_pcb.py 2>/dev/null >/dev/null
REPAIR_ITERS=15 $KP -u hw/scripts/repair_router.py 2>/dev/null | tail -3
$KP -u hw/scripts/finish_line.py 2>/dev/null | grep -vE "memory leak" | tail -5
$KP hw/scripts/finish_pcb.py 2>/dev/null >/dev/null
$KC pcb drc --severity-error --schematic-parity -o $HW/drc_final.rpt $HW/countdown.kicad_pcb 2>/dev/null
grep "Found" $HW/drc_final.rpt
$KP hw/scripts/board_gates.py 2>/dev/null | tail -2
