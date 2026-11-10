"""refine/checks/bake_loft.py - bake the w_link5 swept-envelope relief loft.

For each (a, |b|) column over the plate relief zone, march the plate band
h -2.15..-6.15 and record the deepest sampled h that the J4xJ5 swept
phantom (cradle + j4 case + fore plates, point-cloud, ~0.4 mm pessimistic)
approaches within 0.6 mm.  The kept lip = material below that depth.

The +-b tables are symmetrized (min keep) and embedded into ap7.py as
N.L5_LOFT.  Re-run after changing the cradle/fore geometry or the sweep
limits.  Output: refine/out/_probe/l5_loft.py literal + npy grids.

Run: cradlefix/.venv/bin/python checks/bake_loft.py
"""
import os, sys, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "cad", "arm2b"))

import trimesh
from scipy.spatial import cKDTree
from build123d import export_stl
import p_wrist7 as PW
import p_arm2b as PB

TMP = os.path.join(HERE, "..", "out", "_probe")
os.makedirs(TMP, exist_ok=True)
Q4 = range(-80, 81, 4)          # J4 sweep (ROM >= 160)
Q5 = range(-75, 76, 4)          # J5 sweep (ROM = 140)
GAP = 0.6                        # point-cloud clearance gate (mm)
AS = np.round(np.arange(23.6, 28.61, 0.4), 2)
BS = np.round(np.arange(9.5, 16.51, 0.3), 2)
HS = np.round(np.arange(-2.15, -6.16, -0.25), 2)


def mesh_of(s, name):
    f = os.path.join(TMP, name + ".stl")
    export_stl(s, f, tolerance=0.1, angular_tolerance=0.3)
    m = trimesh.load_mesh(f, force="mesh")
    m.merge_vertices()
    return m


def rot_y(pts, deg, c=(0.0, 0.0)):
    c0, z0 = c
    co, si = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    x, y, z = pts[:, 0] - c0, pts[:, 1], pts[:, 2] - z0
    return np.stack([co * x + si * z + c0, y, -si * x + co * z + z0], axis=1)


def rot_z(pts, deg, c=(30.6, 0.0)):
    x0, y0 = c
    co, si = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    x, y, z = pts[:, 0] - x0, pts[:, 1] - y0, pts[:, 2]
    return np.stack([co * x - si * y + x0, si * x + co * y + y0, z], axis=1)


def grid(bs_sgn):
    fixed = {"cradle": PW.w_j4_cradle(), "j4case": PW.servo_w("j4"),
             "fore_l": PB.rest(PB.fore2("L")), "fore_r": PB.rest(PB.fore2("R"))}
    tr = {nm: cKDTree(mesh_of(s, "fx_" + nm).sample(16000))
          for nm, s in fixed.items()}
    aa, bb, hh = np.meshgrid(AS, bs_sgn * BS, HS, indexing="ij")
    pts = np.stack([aa.ravel(), bb.ravel(), hh.ravel()], axis=1)
    gmin = np.full(len(pts), 1e9)
    for q4 in Q4:
        for q5 in Q5:
            rp = rot_y(rot_z(pts, q5), q4)
            d = np.full(len(pts), 1e9)
            for t in tr.values():
                d = np.minimum(d, t.query(rp)[0])
            gmin = np.minimum(gmin, d)
    return gmin.reshape(len(AS), len(BS), len(HS))


def keep_table(g):
    """per-column keep-top h: deepest bad level's next level down, or None
    (keep full plate) / 'X' (full cut)."""
    out = np.empty((len(AS), len(BS)), dtype=object)
    for i in range(len(AS)):
        for j in range(len(BS)):
            bad = np.where(g[i, j] < GAP)[0]
            if len(bad) == 0:
                out[i, j] = None
            elif bad.max() == len(HS) - 1:
                out[i, j] = "X"
            else:
                out[i, j] = round(HS[bad.max() + 1] + 0.02, 2)
    return out


def main():
    gp = grid(+1.0)
    gn = grid(-1.0)
    np.save(os.path.join(TMP, "loft_grid_pos.npy"), gp)
    np.save(os.path.join(TMP, "loft_grid_neg.npy"), gn)
    g = np.minimum(gp, gn)                     # symmetrize: deeper cut
    kt = keep_table(g)
    with open(os.path.join(TMP, "l5_loft.py"), "w") as f:
        f.write("# baked by checks/bake_loft.py - do not edit\n")
        f.write("LOFT_AS = %s\n" % (list(AS),))
        f.write("LOFT_BS = %s\n" % (list(BS),))
        rows = []
        for i in range(len(AS)):
            rows.append(tuple(None if kt[i, j] is None else
                              (kt[i, j] if kt[i, j] != "X" else -99.0)
                              for j in range(len(BS))))
        f.write("LOFT = %s\n" % (tuple(rows),))
    print("wrote %s" % os.path.join(TMP, "l5_loft.py"))


if __name__ == "__main__":
    main()
