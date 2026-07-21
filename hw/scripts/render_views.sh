#!/bin/zsh
# Render verification views: raytraced top/bottom/oblique + per-layer SVGs.
set -e
KC=/Applications/KiCadCLI/Contents/MacOS/kicad-cli
HW=hw/countdown
OUT=${1:-docs/renders}
mkdir -p $OUT
for side in top bottom; do
  $KC pcb render --side $side -w 2000 -h 1100 --quality high \
    -o $OUT/render_$side.png $HW/countdown.kicad_pcb 2>/dev/null >/dev/null
done
$KC pcb render --side top --rotate "-25,20,10" -w 2000 -h 1100 --quality high \
  -o $OUT/render_oblique.png $HW/countdown.kicad_pcb 2>/dev/null >/dev/null
$KC pcb export svg --layers F.Cu,Edge.Cuts -o $OUT/layer_fcu.svg $HW/countdown.kicad_pcb 2>/dev/null >/dev/null
$KC pcb export svg --layers In1.Cu,Edge.Cuts -o $OUT/layer_in1.svg $HW/countdown.kicad_pcb 2>/dev/null >/dev/null
$KC pcb export svg --layers In2.Cu,Edge.Cuts -o $OUT/layer_in2.svg $HW/countdown.kicad_pcb 2>/dev/null >/dev/null
$KC pcb export svg --layers B.Cu,Edge.Cuts -o $OUT/layer_bcu.svg $HW/countdown.kicad_pcb 2>/dev/null >/dev/null
echo "renders in $OUT"
