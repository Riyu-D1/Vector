"""cradlefix/cf_clearance.py - minimum clearance measurement for the D7-fixed
pairs, using the tested f2_collision machinery (meshes + body_mats).
Per fixed mesh a ProximityQuery is built once; per pose the moving part's
contact-region vertices are transformed and nearest-surface distances queried.
Run: CF_WRIST_DIR=cradlefix/out python3 cradlefix/cf_clearance.py
"""
import math, os, sys, time
import numpy as np
import trimesh

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

def tm_of(name):
    mm = M[name].to_mesh()
    return trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3],
                           np.asarray(mm.tri_verts), process=False)

def wsel(name, lo, hi, stride=1):
    v = np.asarray(M[name].to_mesh().vert_properties)[:, :3]
    w = v - WJ
    sel = np.all((w >= lo) & (w <= hi), axis=1)
    return v[sel][::stride]

PQ = {}
def pq(name):
    if name not in PQ:
        PQ[name] = trimesh.proximity.ProximityQuery(tm_of(name))
    return PQ[name]

def mesh_dist(verts_home, mat, fixed_name):
    pv = (mat[:3, :3] @ verts_home.T).T + mat[:3, 3]
    cp, d, _ = pq(fixed_name).on_surface(pv)
    return float(d.min()), pv[int(d.argmin())]

# ---------------- pair A: w_link5 vs {w_j4_cradle, vendor_sts3250_j4} ----------
t0 = time.time()
v5 = np.vstack([
    wsel("w_link5", np.array([18.0, 10.5, -20.0]), np.array([40.0, 15.5, 0.0])),
    wsel("w_link5", np.array([18.0, -15.5, -20.0]), np.array([40.0, -10.5, 0.0]))])
print("link5 probe verts", len(v5))
step = math.radians(2.5)
best = {}
for q4 in np.arange(LIM[3][0], LIM[3][1] + 1e-9, step):
    for q5 in np.arange(LIM[4][0], LIM[4][1] + 1e-9, step):
        mats = body_mats([0, 0, 0, q4, q5, 0])
        m5 = np.asarray(mats[5][:3, :], np.float64)
        for fn in ("w_j4_cradle", "vendor_sts3250_j4"):
            d, p = mesh_dist(v5, m5, fn)
            k = ("w_link5", fn)
            if d < best.get(k, (1e9,))[0]:
                best[k] = (d, q4, q5, p)
print("A coarse %.0f s" % (time.time() - t0))
for k, (d, q4, q5, p) in sorted(best.items()):
    print("%s x %s: coarse min %.2f mm at J4 %+.1f J5 %+.1f  near W %s"
          % (k[0], k[1], d, math.degrees(q4), math.degrees(q5), np.round(p - WJ, 2)))

fine = {}
for k, (d0, q4c, q5c, _) in best.items():
    for q4 in np.arange(q4c - step, q4c + step + 1e-9, math.radians(0.5)):
        for q5 in np.arange(q5c - step, q5c + step + 1e-9, math.radians(0.5)):
            mats = body_mats([0, 0, 0, q4, q5, 0])
            m5 = np.asarray(mats[5][:3, :], np.float64)
            d, p = mesh_dist(v5, m5, k[1])
            if d < fine.get(k, (1e9,))[0]:
                fine[k] = (d, q4, q5, p)
print("refined (0.5 deg):")
for k, (d, q4, q5, p) in sorted(fine.items()):
    print("%s x %s: min clearance %.2f mm at J4 %+.2f J5 %+.2f  near W %s"
          % (k[0], k[1], d, math.degrees(q4), math.degrees(q5), np.round(p - WJ, 2)))

# ---------------- pair B: w_grip_frame vs w_link4 ----------------------------
t0 = time.time()
vg = wsel("w_grip_frame", np.array([62.0, -15.5, -27.0]), np.array([70.0, 15.5, -8.0]))
print("\ngrip probe verts", len(vg))
bestb = (1e9,)
for q5 in np.arange(math.radians(-45), math.radians(45) + 1e-9, math.radians(1.0)):
    for q6 in np.concatenate([np.arange(math.radians(95), math.radians(180) + 1e-9, math.radians(1.0)),
                              np.arange(math.radians(-180), math.radians(-95) + 1e-9, math.radians(1.0))]):
        mats = body_mats([0, 0, 0, 0, q5, q6])
        m6 = np.asarray(mats[6][:3, :], np.float64)
        d, p = mesh_dist(vg, m6, "w_link4")
        if d < bestb[0]:
            bestb = (d, q5, q6, p)
print("B coarse %.0f s" % (time.time() - t0))
d, q5, q6, p = bestb
print("w_grip_frame x w_link4: coarse min %.2f mm at J5 %+.1f J6 %+.1f near W %s"
      % (d, math.degrees(q5), math.degrees(q6), np.round(p - WJ, 2)))
fb = (1e9,)
for q5f in np.arange(q5 - math.radians(1), q5 + math.radians(1) + 1e-9, math.radians(0.25)):
    for q6f in np.arange(q6 - math.radians(1), q6 + math.radians(1) + 1e-9, math.radians(0.25)):
        mats = body_mats([0, 0, 0, 0, q5f, q6f])
        m6 = np.asarray(mats[6][:3, :], np.float64)
        dd, pp = mesh_dist(vg, m6, "w_link4")
        if dd < fb[0]:
            fb = (dd, q5f, q6f, pp)
d, q5, q6, p = fb
print("w_grip_frame x w_link4: min clearance %.2f mm at J5 %+.2f J6 %+.2f near W %s"
      % (d, math.degrees(q5), math.degrees(q6), np.round(p - WJ, 2)))
