#!/bin/zsh
# Freerouting-free flow: fanout power on empty board, planes, A*-route all
# signals via the repair router, refill, DRC.
set -e
KP=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
KC=/Applications/KiCadCLI/Contents/MacOS/kicad-cli
HW=hw/countdown

echo "== generate board =="
$KP hw/scripts/gen_pcb.py 2>/dev/null | tail -2
echo "== power fanout (empty board) =="
$KP hw/scripts/fanout_post.py 2>/dev/null
echo "== planes + silk =="
$KP hw/scripts/finish_pcb.py 2>/dev/null
echo "== A* route all signals =="
REPAIR_ITERS=40 $KP -u hw/scripts/repair_router.py 2>/dev/null | grep -vE "stitched|routed" | tail -6
echo "== refill + final DRC =="
$KP hw/scripts/finish_pcb.py 2>/dev/null
$KC pcb drc --severity-error --schematic-parity -o $HW/drc_final.rpt $HW/countdown.kicad_pcb 2>/dev/null
grep "Found" $HW/drc_final.rpt
