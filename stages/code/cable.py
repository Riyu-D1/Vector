"""cad/knuckle/cable.py - hidden-cable route check. Copied verbatim.
Usage (from cad/knuckle):  python cable.py
Walks the waypoint polylines below (G frame, home pose) in 0.5 mm steps
and tests every sample against every solid in out/*.stl with
trimesh.contains.  A sample inside any solid = blocked route.
Prints one line per route, then CABLE PASS or CABLE FAIL."""
import glob
import os
import sys

import numpy as np
import trimesh

from frames import arc_pts, arc_pts_yz
from gate import solid_meshes

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")

ROUTES = {
    # base lid -> drum -> J1 service loop -> turret -> J2 cavity -> tunnel
    "A_base_to_J2face": [
        (-16.93, 67.92, 3.5), (-13.31, 53.37, 5.0), (-10.16, 40.75, 6.0),
        (-8.95, 35.90, 12.0), (-8.95, 35.90, 22.0), (-8.95, 35.90, 40.0),
        (-7.98, 32.02, 58.5), (-6.53, 26.20, 58.5), (-4.35, 17.47, 60.0),
        (0.0, 5.5, 100.0), (0.0, 26.0, 112.0), (0.0, 26.0, 124.0),
        (0.0, 27.0, 128.0), (-22.0, 26.0, 150.0), (-30.0, 26.0, 150.0),
        (-32.0, 24.0, 150.0), (-32.0, -24.6, 150.0)],
    # J2 groove (over the top) -> upper arm -> J3 cavity -> J3 notch
    "B_upperarm": arc_pts((0.0, 150.0), 32.0, -27.0, 180.0, 0.0) + [
        (32.0, -31.0, 150.0), (32.0, -36.0, 150.0), (100.0, -68.0, 150.0),
        (150.0, -68.0, 150.0), (118.0, -68.0, 150.0), (120.0, -40.0, 150.0),
        (120.0, -26.0, 150.0), (120.0, -24.6, 150.0)],
    # forearm groove (over the top) -> forearm -> pass -> J4 plug zone
    "C_forearm_in": [(121.0, -22.2, 150.0)] + arc_pts((150.0, 150.0), 29.0,
        -22.2, 180.0, 0.0) + [
        (179.0, -18.0, 150.0), (179.0, -10.0, 150.0), (220.0, 0.0, 150.0),
        (238.0, 19.3, 136.75), (256.0, 19.3, 136.0), (263.0, -10.0, 135.5),
        (263.0, -20.0, 136.0), (263.0, -22.0, 150.0)],
    # J4 plug zone -> pass -> channel -> side hole -> cup groove -> P1/P2 -> J5 plug
    "D_wrist": [(263.0, -20.0, 136.0), (263.0, -10.0, 135.5),
        (256.0, 19.3, 136.0), (280.0, 19.3, 135.0), (280.0, 25.0, 134.5),
        (280.0, 30.2, 133.0)] + arc_pts((280.0, 150.0), 18.75, 32.6, -90.0,
        0.0) + [
        (300.0, 34.6, 150.0), (326.0, 34.6, 150.0), (326.0, 15.0, 150.0),
        (326.0, 14.5, 136.0), (326.0, 10.0, 133.5)],
    # J5 plug -> pod channel -> pod front hole -> gripper groove -> slot -> J6 plug
    "E_gripper": [(326.0, 10.0, 133.5), (326.0, 14.5, 136.0),
        (350.0, 14.5, 150.0), (367.5, 14.5, 150.0)] + arc_pts_yz(
        369.8, 14.5, 0.0, 197.8) + [
        (372.0, -14.0, 145.5), (375.0, -15.0, 145.5), (375.0, -22.0, 145.5),
        (390.0, -24.0, 145.5)],
}


def samples(pts, step=0.5):
    out = []
    for a, b in zip(pts[:-1], pts[1:]):
        a, b = np.array(a, float), np.array(b, float)
        n = max(1, int(np.linalg.norm(b - a) / step))
        out += [a + (b - a) * i / n for i in range(n + 1)]
    return np.array(out)


def main():
    solids = {os.path.basename(p)[:-4]: trimesh.load_mesh(p, force="mesh")
              for p in sorted(glob.glob(os.path.join(OUT, "*.stl")))}
    if not solids:
        print("no STL in out/ - run build.py first")
        return 1
    ok = True
    for name, pts in ROUTES.items():
        s = samples(pts)
        hits = []
        for sn, m in solids.items():
            inside = np.zeros(len(s), bool)
            for piece in solid_meshes(m):
                lo, hi = piece.bounds
                cand = np.all((s >= lo) & (s <= hi), axis=1)
                if cand.any():
                    inside[cand] |= piece.contains(s[cand])
            if inside.any():
                i = int(np.argmax(inside))
                hits.append(f"{sn}@({s[i][0]:.1f},{s[i][1]:.1f},{s[i][2]:.1f})"
                            f" x{int(inside.sum())}")
        ok &= not hits
        print(f"{name}: samples={len(s)} " + ("CLEAR" if not hits else
              "BLOCKED " + "; ".join(hits)))
    print("CABLE PASS" if ok else "CABLE FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
