"""wrist/p_wrist5.py - D5 geometry: the 4 structural wrist parts redrawn as thin
contoured shells (ap5.py numbers).  Same W frame and the same builder/pose flow as
cad/arm2b/p_arm2b.py: builders return W solids, parts() wraps them with rest().
Servo pockets, horn holes, bolt pilots, rack cage and all vendor parts reuse the
TESTED p_arm2b helpers unchanged - nothing here redefines an interface."""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "cad", "arm2b"))
sys.path.insert(0, os.path.join(HERE, "..", "cad", "arm2"))
from build123d import (Plane, Pos, Polygon, RectangleRounded, extrude)
import ap2 as P2
import p_arm2 as PA
import ap2b as B
import p_arm2b as PB
import ap5 as N

box = PA.box
cyl = PB.cyl
rest = PB.rest
pocket = PB.pocket
horn_holes = PB.horn_holes

# ---------- profile helpers ----------
def _ah(b):
    return Plane(origin=(0, b, 0), x_dir=(1, 0, 0), y_dir=(0, 0, 1))   # sketch XY -> (a,h)

def _bh(a):
    return Plane(origin=(a, 0, 0), x_dir=(0, 1, 0), y_dir=(0, 0, 1))   # sketch XY -> (b,h)

def _ab(h):
    return Plane(origin=(0, 0, h), x_dir=(1, 0, 0), y_dir=(0, 1, 0))   # sketch XY -> (a,b)

def ah(b, a0, a1, h0, h1, r):
    return _ah(b) * Pos((a0 + a1) / 2, (h0 + h1) / 2, 0) * RectangleRounded(a1 - a0, h1 - h0, r)

def bh(a, b0, b1, h0, h1, r):
    return _bh(a) * Pos((b0 + b1) / 2, (h0 + h1) / 2, 0) * RectangleRounded(b1 - b0, h1 - h0, r)

def ab(h, a0, a1, b0, b1, r):
    return _ab(h) * Pos((a0 + a1) / 2, (b0 + b1) / 2, 0) * RectangleRounded(a1 - a0, b1 - b0, r)

def poly_ah(b, pts):
    return _ah(b) * Polygon(*pts, align=None)

def xb(face, b0, b1):
    return extrude(face, amount=b1 - b0, dir=(0, 1, 0))

def xa(face, a0, a1):
    return extrude(face, amount=a1 - a0, dir=(1, 0, 0))

def cleat_a(b, h, a_face):
    """mushroom cable-tie cleat on an a-normal face (peg reaches -a)"""
    return cyl((b, h), 2.6, "a", a_face - 3.0, a_face + 0.5) + cyl((b, h), 4.4, "a", a_face - 4.0, a_face - 3.0)

def cleat_b(a, h, b_face):
    """mushroom cable-tie cleat on a b-normal face (peg reaches -b)"""
    return cyl((a, h), 2.6, "b", b_face - 3.0, b_face + 0.5) + cyl((a, h), 4.4, "b", b_face - 4.0, b_face - 3.0)

# ---------- w_j4_cradle: rounded sleeve + pillar bolt plate ----------
def w_j4_cradle():
    s = xb(ah(N.CR_B[0], *N.CR_OUT), *N.CR_B)
    s = s + xb(ah(N.CR_PLATE_B[0], *N.CR_PLATE), *N.CR_PLATE_B)
    for a_, h_ in B.J4_BOLTS:
        s = s + cyl((a_, h_), N.CR_BOSS_D, "b", N.CR_BOSS_B[0], N.CR_BOSS_B[1])
    s = s - pocket("j4")
    a0, a1, b0, b1, h0, h1 = N.CR_SLOT
    s = s - box(a0, a1, b0, b1, h0, h1)
    for a_, h_ in B.J4_BOLTS:
        s = s - cyl((a_, h_), B.M3_PILOT, "b", 24.55, 33.55)
    a0, a1, b0, b1, h0, h1 = N.CR_GROOVE
    s = s - box(a0, a1, b0, b1, h0, h1)
    return s

# ---------- w_link4: horn plate + silhouette spine + J5 shell tub ----------
def w_link4():
    s = xb(ah(B.L4_B[0], *N.L4_PLATE), *B.L4_B)                      # horn plate
    s = s + xb(poly_ah(B.L4_B[0], N.L4_RIB), *B.L4_B)                # spine rib
    s = s + xb(ah(B.L4_B[0], *N.L4_PANEL), *B.L4_B)                  # cage back panel
    tube = ah(N.L4_TUBE_B[0], *N.L4_PANEL) - ah(N.L4_TUBE_B[0], *N.L4_BORE)
    s = s + xb(tube, *N.L4_TUBE_B)                                   # 2 mm cage wall
    s = s - pocket("j5")                                             # case + plug + horn
    for a0, a1, b0, b1, h0, h1 in N.L4_WIN:                          # side windows
        s = s - box(a0, a1, b0, b1, h0, h1)
    s = s - horn_holes((0, 0), "b", B.L4_B[0], B.L4_B[1],
                       B.L4_B[0] - 1, B.L4_B[0] + B.HORN_CB[1],
                       B.L4_B[1] - B.HORN_RECESS[1], B.L4_B[1] + 1)
    for p in N.L4_CLEATS:
        s = s + cleat_a(p[0], p[1], N.L4_PANEL[0])
    return s

# ---------- w_link5: J5 horn plate + J6 U-channel cage ----------
def w_link5():
    h0, h1 = B.L5_TOP
    s = xa(bh(N.L5_TUBE[0], *N.L5_PROF), *N.L5_TUBE)                 # cage shell
    s = s - xa(bh(25.05, *N.L5_BORE), 25.05, N.L5_TUBE[1] + 1)       # bore: floor at -a end
    pl = N.L5_PLUG
    s = s - box(pl[0], pl[1], pl[2], pl[3], pl[4], pl[5])            # plug exit slot
    s = s + extrude(ab(h0, *N.L5_PLATE), amount=h1 - h0, dir=(0, 0, 1))   # J5 horn plate
    s = s - pocket("j6")                                             # case + plug + horn
    a0, a1, w0, w1, r = N.L5_WIN                                     # cheek windows
    s = s - box(a0, a1, -16.0, 16.0, w0, w1)
    s = s - horn_holes((B.A_J5, 0), "h", h0, h1, h0 - 1, h0 + B.HORN_CB[1],
                       h1 - B.HORN_RECESS[1], h1 + 1)
    for p in N.L5_CLEATS:
        s = s + cleat_a(p[0], p[1], N.L5_TUBE[0])
    return s

# ---------- w_grip_frame: J6 horn plate + servo cheeks + rack cage ----------
def w_grip_frame():
    a0, a1 = B.GB_A
    s = xa(bh(a0, *N.GF_PLATE), a0, a1)                              # horn plate (rounded)
    for b0, b1 in ((N.GF_CHEEK_B[0], N.GF_CHEEK_B[1]), (N.GF_CHEEK_B[2], N.GF_CHEEK_B[3])):
        s = s + xb(poly_ah(b0, N.GF_CHEEK), b0, b1)                  # servo cheek
    s = s + box(*N.GF_WEB)                                           # bottom web
    s = s - pocket("g")
    for sg in (1, -1):                                               # rack rails + lips (verbatim section)
        s = s + box(B.BR_A[0], B.CH_A1, -B.BR_B, B.BR_B, *sorted((sg * B.CH_H[0], sg * B.CH_H[1])))
        s = s + box(B.LIP[0], B.CH_A1, -B.BR_B, B.BR_B, *sorted((sg * B.LIP[1], sg * B.CH_H[0])))
    s = s + xa(bh(B.BR_A[0], -B.BR_B, B.BR_B, -B.CH_H[1], B.CH_H[1], N.GF_BRACKET_R), *B.BR_A)
    s = s - cyl((0, 0), B.BR_HOLE, "a", B.BR_A[0] - 1, B.BR_A[1] + 1)
    for sg in (1, -1):                                               # 45 deg chamfers under the lips
        tri = poly_ah(-B.BR_B - 1, ((B.LIP[0], sg * B.LIP[1]), (B.LIP[0], sg * B.CH_H[0]),
                                    (B.LIP[0] - N.GF_LIP_CH, sg * B.LIP[1])))
        s = s - xb(tri, -B.BR_B - 1, B.BR_B + 1)
    s = s - horn_holes((0, 0), "a", a0, a1, B.GB_CB_A, a1 + 1, a0 - 1, a0 + B.HORN_RECESS[1])
    a0w, a1w, w0, w1, r = N.GF_WIN                                   # cheek windows
    s = s - box(a0w, a1w, -15.6, 15.6, w0, w1)
    s = s + cleat_b(N.GF_CLEAT[0], N.GF_CLEAT[2], N.GF_CHEEK_B[0])
    return s

# ---------- part table (same groups as p_arm2b: 'fo' fixed, w4/w5/w6 jointed) ----------
def parts():
    return [
        ("w_j4_cradle", "fo", lambda: rest(w_j4_cradle())),
        ("vendor_sts3215_j4", "fo", PB.vendor_servo("j4")),
        ("w_link4", "w4", lambda: rest(w_link4())),
        ("vendor_sts3215_j5", "w4", PB.vendor_servo("j5")),
        ("w_link5", "w5", lambda: rest(w_link5())),
        ("vendor_sts3215_j6", "w5", PB.vendor_servo("j6")),
        ("w_grip_frame", "w6", lambda: rest(w_grip_frame())),
        ("vendor_sts3215_g", "w6", PB.vendor_servo("g")),
        ("vendor_gear_grip", "w6", PB.vendor_gear),
        ("vendor_rack_u", "w6", lambda: rest(PB.rack("U"))),
        ("vendor_rack_d", "w6", lambda: rest(PB.rack("D"))),
        ("finger_u", "w6", lambda: rest(PB.finger("U"))),
        ("finger_d", "w6", lambda: rest(PB.finger("D"))),
    ]

def pose(shape, group, **kw):
    return PB.pose(shape, "fo" if group.startswith("w") else group, **kw)
