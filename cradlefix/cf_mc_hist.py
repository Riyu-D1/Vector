"""cradlefix/cf_mc_hist.py - 2200-pose MC histogram, same seed as
final2/f2_mc_hist.py (20261103), printing the wrist-family pairs with
up to 8 example poses each so the compound corners are visible.
Run: python3 cradlefix/cf_mc_hist.py   (CF_WRIST_DIR as in cf_probe.py)
"""
import math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
src = open(os.path.join(ROOT, "final2", "f2_collision.py")).read()
src = src.replace(
    'WR = os.path.join(ROOT, "wrist2", "out")',
    'WR = os.environ.get("CF_WRIST_DIR", os.path.join(ROOT, "wrist2", "out"))')
src = src.split("# home-pose declaration audit")[0]
g = {"__name__": "probe", "__file__": os.path.join(ROOT, "final2", "f2_collision.py")}
exec(compile(src, "f2_collision.py", "exec"), g)
posed, colliding, PAIRS_ALL, LIM, BODY = (g[k] for k in ("posed", "colliding", "PAIRS_ALL", "LIM", "BODY"))

WRIST = {"wrist4", "wrist5", "grip", "fore"}
rng = np.random.default_rng(20261103)
from collections import Counter
pair_ct, pose_ct = Counter(), 0
examples = {}
wrist_ct = Counter()
for it in range(2200):
    q = [rng.uniform(lo, hi) for lo, hi in LIM]
    gt = rng.uniform(0.0, 12.5)
    pm = posed(q, gt)
    hits, decl, gap = colliding(pm, PAIRS_ALL)
    if hits:
        pose_ct += 1
        for a, b, v in hits:
            pair_ct[(a, b)] += 1
            if {a, b} <= set() or False:
                pass
            if (a, b) not in examples:
                examples[(a, b)] = (it, np.round(np.degrees(q), 1).tolist(), round(gt, 1), round(v, 1))
            if BODY[a] in WRIST and BODY[b] in WRIST:
                wrist_ct[(a, b)] += 1

print("hit poses: %d / 2200  total pair-hits %d" % (pose_ct, sum(pair_ct.values())))
print("\n-- pair histogram (top 30) --")
for (a, b), c in pair_ct.most_common(30):
    ex = examples[(a, b)]
    print("%5d  %s x %s   e.g. pose %d q=%s gt=%.1f (%.1f mm3)" % (c, a, b, ex[0], ex[1], ex[2], ex[3]))
print("\n-- wrist-internal pairs (bodies fore/wrist4/wrist5/grip) --")
for (a, b), c in wrist_ct.most_common(30):
    ex = examples[(a, b)]
    print("%5d  %s x %s   e.g. pose %d q=%s gt=%.1f" % (c, a, b, ex[0], ex[1], ex[2]))
