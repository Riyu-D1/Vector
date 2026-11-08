"""refine/relief_depth.py - 3D intrusion-depth map for the w_link5 front
b-corner relief: for each (a,|b|) column in the plate corner band, find the
deepest h at which the J4xJ5-swept fixed solids still graze.  Tells whether
the relief can be partial-height (bottom flange kept) instead of cutting
the full plate thickness.

Method as sweep_probe.py: phantom grid points attached to w_link5, swept
through the q4 x q5 grid, point-cloud min distance to the fixed solids
(~0.4 mm sample pessimism).  For each (a,b) column report, for every
sampled h, the min swept gap.

Run: cradlefix/.venv/bin/python relief_depth.py
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "cad", "arm2b"))
sys.path.insert(0, os.path.join(HERE, "..", "cad", "arm2"))

from scipy.spatial import cKDTree
import p_wrist7 as PW
import p_arm2b as PB
from sweep_probe import mesh_of, rot_y, rot_z, mind

HS = (-2.2, -3.0, -4.0, -4.5, -5.0, -5.5, -6.15)
AS = tuple(np.arange(23.0, 38.6, 1.0))
BS = (10.0, 11.0, 12.0, 12.8, 13.5, 14.5, 15.5, 16.41)


def main():
    fixed = {"cradle": PW.w_j4_cradle(), "j4case": PW.servo_w("j4"),
             "fore_l": PB.rest(PB.fore2("L")), "fore_r": PB.rest(PB.fore2("R"))}
    tr = {nm: cKDTree(mesh_of(s, "fx_" + nm).sample(14000))
          for nm, s in fixed.items()}

    ph = []
    for a in AS:
        for b in BS:
            for h in HS:
                ph.append([a, b, h])
    ph = np.array(ph)

    gmin = np.full(len(ph), 1e9)
    gpose = np.zeros((len(ph), 2), dtype=int)
    for q4 in range(-80, 81, 5):
        for q5 in range(-75, 76, 5):
            rp = rot_y(rot_z(ph, q5), q4)
            for tr_ in tr.values():
                d, _ = tr_.query(rp)
                upd = d < gmin
                gmin[upd] = d[upd]
                gpose[upd] = (q4, q5)

    print("min swept gap (mm) by column; rows = a, cols = |b|")
    print("   deepest grazed h per column = first h (top->down) with gap < 1.0")
    hdr = "      " + "".join("%8.1f" % b for b in BS)
    for h_i, h in enumerate(HS):
        print("\n-- h = %.2f --" % h)
        print(hdr)
        for ai, a in enumerate(AS):
            row = ""
            for bi, b in enumerate(BS):
                i = ph.tolist().index([a, b, h]) if False else \
                    (ai * len(BS) + bi) * len(HS) + h_i
                row += "%8.2f" % gmin[i]
            print("%6.1f%s" % (a, row))

    print("\n== deepest h with gap < 1.0 mm, per (a, b) column ==")
    print("      " + "".join("%8.1f" % b for b in BS))
    for ai, a in enumerate(AS):
        row = ""
        for bi, b in enumerate(BS):
            deepest = None
            for h_i, h in enumerate(HS):
                i = (ai * len(BS) + bi) * len(HS) + h_i
                if gmin[i] < 1.0:
                    deepest = h
            row += "%8s" % ("clean" if deepest is None else "%.2f" % deepest)
        print("%6.1f%s" % (a, row))


if __name__ == "__main__":
    main()
