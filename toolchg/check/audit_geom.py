"""toolchg/check/audit_geom.py - D11 independent geometry audit helpers.

Read-only: imports p_toolchg (unposed W-frame solids) and measures with
exact BRep thin-cylinder sections (no trimesh rtree needed).  Prints a
text report; writes nothing.

  A) per part: solids count + sliver volumes, bbox, volume, printed mass
  B) named wall sections -> material segments along probe cylinders
  C) overhang scan for the STATUS print orientation (down dir per part)
  D) independent coupling clearances (lug/bore, catch/spigot, faces,
     groove/key-notch depth, horn bolt pattern, pogo bore positions)

Run:  PYCAD toolchg/check/audit_geom.py   (from repo root)
"""
import os, sys, math
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "toolchg"))
sys.path.insert(0, os.path.join(ROOT, "cradlefix"))
sys.path.insert(0, os.path.join(ROOT, "cad", "arm2b"))
sys.path.insert(0, os.path.join(ROOT, "cad", "arm2"))
from build123d import Solid, Plane
import tc_params as T
import p_toolchg as PW
import ap6 as N
import ap2b as B

H_AX = T.H_AX

# ---------- BRep probe: intersect solid with a thin cylinder, report the
# segment spans along the probe axis ----------
def probe(s, origin, direction, r=0.04, lim=250.0):
    """returns list of (lo, hi) segment spans along `direction`."""
    d = np.asarray(direction, float)
    d = d / np.linalg.norm(d)
    o = np.asarray(origin, float)
    cyl = Solid.make_cylinder(r, lim, Plane(origin=tuple(o), z_dir=tuple(d)))
    try:
        i = s.intersect(cyl)
    except Exception:
        return []
    if i is None:
        return []
    out = []
    for sub in i.solids():
        bb = sub.bounding_box()
        pts = np.array([[x, y, z] for x in (bb.min.X, bb.max.X)
                        for y in (bb.min.Y, bb.max.Y)
                        for z in (bb.min.Z, bb.max.Z)])
        pj = pts @ d
        out.append((float(pj.min()), float(pj.max())))
    return sorted(out)

def fmt(spans):
    return " ".join("%.2f-%.2f (%.2f)" % (a, b, b - a) for a, b in spans)

def r_axial(s, b, h, a0=30.0):
    return probe(s, (a0, b, h), (1, 0, 0))

def r_radial(s, a, ph_deg, r0=0.0):
    p = math.radians(ph_deg)
    d = np.array([0.0, math.cos(p), math.sin(p)])
    o = np.array([a, d[1] * r0, H_AX + d[2] * r0])
    return probe(s, o, d)

def rdown(s, origin):
    return probe(s, origin, (0, 0, 1))

def mesh_of(s):
    v, f = s.tessellate(0.05)
    return trimesh.Trimesh(
        vertices=np.array([[p.X, p.Y, p.Z] for p in v]),
        faces=np.asarray(f, dtype=np.int64), process=False)

def solids_report(name, s):
    sols = list(s.solids())
    vols = sorted(x.volume for x in sols)
    print("%-13s solids=%d vols_mm3=%s" %
          (name, len(sols), ["%.2f" % v for v in vols]))

def overhang(name, m, down, bed_lo, bed_hi_tol=0.3):
    down = np.asarray(down, float)
    n = m.face_normals
    c = m.triangles.mean(axis=1)
    cdist = c @ down
    facing = n @ down                       # >0: faces the bed
    need = (facing > math.cos(math.radians(45.0))) & \
           (cdist > bed_lo + bed_hi_tol)
    flat = need & (facing > math.cos(math.radians(15.0)))
    hmax = float(cdist[need].max() - bed_lo) if need.any() else 0.0
    print("%-13s support-area(>45) %7.1f mm2 nfaces %4d  flat-down(>75) "
          "%6.1f mm2  max overhang height %.1f" %
          (name, float(m.area_faces[need].sum()), int(need.sum()),
           float(m.area_faces[flat].sum()), hmax))

BUILDERS = {
    "tc_master": PW.tc_master, "tc_plate": PW.tc_plate,
    "tool_grip": PW.tool_grip, "tool_pen": PW.tool_pen,
    "tc_vendor_g": PW.vendor_g, "tc_gear": PW.tc_gear,
    "tc_rack_u": lambda: PW.tc_rack_sh("U"),
    "tc_rack_d": lambda: PW.tc_rack_sh("D"),
    "tc_finger_u": lambda: PW.tc_finger_sh("U"),
    "tc_finger_d": lambda: PW.tc_finger_sh("D"),
    "tc_rack": PW.tc_rack,
}
P = {}
for nm, fn in BUILDERS.items():
    try:
        P[nm] = fn()
    except Exception as e:
        print(nm, "BUILD FAILED", e)

print("===== A) solids / volume / mass =====")
for nm, s in P.items():
    solids_report(nm, s)
    b = s.bounding_box()
    mass = s.volume * T.RHO_PETGCF * T.INFILL_EFF
    print("    bbox %.1f x %.1f x %.1f  vol %.2f cm3  print-mass %.1f g"
          % (b.size.X, b.size.Y, b.size.Z, s.volume / 1000, mass))

wg = trimesh.load_mesh(os.path.join(ROOT, "wrist2", "out",
                                    "w_grip_frame.stl"), force="mesh")
wg.merge_vertices()
parts = wg.split(only_watertight=False)
small = sorted(p.volume for p in parts if p.volume < 50)
print("w_grip_frame STL bodies=%d small-vols=%s" %
      (len(parts), ["%.2f" % v for v in small]))

print("===== B) wall sections (BRep probe segments) =====")
s = P["tc_master"]
print("-- tc_master")
print(" spigot wall a70 ph0 :", fmt(r_radial(s, 70.0, 0.0)))
print(" lug band a74.1 ph70 :", fmt(r_radial(s, 74.1, 70.0)))
for r in (14.0, 15.0, 16.0, 17.0):
    p = math.radians(70.0)
    print(" lug axial r%.0f ph70:" % r,
          fmt(r_axial(s, r * math.cos(p), H_AX + r * math.sin(p), 60.0)))
print(" plate axial r14 ph0:", fmt(r_axial(s, 14.0, H_AX, 50.0)))
p = math.radians(45.0)
for rr in (7.0, 10.0, 14.0):
    print(" plate axial r%.0f ph45:" % rr,
          fmt(r_axial(s, rr * math.cos(p), H_AX + rr * math.sin(p), 50.0)))

s = P["tc_plate"]
print("-- tc_plate")
print(" ring wall a70 ph0:", fmt(r_radial(s, 70.0, 0.0)))
print(" groove floor a74.75 ph0:", fmt(r_radial(s, 74.75, 0.0)))
for dph in (-6.0, -3.0, 0.0, 3.0, 6.0):
    print(" groove floor a74.75 ph270%+.0f:" % dph,
          fmt(r_radial(s, 74.75, 270.0 + dph)))
for aa in (72.6, 74.75, 76.9):
    print(" groove floor a%.2f ph270:" % aa, fmt(r_radial(s, aa, 270.0)))
print(" floor a-axial r5:", fmt(r_axial(s, 0.0, H_AX + 5.0, 60.0)))
for rr in (13.5, 14.0, 15.0, 16.0, 17.0, 17.5):
    p = math.radians(118.0)
    print(" catch axial r%.1f ph118:" % rr,
          fmt(r_axial(s, rr * math.cos(p), H_AX + rr * math.sin(p), 60.0)))
p = math.radians(110.0)
print(" detent zone a-axial r19 ph110:",
      fmt(r_axial(s, 19.0 * math.cos(p), H_AX + 19.0 * math.sin(p), 60.0)))
print(" detent bore radial a74 ph110:", fmt(r_radial(s, 74.0, 110.0)))

s = P["tool_grip"]
print("-- tool_grip")
print(" neck radial a79.5 ph0:", fmt(r_radial(s, 79.5, 0.0)))
print(" neck radial a79.5 ph270:", fmt(r_radial(s, 79.5, 270.0)))
print(" keel a95 down-axial:",
      fmt(probe(s, (95.0, 0.0, -10.0), (0, 0, -1))))
print(" cheek b-axial a95 h-40:",
      fmt(probe(s, (95.0, -20.0, -40.0), (0, 1, 0))))
print(" cheek b-axial a110 h-40:",
      fmt(probe(s, (110.0, -20.0, -40.0), (0, 1, 0))))
print(" cage top a110 down-axial:",
      fmt(probe(s, (110.0, 0.0, -10.0), (0, 0, -1))))

s = P["tool_pen"]
print("-- tool_pen")
print(" barrel radial a120 ph0:", fmt(r_radial(s, 120.0, 0.0)))
print(" barrel radial a136 ph0:", fmt(r_radial(s, 136.0, 0.0)))
print(" barrel radial a136 ph120:", fmt(r_radial(s, 136.0, 120.0)))
print(" neck radial a79.5 ph0:", fmt(r_radial(s, 79.5, 0.0)))
print(" bore a-axial:", fmt(r_axial(s, 0.0, H_AX, 60.0)))

s = P["tc_rack"]
print("-- tc_rack (world frame)")
yc, az, x0 = T.RACK_AXIS_Y, T.RACK_AXIS_Z, T.RACK_PLATE_X
for dy in (-91.0, -68.0, -46.0, -22.0, 0.0, 22.0, 46.0, 68.0, 91.0):
    print(" rack z-axial x145 y%+d:" % int(dy + 80),
          fmt(rdown(s, (x0, yc + dy, az - 10.0))))
print(" rack base z-axial x145 y-160:",
      fmt(rdown(s, (x0, yc - 80.0, 2.0))))
print(" cradle plate z-axial x177 y-80 from z50:",
      fmt(rdown(s, (x0 + 32.0, yc, 50.0))))
print(" fork plate x-axial slot-edge yk-20.4 z110:",
      fmt(probe(s, (x0 - 10.0, yc + 23.0 - 20.4, az - 19.5), (1, 0, 0))))
print(" key tab z-axial at slot k2 centre:",
      fmt(rdown(s, (x0, yc + 23.0, az - 22.0))))
print(" key tab z-axial from below seat:",
      fmt(rdown(s, (x0, yc + 23.0, az - 24.0))))

print("===== C) overhang (STATUS orientations) =====")
A_DOWN = np.array([-1.0, 0.0, 0.0])
for nm in ("tc_master", "tc_plate", "tool_grip", "tool_pen", "tc_vendor_g",
           "tc_gear", "tc_rack_u", "tc_rack_d", "tc_finger_u",
           "tc_finger_d"):
    s = P[nm]
    mm = mesh_of(s)
    pts = mm.vertices @ A_DOWN
    overhang(nm + "(-a dn)", mm, A_DOWN, float(pts.min()))
mm = mesh_of(P["tool_grip"])
pts = mm.vertices @ np.array([0.0, 0.0, 1.0])
overhang("tool_grip(+h dn)", mm, (0.0, 0.0, 1.0), float(pts.min()))
pts = mm.vertices @ np.array([0.0, 0.0, -1.0])
overhang("tool_grip(-h dn)", mm, (0.0, 0.0, -1.0), float(pts.min()))
mm = mesh_of(P["tc_rack"])
overhang("tc_rack(-z dn)", mm, (0.0, 0.0, -1.0),
         float(mm.bounds[0][2]))

print("===== D) coupling clearances (independent measure) =====")
sm, sp = P["tc_master"], P["tc_plate"]

def rmax(s, a0, a1):
    mm = mesh_of(s)
    v = mm.vertices
    sel = (v[:, 0] >= a0) & (v[:, 0] <= a1)
    rr = np.hypot(v[sel][:, 1], v[sel][:, 2] - H_AX)
    return rr

def rmin(s, a0, a1, rlo=0.0):
    mm = mesh_of(s)
    v = mm.vertices
    sel = (v[:, 0] >= a0) & (v[:, 0] <= a1)
    rr = np.hypot(v[sel][:, 1], v[sel][:, 2] - H_AX)
    return rr[rr > rlo]

print(" master lug outer r verts a73-75.3: max %.2f (claim 17.3)"
      % rmax(sm, 73.0, 75.3).max())
print(" plate bore/groove-band verts a74.1+-0.2: min %.2f (claim 18.2)"
      % rmin(sp, 73.9, 74.3, 15.0).min())
print(" spigot OD verts a69-72: max %.2f (claim 13.0)"
      % rmax(sm, 69.5, 72.0).max())
print(" catch inner verts a69.5-72.2: min %.2f (claim 13.2)"
      % rmin(sp, 69.5, 72.2, 5.0).min())
p70 = math.radians(70.0)
print(" lug span @r15 ph70:",
      fmt(r_axial(sm, 15.0 * math.cos(p70), H_AX + 15.0 * math.sin(p70),
                  60.0)), "(claim lug -a face 72.4)")
p118 = math.radians(118.0)
print(" catch span @r15 ph118:",
      fmt(r_axial(sp, 15.0 * math.cos(p118), H_AX + 15.0 * math.sin(p118),
                  60.0)), "(claim catch face 72.2)")
p0 = math.radians(0.0)
print(" spigot tip @r5:", fmt(r_axial(sm, 5.0, H_AX, 60.0)),
      "(claim tip 75.8)")
print(" socket floor @r5:", fmt(r_axial(sp, 0.0, H_AX + 5.0, 60.0)),
      "(claim floor face 76.0)")
print(" horn PCD %.1f ang %s hole %.1f cb %s recess %s" %
      (B.SV_HORN_PCD, B.HORN_ANG, B.HORN_HOLE, B.HORN_CB, B.HORN_RECESS))
print(" TC_CB_A %.1f == GF_CB_A %.1f" % (T.TC_CB_A, N.GF_CB_A))
for r, ph in zip(T.TC_PIN_R, T.TC_PIN_PH):
    pr = math.radians(ph)
    x, y = r * math.cos(pr), H_AX + r * math.sin(pr)
    print(" pogo bore r%.0f ph%.0f:" % (r, ph), fmt(r_axial(sp, x, y, 60.0)),
          "(empty = bore present)")
