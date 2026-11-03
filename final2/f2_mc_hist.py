"""final2/f2_mc_hist.py - MC section of f2_collision.py re-run for stats only.
Same seed + same pose stream as the main run -> identical hits, but prints a
pair histogram + hit-pose stats instead of the first-40 raw lines.
"""
import re, math, sys
import numpy as np

src = open("final2/f2_collision.py").read()
src = src.split("# home-pose declaration audit")[0]
g = {"__name__": "probe", "__file__": "/Users/deepakdiwan/Vector-wt/final2/final2/f2_collision.py"}
exec(compile(src, "f2_collision.py", "exec"), g)
posed, colliding, PAIRS_ALL, LIM, minz = (g[k] for k in
    ("posed", "colliding", "PAIRS_ALL", "LIM", "minz"))

rng = np.random.default_rng(20261103)
from collections import Counter
pair_ct, pose_ct = Counter(), 0
worst = []
for it in range(2200):
    q = [rng.uniform(lo, hi) for lo, hi in LIM]
    gt = rng.uniform(0.0, 12.5)
    pm = posed(q, gt)
    hits, decl, gap = colliding(pm, PAIRS_ALL)
    if hits:
        pose_ct += 1
        for a, b, v in hits:
            pair_ct[(a, b)] += 1
            worst.append((v, it, np.round(np.degrees(q), 0).tolist(), a, b))

print("hit poses: %d / 2200 (%.0f%%)  total pair-hits %d"
      % (pose_ct, 100.0 * pose_ct / 2200, sum(pair_ct.values())))
print("\n-- pair histogram (top 30) --")
for (a, b), c in pair_ct.most_common(30):
    print("%5d  %s x %s" % (c, a, b))
print("\n-- biggest volumes --")
for v, it, q, a, b in sorted(worst, reverse=True)[:15]:
    print("%8.0f mm3  pose %d q=%s  %s x %s" % (v, it, q, a, b))
# angle-conditioned stats: hits vs |J1| and wrist extremes
j1stop = sum(c for (a, b), c in pair_ct.items() if {a, b} == {"base_reinf", "yaw_limit"})
cradle = sum(c for (a, b), c in pair_ct.items() if {a, b} == {"w_j4_cradle", "w_link5"})
print("\nyaw-stop hits %d | cradle x link5 hits %d" % (j1stop, cradle))
