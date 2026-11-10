#!/bin/bash
cd /Users/deepakdiwan/Vector-wt/refine/fullcheck/fea
python3 -c "import sys; sys.path.insert(0,'.'); import run_fcfea; run_fcfea.one('$1', 1.0, '$1_f')" > "$1_f.run.log" 2>&1
