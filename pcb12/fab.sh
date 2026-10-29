#!/bin/bash
# Fab pipeline: DRC + gerber/drill export for soma-carrier-v12.kicad_pcb
set -e
KCLI="/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
PCB=/Users/deepakdiwan/Vector-wt/pcb12/pcb12/soma-carrier-v12.kicad_pcb
OUT=/Users/deepakdiwan/Vector-wt/pcb12/pcb12/gerbers
cd /Users/deepakdiwan/Vector-wt/pcb12/pcb12

echo "=== Fill zones (bakes GND pour into file) ==="
/Users/deepakdiwan/soma/.venv/bin/python3 fill_zones.py "$PCB"

echo "=== DRC ==="
"$KCLI" pcb drc --format report --output drc_report.txt \
    --severity-all "$PCB" || true
grep -c 'violations' drc_report.txt || true
grep 'violations\|unconnected' drc_report.txt | head -10 || true

echo "=== Gerbers ==="
mkdir -p "$OUT"
"$KCLI" pcb export gerbers -l F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts,F.Fab,B.Fab,F.Courtyard,B.Courtyard,F.Paste,B.Paste,F.Adhesive,B.Adhesive,Margin \
    --check-zones --output "$OUT/" "$PCB"
"$KCLI" pcb export drill --format excellon --output "$OUT/" "$PCB"
ls -la "$OUT"
echo "=== done ==="
