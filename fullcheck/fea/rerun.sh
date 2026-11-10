#!/bin/bash
cd /Users/deepakdiwan/Vector-wt/refine/fullcheck/fea
# wait for the first batch to drain (no run_fcfea processes left)
while pgrep -f "run_fcfea.py" > /dev/null; do sleep 30; done
xargs -P 4 -n1 ./run_one.sh < parts_rerun.txt
