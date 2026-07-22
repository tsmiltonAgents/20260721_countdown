#!/bin/zsh
# Adaptive net-ordering: nets freerouting fails get first-mover priority on
# the next cycle. Converges because the priority list grows monotonically.
set -e
KP=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
KC=/Applications/KiCadCLI/Contents/MacOS/kicad-cli
HW=hw/countdown
PRIORITY=""

for cycle in 1 2 3 4 5 6 7 8; do
  echo "== cycle $cycle (priority: ${PRIORITY:-none}) =="
  $KP hw/scripts/gen_pcb.py 2>/dev/null >/dev/null
  if [ -n "$PRIORITY" ]; then
    python3 hw/scripts/dsn_stage.py protect $HW/countdown.dsn $HW/a_p.dsn >/dev/null
    python3 hw/scripts/dsn_stage.py stage1 $HW/a_p.dsn $HW/a.dsn "$PRIORITY" >/dev/null
    python3 hw/scripts/run_fr.py $HW/a.dsn $HW/a.ses 300 240 | grep -c completed
    $KP hw/scripts/import_ses.py $HW/a.ses 2>/dev/null | tail -1
    $KP - 2>/dev/null <<'PYEOF'
import pcbnew
b = pcbnew.LoadBoard("hw/countdown/countdown.kicad_pcb")
pcbnew.ExportSpecctraDSN(b, "hw/countdown/countdown.dsn")
PYEOF
  fi
  python3 hw/scripts/dsn_stage.py protect $HW/countdown.dsn $HW/full.dsn >/dev/null
  python3 hw/scripts/run_fr.py $HW/full.dsn $HW/full.ses 300 300 | grep -c completed
  $KP hw/scripts/import_ses.py $HW/full.ses 2>/dev/null | tail -1
  $KC pcb drc --severity-error --format json -o $HW/drc.json $HW/countdown.kicad_pcb 2>/dev/null >/dev/null
  LEFT=$(python3 - <<'PYEOF'
import json
d = json.load(open("hw/countdown/drc.json"))
nets = set()
for u in d["unconnected_items"]:
    for i in u["items"]:
        if "[" in i["description"]:
            nets.add(i["description"].split("[")[1].split("]")[0])
print(",".join(sorted(nets)))
PYEOF
)
  N=$(python3 -c "import json;d=json.load(open('$HW/drc.json'));print(len(d['unconnected_items']))")
  echo "cycle $cycle: unconnected=$N leftover nets: ${LEFT:-none}"
  if [ "$N" = "0" ]; then
    echo "ROUTING COMPLETE at cycle $cycle"
    break
  fi
  if [ -n "$PRIORITY" ]; then PRIORITY="$PRIORITY,$LEFT"; else PRIORITY="$LEFT"; fi
  PRIORITY=$(python3 -c "print(','.join(sorted(set('$PRIORITY'.split(',')))))")
done

echo "== post: edge fixes, planes, repair, gates =="
REPAIR_ITERS=10 $KP -u hw/scripts/repair_router.py 2>/dev/null | grep -vE "memory leak" | tail -4
$KP hw/scripts/finish_pcb.py 2>/dev/null >/dev/null
REPAIR_ITERS=10 $KP -u hw/scripts/repair_router.py 2>/dev/null | grep -vE "memory leak" | tail -4
$KP hw/scripts/finish_pcb.py 2>/dev/null >/dev/null
$KC pcb drc --severity-error --schematic-parity -o $HW/drc_final.rpt $HW/countdown.kicad_pcb 2>/dev/null
grep "Found" $HW/drc_final.rpt
$KP hw/scripts/board_gates.py 2>/dev/null | tail -2
