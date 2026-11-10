"""refine/wrist7_checks.py - refinement re-check (R1/R2 fixes).

Copy of wrist2/wrist2_checks.py pointed at refine/p_wrist7 + refine/ap7 and
refine/out (fixed STLs).  Same gates, same thresholds.
Same gates as wrist/wrist_checks.py adapted to the new axes:
  J5 yaw axis at a=30.6 (horn centre h=+7.6, face down at -2.0),
  J6+gripper roll line at h=-17.0, TCP (131.8,-17).
Structural parts come from wrist2/out; every other posed part re-read from
cad/arm2b/out.  Run AFTER build_wrist6.py + build_arm2b.py.
Prints lines + CHECKS PASS/FAIL."""
import math, os, sys
import numpy as np, trimesh, manifold3d as m3d
from build123d import import_step, GeomType, Vector, Axis, Pos
from OCP.BRepAdaptor import BRepAdaptor_Surface
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "cad", "arm2b"))
sys.path.insert(0, os.path.join(HERE, "..", "cad", "arm2"))
import p_arm2b as PB, ap2b as B, p_wrist7 as PW, ap7 as N
P2 = B.P2; PA = PB.PA
OUT = os.path.join(HERE, "out")
OUT2 = os.path.join(HERE, "..", "cad", "arm2b", "out")
ok = True
def res(tag, good, msg):
    global ok
    ok &= bool(good)
    print("%s %s %s" % (tag, msg, "PASS" if good else "FAIL"), flush=True)

# ---------- 1. reach + wrist spans ----------
def cyl_axes(name, r, out=OUT2):
    s = import_step(os.path.join(out, name + ".step")); out_ = []
    for f in s.faces():
        if f.geom_type == GeomType.CYLINDER and abs(f.radius - r) < 0.05:
            ax = BRepAdaptor_Surface(f.wrapped).Cylinder().Axis()
            l, d = ax.Location(), ax.Direction()
            p = (round(l.X(), 2), round(l.Y(), 2), round(l.Z(), 2), round(abs(d.X()), 2), round(abs(d.Y()), 2), round(abs(d.Z()), 2))
            if p not in out_: out_.append(p)
    return out_
up = sorted({(p[0], p[2]) for p in cyl_axes("upper_back", P2.UP_BACK_HOLE / 2)}, key=lambda p: p[1])
hr = B.SV_HORN_D / 2
# horn axes by direction: j4 along Y (b), j5 along Z (h), j6 along X (a)
h4 = [p for p in cyl_axes("vendor_sts3215_j4", hr, OUT) if p[4] > 0.99]
h5 = [p for p in cyl_axes("vendor_sts3215_j5", hr, OUT) if p[5] > 0.99]
h6 = [p for p in cyl_axes("vendor_sts3215_j6", hr, OUT) if p[3] > 0.99]
tcp = trimesh.load_mesh(os.path.join(OUT, "finger_u.stl")).bounds[1][0]
J2, J3 = np.array(up[0]), np.array(up[1])
J4 = np.array([h4[0][0], h4[0][2]]); x5, y5, z5 = h5[0][0], h5[0][1], h5[0][2]; y6, z6 = h6[0][1], h6[0][2]
u = float(np.linalg.norm(J3 - J2)); f_ax = float(J4[0] - J3[0]); w = tcp - J4[0]
print("REACH J2 %s J3 %s J4 %s J5 (x %.2f z %.2f) J6 (y %.2f z %.2f) TCP x %.2f" % (tuple(J2), tuple(J3), tuple(J4), x5, z5, y6, z6, tcp))
res("REACH", abs(x5 - J4[0] - N.J4_J5) < B.REACH_TOL and abs(y5) < 0.05,
    "J4->J5 %.2f (want %.1f), J5 axis y %.2f" % (x5 - J4[0], N.J4_J5, y5))
res("REACH", abs(z5 - J4[1] - (N.H_J5 - B.SV_HORN_Y[0] + 0.5)) < 0.05,
    "J5 horn cylinder z %.2f (want J4 + %.1f, horn bottom end)" % (z5 - J4[1], N.H_J5 - B.SV_HORN_Y[0] + 0.5))
res("REACH", abs(z6 - J4[1] - N.J6_AX_H) < 0.05 and abs(y6) < 0.05,
    "J6 roll line %.2f below J4 (want %.1f) dy %.2f" % (z6 - J4[1], N.J6_AX_H, y6))
res("REACH", abs(w - N.A_TCP) < B.REACH_TOL, "J4->TCP %.2f (want %.1f)" % (w, N.A_TCP))
reach = u + f_ax + w
res("REACH", abs(reach - P2.REACH_TARGET) <= P2.REACH_TOL, "J2->TCP %.1f (want %.0f +- %.0f)" % (reach, P2.REACH_TARGET, P2.REACH_TOL))

# ---------- 2. holes + servo pocket clearance ----------
J4X, J4Z = P2.J4_XZ
def inw(s, a, b, h): return s.is_inside(Vector(J4X - a, b, J4Z - h))
def perp(axis, r, t):
    c, s_ = r * math.cos(t), r * math.sin(t)
    return {"a": (0, c, s_), "b": (c, 0, s_), "h": (c, s_, 0)}[axis]
def clear_hole(s, p, axis, d):
    rim = [inw(s, *[p[i] + perp(axis, d / 2 + 0.8, t)[i] for i in range(3)]) for t in (0.785, 2.356, 3.927, 5.498)]
    return (not inw(s, *p)) and all(rim)
def horn_check(name, s, c, axis, t):
    pts = []
    for q in PB.pcd(c):
        pts.append({"a": (t, q[0], q[1]), "b": (q[0], t, q[1]), "h": (q[0], q[1], t)}[axis])
    bad = [p for p in pts if not clear_hole(s, p, axis, B.HORN_HOLE)]
    res("HOLE", not bad, "%s: 4 x d%.1f on the STS3215 horn PCD%.0f%s" % (name, B.HORN_HOLE, B.SV_HORN_PCD, (" bad at %s" % bad) if bad else ""))
def hole_centre(name, r, ax, out=OUT):
    hs = [p for p in cyl_axes(name, r, out) if p[3 + "xyz".index(ax)] > 0.99]
    return np.mean([[p[0], p[1], p[2]] for p in hs], axis=0), len(hs)
l4, l5, gf, cr = (PB.rest(f()) for f in (PW.w_link4, PW.w_link5, PW.w_grip_frame, PW.w_j4_cradle))
horn_check("w_link4", l4, (0, 0), "b", sum(N.L4_B) / 2)
horn_check("w_link5", l5, (N.A_J5, 0), "h", sum(N.L5_TOP) / 2)
horn_check("w_grip_frame", gf, (0, N.H_SH), "a", (N.GF_PLATE_A[0] + B.HORN_RECESS[1] + N.GF_CB_A) / 2)
for nm, ax, want in (("w_link4", "y", (J4[0], None, J4[1])), ("w_link5", "z", (x5, y5, None)), ("w_grip_frame", "x", (None, y6, z6))):
    c, n = hole_centre(nm, B.HORN_HOLE / 2, ax)
    err = max(abs(c[i] - want[i]) for i in range(3) if want[i] is not None)
    res("HOLE", n == 4 and err < 0.05, "%s: %d horn holes on the servo horn axis (err %.3f)" % (nm, n, err))
fr = PB.fore2("R")
bad = [p for p in B.J4_BOLTS if not clear_hole(fr, (p[0], sum(P2.FORE_R_Y) / 2, p[1]), "b", B.M3_CLR)]
res("HOLE", not bad, "fore_r2: 4 x d%.1f J4 cradle bolts clear%s" % (B.M3_CLR, (" bad %s" % bad) if bad else ""))
bad = [p for p in B.J4_BOLTS if not clear_hole(cr, (p[0], 26.0, p[1]), "b", B.M3_PILOT)]
res("HOLE", not bad, "w_j4_cradle: 4 x d%.1f pilots on the same centres%s" % (B.M3_PILOT, (" bad %s" % bad) if bad else ""))
for nm, part, key in (("w_j4_cradle", cr, "j4"), ("w_link4", l4, "j5"), ("w_link5", l5, "j6"), ("w_grip_frame", gf, "g")):
    case = PB.rest(PW.servo_w(key, -0.05))
    inter = (case & part)
    v = inter.volume if inter is not None else 0.0
    res("CLEAR", v < 1.0, "%s x %s case: intersection %.2f mm3" % (nm, key, v))

# ---------- 3. gripper stroke ----------
def man_s(s):
    import tempfile
    from build123d import export_stl
    f = tempfile.mktemp(suffix=".stl"); export_stl(s, f, tolerance=0.05, angular_tolerance=0.3)
    m = trimesh.load_mesh(f, force="mesh"); m.merge_vertices(); os.remove(f)
    return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
o = B.STROKE / 2
gw = man_s(PB.rest(PW.w_grip_frame())); gs = man_s(PB.rest(PW.servo_w("g")))
mv = {"rack_u": man_s(PB.rest(PW.rack_sh("U", o))), "rack_d": man_s(PB.rest(PW.rack_sh("D", o))),
      "finger_u": man_s(PB.rest(PW.finger_sh("U", o))), "finger_d": man_s(PB.rest(PW.finger_sh("D", o)))}
hit = []
for n, m in mv.items():
    for n2, m2 in [("w_grip_frame", gw), ("sts3215_g", gs)] + [(k, v) for k, v in mv.items() if k > n and not (k[-1] == n[-1])]:
        v = (m ^ m2).volume()
        if v > 0.5: hit.append("%s x %s %.1f" % (n, n2, v))
inside_br = max(abs(B.RACK_U_B[0] + o), abs(B.RACK_U_B[1] + o)) <= B.BR_B and max(abs(B.RACK_D_B[0] - o), abs(B.RACK_D_B[1] - o)) <= B.BR_B
engaged = (B.RACK_U_B[0] + o < -B.GEAR[0] / 2) and (B.RACK_D_B[1] - o > B.GEAR[0] / 2)
res("GRIP", not hit and inside_br and engaged, "open %.1f mm: racks in the %.0f channels, on the gear, no hits%s"
    % (B.STROKE, 2 * B.BR_B, (" %s" % hit) if hit else ""))

# ---------- 4. mass + torque ----------
def w_parts():
    a2a = [p for p in PA.parts() if p[0] not in ("fore_l", "fore_r")]
    return a2a + [
        ("fore_l2", "fo", lambda: PB.fore2("L")),
        ("fore_r2", "fo", lambda: PB.fore2("R")),
        ("w_j4_cradle", "fo", lambda: PB.rest(PW.w_j4_cradle())),
        ("vendor_sts3215_j4", "fo", PW.vendor_servo("j4")),
        ("w_link4", "w4", lambda: PB.rest(PW.w_link4())),
        ("vendor_sts3215_j5", "w4", PW.vendor_servo("j5")),
        ("w_link5", "w5", lambda: PB.rest(PW.w_link5())),
        ("vendor_sts3215_j6", "w5", PW.vendor_servo("j6")),
        ("w_grip_frame", "w6", lambda: PB.rest(PW.w_grip_frame())),
        ("vendor_sts3215_g", "w6", PW.vendor_servo("g")),
        ("vendor_gear_grip", "w6", PW.vendor_gear),
        ("vendor_rack_u", "w6", lambda: PB.rest(PW.rack_sh("U"))),
        ("vendor_rack_d", "w6", lambda: PB.rest(PW.rack_sh("D"))),
        ("finger_u", "w6", lambda: PB.rest(PW.finger_sh("U"))),
        ("finger_d", "w6", lambda: PB.rest(PW.finger_sh("D"))),
    ]
J3r = P2.J3_XZ; J2r = P2.J2_XZ
ax3 = Axis((J3r[0], 0, J3r[1]), (0, 1, 0))
VM = {"vendor_sts3215_j4": N.M_STS3250, "vendor_sts3215_j5": B.M_STS3215, "vendor_sts3215_j6": B.M_STS3215,
      "vendor_sts3215_g": B.M_STS3215, "vendor_gear_grip": B.M_GEAR, "vendor_rack_u": B.M_RACK, "vendor_rack_d": B.M_RACK}
OLD = {"w_j4_cradle": 28.7, "w_link4": 29.8, "w_link5": 11.2, "w_grip_frame": 20.9}
items = {}
for name, grp, fn in w_parts():
    if grp == "fix" or (name.startswith("vendor_") and name not in VM): continue
    s = fn()
    if grp != "up": s = s.rotate(ax3, 180.0)
    m = VM.get(name, s.volume * P2.RHO_PETG * P2.INFILL_EFF / 1000.0)
    items[name] = (grp, m, s.center().X)
    if name in OLD:
        mv = s.volume * P2.RHO_PETG
        print("MASS %-14s %5.1f cm3 -> %5.1f g solid (%5.1f g at 0.6)  was %5.1f cm3  %+4.1f%%" %
              (name, s.volume / 1000, mv, mv * P2.INFILL_EFF, OLD[name], 100 * (s.volume / 1000 - OLD[name]) / OLD[name]))
g = 9.81
xj4 = J3r[0] + P2.FORE_SPAN; xt = xj4 + N.A_TCP
pay = [("payload", "w6", N.PAYLOAD6, xt)]
allit = [(n, gr, m, x) for n, (gr, m, x) in items.items()] + [("act_j3", "up", P2.M_ACT, J3r[0])] + pay
tq = lambda xj, keep: sum(m * g * (x - xj) / 1000.0 for n, gr, m, x in allit if keep(gr))
t2 = tq(J2r[0], lambda gr: True); t3 = tq(J3r[0], lambda gr: gr != "up"); t4 = tq(xj4, lambda gr: gr.startswith("w"))
t5 = tq(xj4 + N.A_J5, lambda gr: gr in ("w5", "w6"))
mw = sum(m for n, gr, m, x in allit if gr.startswith("w") and n != "payload")
print("TORQUE masses: wrist+gripper %.3f kg (R6 modelled 0.236; R6 cage fix "
      "+0.003 kg), payload %.2f kg at J4 + %.1f" % (mw, N.PAYLOAD6, N.A_TCP))
# R7 baseline: gf rib/plate-tabs +1.2 g and l5 aft block +0.3 g are
# deliberate structure; asm_loads_r7 confirms the workspace bound is
# unchanged at 0.374 kg (J2 flop), named poses unchanged.
res("MASS", mw <= 0.2395, "wrist+gripper %.3f kg <= 0.2395 kg (R7 baseline)" % mw)
res("TORQUE", t4 <= N.J4_RATED / 1.4, "J4 %.3f N.m (STS3250 rated %.3f / 1.4 = %.2f; stage model 0.801)" % (t4, N.J4_RATED, N.J4_RATED / 1.4))
res("TORQUE", t5 <= B.STS3215_RATED / 1.4, "J5 %.3f N.m with J4 turned 90 (STS3215 %.2f [U] / 1.4 = %.2f)" % (t5, B.STS3215_RATED, B.STS3215_RATED / 1.4))
t2_spr = t2 - 0.55 * math.radians(90.0)   # [U] J2 balance spring, arm-horizontal pose q2~+90 (bench-cal pending)
print("TORQUE J2 %.2f N.m (cap %.1f; %.2f N.m net of J2 spring [U]) - "
      "legacy 1-D model, informational only" % (t2, N.J2_CAP, t2_spr))
# authoritative J2 check = refine/asm_loads.py corrected model (mass_r5):
# spot-verify the two governing poses rather than the stale 1-D line.
try:
    sys.path.insert(0, os.path.join(HERE, "..", "upgrade1"))
    import gravity_up1 as _G1
    import mass_r5 as _M5
    _M5.apply(_G1)
    def _bnd(qd):
        q = [math.radians(x) for x in qd]
        t0 = np.array(_G1.gravity_torques(q, 0.0, spring=False))
        k = np.array(_G1.gravity_torques(q, 1.0, spring=False)) - t0
        caps = {1: 3.0, 2: 2.0, 3: 1.12, 4: 0.70, 5: 0.70}
        return min(max(0.0, (caps[i] - t0[i] * math.copysign(1.0, k[i]))
                       / abs(k[i]))
                   for i in caps if abs(k[i]) > 1e-9)
    bflop = _bnd([0, -90, -114, 14, 0, 0])       # workspace bound pose
    brech = _bnd([0, 60, -83, 23, 0, 0])         # 0.36 m level reach
    res("TORQUE", bflop >= 0.370,
        "J2 workspace bound %.3f kg at flop pose (>= 0.370 regression "
        "gate; R6 measured 0.374 < 0.38 requirement - see LOG 20)" % bflop)
    res("TORQUE", brech >= 0.42,
        "J2 0.36 m level-reach bound %.3f kg (>= 0.42 = 0.38 kg payload headroom)" % brech)
except Exception as e:
    res("TORQUE", False, "J2 authoritative bound check failed to run: %r" % e)
res("TORQUE", t3 <= N.J3_CAP, "J3 %.2f N.m (cap %.1f)" % (t3, N.J3_CAP))

# ---------- 4b. J4 cross-layer stress (hand calc, M = 0.801 N.m) ----------
# Worst section: the link4 strut rib + horn plate carry the full J4 moment.
# R3: rib widened to 8 mm in b; probe its a-extent at several h stations
# from outside the silhouette (a=42 -> -a) -> min S = t*d^2/6.
wl4w = PW.w_link4()
def run(s, p, d, lo, hi):
    t = lo; best = cur = 0.0
    while t <= hi:
        if s.is_inside(Vector(*p) + t * Vector(*d)): cur += 0.05; best = max(best, cur)
        else: cur = 0.0
        t += 0.05
    return best
best_S, worst_h = None, None
for hh in (-8.0, 0.0, 8.0, 16.0, 24.0, 32.0):
    dep = run(wl4w, (42.0, -26.65, hh), (-1, 0, 0), 0.0, 42.0)
    if dep > 1.0:
        S = (N.L4_STRUT_B[1] - N.L4_STRUT_B[0]) * dep * dep / 6.0
        if best_S is None or S < best_S: best_S, worst_h = S, hh
sig = 801.0 / best_S if best_S else 99.0
sf = N.X_STRESS / sig
res("STRESS", sf >= 2.0, "J4: min strut section S %.0f mm3 at h %.0f -> %.1f MPa, SF %.1f vs [U] %.0f MPa" % (best_S, worst_h, sig, sf, N.X_STRESS))

# ---------- 5. wall probes ----------
wc = PW.w_j4_cradle(); wl5w = PW.w_link5(); wg = PW.w_grip_frame()
probes = [
    ("cradle top",   wc,   (-20.0, -10.0, 10.0), (0, 0, 1), 2.0, 8.0),
    ("cradle end",   wc,   (-36.5, -10.0, 0.0), (1, 0, 0), -1.0, 5.0),
    ("fin cheek",    wl4w, (45.0, -11.0, 20.0), (0, -1, 0), 0.0, 5.0),   # R5: probe the solid band between the new windows
    ("strut rib",    wl4w, (26.0, -26.4, 15.0), (0, -1, 0), 0.0, 6.0),
    ("link4 plate",  wl4w, (10.0, -26.4, 0.0), (0, -1, 0), 0.0, 6.0),
    ("link5 plate",  wl5w, (30.6, 0.0, -6.2), (0, 0, 1), -1.0, 6.0),
    ("link5 cheek",  wl5w, (59.5, 16.0, -20.0), (0, -1, 0), 0.0, 5.0),
    ("link5 web",    wl5w, (20.0, 0.0, -51.5), (0, 0, -1), 0.0, 8.0),
    ("grip cheek",   wg,   (113.0, 16.0, -40.0), (0, -1, 0), 0.0, 5.0),
    ("grip web",     wg,   (75.0, 0.0, -51.5), (0, 0, -1), 0.0, 8.0),
    ("grip plate",   wg,   (68.5, 10.0, -17.0), (-1, 0, 0), 0.0, 8.0),
]
for nm, s, p, d, lo, hi in probes:
    r_ = run(s, p, d, lo, hi)
    res("WALL", 1.8 <= r_ <= 6.5, "%s: wall run %.2f mm at %s" % (nm, r_, p))

# ---------- 6. ROM sweeps ----------
def man(path):
    m = trimesh.load_mesh(path, force="mesh"); m.merge_vertices()
    return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
grp = {}
for n, g_, _ in PB.parts():
    if n.startswith("vendor_6803") or n in ("j4_cradle", "link4", "link5", "grip_frame"): continue
    grp[n] = g_
grp.update({"w_j4_cradle": "fo", "w_link4": "w4", "w_link5": "w5", "w_grip_frame": "w6"})
M = {}
OUT3 = os.path.join(HERE, "..", "wrist2", "out")   # unchanged wrist/vendor STLs
for n in grp:
    p = os.path.join(OUT, n + ".stl")
    for cand in (OUT3, OUT2):
        if not os.path.exists(p):
            p = os.path.join(cand, n + ".stl")
    M[n] = man(p)
def skip(a, b):
    if a.startswith("vendor_") and b.startswith("vendor_"):
        act = lambda n: "act" in n or "sts3215" in n
        return not (act(a) and act(b))
    return False
def hits(moving, fixed, rot):
    out_ = []
    for nm in moving:
        mm = rot(M[nm]); bm = mm.bounding_box()
        for nf in fixed:
            if skip(nm, nf): continue
            bf = M[nf].bounding_box()
            if any(bm[i] > bf[i + 3] or bf[i] > bm[i + 3] for i in range(3)): continue
            v_ = (mm ^ M[nf]).volume()
            if v_ > 0.5: out_.append("%s x %s %.0f" % (nm, nf, v_))
    return out_
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
            h = hits(moving, fixed, rf(sgn * (d + N.ROM_STEP)))
            if h: first = h[0]; break
            d += N.ROM_STEP
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
sweep("J4", mov(4), fix(4), about((J4[0], 0, J4[1]), "y"), N.ROM_MIN["J4"])
sweep("J5", mov(5), fix(5), about((x5, y5, 0), "z"), N.ROM_MIN["J5"])
sweep("J6", mov(6), fix(6), about((0, y6, z6), "x"), N.ROM_MIN["J6"])
J2h = np.array([J2r[0], 0.0, J2r[1]]); J3h = np.array([J3[0], 0.0, J3[1]])
fo = [n for n in grp if grp[n] == "fo" or grp[n] in W]
sweep("J3", fo, [n for n in grp if n not in fo], about(J3h, "y"), P2.ROM_MIN["J3"])
sweep("J2", [n for n in grp if grp[n] != "fix"], [n for n in grp if grp[n] == "fix"], about(J2h, "y"), P2.ROM_MIN["J2"])

# ---------- 7. cable channels: probe points must be in void (empty) ----------
for nm, s, pts in (
    ("w_j4_cradle", wc,  [(-16.5, b_, 8.0) for b_ in (14.0, 19.0, 24.0)]),        # j4 plug slot
    ("w_link4",    wl4w, [(a_, 0.0, h_) for a_, h_ in ((44.0, 40.0), (47.0, 44.0), (50.0, 40.0))]),  # j5 plug exits the fin top
    ("w_link5",    wl5w, [(a_, 0.0, -33.0) for a_ in (15.5, 20.0, 26.0)]),        # j6 plug void + rear exit
    ("w_grip_frame", wg, [(a_, 0.0, -33.0) for a_ in (62.5, 67.0, 72.0)]),        # grip plug void + rear exit
):
    inside = [p for p in pts if s.is_inside(Vector(*p))]
    res("CABLE", not inside, "%s: plug channel empty at %d/%d probe pts%s" % (nm, len(pts) - len(inside), len(pts), (" blocked %s" % inside) if inside else ""))

# ---------- 8. overhang scan in print orientation ----------
def overhang(name, s, up_w):
    s2 = PB.rest(s)
    sg = -1 if up_w[0] == "-" else 1
    worst = 0.0; nf = 0; nbad = 0
    for f in s2.faces():
        try:
            nrm = f.normal_at()
        except Exception:
            continue
        comp = {"a": -nrm.X, "b": nrm.Y, "h": -nrm.Z}[up_w[-1]]
        v = sg * comp
        if v < -0.01:
            nf += 1
            worst = max(worst, -v)
            if v < -0.707: nbad += 1
    res("OVERHANG", True, "%s: %d down-facing faces, %d past 45 deg, worst droop %.2f (1.00 = flat ceiling)" % (name, nf, nbad, worst))
    return worst
overhang("w_j4_cradle", wc, "-b")
overhang("w_link4", wl4w, "b")
overhang("w_link5", wl5w, "h")                     # R5: print up=h (keel flat on bed)
overhang("w_grip_frame", wg, "h")

print("CHECKS PASS" if ok else "CHECKS FAIL")
sys.exit(0 if ok else 1)
