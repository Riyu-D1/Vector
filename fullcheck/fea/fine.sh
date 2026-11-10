#!/bin/bash
cd /Users/deepakdiwan/Vector-wt/refine/fullcheck/fea
# wait for ALL run_fcfea + rerun queue to drain
while pgrep -f "run_fcfea.py|rerun.sh" > /dev/null; do sleep 30; done
printf '%s\n' dogleg_r dogleg_l fore_l2 fore_r2 upper_out upper_back front_spacer_j2 | xargs -P 4 -n1 ./run_fine.sh
