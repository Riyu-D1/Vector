"""lighten/build_lighten.py - D9 hybrid lightening: stock link plates with
safe window/pocket cuts.

Replicates cad/arm2/p_arm2.py upper_out()/upper_back() EXACTLY - same calls,
same params - except the single stock stadium slot (ap2.window) is replaced
by this stage's window set. Runs in the reBot rest frame like the source,
then PA.pose(..., "up") applies the same home pose as build_arm2b.py.

Window set (rest frame, plate is the stadium in XZ at z=143.5, span
J2=-20 -> J3=106.7, half-height +-30.5, thickness y):
  - two rectangular openings x [14.5,38] and [48.8,72.3], z 143.5+-22,
    corner fillet R8 (stage: fillets >= 3 mm)
  - mid rib x 38..48.8 (10.8 mm) + side rails z |dz| 22..30.5 (8.5 mm)
  - every cutter point stays >= 33 mm from both joint axes (ring lands,
    M3 PCD lands r25, bearing/bore interfaces all inside r33)
Variant "wp" adds blind pockets 1.6 mm deep from the OUTBOARD face over the
rails + mid rib (web bottom 4.0 -> 2.4 mm = min wall), edges inset 1.0 mm.

Outputs (lighten/out/): <part>.stl/.step  = untouched stock (reference),
                        <part>_l.stl/.step = windows-only,
                        <part>_lp.stl/.step = windows + pockets.
Run:  ~/Vector-wt/cradlefix/.venv/bin/python lighten/build_lighten.py
"""
import os, sys, math
import trimesh
from build123d import (Solid, Plane, export_stl, export_step)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "out")
sys.path.insert(0, os.path.join(ROOT, "cad", "arm2"))
import ap2 as P
import p_arm2 as PA
A = P.A
os.makedirs(OUT, exist_ok=True)

MIN = PA.MIN
cyl_y, box, pcd_xz = PA.cyl_y, PA.box, PA.pcd_xz

# ---------------- window parameters (rest frame, mm) ----------------
WIN_X = [(14.5, 38.0), (48.8, 72.3)]      # two openings (x extents)
WIN_ZH = 22.0                              # z half-height about 143.5
FILLET_R = 8.0                             # corner fillet (>= 3 stage)
KEEP_R = 33.0                              # min distance to a joint axis
POCKET_D = 1.6                             # blind pocket depth (wp variant)
POCKET_IN = 1.0                            # pocket inset inside material
ZC = 143.5
# v2 (_l2): same openings, shallow z +-10 -> ~20.5 mm side rails + mid rib
# preserved (v1's 8.5 mm rails lost the shear web: +81% deflection).
WIN2_ZH = 10.0
FILLET2_R = 6.0


def rrect(x0, x1, z0, z1, r, y0, y1):
    """rounded-rect cutter: 4 corner cylinders + cross of two boxes (XZ)."""
    s = box(x0 + r, x1 - r, y0, y1, z0, z1) + \
        box(x0, x1, y0, y1, z0 + r, z1 - r)
    for cx in (x0 + r, x1 - r):
        for cz in (z0 + r, z1 - r):
            s = s + cyl_y(cx, cz, 2 * r, y0, y1)
    return s


def windows(y0, y1, zh=WIN_ZH, fr=FILLET_R):
    s = None
    for x0, x1 in WIN_X:
        c = rrect(x0, x1, ZC - zh, ZC + zh, fr, y0 - 1, y1 + 1)
        s = c if s is None else s + c
    return s


def pockets(yface, inward):
    """blind pockets on the rails + rib, from the outboard face.
    yface = plate outer y; inward = +1 if material lies toward +y."""
    y0 = yface - POCKET_D if inward < 0 else yface
    y1 = yface if inward < 0 else yface + POCKET_D
    cuts = []
    # side rails z in [113,121.5] / [165.5,174] over the window x-span
    for z0, z1 in ((113.0, ZC - WIN_ZH), (ZC + WIN_ZH, 174.0)):
        cuts.append(box(WIN_X[0][0] + POCKET_IN, WIN_X[1][1] - POCKET_IN,
                        y0, y1, z0 + POCKET_IN, z1 - POCKET_IN))
    # mid rib (between the two windows)
    cuts.append(box(WIN_X[0][1] + POCKET_IN, WIN_X[1][0] - POCKET_IN,
                    y0, y1, ZC - WIN_ZH + POCKET_IN, ZC + WIN_ZH - POCKET_IN))
    s = cuts[0]
    for c in cuts[1:]:
        s = s + c
    return s


# ---------------- plates: p_arm2.py verbatim minus the stock window ----
def upper_out_l(pocket=False, v2=False):
    """p_arm2.upper_out() with this stage's windows [+ optional pockets].

    v2 (_l2) KEEPS the stock neutral-axis slot and only adds the two
    shallow extension windows; v1 (_l/_lp) replaced the stock slot."""
    y0, y1 = P.UP_OUT_Y
    s = PA.stadium(y0, y1, P.UP_R) - windows(
        y0, y1, *( (WIN2_ZH, FILLET2_R) if v2 else () ))
    if v2:
        s = s - PA.window(y0, y1)
    for c in (P.J2_XZ, P.J3_XZ):
        s = s + (cyl_y(c[0], c[1], 2 * P.UP_R, *P.UP_COLLAR_Y))
        s = s - cyl_y(c[0], c[1], P.RING_D, y0 - 1, P.UP_COLLAR_Y[1] + 1)
    if pocket:
        s = s - pockets(y0, +1)              # outboard face = y0 (-Y side)
    return s


def upper_back_l(pocket=False, v2=False):
    """p_arm2.upper_back() with this stage's windows [+ optional pockets].

    v2 (_l2) keeps the stock neutral-axis slot (see upper_out_l)."""
    y0, y1 = P.UP_BACK_Y
    s = PA.stadium(y0, y1, P.UP_R) - windows(
        y0, y1, *( (WIN2_ZH, FILLET2_R) if v2 else () ))
    if v2:
        s = s - PA.window(y0, y1)
    h = (P.CSK_D - P.M3_CLR) / 2
    for c in (P.J2_XZ, P.J3_XZ):
        s = s - cyl_y(c[0], c[1], P.UP_BACK_HOLE, y0 - 1, y1 + 1)
        for x, z in pcd_xz(c, A.LINK_PCD, PA.link_angles()):
            cone = Solid.make_cone(P.M3_CLR / 2, P.CSK_D / 2, h,
                                   Plane(origin=(x, y1 - h, z),
                                         z_dir=(0, 1, 0)))
            s = s - cyl_y(x, z, P.M3_CLR, y0 - 1, y1 + 1) - cone - \
                cyl_y(x, z, P.CSK_D, y1, y1 + 1)
    if pocket:
        s = s - pockets(y1, -1)              # outboard face = y1 (+Y side)
    return s


# ---------------- keep-out / sanity checks ----------------
def check_keepout():
    """every window corner/edge must stay >= KEEP_R of both joint axes."""
    worst = 1e9
    for x0, x1 in WIN_X:
        for z in (ZC - WIN_ZH, ZC + WIN_ZH):
            for x in (x0, x1):
                for jx, jz in (P.J2_XZ, P.J3_XZ):
                    worst = min(worst, math.hypot(x - jx, z - jz))
        # perpendicular foot inside the edge
        for x in (x0, x1):
            pass
        for jx, jz in (P.J2_XZ, P.J3_XZ):
            for z in (ZC - WIN_ZH, ZC + WIN_ZH):
                if x0 <= jx <= x1:
                    worst = min(worst, abs(z - jz))
            for x in (x0, x1):
                if ZC - WIN_ZH <= jz <= ZC + WIN_ZH:
                    worst = min(worst, abs(x - jx))
    assert worst >= KEEP_R, worst
    print("keep-out check: closest cutter point %.1f mm from a joint axis "
          "(>= %.0f) OK" % (worst, KEEP_R))


def report(tag, s):
    b = s.bounding_box()
    stl = os.path.join(OUT, tag + ".stl")
    for at in (0.3, 0.5, 0.4, 0.2, 0.6):
        export_stl(s, stl, tolerance=0.05, angular_tolerance=at)
        m = trimesh.load_mesh(stl, force="mesh"); m.merge_vertices()
        if m.is_watertight:
            break
    export_step(s, os.path.join(OUT, tag + ".step"))
    print("%-16s bbox %.1f x %.1f x %.1f  vol %.2f cm3  wt %s"
          % (tag, b.size.X, b.size.Y, b.size.Z, s.volume / 1000,
             m.is_watertight))
    return s.volume


check_keepout()
# v2 keep-out check: window z-extent +-10, corners >= r6 -> recompute
worst = 1e9
for x0, x1 in WIN_X:
    for z in (ZC - WIN2_ZH, ZC + WIN2_ZH):
        for x in (x0, x1):
            for jx, jz in (P.J2_XZ, P.J3_XZ):
                worst = min(worst, math.hypot(x - jx, z - jz))
print("v2 keep-out: closest cutter point %.1f mm (>= %.0f)" % (worst, KEEP_R))
RHO, INFILL = 1.27e-3, 0.6
import sys as _s
_only = _s.argv[1] if len(_s.argv) > 1 else None
for name, mk in (("upper_out", PA.upper_out), ("upper_back", PA.upper_back)):
    v0 = PA.pose(mk(), "up").volume
    if _only in (None, "stock"):
        report(name, PA.pose(mk(), "up"))
    for tag, pk, v2 in (("_l", False, False), ("_lp", True, False),
                        ("_l2", False, True)):
        if _only and tag.strip("_") != _only.strip("_"):
            continue
        fn = upper_out_l if name == "upper_out" else upper_back_l
        v = report(name + tag, PA.pose(fn(pk, v2=v2), "up"))
        dv = (v0 - v) * RHO
        print("   %-16s removed %.2f cm3 = %.2f g solid / %.2f g print"
              % (name + tag, (v0 - v) / 1000, dv, dv * INFILL))
print("BUILD DONE -> %s" % OUT)
