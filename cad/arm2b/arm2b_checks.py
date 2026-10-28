"""cad/arm2b/arm2b_checks.py - A2b numeric checks.  Run AFTER build_arm2b.py (needs out/*.stl, out/*.step).
Prints REACH / HOLE / GRIP / TORQUE / ROM lines and CHECKS PASS or CHECKS FAIL."""
import math, os, sys
import numpy as np, trimesh, manifold3d as m3d
from build123d import import_step, GeomType, Vector, Axis, Pos
from OCP.BRepAdaptor import BRepAdaptor_Surface
import p_arm2b as PB, ap2b as B
P2 = B.P2; PA = PB.PA
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "out")
ok = True
def res(tag, good, msg):
    global ok
    ok &= bool(good)
    print("%s %s %s" % (tag, msg, "PASS" if good else "FAIL"), flush=True)

# ---------- 1. reach + wrist spans, measured on the posed parts ----------
def cyl_axes(name, r):
    s = import_step(os.path.join(OUT, name + ".step")); out = []
    for f in s.faces():
        if f.geom_type == GeomType.CYLINDER and abs(f.radius - r) < 0.05:
            ax = BRepAdaptor_Surface(f.wrapped).Cylinder().Axis()
            l, d = ax.Location(), ax.Direction()
            p = (round(l.X(), 2), round(l.Y(), 2), round(l.Z(), 2), round(abs(d.X()), 2), round(abs(d.Y()), 2), round(abs(d.Z()), 2))
            if p not in out: out.append(p)
    return out
up = sorted({(p[0], p[2]) for p in cyl_axes("upper_back", P2.UP_BACK_HOLE / 2)}, key=lambda p: p[1])
hr = B.SV_HORN_D / 2
h4, h5, h6 = cyl_axes("vendor_sts3215_j4", hr), cyl_axes("vendor_sts3215_j5", hr), cyl_axes("vendor_sts3215_j6", hr)
tcp = trimesh.load_mesh(os.path.join(OUT, "finger_u.stl")).bounds[1][0]
J2, J3 = np.array(up[0]), np.array(up[1])
J4 = np.array([h4[0][0], h4[0][2]]); x5, y5 = h5[0][0], h5[0][1]; y6, z6 = h6[0][1], h6[0][2]
u = float(np.linalg.norm(J3 - J2)); f_ax = float(J4[0] - J3[0]); w = tcp - J4[0]
print("REACH J2 %s J3 %s J4 %s (J4 servo horn) J5 x %.2f y %.2f (vertical) J6 y %.2f z %.2f (along X) TCP x %.2f" % (tuple(J2), tuple(J3), tuple(J4), x5, y5, y6, z6, tcp))
res("REACH", abs(x5 - J4[0] - B.J4_J5) < B.REACH_TOL and abs(y5) < 0.05, "J4->J5 %.2f (want %.1f), J5 axis y %.2f" % (x5 - J4[0], B.J4_J5, y5))
res("REACH", abs(z6 - J4[1]) < 0.05 and abs(y6) < 0.05, "J6 axis on the J4 height: dz %.2f dy %.2f; J5->J6 frame %.1f on it, J6 horn face at J4 + %.1f" % (z6 - J4[1], y6, B.J5_J6, B.A6_FACE))
res("REACH", abs(w - B.A_TCP) < B.REACH_TOL, "J4->TCP %.2f (want %.1f = %.1f + %.1f + %.1f)" % (w, B.A_TCP, B.J4_J5, B.J5_J6, B.J6_TCP))
reach = u + f_ax + w
res("REACH", abs(reach - P2.REACH_TARGET) <= P2.REACH_TOL, "J2->TCP %.1f = %.1f + %.1f + %.1f (want %.0f +- %.0f)" % (reach, u, f_ax, w, P2.REACH_TARGET, P2.REACH_TOL))

# ---------- 2. holes (rest-frame shapes, W coordinates) ----------
J4X, J4Z = P2.J4_XZ
def inw(s, a, b, h): return s.is_inside(Vector(J4X - a, b, J4Z - h))
def perp(axis, r, t):
    c, s_ = r * math.cos(t), r * math.sin(t)
    return {"a": (0, c, s_), "b": (c, 0, s_), "h": (c, s_, 0)}[axis]
def clear_hole(s, p, axis, d):
    """p = (a,b,h) on the hole axis: centre empty, material 0.8 outside the edge on 4 sides"""
    rim = [inw(s, *[p[i] + perp(axis, d / 2 + 0.8, t)[i] for i in range(3)]) for t in (0.785, 2.356, 3.927, 5.498)]
    return (not inw(s, *p)) and all(rim)
def horn_check(name, s, c, axis, t):
    pts = []
    for q in PB.pcd(c):
        pts.append({"a": (t, q[0], q[1]), "b": (q[0], t, q[1]), "h": (q[0], q[1], t)}[axis])
    bad = [p for p in pts if not clear_hole(s, p, axis, B.HORN_HOLE)]
    res("HOLE", not bad, "%s: 4 x d%.1f on the STS3215 horn PCD%.0f%s" % (name, B.HORN_HOLE, B.SV_HORN_PCD, (" bad at %s" % bad) if bad else ""))
def hole_centre(name, r, ax):
    """centre of the 4 horn holes measured in the posed STEP vs the servo horn axis"""
    hs = [p for p in cyl_axes(name, r) if p[3 + "xyz".index(ax)] > 0.99]
    return np.mean([[p[0], p[1], p[2]] for p in hs], axis=0), len(hs)
l4, l5, gf = PB.link4(), PB.link5(), PB.grip_frame()
horn_check("link4", l4, (0, 0), "b", sum(B.L4_B) / 2)
horn_check("link5", l5, (B.A_J5, 0), "h", sum(B.L5_TOP) / 2)
horn_check("grip_frame", gf, (0, 0), "a", (B.GB_A[0] + B.HORN_RECESS[1] + B.GB_CB_A) / 2)
for nm, ax, want in (("link4", "y", (J4[0], None, J4[1])), ("link5", "z", (x5, y5, None)), ("grip_frame", "x", (None, y6, z6))):
    c, n = hole_centre(nm, B.HORN_HOLE / 2, ax)
    err = max(abs(c[i] - want[i]) for i in range(3) if want[i] is not None)
    res("HOLE", n == 4 and err < 0.05, "%s: %d horn holes measured, pattern centre on the servo horn axis (err %.3f)" % (nm, n, err))
for side in ("L", "R"):
    s = PB.fore2(side); y = sum(P2.FORE_L_Y if side == "L" else P2.FORE_R_Y) / 2
    res("HOLE", inw(s, 0, y, 0) and inw(s, 0, y, 18.5) and inw(s, 18.5, y, 0), "fore_%s2: old reBot d38 DM4310 pilot plugged" % side.lower())
fr, cr = PB.fore2("R"), PB.j4_cradle()
bad = [p for p in B.J4_BOLTS if not clear_hole(fr, (p[0], sum(P2.FORE_R_Y) / 2, p[1]), "b", B.M3_CLR)]
res("HOLE", not bad, "fore_r2: 4 x d%.1f J4 cradle bolts clear%s" % (B.M3_CLR, (" bad %s" % bad) if bad else ""))
bad = [p for p in B.J4_BOLTS if not clear_hole(cr, (p[0], B.J4_CRADLE_B[1] - 2.0, p[1]), "b", B.M3_PILOT)]
res("HOLE", not bad, "j4_cradle: 4 x d%.1f pilots on the same centres, 8 deep%s" % (B.M3_PILOT, (" bad %s" % bad) if bad else ""))
res("HOLE", 0.1 <= B.SV_CLR <= 0.3, "STS3215 pockets: %.2f per side on the %.1f x %.1f x %.1f case" % (B.SV_CLR, B.SV_X[1] - B.SV_X[0], 2 * B.SV_Z, B.SV_Y[1] - B.SV_Y[0]))

# ---------- 3. gripper stroke: racks + fingers at full open, W frame ----------
def man_s(s):
    import tempfile
    from build123d import export_stl
    f = tempfile.mktemp(suffix=".stl"); export_stl(s, f, tolerance=0.05, angular_tolerance=0.3)
    m = trimesh.load_mesh(f, force="mesh"); m.merge_vertices(); os.remove(f)
    return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
o = B.STROKE / 2
gw = man_s(PB.grip_frame()); gs = man_s(PB.vendor_servo("g")())
mv = {"rack_u": man_s(PB.rest(PB.rack("U", o))), "rack_d": man_s(PB.rest(PB.rack("D", o))),
      "finger_u": man_s(PB.rest(PB.finger("U", o))), "finger_d": man_s(PB.rest(PB.finger("D", o)))}
hit = []
for n, m in mv.items():
    for n2, m2 in [("grip_frame", gw), ("sts3215_g", gs)] + [(k, v) for k, v in mv.items() if k > n and not (k[-1] == n[-1])]:
        v = (m ^ m2).volume()
        if v > 0.5: hit.append("%s x %s %.1f" % (n, n2, v))
inside_br = max(abs(B.RACK_U_B[0] + o), abs(B.RACK_U_B[1] + o)) <= B.BR_B and max(abs(B.RACK_D_B[0] - o), abs(B.RACK_D_B[1] - o)) <= B.BR_B
engaged = (B.RACK_U_B[0] + o < -B.GEAR[0] / 2) and (B.RACK_D_B[1] - o > B.GEAR[0] / 2)
res("GRIP", not hit and inside_br and engaged, "open %.1f mm (finger gap %.1f -> %.1f): racks stay in the %.0f mm channels and on the gear, no hits%s"
    % (B.STROKE, 2 * B.FINGER_GAP, 2 * (B.FINGER_GAP + o), 2 * B.BR_B, (" %s" % hit) if hit else ""))

# ---------- 4. static torque, arm straight and horizontal (rest frame, forearm + wrist unfolded 180 about J3) ----------
J3r = P2.J3_XZ; J2r = P2.J2_XZ
ax3 = Axis((J3r[0], 0, J3r[1]), (0, 1, 0))
VM = {"vendor_sts3215_j4": B.M_STS3215, "vendor_sts3215_j5": B.M_STS3215, "vendor_sts3215_j6": B.M_STS3215,
      "vendor_sts3215_g": B.M_STS3215, "vendor_gear_grip": B.M_GEAR, "vendor_rack_u": B.M_RACK, "vendor_rack_d": B.M_RACK}
items = {}
for name, grp, fn in PB.parts():
    if grp == "fix" or (name.startswith("vendor_") and name not in VM): continue
    s = fn()
    if grp != "up": s = s.rotate(ax3, 180.0)
    m = VM.get(name, s.volume * P2.RHO_PETG * P2.INFILL_EFF / 1000.0)
    items[name] = (grp, m, s.center().X)
g = 9.81
xj4 = J3r[0] + P2.FORE_SPAN; xt = xj4 + B.A_TCP
pay = [("payload", "w6", B.PAYLOAD, xt)]
allit = [(n, gr, m, x) for n, (gr, m, x) in items.items()] + [("act_j3", "up", P2.M_ACT, J3r[0])] + pay
tq = lambda xj, keep: sum(m * g * (x - xj) / 1000.0 for n, gr, m, x in allit if keep(gr))
t2 = tq(J2r[0], lambda gr: True); t3 = tq(J3r[0], lambda gr: gr != "up"); t4 = tq(xj4, lambda gr: gr.startswith("w"))
t5 = tq(xj4 + B.A_J5, lambda gr: gr in ("w5", "w6"))
mw = sum(m for n, gr, m, x in allit if gr.startswith("w") and n != "payload")
mj4 = sum(m for n, gr, m, x in allit if n in ("j4_cradle", "vendor_sts3215_j4"))
print("TORQUE masses: wrist+gripper (J4 horn onward) %.3f kg, J4 servo+cradle %.3f kg, payload %.2f kg at J4 + %.1f" % (mw, mj4, B.PAYLOAD, B.A_TCP))
lim = B.STS3215_RATED / B.TORQUE_SF
res("TORQUE", t4 <= lim, "J4 %.2f N.m (STS3215 rated %.2f [U] / %.1f = %.2f)" % (t4, B.STS3215_RATED, B.TORQUE_SF, lim))
res("TORQUE", t5 <= lim, "J5 %.2f N.m with J4 turned 90 (same limit %.2f)" % (t5, lim))
res("TORQUE", t2 <= P2.TORQUE_MAX["J2"], "J2 %.2f N.m with the real wrist (A2a need <= %.2f, limit %.2f)" % (t2, P2.TORQUE_MAX["J2"], P2.J2_LIMIT))
res("TORQUE", t3 <= P2.TORQUE_MAX["J3"], "J3 %.2f N.m with the real wrist (A2a need <= %.2f, limit %.2f)" % (t3, P2.TORQUE_MAX["J3"], P2.J3_LIMIT))

# ---------- 5. ROM sweeps from the home pose (posed meshes) ----------
def man(path):
    m = trimesh.load_mesh(path, force="mesh"); m.merge_vertices()
    return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
grp = {n: g_ for n, g_, _ in PB.parts() if not n.startswith("vendor_6803")}
M = {n: man(os.path.join(OUT, n + ".stl")) for n in grp}
def skip(a, b):
    if a.startswith("vendor_") and b.startswith("vendor_"):
        act = lambda n: "act" in n or "sts3215" in n
        return not (act(a) and act(b))
    return False
def hits(moving, fixed, rot):
    out = []
    for nm in moving:
        mm = rot(M[nm]); bm = mm.bounding_box()
        for nf in fixed:
            if skip(nm, nf): continue
            bf = M[nf].bounding_box()
            if any(bm[i] > bf[i + 3] or bf[i] > bm[i + 3] for i in range(3)): continue
            v_ = (mm ^ M[nf]).volume()
            if v_ > 0.5: out.append("%s x %s %.0f" % (nm, nf, v_))
    return out
def about(c, axis):
    c = np.asarray(c, float)
    def f(deg):
        r = [0.0, 0.0, 0.0]; r["xyz".index(axis)] = deg
        return lambda mf: mf.translate((-c).tolist()).rotate(r).translate(c.tolist())
    return f
def sweep(j, moving, fixed, rf, need):
    lim = {}
    for sgn in (1, -1):
        d = 0.0; first = ""
        while d < 180.0:
            h = hits(moving, fixed, rf(sgn * (d + B.ROM_STEP)))
            if h: first = h[0]; break
            d += B.ROM_STEP
        lim[sgn] = (d, first)
    tot = lim[1][0] + lim[-1][0]
    res("ROM", tot >= need, "%s free %+.0f..%+.0f deg (total %.0f, need >= %.0f) stops: + [%s] - [%s]" % (j, -lim[-1][0], lim[1][0], tot, need, lim[1][1], lim[-1][1]))
W = {"w4": 4, "w5": 5, "w6": 6}
wr = [n for n in grp if grp[n] in W]
h0 = []
for i, n in enumerate(wr):
    h0 += hits([n], [k for k in grp if k != n and (k not in wr or wr.index(k) > i)], lambda m: m)
res("ROM", not h0, "home pose wrist + gripper clear of every part%s" % (" %s" % h0 if h0 else ""))
mov = lambda k: [n for n in grp if W.get(grp[n], 0) >= k]
fix = lambda k: [n for n in grp if W.get(grp[n], 0) < k]
sweep("J4", mov(4), fix(4), about((J4[0], 0, J4[1]), "y"), B.ROM_MIN["J4"])
sweep("J5", mov(5), fix(5), about((x5, y5, 0), "z"), B.ROM_MIN["J5"])
sweep("J6", mov(6), fix(6), about((0, y6, z6), "x"), B.ROM_MIN["J6"])
J2h = np.array([J2r[0], 0.0, J2r[1]]); J3h = np.array([J3[0], 0.0, J3[1]])
fo = [n for n in grp if grp[n] == "fo" or grp[n] in W]
sweep("J3", fo, [n for n in grp if n not in fo], about(J3h, "y"), P2.ROM_MIN["J3"])
sweep("J2", [n for n in grp if grp[n] != "fix"], [n for n in grp if grp[n] == "fix"], about(J2h, "y"), P2.ROM_MIN["J2"])
print("CHECKS PASS" if ok else "CHECKS FAIL")
sys.exit(0 if ok else 1)
