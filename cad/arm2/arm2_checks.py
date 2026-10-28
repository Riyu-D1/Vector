"""cad/arm2/arm2_checks.py - A2a numeric checks.  Run AFTER build_arm2.py (needs out/*.stl, out/*.step).
Prints REACH / HOLE / TORQUE / ROM lines and CHECKS PASS or CHECKS FAIL."""
import math, os, sys, glob
import numpy as np, trimesh, manifold3d as m3d
from build123d import import_step, GeomType, Vector
from OCP.BRepAdaptor import BRepAdaptor_Surface
import ap2 as P, p_arm2 as PA
A = P.A
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "out")
ok = True
def res(tag, good, msg):
    global ok
    ok &= bool(good)
    print("%s %s %s" % (tag, msg, "PASS" if good else "FAIL"), flush=True)

# ---------- 1. reach, measured on the posed parts ----------
def hole_axes(name, r):
    s = import_step(os.path.join(OUT, name + ".step")); pts = []
    for f in s.faces():
        if f.geom_type == GeomType.CYLINDER and abs(f.radius - r) < 0.05:
            loc = BRepAdaptor_Surface(f.wrapped).Cylinder().Axis().Location()
            p = (round(loc.X(), 2), round(loc.Z(), 2))
            if p not in pts: pts.append(p)
    return pts
up = sorted(hole_axes("upper_back", P.UP_BACK_HOLE / 2), key=lambda p: p[1])
j4 = hole_axes("fore_l", 19.0)
if len(up) != 2 or len(j4) != 1:
    res("REACH", False, "hole axes not found: upper_back %s fore_l %s" % (up, j4))
else:
    J2, J3, J4 = np.array(up[0]), np.array(up[1]), np.array(j4[0])
    u = np.linalg.norm(J3 - J2)
    fdir = np.array([1.0, 0.0])                       # home pose: forearm points +X
    f_ax = float(np.dot(J4 - J3, fdir)); off = float(abs((J4 - J3)[1]))
    reach = u + f_ax + P.J4_TCP_A2B
    print("REACH J2 %s J3 %s J4 %s" % (tuple(J2), tuple(J3), tuple(J4)))
    res("REACH", abs(u - P.UP_SPAN) < 0.1, "upper J2->J3 %.2f (want %.1f)" % (u, P.UP_SPAN))
    res("REACH", abs(f_ax - P.FORE_SPAN) < 0.1, "forearm J3->J4 axial %.2f (want %.1f), offset %.2f (want %.1f)" % (f_ax, P.FORE_SPAN, off, P.J4_OFFSET))
    res("REACH", abs(reach - P.REACH_TARGET) <= P.REACH_TOL, "J2->TCP %.1f = %.1f + %.1f + A2b %.1f (want %.0f +- %.0f)" % (reach, u, f_ax, P.J4_TCP_A2B, P.REACH_TARGET, P.REACH_TOL))

# ---------- 2. holes vs the actuator interface (rest frame, before posing) ----------
def pcd(c, d, angs): return PA.pcd_xz(c, d, angs)
def inside(s, x, y, z): return s.is_inside(Vector(x, y, z))
def clear_hole(s, name, x, y, z, d):
    """hole centre empty, and material 0.8 mm outside the hole edge on 4 sides"""
    rim = [inside(s, x + (d / 2 + 0.8) * math.cos(a), y, z + (d / 2 + 0.8) * math.sin(a)) for a in (0.785, 2.356, 3.927, 5.498)]
    return (not inside(s, x, y, z)) and all(rim)
def check_holes(name, s, centres, d, ymid, what):
    bad = [c for c in centres if not clear_hole(s, name, c[0], ymid, c[1], d)]
    res("HOLE", not bad, "%s: %d x d%.1f %s%s" % (name, len(centres), d, what, (" bad at %s" % bad) if bad else ""))
J2r, J3r = P.J2_XZ, P.J3_XZ
links = PA.link_angles()
for nm, fn, cs, y in [("back_spacer_j2", lambda: PA.back_spacer(J2r), [J2r], sum(P.BACK_SP_Y) / 2),
                      ("back_spacer_j3", lambda: PA.back_spacer(J3r), [J3r], sum(P.BACK_SP_Y) / 2),
                      ("upper_back", PA.upper_back, [J2r, J3r], P.UP_BACK_Y[0] + 0.5)]:
    s = fn()
    check_holes(nm, s, sum([pcd(c, A.LINK_PCD, links) for c in cs], []), A.LINK_PILOT_D, y, "on actuator back pilots PCD%.0f" % A.LINK_PCD)
fs2 = PA.front_spacer("J2"); fs3 = PA.front_spacer("J3")
for nm, s, c, y in [("front_spacer_j2", fs2, J2r, -33.6), ("front_spacer_j3", fs3, (J3r[0] - P.DX_UP, J3r[1]), -33.6)]:
    check_holes(nm, s, pcd(c, A.OUT_M3_PCD, A.OUT_M3_ANG), 3.0, y, "on actuator M3 PCD%.0f" % A.OUT_M3_PCD)
    check_holes(nm, s, pcd(c, A.OUT_DOWEL_PCD, A.OUT_DOWEL_ANG), A.OUT_DOWEL_D, y, "on actuator dowels PCD%.0f" % A.OUT_DOWEL_PCD)
    old = [p for p in pcd(c, 24.0, [30.0, 150.0, 270.0]) if not inside(s, p[0], y, p[1])]
    res("HOLE", not old, "%s: old reBot dowel holes plugged%s" % (nm, (" open at %s" % old) if old else ""))
l1 = PA.rebot("03_Link1")
check_holes("link1", l1, pcd(J2r, A.OUT_M3_PCD, A.OUT_M3_ANG), 3.0, -37.1, "J2 cheek on actuator M3")
dl = PA.rebot("02_Lower_Upper_Link_L")
check_holes("dogleg_l", dl, pcd(P.J3_XZ_REBOT, A.OUT_M3_PCD, A.OUT_M3_ANG), 3.0, -38.1, "J3 end on actuator M3")
res("HOLE", 0.1 <= P.RING_D - A.OD <= 0.3, "upper_out ring d%.2f on housing OD %.2f (clearance %.2f)" % (P.RING_D, A.OD, P.RING_D - A.OD))
uo = PA.upper_out(); ym = sum(P.UP_OUT_Y) / 2
ring = all((not inside(uo, c[0] + (A.OD / 2) * math.cos(a), ym, c[1] + (A.OD / 2) * math.sin(a))) and inside(uo, c[0] + (P.RING_D / 2 + 0.8) * math.cos(a), ym, c[1] + (P.RING_D / 2 + 0.8) * math.sin(a))
           for c in (J2r, J3r) for a in np.linspace(0, 2 * math.pi, 12, endpoint=False))
res("HOLE", ring, "upper_out: housing OD free and ring wall present at both ends")
# forearm plate bolts onto the dogleg top end: every small dogleg hole near the top end must be clear in fore_l
dsh = dl.moved(PA.Location((P.DX_UP, P.DOGLEG_DY["L"], 0)))
tops = []
for f in dsh.faces():
    if f.geom_type == GeomType.CYLINDER and f.radius < 2.0:
        loc = BRepAdaptor_Surface(f.wrapped).Cylinder().Axis().Location(); p = (round(loc.X(), 2), round(loc.Z(), 2))
        if p[1] > 180 and p not in tops: tops.append(p)
fl = PA.fore_plate("L")
badf = [p for p in tops if inside(fl, p[0], sum(P.FORE_L_Y) / 2, p[1])]
res("HOLE", len(tops) >= 4 and not badf, "fore_l: %d dogleg top-end holes clear%s" % (len(tops), (" blocked %s" % badf) if badf else ""))
yl = PA.yaw_limit(); bb = yl.bounding_box(); zm = (bb.min.Z + bb.max.Z) / 2
hh = [(P.SV_HORN_PCD / 2 * math.cos(math.radians(P.J1_YAW + 90 * i)), P.SV_HORN_PCD / 2 * math.sin(math.radians(P.J1_YAW + 90 * i))) for i in range(4)]
yb = [h for h in hh if inside(yl, h[0], h[1], zm)]
res("HOLE", (not yb) and inside(yl, 5.0, 0.0, zm) and not inside(yl, 0, 0, bb.min.Z + 1.0), "yaw_limit: 4 horn holes PCD%.0f clear, old d14 plugged, horn recess open" % P.SV_HORN_PCD)

# ---------- 3. static torque, arm straight and horizontal (rest frame, forearm unfolded 180) ----------
from build123d import Axis
ax3 = Axis((J3r[0], 0, J3r[1]), (0, 1, 0))
m_g = lambda s: s.volume * P.RHO_PETG * P.INFILL_EFF / 1000.0     # kg
up_items, fo_items = [], []
for name, grp, fn in PA.parts():
    if grp == "fix" or name.startswith("vendor_"): continue
    s = fn()
    if grp == "fo": s = s.rotate(ax3, 180.0)
    (up_items if grp == "up" else fo_items).append((m_g(s), s.center().X))
g = 9.81
s48 = 0.48
w45, w56, tool = 78.3 * s48, 40.0 * s48, max(155.4 * s48, 75.0)
xj4 = J3r[0] + P.FORE_SPAN; xj5 = xj4 + w45; xj6 = xj5 + w56; xt = xj6 + tool
wrist = [(0.055, xj4), (0.020, xj4 + w45 / 2), (0.055, xj5), (0.020, xj5 + w56 / 2), (0.055, xj6), (P.M_GRIP, xj6 + 0.4 * tool), (P.PAYLOAD, xt)]
allit = up_items + [(P.M_ACT, J3r[0])] + fo_items + wrist
tq = lambda xj, its: sum(m * g * (x - xj) / 1000.0 for m, x in its if x > xj)
t2 = tq(J2r[0], allit); t3 = tq(J3r[0], fo_items + wrist)
mu = sum(m for m, _ in up_items); mf = sum(m for m, _ in fo_items)
print("TORQUE masses: upper printed %.3f kg, forearm printed %.3f kg, J3 actuator %.3f [U], wrist+grip %.3f, payload %.2f; J4->TCP %.1f" % (mu, mf, P.M_ACT, sum(m for m, _ in wrist[:-1]), P.PAYLOAD, xt - xj4))
res("TORQUE", t2 <= P.TORQUE_MAX["J2"], "J2 %.2f N.m (rebot_torque 0.48: %.2f, limit %.2f, margin %.2fx, need <= %.2f)" % (t2, P.J2_REF, P.J2_LIMIT, P.J2_LIMIT / t2, P.TORQUE_MAX["J2"]))
res("TORQUE", t3 <= P.TORQUE_MAX["J3"], "J3 %.2f N.m (rebot_torque 0.48: %.2f, limit %.2f, margin %.2fx, need <= %.2f)" % (t3, P.J3_REF, P.J3_LIMIT, P.J3_LIMIT / t3, P.TORQUE_MAX["J3"]))

# ---------- 4. ROM sweeps from the home pose (posed meshes) ----------
def man(path):
    m = trimesh.load_mesh(path, force="mesh"); m.merge_vertices()
    return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
grp = {n: g_ for n, g_, _ in PA.parts() if not n.startswith("vendor_6803")}   # the bearing is the joint: it touches both sides
M = {n: man(os.path.join(OUT, n + ".stl")) for n in grp}
J2h = np.array([P.J2_XZ[0], 0.0, P.J2_XZ[1]])
a = math.radians(P.POSE_J2); v = np.array([P.UP_SPAN, 0.0, 0.0])
J3h = J2h + np.array([v[0] * math.cos(a), 0.0, -v[0] * math.sin(a)])
def rot(mf, c, deg):
    return mf.translate((-c).tolist()).rotate([0.0, deg, 0.0]).translate(c.tolist())
def hits(moving, fixed, c, deg):
    out = []
    for nm in moving:
        mm = rot(M[nm], c, deg)
        for nf in fixed:
            if nm.startswith("vendor_") and nf.startswith("vendor_") and not ("act" in nm and "act" in nf): continue
            v_ = (mm ^ M[nf]).volume()
            if v_ > 0.5: out.append("%s x %s %.0f" % (nm, nf, v_))
    return out
def sweep(j, moving, fixed, c):
    lim = {}
    for sgn in (1, -1):
        d = 0.0; first = ""
        while d < 180.0:
            h = hits(moving, fixed, c, sgn * (d + P.ROM_STEP))
            if h: first = h[0]; break
            d += P.ROM_STEP
        lim[sgn] = (d, first)
    tot = lim[1][0] + lim[-1][0]
    res("ROM", tot >= P.ROM_MIN[j], "%s free %+.0f..%+.0f deg (total %.0f, need >= %.0f) stops: + [%s] - [%s]" % (j, -lim[-1][0], lim[1][0], tot, P.ROM_MIN[j], lim[1][1], lim[-1][1]))
h0 = hits([n for n in grp if grp[n] != "fix"], [n for n in grp if grp[n] == "fix"], J2h, 0.0)
res("ROM", not h0, "home pose J2 joint clear%s" % (" %s" % h0 if h0 else ""))
fo = [n for n in grp if grp[n] == "fo"]; nonfo = [n for n in grp if grp[n] != "fo"]
sweep("J3", fo, nonfo, J3h)
sweep("J2", [n for n in grp if grp[n] != "fix"], [n for n in grp if grp[n] == "fix"], J2h)
print("CHECKS PASS" if ok else "CHECKS FAIL")
sys.exit(0 if ok else 1)
