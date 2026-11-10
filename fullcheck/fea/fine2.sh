#!/bin/bash
cd /Users/deepakdiwan/Vector-wt/refine/fullcheck/fea
for p in "$@"; do
  python3 -c "import sys; sys.path.insert(0,'.'); import run_fcfea; run_fcfea.one('$p',1.4,'${p}_g')" > "${p}_g.run.log" 2>&1
done
