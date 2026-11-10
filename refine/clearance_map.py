"""refine/clearance_map.py - (a,b) clearance-margin map in the w_link5
relief band, to bound how far a smooth inner-edge taper can extend.

For each phantom point (a,|b|,h) in the relief zone, the minimum swept
gap over the J4xJ5 envelope.  ~-0.4 mm pessimistic (point sampling).
"""
import os, sys, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "cad", "arm2b"))
sys.path.insert(0, os.path.join(HERE, "..", "cad", "arm2"))

import trimesh
from scipy.spatial import cKDTree
from build123d import export_stl
import p_wrist7 as PW
import p_arm2b as PB
from sweep_probe import mesh_of, rot_y, rot_z, TMP


def mind(trees, pts):
    dmin, dnm, dp = 1e9, None, None
    for nm, tr in trees.items():
        d, i = tr.query(pts)
        j = d.argmin()
        if d[j] < dmin:
            dmin, dnm, dp = d[j], nm, pts[j]
    return dmin, dnm, dp


def main():
    fixed = {"cradle": PW.w_j4_cradle(), "j4case": PW.servo_w("j4"),
             "fore_l": PB.rest(PB.fore2("L")), "fore_r": PB.rest(PB.fore2("R"))}
    tr = {nm: cKDTree(mesh_of(s, "cm_" + nm).sample(14000))
          for nm, s in fixed.items()}

    # grid: a in 24..38 step 1, |b| in 10..16.5 step 0.5, h mid-plate -4.15
    pts = []
    for a in np.arange(24.0, 38.01, 1.0):
        for b in np.arange(10.0, 16.51, 0.5):
            pts.append([a, b, -4.15])
    pts = np.array(pts)
    res = np.full(len(pts), 1e9)
    for q4 in range(-80, 81, 4):
        for q5 in range(-75, 76, 4):
            rp = rot_y(rot_z(pts, q5), q4)
            for nm, trr in tr.items():
                d, i = trr.query(rp)
                res = np.minimum(res, d)
    print("   a \\ b " + " ".join("%5.1f" % b
                                for b in np.arange(10.0, 16.51, 0.5)))
    for ai, a in enumerate(np.arange(24.0, 38.01, 1.0)):
        row = res[ai * 14:(ai + 1) * 14]
        print("%6.1f " % a + " ".join("%5.2f" % v for v in row))


if __name__ == "__main__":
    main()
