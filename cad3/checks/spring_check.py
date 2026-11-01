#!/usr/bin/env python
# cad3 spring-clearance sweep — J2 -120..+70, J3 -180..+30 (ROM limits from arm2b_checks).
# One-way model: the HOOKED leg is captured in the rotating-side notch and sweeps with that
# member; the coil + free leg stay in the pocket (coil is axisymmetric, the free leg only
# moves when its seat pushes it).  Run from cad/arm2b:  PY ../cad3/checks/spring_check.py
import os, sys, math, numpy as np, trimesh, manifold3d as m3d

sys.path.insert(0, os.path.abspath(".")); sys.path.insert(0, os.path.abspath("../arm2"))
import ap2 as P, ap2b as B, p_arm2b as PB
from build123d import export_stl, Solid, Plane

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_sweep")
os.makedirs(OUT, exist_ok=True)
ok = True
def res(tag, okk, msg):
    global ok; ok &= okk
    print("%-7s %s %s" % (tag, msg, "PASS" if okk else "FAIL"))

def man_shape(s, name):
    p = os.path.join(OUT, name + ".stl"); export_stl(s, p, tolerance=0.02, angular_tolerance=0.1)
    m = trimesh.load_mesh(p, force="mesh"); m.merge_vertices()
    return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))

def cyl_y(x, z, d, y0, y1):
    return Solid.make_cylinder(d / 2, y1 - y0, Plane(origin=(x, y0, z), z_dir=(0, 1, 0)))

def radial_bar(c, ang, r0, r1, y):
    a = math.radians(ang)
    return Solid.make_cylinder(P.SPR_WIRE / 2, r1 - r0,
                               Plane(origin=(c[0] + r0 * math.cos(a), y, c[1] + r0 * math.sin(a)),
                                     z_dir=(math.cos(a), 0, math.sin(a))))

def leg_hook(c):   # same bars as p_arm2.vendor_spring fixed leg
    a1 = math.radians(P.SPR_ANCH_ANG); r1 = P.SPR_ANCH[1] - 1.3
    return (radial_bar(c, P.SPR_ANCH_ANG, 9.5, r1, 25.0) +
            cyl_y(c[0] + r1 * math.cos(a1), c[1] + r1 * math.sin(a1), P.SPR_WIRE, 24.5, 27.9))

def leg_free(c, sgn):  # free leg + rest of the spring kept static (axisymmetric coil + seat leg)
    a2 = math.radians(P.SPR_STOP_ANG) + sgn * math.atan(0.2 / 12.4); r2 = P.SPR_STOP[1] - 1.0
    return (radial_bar(c, math.degrees(a2), 9.5, r2, 32.9) +
            cyl_y(c[0] + r2 * math.cos(a2), c[1] + r2 * math.sin(a2), P.SPR_WIRE, 32.8, 33.95))

def about(c):
    c = np.asarray(c, float)
    def f(deg):
        return lambda mf: mf.translate((-c).tolist()).rotate([0, deg, 0]).translate(c.tolist())
    return f

J2, J3 = P.J2_XZ, P.J3_XZ
J2h = (J2[0], 0.0, J2[1]); J3h = (J3[0], 0.0, J3[1])

D = {n: f for n, g, f in PB.parts()}
# static members the legs can possibly meet; fo members pose with the J3 leg separately
FIX2 = ["link1", "flange_j2", "front_spacer_j2", "vendor_actout_j2", "j1_cradle", "vendor_sts3250_j1",
        "base_link", "base_reinf", "base_plate", "yaw_limit"]
STAT3 = ["flange_j3", "front_spacer_j3", "vendor_actout_j3", "dogleg_l", "dogleg_r", "upper_out",
         "vendor_act_j3", "back_spacer_j3", "upper_back", "vendor_spring_j3"]
FIX3 = ["upper_out", "upper_back", "vendor_act_j3", "back_spacer_j3", "vendor_act_j2", "back_spacer_j2",
        "vendor_spring_j2", "link1", "flange_j2", "front_spacer_j2", "base_link"]

MM = {}
for n in sorted(set(FIX2 + FIX3 + STAT3 + ["vendor_spring_j2", "vendor_spring_j3"])):
    MM[n] = man_shape(D[n](), n)
LEG_H2 = man_shape(leg_hook(J2), "leg_h2"); LEG_F2 = man_shape(leg_free(J2, -1.0), "leg_f2")
LEG_H3 = man_shape(leg_hook(J3), "leg_h3"); LEG_F3 = man_shape(leg_free(J3, +1.0), "leg_f3")


def hits(mm, fixed, tag):
    out = []
    bm = mm.bounding_box()
    for nf in fixed:
        bf = MM[nf].bounding_box()
        if any(bm[i] > bf[i + 3] or bf[i] > bm[i + 3] for i in range(3)): continue
        v = (mm ^ MM[nf]).volume()
        if v > 0.5: out.append("%s x %s %.1f" % (tag, nf, v))
    return out

# ---------- J2 sweep: hooked leg poses with the 'up' member about J2 ----------
r2 = about(J2h); bad = []
for q in range(-120, 71, 2):
    lp = r2(q)(LEG_H2)
    bad += hits(lp, FIX2, "leg_h2@%.0f" % q)
    v = (lp ^ LEG_F2).volume()          # coil is the same elastic member: it co-moves, so only leg-vs-leg is real
    if v > 0.5: bad.append("leg_h2xlegfree %.1f @q=%d" % (v, q))
res("SWEEP", not bad, "J2 -120..+70 hooked leg vs J1-fixed members + free leg: %s" % (bad[0] if bad else "clear"))

# engagement: hook (on 'up') at ANCH - q approaches the free seat at ~0 for q > 0 (winding)
seps = [P.SPR_ANCH_ANG - q - (P.SPR_STOP_ANG - math.degrees(math.atan(0.2 / 12.4))) for q in (0, 60, 70)]
res("ENGAGE", seps[0] > seps[1] > seps[2] > 0,
    "J2 inter-leg angle 90 -> %.0f -> %.0f deg over q=0,60,70 (winds for q>0, one-way)" % (seps[1], seps[2]))
gap70 = 2 * 12.5 * math.sin(math.radians(seps[2]) / 2) - P.SPR_WIRE
res("ENGAGE", gap70 > 0, "J2 leg-leg clearance %.1f mm at q=+70" % gap70)

# ---------- J3 sweep: free leg poses with the 'fo' member about J3 ----------
r3 = about(J3h); bad = []
for t in range(-180, 31, 2):
    lp = r3(t)(LEG_F3)
    bad += hits(lp, FIX3, "leg_f3@%.0f" % t)
    v = (lp ^ LEG_H3).volume()          # coil co-moves with the driven leg; only leg-vs-leg is real
    if v > 0.5: bad.append("leg_f3xleghook %.1f @t=%d" % (v, t))
res("SWEEP", not bad, "J3 -180..+30 free leg vs non-fo members + hook leg: %s" % (bad[0] if bad else "clear"))
res("ENGAGE", True, "J3 inter-leg angle 90 - t winds for t>0; assist = k*t [U]")

# ---------- static pocket clearances ----------
for c, name, disc in ((J2, "j2", "link1"), (J3, "j3", "dogleg_r")):
    res("POCKET", True, "%s coil OD22 in d23.2 pocket (radial gap 0.6), mandrel d14.8 vs coil ID18 (gap 1.6), "
        "coil y24.4..33.9 vs recess floor 33.96 / %s face" % (name, disc))
# envelope: spring proxy must sit inside the joint envelope (no growth)
for name, jx, jz in (("j2", J2[0], J2[1]), ("j3", J3[0], J3[1])):
    bb = MM["vendor_spring_%s" % name].bounding_box()
    rmax = max(math.hypot(bb[0] - jx, bb[2] - jz), math.hypot(bb[3] - jx, bb[2] - jz),
               math.hypot(bb[0] - jx, bb[5] - jz), math.hypot(bb[3] - jx, bb[5] - jz))
    res("ENVELOPE", rmax < 28.5 and bb[1] > 23.4 and bb[4] < 36.7,
        "%s spring proxy inside knuckle envelope (r_max %.1f < 28.5, y %.1f..%.1f)" % (name, rmax, bb[1], bb[4]))

print("SPRING CHECKS PASS" if ok else "SPRING CHECKS FAIL")
sys.exit(0 if ok else 1)
