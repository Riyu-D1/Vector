#!/bin/bash
cd /Users/deepakdiwan/Vector-wt/refine/fullcheck/fea
python3 -c "import sys; sys.path.insert(0,'.'); import run_fcfea; run_fcfea.one('$1', 1.4, '$1_g')" > "$1_g.run.log" 2>&1
