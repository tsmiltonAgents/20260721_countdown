#!/bin/zsh
# Run the whole routing flow repeatedly until DRC is perfectly clean.
KP=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
KC=/Applications/KiCadCLI/Contents/MacOS/kicad-cli
HW=hw/countdown
for round in $(seq 1 ${MAX_ROUNDS:-12}); do
  echo "######## ROUND $round ########"
  ./hw/scripts/route_all.sh 2>&1 | grep -E "Found" | head -3
  $KP -u hw/scripts/finish_line.py 2>/dev/null | grep -vE "memory leak" | head -8
  $KP hw/scripts/finish_pcb.py 2>/dev/null >/dev/null
  $KC pcb drc --severity-error --schematic-parity --format json -o $HW/drc_check.json $HW/countdown.kicad_pcb 2>/dev/null >/dev/null
  N=$(python3 -c "import json;d=json.load(open('$HW/drc_check.json'));print(len(d['unconnected_items'])+len(d['violations']))")
  $KP hw/scripts/board_gates.py 2>/dev/null | tail -3
  G=$($KP hw/scripts/board_gates.py 2>/dev/null | grep -c "^GATE:")
  N=$((N + G))
  echo "ROUND $round result: open issues = $N"
  if [ "$N" = "0" ]; then
    echo "PERFECT BOARD"
    exit 0
  fi
done
echo "no clean round in $MAX_ROUNDS attempts"
exit 1
