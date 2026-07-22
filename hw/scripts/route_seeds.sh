#!/bin/zsh
# Perturb don't-care passives by 0.1mm steps to reseed freerouting until a
# round closes with 0 unconnected + 0 violations.
KP=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
KC=/Applications/KiCadCLI/Contents/MacOS/kicad-cli
HW=hw/countdown
GP=hw/scripts/gen_pcb.py
cp $GP $GP.orig
for seed in $(seq 0 ${MAX_SEEDS:-30}); do
  python3 - "$seed" <<'PYEOF'
import re, sys
seed = int(sys.argv[1])
src = open("hw/scripts/gen_pcb.py.orig").read()
# deterministic pseudo-random nudges per seed for open-space passives
import hashlib
def nudge(ref, xy):
    h = hashlib.md5(f"{seed}:{ref}".encode()).digest()
    dx = ((h[0] % 7) - 3) * 0.1
    dy = ((h[1] % 7) - 3) * 0.1
    return round(xy[0] + dx, 1), round(xy[1] + dy, 1)
subs = {
    "C4": (8.0, 1.6), "C5": (4.6, 2.0), "C6": (4.6, 21.0), "R9": (2.6, 7.0),
    "C3": (34.6, 18.6), "C2": (35.4, 9.8),
}
out = src
for ref, xy in subs.items():
    if seed == 0:
        break
    nx, ny = nudge(ref, xy)
    out = re.sub(rf'"{ref}":  \([0-9.]+, [0-9.]+,', f'"{ref}":  ({nx}, {ny},', out)
open("hw/scripts/gen_pcb.py", "w").write(out)
PYEOF
  $KP hw/scripts/gen_pcb.py 2>/dev/null >/dev/null || continue
  $KC pcb drc --severity-error --format json -o $HW/drc.json $HW/countdown.kicad_pcb 2>/dev/null >/dev/null
  PV=$(python3 -c "import json;print(len(json.load(open('$HW/drc.json'))['violations']))")
  if [ "$PV" != "0" ]; then echo "seed $seed: placement violations $PV, skip"; continue; fi
  python3 hw/scripts/dsn_stage.py protect $HW/countdown.dsn $HW/full.dsn >/dev/null
  python3 hw/scripts/run_fr.py $HW/full.dsn $HW/full.ses 300 240 >/dev/null
  $KP hw/scripts/import_ses.py $HW/full.ses 2>/dev/null >/dev/null
  $KC pcb drc --severity-error --format json -o $HW/drc.json $HW/countdown.kicad_pcb 2>/dev/null >/dev/null
  N=$(python3 -c "import json;d=json.load(open('$HW/drc.json'));print(len(d['unconnected_items'])+len(d['violations']))")
  echo "seed $seed: issues = $N"
  if [ "$N" = "0" ]; then
    echo "PERFECT at seed $seed"
    cp hw/scripts/gen_pcb.py hw/scripts/gen_pcb_winning.py
    exit 0
  fi
done
cp $GP.orig $GP
echo "no perfect seed found"
exit 1
