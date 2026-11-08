"""refine/fea/sigscan_r3.py - max layer-normal tension scan.

analyze_r3.py only reports sig_n at the top-5 von-Mises nodes; a larger
sigma_n can hide at a lower-VM node.  This scanner reports, over ALL
filtered (non patch-adjacent) nodes:
  - max tensile sigma_n(axis) with location
  - max compressive sigma_n(axis)
  - max in-layer VM for the same axis convention
  - max shear with one index on the layer axis (interlayer shear)

Run:  python3 sigscan_r3.py <part>.frd <part>.inp <axis(x|y|z)>
"""
import math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)),
                                "cad3", "fea"))
from frd2vtu import read_frd, vonmises  # noqa
from analyze_r3 import read_nsets, layer_split, AX  # noqa


def main(frd, inp, laxis):
    nodes, elems, steps = read_frd(frd)
    ns = read_nsets(inp)
    nfix = ns.get("NFIX", set())
    nload = set()
    for k, v in ns.items():
        if k.startswith("NLOAD"):
            nload |= v
    constrained = nfix | nload
    tainted = set(constrained)
    for e in elems:
        if any(n in constrained for n in e):
            tainted.update(e)
    a = AX[laxis]
    # R7 fix: s6 = (sxx,syy,szz,sxy,syz,sxz); the true through-layer
    # shear pair for layer-normal a are the two components that include
    # index a: x->{sxy(3),sxz(5)} y->{sxy(3),syz(4)} z->{syz(4),sxz(5)}.
    # The old formula s6[3+((a+1)%3)]/s6[3+((a+2)%3)] paired sxy+syz for
    # every axis - an in-layer+interlayer mix that mis-stated the mode.
    TAU_IDX = {0: (3, 5), 1: (3, 4), 2: (4, 5)}
    ta, tb = TAU_IDX[a]
    byname = {}
    for i, s in enumerate(steps):
        byname.setdefault(s["name"], []).append(s["data"])
    for si, disp in enumerate(byname.get("DISP", [])):
        stress = byname["STRESS"][si]
        rows = []
        for n, s in stress.items():
            if n in tainted:
                continue
            s6 = s[:6]
            sn, vi = layer_split(s6, laxis)
            tsh = math.sqrt(s6[ta] ** 2 + s6[tb] ** 2)
            rows.append((sn, vi, tsh, vonmises(s6), n))
        st = max(rows, key=lambda r: r[0])
        sc = min(rows, key=lambda r: r[0])
        sv = max(rows, key=lambda r: r[1])
        ss = max(rows, key=lambda r: r[2])
        print("%s axis=%s step%d: filtered nodes %d"
              % (os.path.basename(frd), laxis, si + 1, len(rows)))
        for tag, r in (("tensile sig_n", st), ("compress sig_n", sc),
                       ("in-layer VM ", sv), ("interlayer tau", ss)):
            print("   %s %+.2f / %.2f / %.2f MPa @n%d %s"
                  % (tag, r[0], r[1], r[2], r[4],
                     tuple(round(c, 1) for c in nodes[r[4]])))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
