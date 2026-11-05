"""toolchg/p_toolchg.py - D10 automounter geometry, same conventions as
cradlefix/p_wrist6.py (helpers imported from the tested D6/D7 code, never
redrawn):  W frame, a = tool direction, b = world y, h = up;  roll axis at
b = 0, h = -17.  Everything new lives under toolchg/.

  tc_master  - J6-horn plate + spigot + 3 bayonet lugs (arm side)
  tc_plate   - socket plate: ring + 3 catches + floor + dock groove + key
               (shared front end of every tool)
  tool_grip  - tc_plate + the D6 w_grip_frame body shifted +TC_SH in a
  tool_pen   - tc_plate + pen/pointer holder
  tc_rack    - 4-slot docking rack (drawn in world frame)
"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
for d in ("../cradlefix", "../cad/arm2b", "../cad/arm2"):
    sys.path.insert(0, os.path.join(HERE, d))
from build123d import (Plane, Pos, Rot, Polygon, RectangleRounded, Axis,
                       Solid, Face, extrude, revolve, Location)
import ap2 as P2
import p_arm2 as PA
import ap2b as B
import p_arm2b as PB
import ap6 as N
import tc_params as T

box = PA.box
cyl = PB.cyl
rest = PB.rest
horn_holes = PB.horn_holes
SH = T.TC_SH
ROLL_AX = Axis((0.0, 0.0, T.H_AX), (1.0, 0.0, 0.0))   # revolve axis

# ---------- local helpers (same style as p_wrist6) ----------
def _ah(b):
    return Plane(origin=(0, b, 0), x_dir=(1, 0, 0), y_dir=(0, 0, 1))

def _bh(a):
    return Plane(origin=(a, 0, 0), x_dir=(0, 1, 0), y_dir=(0, 0, 1))

def poly_ah(b, pts):
    return _ah(b) * Polygon(*pts, align=None)

def poly_bh(a, pts):
    return _bh(a) * Polygon(*pts, align=None)

def bh(a, b0, b1, h0, h1, r):
    return _bh(a) * Pos((b0 + b1) / 2, (h0 + h1) / 2, 0) * \
        RectangleRounded(b1 - b0, h1 - h0, r)

def xb(face, b0, b1):
    return extrude(face, amount=b1 - b0, dir=(0, 1, 0))

def xa(face, a0, a1):
    return extrude(face, amount=a1 - a0, dir=(1, 0, 0))

def _rads(ph):
    return math.radians(ph)

def sector(ph, arc, r0, r1, a0, a1, closed=True):
    """angular-sector prism about the roll axis: ph centre deg, arc width
    deg, r0..r1 (from the axis in the b-h plane), extruded a0..a1."""
    if closed or r0 == 0:
        pts = [(0.0, T.H_AX)]
    else:
        p0 = _rads(ph - arc / 2)
        pts = [(r0 * math.cos(p0), T.H_AX + r0 * math.sin(p0))]
    n = max(2, int(arc / 12))
    for i in range(n + 1):
        p = _rads(ph - arc / 2 + arc * i / n)
        pts.append((r1 * math.cos(p), T.H_AX + r1 * math.sin(p)))
    if not (closed or r0 == 0):
        p1 = _rads(ph + arc / 2)
        pts.append((r0 * math.cos(p1), T.H_AX + r0 * math.sin(p1)))
    return xa(poly_bh(a0, pts), a0, a1)

def ring(profile):
    """revolve an (a, r) profile about the roll axis -> full 360 solid."""
    pts = [(a_, T.H_AX + r_) for a_, r_ in profile]
    return revolve(poly_ah(0.0, pts), axis=ROLL_AX)

def rcyl(a, ph, d, r0, r1):
    """radial cylinder at phase ph, diameter d, r0..r1 from the axis."""
    lo = Plane(origin=(a, r0 * math.cos(_rads(ph)),
                       T.H_AX + r0 * math.sin(_rads(ph))),
               z_dir=(0.0, math.cos(_rads(ph)), math.sin(_rads(ph))))
    return Solid.make_cylinder(d / 2, r1 - r0, lo)

# ---------- shifted g servo (tool side, +SH in a) ----------
def _g_loc():
    o = (N.A_G + SH, 0.0, N.J6_AX_H)
    ly, lx = (1, 0, 0), (0, 0, 1)
    lz = (lx[1] * ly[2] - lx[2] * ly[1], lx[2] * ly[0] - lx[0] * ly[2],
          lx[0] * ly[1] - lx[1] * ly[0])
    return Location(Plane(origin=o, x_dir=lx, z_dir=lz))

def g_pocket(clr=B.SV_CLR, plug_clr=0.3):
    return _g_loc() * PB.servo_kp(clr, plug_clr, True)

def vendor_g():
    return _g_loc() * PB.servo_kp()

# =========================================================== tc_master
def tc_master():
    a0, a1 = T.TC_PLATE_A
    s = cyl((0, T.H_AX), 2 * T.TC_PLATE_R, "a", a0, a1)          # horn plate
    s = s + cyl((0, T.H_AX), 2 * T.TC_SPIGOT_R, "a", a0, T.TC_SPIGOT_TIP)
    def ring_chamfer(a_lo, r_lo, a_hi, r_hi):
        """ring cutter removing material OUTSIDE the cone profile
        r(a): chamfers an edge without gutting the core."""
        cone = Solid.make_cone(
            r_lo, r_hi, a_hi - a_lo,
            Plane(origin=(a_lo, 0, T.H_AX), z_dir=(1, 0, 0)))
        out = cyl((0, T.H_AX), 2 * (T.TC_LUG_R + 1.5), "a", a_lo, a_hi)
        return out - cone
    for ph in T.TC_LUG_PH:                                      # bayonet lugs
        lug = sector(ph, T.TC_LUG_ARC, T.TC_LUG_IN, T.TC_LUG_R,
                     T.TC_LUG_A[0], T.TC_LUG_A[1], closed=False)
        # 45deg chamfers on the lug's -a edge and +a tip edge
        lug = lug - ring_chamfer(T.TC_LUG_A[0], T.TC_LUG_R - 1.0,
                                 T.TC_LUG_A[0] + 1.0, T.TC_LUG_R + 0.3)
        lug = lug - ring_chamfer(T.TC_LUG_A[1] - 1.0, T.TC_LUG_R,
                                 T.TC_LUG_A[1], T.TC_LUG_R - 0.9)
        s = s + lug
    s = s - cyl((0, T.H_AX), T.TC_BORE_D, "a", a0 - 1, T.TC_SPIGOT_TIP + 1)
    s = s - horn_holes((0, T.H_AX), "a", a0, a1, T.TC_CB_A, a1 + 1,
                       a0 - 1, a0 + B.HORN_RECESS[1])
    # detent dimple on lug1 OD (master-frame phase where the ball seats
    # at lock)
    s = s - rcyl((T.TC_LUG_A[0] + T.TC_LUG_A[1]) / 2,
                 T.TC_DIMPLE_PH, T.TC_DIMPLE_D,
                 T.TC_LUG_R - T.TC_DIMPLE_DPTH - 0.05, T.TC_LUG_R + 1)
    return s

# =========================================================== tc_plate
def _ring_floor():
    """socket ring + floor as one revolve: bore 18.2, OD 23, floor disc."""
    a0, a1 = T.TC_RING_A
    f0, f1 = T.TC_FLOOR_A
    prof = [(a0, T.TC_RING_ROUT), (a1, T.TC_RING_ROUT), (a1, 0.0),
            (f0, 0.0), (f0, T.TC_RING_RIN), (a0, T.TC_RING_RIN)]
    return ring(prof)

def _catch(ph):
    """one inward catch: profile revolved exactly over the catch arc, so
    the -a lead face gets a real chamfered ramp (support-free print)."""
    a0, a1 = T.TC_CATCH_A
    p0 = _rads(ph - T.TC_CATCH_ARC / 2)
    pl = Plane(origin=(0.0, 0.0, T.H_AX), x_dir=(1, 0, 0),
               y_dir=(0.0, math.cos(p0), math.sin(p0)))
    # outer edge 0.4 into the ring wall -> fused body, not tangent contact
    prof = pl * Polygon((a0, T.TC_RING_RIN + 0.4),
                        (a0 + 2.2, T.TC_CATCH_R),
                        (a1, T.TC_CATCH_R), (a1, T.TC_RING_RIN + 0.4),
                        align=None)
    return revolve(prof, axis=ROLL_AX, revolution_arc=T.TC_CATCH_ARC)

def tc_plate():
    s = _ring_floor()
    for ph in T.TC_CATCH_PH:
        s = s + _catch(ph)
    # dock groove on the OD
    g0, g1 = T.TC_DOCK_A
    s = s - (cyl((0, T.H_AX), 2 * T.TC_RING_ROUT + 2, "a", g0, g1)
             - cyl((0, T.H_AX), 2 * T.TC_DOCK_R, "a", g0 - 1, g1 + 1))
    # key notch in the groove floor (bottom phase)
    kw = T.TC_KEY_W / 2
    s = s - box(g0 + 0.25, g1 - 0.25, -kw, kw,
                T.H_AX - T.TC_DOCK_R - T.TC_KEY_D, T.H_AX - T.TC_DOCK_R + 0.05)
    # detent plunger bore (radial, through the ring wall)
    s = s - rcyl(T.TC_DET_A, T.TC_DET_PH, T.TC_DET_D,
                 T.TC_RING_RIN - 0.5, T.TC_RING_ROUT + 1)
    # pogo pin bores through the floor into the body
    for r, ph in zip(T.TC_PIN_R, T.TC_PIN_PH):
        x = r * math.cos(_rads(ph))
        y = T.H_AX + r * math.sin(_rads(ph))
        s = s - cyl((x, y), T.TC_PIN_D, "a",
                    T.TC_FLOOR_A[0] - 0.5, T.TC_FLOOR_A[1] + 4.0)
    return s

# =========================================================== tool_grip
def _neck():
    """joins the socket floor back face (a BODY_A) to the cage front."""
    s = cyl((0, T.H_AX), 33.0, "a", T.TC_BODY_A, T.TC_BODY_A + 2.4)
    s = s + box(T.TC_BODY_A, T.TC_BODY_A + 2.4, -14.91, 14.91, -45.0, -26.0)
    return s

def tool_grip():
    s = tc_plate() + _neck()
    for sg in (1, -1):        # cage cheeks (GF_CAGE shifted)
        pts = tuple((a + SH, h) for a, h in N.GF_CAGE)
        s = s + xb(poly_ah(sg * N.GF_CHEEK_B[0], pts),
                   *sorted((sg * N.GF_CHEEK_B[0], sg * N.GF_CHEEK_B[1])))
    s = s + box(71.5 + SH, 114.7 + SH, -N.GF_CHEEK_B[1], N.GF_CHEEK_B[1],
                N.GF_BOTTOM - 2.0, N.GF_BOTTOM)                 # keel web
    a0w, a1w, bh0, bh1 = N.GF_BACKWALL
    s = s + box(a0w + SH, a1w + SH, -N.GF_CHEEK_B[1], N.GF_CHEEK_B[1],
                bh0, bh1)                                       # back-bottom wall
    s = s - g_pocket()
    hs, sh = N.H_SH, N.A_SH + SH
    for sg in (1, -1):        # rack rails + lips
        s = s + box(B.BR_A[0] + sh, B.CH_A1 + sh, -B.BR_B, B.BR_B,
                    *sorted((sg * B.CH_H[0] + hs, sg * B.CH_H[1] + hs)))
        s = s + box(B.LIP[0] + sh, B.CH_A1 + sh, -B.BR_B, B.BR_B,
                    *sorted((sg * B.LIP[1] + hs, sg * B.CH_H[0] + hs)))
    s = s + xa(bh(B.BR_A[0] + sh, -B.BR_B, B.BR_B,
                  -B.CH_H[1] + hs, B.CH_H[1] + hs, N.GF_BRACKET_R),
               B.BR_A[0] + sh, B.BR_A[1] + sh)
    s = s - cyl((0, hs), B.BR_HOLE, "a", B.BR_A[0] + sh - 1, B.BR_A[1] + sh + 1)
    for sg in (1, -1):        # 45 deg chamfers under the lips
        tri = poly_ah(-B.BR_B - 1,
                      ((B.LIP[0] + sh, sg * B.LIP[1] + hs),
                       (B.LIP[0] + sh, sg * B.CH_H[0] + hs),
                       (B.LIP[0] + sh - N.GF_LIP_CH, sg * B.LIP[1] + hs)))
        s = s - xb(tri, -B.BR_B - 1, B.BR_B + 1)
    for ac, ahw, hc, hhw in N.GF_WIN:                            # cheek windows
        s = s - box(ac - ahw + SH, ac + ahw + SH, -N.GF_CHEEK_B[1] - 1,
                    N.GF_CHEEK_B[1] + 1, hc - hhw, hc + hhw)
    s = s + PB.cyl((N.GF_CLEAT[0] + SH, N.GF_CLEAT[2]), 2.6, "b",
                   -N.GF_CHEEK_B[1] - 3.0, -N.GF_CHEEK_B[1] + 0.5)
    s = s + PB.cyl((N.GF_CLEAT[0] + SH, N.GF_CLEAT[2]), 4.4, "b",
                   -N.GF_CHEEK_B[1] - 4.0, -N.GF_CHEEK_B[1] - 3.0)
    return s

# shifted vendor proxies for the tool body
def tc_rack_sh(which, open_mm=0.0):
    sg = 1 if which == "U" else -1
    return Pos(SH, 0, 0) * Pos(N.A_SH, 0, N.H_SH) * PB.rack(which, open_mm)

def tc_finger_sh(which, open_mm=0.0):
    sg = 1 if which == "U" else -1
    return Pos(SH, 0, 0) * Pos(0, sg * open_mm, 0) * Pos(N.A_SH, 0, N.H_SH) * PB.finger(which)

def tc_gear():
    return rest(cyl((0, N.H_SH), B.GEAR[0], "a",
                    B.GEAR[1] + N.A_SH + SH, B.GEAR[2] + N.A_SH + SH))

# =========================================================== tool_pen
def tool_pen():
    s = tc_plate()
    s = s + cyl((0, T.H_AX), 33.0, "a", T.TC_BODY_A, 90.0)          # neck
    s = s + cyl((0, T.H_AX), 2 * T.PEN_BODY_R, "a", 88.0, 140.0)    # barrel
    s = s + Solid.make_cone(T.PEN_BODY_R, 5.5, 8.0,
                            Plane(origin=(140.0, 0, T.H_AX), z_dir=(1, 0, 0)))
    s = s - cyl((0, T.H_AX), T.PEN_D, "a", T.TC_BODY_A, T.PEN_TIP_A)  # pen bore
    for ph in (30.0, 210.0):                                        # set screws
        s = s - rcyl(136.0, ph, T.PEN_SET_D, T.PEN_BODY_R - 4.0,
                     T.PEN_BODY_R + 1)
    # pin-bore wiring exits (same as tool_grip: bores continue 4 mm back)
    return s

# =========================================================== tc_rack
def tc_rack():
    """4-slot dock rack, world frame. Plate normal to the tool axis at
    x = RACK_PLATE_X; slot floor cradles the ring groove."""
    x0 = T.RACK_PLATE_X - T.RACK_PLATE_T / 2
    x1 = T.RACK_PLATE_X + T.RACK_PLATE_T / 2
    yc = T.RACK_AXIS_Y
    az = T.RACK_AXIS_Z
    y0, y1 = yc - 1.5 * T.RACK_SLOT_PITCH - 24, yc + 1.5 * T.RACK_SLOT_PITCH + 24
    ztop = az + 8.0
    s = box(x0, x1, y0, y1, az - T.RACK_SEAT_R - 4.0, ztop)
    for k in range(T.RACK_N_SLOTS):
        yk = yc + (k - 1.5) * T.RACK_SLOT_PITCH
        slot = box(x0 - 1, x1 + 1, yk - T.RACK_SLOT_W / 2,
                   yk + T.RACK_SLOT_W / 2, az, ztop + 1)
        seat = cyl((yk, az), 2 * T.RACK_SEAT_R, "a", x0 - 1, x1 + 1)
        s = s - (slot + seat)
        key = box(x0 + 0.4, x1 - 0.4, yk - T.RACK_KEY[0] / 2,
                  yk + T.RACK_KEY[0] / 2,
                  az - T.RACK_SEAT_R, az - T.RACK_SEAT_R + T.RACK_KEY[1])
        s = s + key
    # body cradle plate under the tool case (2nd support, kills tipping):
    # open U-notch down to z 66, clears the case bottom (~75) by ~9 mm
    x2 = T.RACK_PLATE_X + 30.0
    s = s + box(x2, x2 + 4.0, y0, y1, 62.0, az - 18.0)
    for k in range(T.RACK_N_SLOTS):
        yk = yc + (k - 1.5) * T.RACK_SLOT_PITCH
        s = s - box(x2 - 1, x2 + 5.0, yk - 16.0, yk + 16.0,
                    66.0, ztop + 1)
    # legs + base
    s = s + box(x0, x1, y0, y1, 0.0, az - T.RACK_SEAT_R - 4.0)
    s = s + box(x2, x2 + 4.0, y0, y1, 0.0, 62.0)
    s = s + box(x0 - 4.0, x2 + 8.0, y0 - 8.0, y1 + 8.0, 0.0, 4.0)
    return s

# =========================================================== table
def parts():
    return [
        ("tc_master", "w6", lambda: rest(tc_master())),
        ("tc_plate", "w6", lambda: rest(tc_plate())),
        ("tool_grip", "w6", lambda: rest(tool_grip())),
        ("tool_pen", "w6", lambda: rest(tool_pen())),
        ("tc_vendor_g", "w6", lambda: rest(vendor_g())),
        ("tc_gear", "w6", tc_gear),
        ("tc_rack_u", "w6", lambda: rest(tc_rack_sh("U"))),
        ("tc_rack_d", "w6", lambda: rest(tc_rack_sh("D"))),
        ("tc_finger_u", "w6", lambda: rest(tc_finger_sh("U"))),
        ("tc_finger_d", "w6", lambda: rest(tc_finger_sh("D"))),
        ("tc_rack", "fix", tc_rack),
    ]

def pose(shape, group, **kw):
    return PB.pose(shape, "fo" if group and group.startswith("w") else group,
                   **kw)
