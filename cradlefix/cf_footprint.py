"""cradlefix/cf_footprint.py - union of every J4xJ5-grid intersection,
mapped into each part's home frame -> the material zone that must move.

For the two pairs {w_j4_cradle, vendor_sts3250_j4} x w_link5 over the
full +-70/+-70 2.5 deg grid: at each hit pose the boolean intersection is
transformed into (a) w_link5 home coords and (b) the fixed part's frame
(= world = W frame).  Both are unioned and dumped as STL; the home-frame
bbox + per-axis extent of the union footprint is printed.

Run: python3 cradlefix/cf_footprint.py
"""
import math, os, sys, time
import numpy as np
import trimesh
import manifold3d as m3d

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
src = open(os.path.join(ROOT, "final2", "f2_collision.py")).read()
src = src.replace(
    'WR = os.path.join(ROOT, "wrist2", "out")',
    'WR = os.environ.get("CF_WRIST_DIR", os.path.join(ROOT, "wrist2", "out"))')
src = src.split("# home-pose declaration audit")[0]
g = {"__name__": "probe", "__file__": os.path.join(ROOT, "final2", "f2_collision.py")}
exec(compile(src, "f2_collision.py", "exec"), g)
M, BODY, BIDX, LIM, body_mats = g["M"], g["BODY"], g["BIDX"], g["LIM"], g["body_mats"]

WJ = np.array([96.4, 0.0, 216.2])
UP = ["w_j4_cradle", "vendor_sts3250_j4"]
DN = "w_link5"
STEP = math.radians(2.5)
t0 = time.time()
fix = {n: M[n] for n in UP}
foot_dn, foot_up = {}, {n: None for n in UP}
hitcount = {n: 0 for n in UP}
inv5 = None
for q4 in np.arange(LIM[3][0], LIM[3][1] + 1e-9, STEP):
    for q5 in np.arange(LIM[4][0], LIM[4][1] + 1e-9, STEP):
        q = [0, 0, 0, q4, q5, 0]
        mats = body_mats(q)
        m5 = M[DN].transform(np.asarray(mats[5][:3, :], np.float64))
        b5 = m5.bounding_box()
        for n in UP:
            bu = fix[n].bounding_box()
            if (b5[0] > bu[3] or bu[0] > b5[3] or b5[1] > bu[4] or bu[1] > b5[4]
                    or b5[2] > bu[5] or bu[2] > b5[5]):
                continue
            inter = m5 ^ fix[n]
            if inter.volume() <= 0.5:
                continue
            hitcount[n] += 1
            # into link5 home frame
            i5 = inter.transform(np.asarray(np.linalg.inv(mats[5])[:3, :], np.float64))
            foot_dn[n] = i5 if foot_dn.get(n) is None else foot_dn[n] + i5
            foot_up[n] = inter if foot_up[n] is None else foot_up[n] + inter
print("%.0f s" % (time.time() - t0))
os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
for n in UP:
    print("%s x %s: %d hit poses" % (n, DN, hitcount[n]))
    if foot_dn.get(n) is not None:
        tm = trimesh.Trimesh(np.asarray(foot_dn[n].to_mesh().vert_properties)[:, :3],
                             np.asarray(foot_dn[n].to_mesh().tri_verts))
        p = os.path.join(HERE, "out", "fp_%s_on_link5.stl" % n)
        tm.export(p)
        b = tm.bounds
        print("   footprint on link5 home, W coords: a %.1f..%.1f  b %.1f..%.1f  h %.1f..%.1f"
              % (b[0][0] - WJ[0], b[1][0] - WJ[0], b[0][1], b[1][1],
                 b[0][2] - WJ[2], b[1][2] - WJ[2]))
        tm2 = trimesh.Trimesh(np.asarray(foot_up[n].to_mesh().vert_properties)[:, :3],
                              np.asarray(foot_up[n].to_mesh().tri_verts))
        p2 = os.path.join(HERE, "out", "fp_%s_on_%s.stl" % (DN, n))
        tm2.export(p2)
        b2 = tm2.bounds
        print("   footprint on %s (world/W): a %.1f..%.1f  b %.1f..%.1f  h %.1f..%.1f"
              % (n, b2[0][0] - WJ[0], b2[1][0] - WJ[0], b2[0][1], b2[1][1],
                 b2[0][2] - WJ[2], b2[1][2] - WJ[2]))
