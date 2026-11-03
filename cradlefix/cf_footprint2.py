"""cradlefix/cf_footprint2.py - same swept-intersection footprint as
cf_footprint.py but for the J5xJ6 family (grip body vs wrist4):
  {w_grip_frame, vendor_sts3215_g, plug_g} x {w_link4, vendor_sts3215_j5}
over J5xJ6 at 2.5 deg (J4=0 - J4-invariant pairs).
Footprints mapped into each part's home frame; STL dumps in cradlefix/out.
Run: python3 cradlefix/cf_footprint2.py
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
M, BODY, BIDX, LIM, body_mats, DECLARED = (g[k] for k in
    ("M", "BODY", "BIDX", "LIM", "body_mats", "DECLARED"))

WJ = np.array([96.4, 0.0, 216.2])
UP = ["w_link4", "vendor_sts3215_j5"]          # wrist4 body (fixed at J4=0)
DN = ["w_grip_frame", "vendor_sts3215_g", "plug_g"]   # grip body
STEP = math.radians(2.5)
t0 = time.time()
fix = {n: M[n] for n in UP}
fb = {n: fix[n].bounding_box() for n in UP}
foot_up = {}
foot_dn = {}
hitcount = {}
for q5 in np.arange(LIM[4][0], LIM[4][1] + 1e-9, STEP):
    for q6 in np.arange(LIM[5][0], LIM[5][1] + 1e-9, STEP):
        q = [0, 0, 0, 0, q5, q6]
        mats = body_mats(q)
        mv = {}
        bb6 = {}
        for n in DN:
            mv[n] = M[n].transform(np.asarray(mats[6][:3, :], np.float64))
            bb6[n] = mv[n].bounding_box()
        for nd in DN:
            for nu in UP:
                if frozenset((nd, nu)) in DECLARED:
                    continue
                bu = fb[nu]
                b6 = bb6[nd]
                if (b6[0] > bu[3] or bu[0] > b6[3] or b6[1] > bu[4] or bu[1] > b6[4]
                        or b6[2] > bu[5] or bu[2] > b6[5]):
                    continue
                inter = mv[nd] ^ fix[nu]
                if inter.volume() <= 0.5:
                    continue
                k = (nd, nu)
                hitcount[k] = hitcount.get(k, 0) + 1
                i_dn = inter.transform(np.asarray(np.linalg.inv(mats[6])[:3, :], np.float64))
                foot_dn[k] = i_dn if foot_dn.get(k) is None else foot_dn[k] + i_dn
                foot_up[k] = inter if foot_up.get(k) is None else foot_up[k] + inter
print("%.0f s" % (time.time() - t0))
os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
for (nd, nu), c in sorted(hitcount.items()):
    print("%s x %s: %d hit poses" % (nd, nu, c))
    for which, foot, frame in (("on_%s" % nd, foot_dn[(nd, nu)], "W"),
                              ("on_%s" % nu, foot_up[(nd, nu)], "W")):
        mm = foot.to_mesh()
        tm = trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3],
                             np.asarray(mm.tri_verts))
        p = os.path.join(HERE, "out", "fp_%s_x_%s_%s.stl" % (nd, nu, which))
        tm.export(p)
        b = tm.bounds - np.array([WJ, WJ])
        print("   %-28s W a %6.1f..%6.1f  b %6.1f..%6.1f  h %6.1f..%6.1f"
              % (which, b[0][0], b[1][0], b[0][1], b[1][1], b[0][2], b[1][2]))
