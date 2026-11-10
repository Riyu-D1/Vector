#!/bin/bash
cd /Users/deepakdiwan/Vector-wt/refine/fullcheck/fea
# convergence pass at cl=1.4 for the binding-margin parts (cl=1.0 OOMs:
# 8x element growth on 200k-node meshes). Waits for the heavy queue.
while pgrep -f "ccx -i|run_one.sh" > /dev/null; do sleep 30; done
printf '%s\n' dogleg_r dogleg_l fore_l2 fore_r2 | xargs -P 2 -n1 ./run_fine14.sh
