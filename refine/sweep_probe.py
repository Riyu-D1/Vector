"""refine/sweep_probe.py - real J4xJ5 sweep clearance at the w_link5 front
relief cut + J6-roll clearance for a proposed w_grip_frame outer-face rib.

W frame: J4 axis = b line through the origin; J5 axis = h line through
(30.6,0); J6 axis = a line through (0,-17).  Chain order: J5 rotation (in
W frame) then J4 rotation (proximal).  w_grip_frame rolls about J6 with
the whole distal stack; statics = w_link5, w_link4, j5 case, j6 case.

Point-cloud distance - a lower bound on the true gap (sample ~0.4 mm, so
read ~-0.4 mm pessimistic).

Run: cradlefix/.venv/bin/python sweep_probe.py
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

TMP = os.path.join(HERE, "out", "_probe")
os.makedirs(TMP, exist_ok=True)


def mesh_of(s, name, tol=0.1):
    f = os.path.join(TMP, name + ".stl")
    export_stl(s, f, tolerance=tol, angular_tolerance=0.3)
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


def rot_x(pts, deg, c=(0.0, -17.0)):
    y0, z0 = c
    co, si = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    x, y, z = pts[:, 0], pts[:, 1] - y0, pts[:, 2] - z0
    return np.stack([x, co * y - si * z + y0, si * y + co * z + z0], axis=1)


def mind(trees, pts):
    dmin, dnm, dp = 1e9, None, None
    for nm, tr in trees.items():
        d, i = tr.query(pts)
        j = d.argmin()
        if d[j] < dmin:
            dmin, dnm, dp = d[j], nm, pts[j]
    return dmin, dnm, dp


def main():
    l5 = PW.w_link5()
    fixed = {"cradle": PW.w_j4_cradle(), "j4case": PW.servo_w("j4"),
             "fore_l": PB.rest(PB.fore2("L")), "fore_r": PB.rest(PB.fore2("R"))}
    l5m = mesh_of(l5, "l5")
    pts = l5m.sample(8000)
    tr = {nm: cKDTree(mesh_of(s, "fx_" + nm).sample(14000))
          for nm, s in fixed.items()}

    print("== J4xJ5 sweep: min gap of w_link5 vs fixed solids (mm) ==")
    print("%5s %5s" % ("q4", "q5"), " min_gap   vs     at")
    worst = (1e9, None, None, None, None)
    for q4 in range(-80, 81, 10):
        for q5 in range(-75, 76, 10):
            rp = rot_y(rot_z(pts, q5), q4)
            d, nm, p = mind(tr, rp)
            if d < worst[0]:
                worst = (d, q4, q5, nm, p)
            if d < 3.0:
                print("%5d %5d  %7.2f  %-7s (%.1f,%.1f,%.1f)"
                      % (q4, q5, d, nm, *p))
    d, q4, q5, nm, p = worst
    print("worst: %.2f mm at q4=%d q5=%d vs %s at (%.1f,%.1f,%.1f)"
          % (d, q4, q5, nm, *p))

    # relief-zone phantom points: swept gap if the cut were filled
    print("\n== phantom points in the relief zone (swept gap, J4xJ5) ==")
    ph = []
    for a in (23.6, 25.0, 26.6, 28.2):
        for b in (10.0, 11.0, 12.0, 14.0, 16.41):
            for h in (-2.15, -4.15, -6.15):
                for sg in (1, -1):
                    ph.append([a, sg * b, h])
    ph = np.array(ph)
    pw = 1e9; pp = None
    for q4 in range(-80, 81, 5):
        for q5 in range(-75, 76, 5):
            rp = rot_y(rot_z(ph, q5), q4)
            d, nm, p = mind(tr, rp)
            if d < pw:
                pw, pp, pq = d, p, (q4, q5)
    print("min phantom gap %.2f mm at %s pt (%.1f,%.1f,%.1f)" % (pw, pq, *pp))

    # per-point: which relief-zone coords are clearance-critical?
    print("\n== per-point min swept gap (original coords) ==")
    print("%6s %7s %7s %8s" % ("a", "b", "h", "gap_mm"))
    for i, p in enumerate(ph):
        dmin = 1e9
        for q4 in range(-80, 81, 5):
            for q5 in range(-75, 76, 5):
                rp = rot_y(rot_z(p.reshape(1, 3), q5), q4)
                d, nm, dp = mind(tr, rp)
                dmin = min(dmin, d)
        print("%6.1f %7.1f %7.2f %8.2f" % (p[0], p[1], p[2], dmin))

    # ---- gf roll check: candidate outer-face rib zone vs statics ----
    gf = PW.w_grip_frame()
    statics = {"l5": l5, "l4": PW.w_link4(), "j5case": PW.servo_w("j5"),
               "j6case": PW.servo_w("j6")}
    gfm = mesh_of(gf, "gf")
    tr2 = {nm: cKDTree(mesh_of(s, "st_" + nm).sample(14000))
           for nm, s in statics.items()}
    gp = gfm.sample(8000)
    print("\n== J6 roll: min gap w_grip_frame vs statics (mm) ==")
    w2 = (1e9, None, None, None)
    for q6 in range(-180, 181, 10):
        rp = rot_x(gp, q6)
        d, nm, p = mind(tr2, rp)
        if d < w2[0]:
            w2 = (d, q6, nm, p)
        if d < 2.0:
            print("  q6=%4d  %6.2f  %-7s (%.1f,%.1f,%.1f)" % (q6, d, nm, *p))
    print("worst: %.2f mm at q6=%d vs %s" % w2[:3])


if __name__ == "__main__":
    main()
