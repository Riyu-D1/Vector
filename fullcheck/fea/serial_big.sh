#!/bin/bash
cd /Users/deepakdiwan/Vector-wt/refine/fullcheck/fea
rm -f base_link.frd link1_g.frd base_plate.frd
bash run_one.sh base_link
python3 -c "import sys; sys.path.insert(0,'.'); import run_fcfea; run_fcfea.one('link1',1.4,'link1_g')" >> link1_g.run.log 2>&1
bash run_one.sh base_plate
echo ALLDONE
