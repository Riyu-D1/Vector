"""SOMA arm v3 — structural parts (Stream B).

Arm frame: Z up, origin = drum centre on the recess floor.
  z 0..4      drum plate (2.5 mm seats in the lid recess, 1.5 proud)
  z 4..85     fixed housing: J1 actuator (vertical) + 6808 seat
  z 88..      turret plate + J2 cradle  (J2 axis Y at z = J2_Z)
  +X          upper link (J2 -> J3, 120)  forearm (J3 -> J4, 100)
              wrist pod (J4 pitch servo, J5 roll servo)  gripper (J6)

Joint conventions: J1 +Z, J2/J3/J4 +Y, J5/J6 +X.

Servo mounting (verified STS3215 pattern): the servo CASE sits in a fork;
its two END FACES bear on the fork cheek inner faces; M2 screws through
the cheeks into the ear-hole grids (24.45x20.5 output face / 20.7x20.5
back face). The output wheel drives the DISTAL cheek through a printed
horn-extension inside the proximal cheek bore.
"""
import math
from build123d import Axis, Box, Cylinder, Pos, Rot, Part, Compound, fillet

from arm_params import (ACTUATOR, SERVO, JOINTS, LINKS, BEARINGS, CASE,
                        DRUM_POSTS, TOL, CABLE)

# ---------------------------------------------------------------------------
# Z layout
# ---------------------------------------------------------------------------
DRUM_H = 4.0
ACT_FLOOR = 7.5                                  # actuator back face z
ACT_TOP = ACT_FLOOR + ACTUATOR.body_l            # output face z = 77.5
CAP_Z0, CAP_Z1 = 77.0, 86.0                      # bearing cap ring
BRG_Z0, BRG_Z1 = 78.0, 85.0                      # 6808 race zone
TURRET_PLATE_Z = 94.0                            # plate bottom (8 mm over cap)
J2_Z = 144.0                                     # J2/J3/J4 axis height

HOUSING_OD = 110.0
TURRET_D = 98.0

# actuator cradle (J2 on turret, J3 on upper link): a split block clamps
# the Ø60 body midsection; the 70 mm body ends protrude ±4.5.
CRADLE_IN = 25.5          # cradle block inner faces
CRADLE_T = 5.0            # -> outer +-30.5
# driven-link cheeks: -Y cheek inner rests on the body end face (-35);
# +Y cheek inner meets the output flange face (+36.5, 1.5 proud).
LINK_NEG_IN = -35.1       # -Y cheek inner face (body face -0.1)
LINK_POS_IN = 36.7        # +Y cheek inner face (flange face +0.2)
CHEEK_T = 5.0             # -> outers -40.5 / +41.7

# servo fork stack: case end faces at ~+-17.85, ear tabs reach ~20.85,
# output wheel face ~21.65 — carrier cheek inner faces at +-21.2 clear
# the ears (>=0.3) while the wheel enters the cheek bore.
SV_IN = 21.2              # servo fork cheek inner faces
SV_T = 5.0                # -> outer +-26.2
WR_IN = 26.7              # distal cheek inner faces (0.5 clear of carrier)
WR_T = 5.0                # -> outer +-31.7
WHEEL_FACE = 21.65        # output wheel face, rel servo centre

J3_X = LINKS.l_upper                    # 120
J4_X = J3_X + LINKS.l_fore              # 220
J5_X = J4_X + 51.0                      # J5 axis (pod back clears J4 block sweep)
TIP_X = J4_X + LINKS.l_tool             # gripper tip ~275

GRIP_JAW_L = 40.0


def _bore(d, h, axis="Z"):
    c = Cylinder(d / 2, h)
    if axis == "Y":
        c = Rot(-90, 0, 0) * c
    elif axis == "X":
        c = Rot(0, 90, 0) * c
    return c


def _bolt_circle(pcd, n, d, depth, axis="Z", start_deg=0.0):
    holes = None
    for i in range(n):
        a = math.radians(start_deg + i * 360.0 / n)
        h = Pos(pcd / 2 * math.cos(a), pcd / 2 * math.sin(a), 0) \
            * _bore(d, depth, axis)
        holes = h if holes is None else holes + h
    return holes


def _star(pcd, n, d, depth, axis="Z", slot=3.0):
    """Slotted bolt circle — tolerates UNVERIFIED flange patterns."""
    holes = None
    for i in range(n):
        a = math.radians(i * 360.0 / n)
        h = Pos(pcd / 2 * math.cos(a), pcd / 2 * math.sin(a), 0) \
            * Rot(0, 0, math.degrees(a)) * Pos(slot / 2, 0, 0) \
            * Box(d + slot, d, depth)
        holes = h if holes is None else holes + h
    if axis == "Y":
        holes = Rot(-90, 0, 0) * holes
    elif axis == "X":
        holes = Rot(0, 90, 0) * holes
    return holes


def _servo_pocket(axis, center):
    """Servo case pocket; `axis` = shaft direction. Case span along the
    shaft is ~35.7 -> pocket 36.6 (+~0.4 end clearance per side)."""
    ln, th, ax = SERVO.body_l + 0.7, SERVO.body_t + 0.7, 2 * SV_IN
    if axis == "Y":
        return Pos(*center) * Box(ln, ax, th)
    if axis == "X":
        return Pos(*center) * Box(ax, ln, th)
    return Pos(*center) * Box(ln, th, ax)   # Z


def _servo_grid_holes(axis, center, t):
    """M2 clearance holes through both cheeks onto the ear grids.
    For shaft//Y the faces are X-Z: 24.45 along X, 20.5 along Z."""
    holes = None
    a, b = SERVO.grid_a[0] / 2, SERVO.grid_a[1] / 2
    for s1 in (-1, 1):
        for s2 in (-1, 1):
            if axis == "Y":
                h = Pos(center[0] + s1 * a, center[1],
                        center[2] + s2 * b) * _bore(2.2, t, "Y")
            elif axis == "X":
                h = Pos(center[0], center[1] + s1 * a,
                        center[2] + s2 * b) * _bore(2.2, t, "X")
            else:
                h = Pos(center[0] + s1 * a, center[1] + s2 * b,
                        center[2]) * _bore(2.2, t, "Z")
            holes = h if holes is None else holes + h
    return holes


def _flange_iface(part, x, z):
    """+Y link cheek: slotted M4 star through to the output flange face
    (flange face = cheek inner face, 0.2 mm clearance). UNVERIFIED
    pattern — slots tolerate PCD error."""
    part -= Pos(x, LINK_POS_IN + CHEEK_T / 2, z) \
        * _star(ACTUATOR.out_pcd, ACTUATOR.out_bolts, ACTUATOR.out_bolt_d,
                CHEEK_T + 2, "Y")
    return part


# ===========================================================================
# BASE HOUSING
# ===========================================================================
def base_housing() -> Part:
    """Fixed housing, split at z=78 so the J1 actuator drops in from the
    top; the separate `bearing_cap` ring closes it and seats the 6808."""
    p = Pos(0, 0, DRUM_H / 2) * Cylinder(CASE.drum_d / 2, DRUM_H)
    # shell, closed at CAP_Z0 (the cap carries the bearing seat)
    p += Pos(0, 0, (DRUM_H + CAP_Z0) / 2) * Cylinder(HOUSING_OD / 2,
                                                   CAP_Z0 - DRUM_H)
    # light annular cavity around the actuator pocket
    p -= Pos(0, 0, (24 + 70) / 2) * Cylinder(38.0, 46)
    # actuator pocket Ø60.4, floor at 4..7.5, open at the top (insertion)
    p -= Pos(0, 0, (ACT_FLOOR + CAP_Z0) / 2) \
        * Cylinder(ACTUATOR.body_d / 2 + TOL.loose, CAP_Z0 - ACT_FLOOR + 0.5)
    # cable gallery beside the actuator (-Y wall) to the top face
    p -= Pos(0, -(ACTUATOR.body_d / 2 + 4), (10 + CAP_Z0) / 2) \
        * Box(CABLE.channel_w + 2, 10, CAP_Z0 - 10)
    # rear cable entry (case rear channel side, +Y rim, low)
    p -= Pos(0, HOUSING_OD / 2 - 6, 13) * Box(CABLE.channel_w + 4, 16, 12)
    # cap bolts: 4x M4 inserts in the top rim at r=48
    for i in range(4):
        a = math.radians(i * 90 + 45)
        p -= Pos(48 * math.cos(a), 48 * math.sin(a), CAP_Z0 - 4) \
            * Cylinder(TOL.insert_m4_d / 2, 8)
    # drum M4 hold-downs (csk through drum into the lid posts)
    for x, y in DRUM_POSTS:
        p -= Pos(x, y, DRUM_H / 2) * _bore(CASE.post_hole_d, DRUM_H + 1)
        p -= Pos(x, y, DRUM_H - 1.2) * Cylinder(4.2, 2.5)
    return p


def bearing_cap() -> Part:
    """Ring cap (z77..86) bolted over the housing top: seats the 6808
    outer race, clamps the actuator's top shoulder, carries the cable
    riser slot."""
    c = Pos(0, 0, (CAP_Z0 + CAP_Z1) / 2) * Cylinder(HOUSING_OD / 2,
                                                  CAP_Z1 - CAP_Z0)
    c -= Pos(0, 0, (CAP_Z0 + CAP_Z1) / 2) * Cylinder(24.0, CAP_Z1 - CAP_Z0 + 4)
    # 6808 outer-race seat (race zone 78..85; seat floor ring 77..78)
    c -= Pos(0, 0, (BRG_Z0 + BRG_Z1) / 2) \
        * Cylinder(BEARINGS["6808"][1] / 2 + TOL.press,
                   BRG_Z1 - BRG_Z0 + 0.3)
    # clamp lip: shallow Ø60.6 relief over the actuator top shoulder
    c -= Pos(0, 0, CAP_Z0 + 1.0) * Cylinder(30.3, 2.0)
    # cap bolts: M4 clearance into the rim inserts
    for i in range(4):
        a = math.radians(i * 90 + 45)
        c -= Pos(48 * math.cos(a), 48 * math.sin(a), (CAP_Z0 + CAP_Z1) / 2) \
            * _bore(4.4, CAP_Z1 - CAP_Z0 + 2)
        c -= Pos(48 * math.cos(a), 48 * math.sin(a), CAP_Z1 - 1.4) \
            * Cylinder(7.2, 2.8)                        # head pockets
    # cable riser slot over the housing gallery (-Y, r~34)
    c -= Pos(0, -(ACTUATOR.body_d / 2 + 4), (CAP_Z0 + CAP_Z1) / 2) \
        * Box(CABLE.channel_w + 2, 10, CAP_Z1 - CAP_Z0 + 2)
    return c


# ===========================================================================
# TURRET (on 6808 inner race; carries J2 actuator cradle)
# ===========================================================================
def turret() -> Part:
    """Hub plate + inner-race plug. Cables rise through the cap slot at
    r~34 (-Y), cross the 8 mm air gap under the plate edge, and enter the
    turret core through the plate hole (service loop twists in the gap)."""
    plate = Pos(0, 0, TURRET_PLATE_Z + 2) * Cylinder(TURRET_D / 2, 4)
    # plug in the inner race, bottom face just over the output flange
    plug = Pos(0, 0, (ACT_TOP + 0.3 + TURRET_PLATE_Z) / 2) \
        * Cylinder(BEARINGS["6808"][0] / 2 - 0.1,
                   TURRET_PLATE_Z - ACT_TOP - 0.3)
    t = plate + plug
    # 6xM4 through-bolts into the J1 output flange face (assumed PCD36)
    t -= Pos(0, 0, (ACT_TOP + TURRET_PLATE_Z + 4) / 2) \
        * _bolt_circle(ACTUATOR.out_pcd, ACTUATOR.out_bolts,
                       ACTUATOR.out_bolt_d,
                       TURRET_PLATE_Z + 4 - ACT_TOP)
    # cable hole in the plate over the housing riser slot (-Y, r~34)
    t -= Pos(0, -(ACTUATOR.body_d / 2 + 4), TURRET_PLATE_Z + 2) \
        * Box(CABLE.channel_w + 2, 10, 6)
    # J2 cradle: lower half-pipe shell (OD68, ID60.4) + split cap above;
    # silhouette stays r~35 so the driven link's rails sweep clear.
    t += Pos(0, 0, J2_Z) * Rot(-90, 0, 0) \
        * Cylinder(ACTUATOR.body_d / 2 + 4, 2 * (CRADLE_IN + CRADLE_T))
    t -= Pos(0, 0, J2_Z + 17.2) * Box(80, 80, 34.4)       # keep lower half
    t -= Pos(0, 0, J2_Z) * _bore(ACTUATOR.body_d + 2 * TOL.loose,
                                 2 * (CRADLE_IN + CRADLE_T) + 4, "Y")
    # shell support: two end webs bridging plate -> shell end walls at
    # |y|~30; the driven link's plates (|y|>=35.1) sweep over them and
    # its beam edges pass through the centre corridor
    for sy in (-1, 1):
        t += Pos(0, sy * 26.5, 105) * Box(32, 5, 17)
    # split-plane bolt lugs (inner edge r~31.5, clear of Ø60.6)
    for sx in (-1, 1):
        for sy in (-1, 1):
            t += Pos(sx * 36.5, sy * 25, J2_Z - 2.5) * Box(10, 10, 5)
            t -= Pos(sx * 36.5, sy * 25, J2_Z - 4) \
                * _bore(TOL.insert_m4_d, 8)
    # cable passage through the plate into the cradle zone (-X back)
    t -= Pos(-34, 0, TURRET_PLATE_Z + 2) * Box(14, CABLE.channel_w + 2, 8)
    return t


def _cradle_cap(x):
    """Upper half-shell clamping the actuator (bolts onto the lands)."""
    cap = Pos(x, 0, J2_Z) * Rot(-90, 0, 0) \
        * Cylinder(ACTUATOR.body_d / 2 + 4, 2 * (CRADLE_IN + CRADLE_T))
    cap -= Pos(x, 0, J2_Z - 17.2) * Box(80, 80, 34.4)     # keep upper half
    cap -= Pos(x, 0, J2_Z) * _bore(ACTUATOR.body_d + 2 * TOL.loose,
                                   2 * (CRADLE_IN + CRADLE_T) + 4, "Y")
    for sx in (-1, 1):
        for sy in (-1, 1):
            cap += Pos(x + sx * 36.5, sy * 25, J2_Z + 2.5) * Box(10, 10, 5)
            cap -= Pos(x + sx * 36.5, sy * 25, J2_Z) * _bore(4.4, 12)
    return cap


def turret_cap() -> Part:
    return _cradle_cap(0)


# ===========================================================================
# UPPER LINK (J2 -> J3)
# ===========================================================================
def _link_end(x, plate_h):
    """Driven-link end: two side plates, disc at the joint axis.
    -Y plate lands on the actuator body end face (shallow nest);
    +Y plate bolts to the output flange (star)."""
    cn, cp = LINK_NEG_IN - CHEEK_T / 2, LINK_POS_IN + CHEEK_T / 2
    f = None
    for cy in (cn, cp):
        d = Pos(x, cy, J2_Z) * Rot(-90, 0, 0) * Cylinder(37, CHEEK_T)
        f = d if f is None else f + d
    # -Y plate: shallow nest for the body end face (radial location)
    f -= Pos(x, LINK_NEG_IN - 0.4, J2_Z) * _bore(
        ACTUATOR.body_d + 0.6, 0.8, "Y")
    # +Y plate: flange bolt star
    f = _flange_iface(f, x, J2_Z)
    return f


def _cable_slot(f, x, cn):
    """Cable slot through the -Y plate below the axis.  Must be cut
    AFTER the plate beams are added (they share the plate plane)."""
    f -= Pos(x + 6, cn, J2_Z - 22) * Box(12, CHEEK_T + 2, 12)
    return f


def upper_link() -> Part:
    u = _link_end(0, 37)
    cn, cp = LINK_NEG_IN - CHEEK_T / 2, LINK_POS_IN + CHEEK_T / 2
    x1 = J3_X - 41
    # side-plate beams continue each plate to just short of J3; the
    # bottom edge is -30 near J2 (r>=34 off the axis) and steps to -15
    # past x30 so the plate clears the turret plate/cap discs at +30
    for cy in (cn, cp):
        u += Pos(11, cy, J2_Z + 5) * Box(38, CHEEK_T, 70)
        u += Pos(54.5, cy, J2_Z + 12.5) * Box(49, CHEEK_T, 55)
    # top rail joins the plates over the full span; no bottom rail --
    # anything under the beams sweeps into the plate/webs at J2 +30
    u += Pos(35.5, 0.8, J2_Z + 38) * Box(87, 81.8, 4)
    # centre web joins the plates and carries the J3 saddle; starts
    # clear of the J2 cradle-lug silhouette (r>42); cable bore beside -Y
    u += Pos(62, 0.8, J2_Z) * Box(36, 76, 20)
    u -= Pos(62, -24, J2_Z - 6) * Box(36, 10, 10)
    # J3 saddle: lower half-pipe shell (same as the turret cradle)
    u += Pos(J3_X, 0, J2_Z) * Rot(-90, 0, 0) \
        * Cylinder(ACTUATOR.body_d / 2 + 4, 2 * (CRADLE_IN + CRADLE_T))
    u -= Pos(J3_X, 0, J2_Z + 17.2) * Box(80, 80, 34.4)
    u -= Pos(J3_X, 0, J2_Z) * _bore(ACTUATOR.body_d + 2 * TOL.loose,
                                    2 * (CRADLE_IN + CRADLE_T) + 4, "Y")
    for sx in (-1, 1):
        for sy in (-1, 1):
            u += Pos(J3_X + sx * 36.5, sy * 25, J2_Z - 2.5) * Box(10, 10, 5)
            u -= Pos(J3_X + sx * 36.5, sy * 25, J2_Z - 4) \
                * _bore(TOL.insert_m4_d, 8)
    # saddle strut from the web to the shell (-X face); stays below the
    # split plane so it can't touch the cap
    u += Pos(J3_X - 37, 0.8, J2_Z - 6) * Box(14, 34, 12)
    return _cable_slot(u, 0, cn)


def upper_link_cap() -> Part:
    return _cradle_cap(J3_X)


# ===========================================================================
# FOREARM (J3 -> J4 servo fork at tip)
# ===========================================================================
def forearm() -> Part:
    f = _link_end(J3_X, 37)
    cn, cp = LINK_NEG_IN - CHEEK_T / 2, LINK_POS_IN + CHEEK_T / 2
    x1 = J4_X - 16
    # side-plate beams continue each plate toward the wrist; bottom
    # edge at -30 clears the carrier silhouettes through J2/J3 ROM
    for cy in (cn, cp):
        f += Pos((J3_X + 4 + x1) / 2, cy, J2_Z + 5) \
            * Box(x1 - (J3_X + 4), CHEEK_T, 70)
    # top + bottom edge rails (start past the J3 shell silhouette); the
    # top rail stops at x196 to clear the wrist rail's J4=-95 sweep
    f += Pos((J3_X + 42 + 196) / 2, 0.8, J2_Z + 38) \
        * Box(196 - J3_X - 42, 81.8, 4)
    f += Pos((J3_X + 42 + J4_X - 14) / 2, 0.8, J2_Z - 28) \
        * Box(J4_X - 14 - J3_X - 42, 81.8, 4)
    # centre web joins the plates; a narrower spine continues to the J4
    # tip block, staying inside the wrist's plate band (|y|<=24)
    f += Pos((J3_X + 42 + 190) / 2, 0.8, J2_Z) * Box(190 - J3_X - 42, 76, 16)
    f += Pos(198, 0.8, J2_Z) * Box(24, 48, 16)
    f -= Pos(175, -24, J2_Z - 4) * Box(32, 10, 8)
    f -= Pos(198, -16, J2_Z - 4) * Box(24, 8, 8)
    # J4 servo fork at tip: block spanning the carrier cheek planes;
    # z +-14 keeps its silhouette clear of the J5 pod's sweep corridor
    fy = SV_IN + SV_T / 2
    f += Pos(J4_X, 0, J2_Z) * Box(32, 2 * (SV_IN + SV_T), 28)
    f -= Pos(J4_X, 0, J2_Z) * _servo_pocket("Y", (0, 0, 0))
    f -= _servo_grid_holes("Y", (J4_X, 0, J2_Z), 60)
    # horn bore on -Y forearm cheek, back-boss bore +Y
    f -= Pos(J4_X, -fy, J2_Z) * _bore(SERVO.wheel_d + 2, SV_T + 2, "Y")
    f -= Pos(J4_X, +fy, J2_Z) * _bore(SERVO.wheel_d + 2, SV_T + 2, "Y")
    # idler stub on +Y outer face for the wrist cheek
    f += Pos(J4_X, SV_IN + SV_T + 1.5, J2_Z) \
        * Rot(-90, 0, 0) * Cylinder(4.0, 4.5)
    return _cable_slot(f, J3_X, cn)


def horn_ext_y(x):
    """Printed horn spacer for the J4 output: disc filling the gap
    between the wheel face (~-21.65) and the wrist cheek inner (-26.7);
    M3 bolts pass through the wrist cheek + this disc into the wheel."""
    ln = WR_IN - WHEEL_FACE + 0.3
    h = Cylinder(SERVO.wheel_d / 2 - 0.2, ln)
    h += Pos(0, 0, ln / 2 + 0.8) * Cylinder(7, 1.6)     # foot on wheel face
    h -= _bolt_circle(14.0, 4, 3.4, ln + 4)
    h -= _bore(3.0, ln + 4)
    h = Rot(90, 0, 0) * h
    return Pos(x, -(WHEEL_FACE + WR_IN) / 2, J2_Z) * h


# ===========================================================================
# WRIST POD: U-shell over forearm tip (J4) + J5 servo inside + horn to nose
# ===========================================================================
def wrist() -> Part:
    wy = WR_IN + WR_T / 2
    w = None
    # J4 disc plates (driven end) wrapping the forearm tip
    for sy in (-1, 1):
        c = Pos(J4_X, sy * wy, J2_Z) * Rot(-90, 0, 0) \
            * Cylinder(29, WR_T)
        w = c if w is None else w + c
    # plate beams continue forward to the J5 pod face
    for sy in (-1, 1):
        w += Pos(J4_X + 17.5, sy * wy, J2_Z) * Box(43, WR_T, 32)
    # top/bottom rails join the plate beams to the pod (clear the
    # forearm tip silhouette r~30)
    for s in (-1, 1):
        w += Pos(J4_X + 40, 0, J2_Z + s * 16) \
            * Box(18, 2 * WR_IN + 2 * WR_T, 4)
    # -Y cheek: wheel/horn bore + M3 bolts into the wheel
    w -= Pos(J4_X, -wy, J2_Z) * _bore(SERVO.wheel_d + 2.6, WR_T + 2, "Y")
    w -= Pos(J4_X, -wy, J2_Z) * _bolt_circle(14.0, 4, 3.4, WR_T + 4, "Y")
    w -= Pos(J4_X, -wy, J2_Z) * _bore(3.0, WR_T + 4, "Y")
    # +Y cheek: socket for the forearm stub
    w -= Pos(J4_X, wy, J2_Z) * _bore(8.3, WR_T + 2, "Y")
    # pod holding the J5 servo (shaft +X); end cheeks at +-21.2..26.2.
    # The pocket opens both +-Y faces so the case slides in along Y.
    w += Pos(J5_X, 0, J2_Z) * Box(2 * (SV_IN + SV_T), 52, 36)
    w -= Pos(J5_X, 0, J2_Z) * Box(2 * SV_IN, 60, SERVO.body_t + 0.7)
    # M2 holes through the +-X end cheeks onto the ear grids
    for s1 in (-1, 1):
        for s2 in (-1, 1):
            for sx in (-1, 1):
                w -= Pos(J5_X + sx * (SV_IN + SV_T / 2),
                         s1 * SERVO.grid_a[0] / 2,
                         J2_Z + s2 * SERVO.grid_a[1] / 2) * _bore(2.2, 8, "X")
    # horn bore through +X cheek (wheel reaches into it); stub bore -X
    w -= Pos(J5_X + SV_IN + SV_T / 2, 0, J2_Z) \
        * _bore(SERVO.wheel_d + 2, SV_T + 2, "X")
    w -= Pos(J5_X - SV_IN - SV_T / 2, 0, J2_Z) \
        * _bore(SERVO.wheel_d + 2, SV_T + 2, "X")
    # cable channel along the shell bottom
    w -= Pos(J5_X - 4, -18, J2_Z - 14) \
        * Box(40, CABLE.channel_w, CABLE.channel_h)
    return w


# ===========================================================================
# NOSE + GRIPPER (J5 flange -> rail block + J6 servo + jaws)
# ===========================================================================
def horn_ext_x():
    """Horn spacer for the J5 output: fills the gap between the wheel
    face (J5_X+21.65) and the nose plate face (J5_X+WR_IN); M3 bolts
    pass through the plate + spacer into the wheel."""
    ln = WR_IN - WHEEL_FACE + 0.3
    h = Cylinder(SERVO.wheel_d / 2 - 0.2, ln)
    h += Pos(0, 0, -ln / 2 - 0.8) * Cylinder(7, 1.6)   # foot on wheel face
    h -= _bolt_circle(14.0, 4, 3.4, ln + 4)
    h -= _bore(3.0, ln + 4)
    h = Rot(0, -90, 0) * h
    return Pos(J5_X + (WHEEL_FACE + WR_IN) / 2, 0, J2_Z) * h


NOSE_PLATE_X = J5_X + WR_IN         # inner face of the nose plate
RAIL_X0 = NOSE_PLATE_X + 4
RAIL_L = 46.0
J6_X = J5_X + 40.0


def nose() -> Part:
    # face plate on the J5 horn (+X face): Ø44 disc, M3 star into wheel
    n = Pos(NOSE_PLATE_X + 2, 0, J2_Z) * Rot(0, 90, 0) * Cylinder(22, 4)
    n -= Pos(NOSE_PLATE_X + 2, 0, J2_Z) * _bolt_circle(14.0, 4, 3.4, 8, "X")
    # rail block forward
    n += Pos(RAIL_X0 + RAIL_L / 2, 0, J2_Z) * Box(RAIL_L, 34, 28)
    # jaw rail slot through the block (jaws slide +-Y), open both X ends
    n -= Pos(RAIL_X0 + RAIL_L / 2, 0, J2_Z - 8) * Box(RAIL_L + 4, 24, 8)
    # finger-rise window through the rail top (jaw tips + pads emerge)
    n -= Pos(RAIL_X0 + 27, 0, J2_Z + 4) * Box(38, 24, 16)
    # J6 servo on top, shaft +Z, wheel down into the rail slot.
    # Case bottom face rests on the block top; the pocket recesses
    # 3.4 mm below it for the ear tabs + wheel.
    sz = J2_Z + 14 + SV_IN
    n -= Pos(J6_X, 0, sz) * _servo_pocket("Z", (0, 0, 0))
    # wheel/pinion bore down to the rack slot + M2 pilots into the block
    n -= Pos(J6_X, 0, J2_Z + 5) * _bore(SERVO.wheel_d + 2, 20)
    for s1 in (-1, 1):
        for s2 in (-1, 1):
            n -= Pos(J6_X + s1 * SERVO.grid_a[0] / 2,
                     s2 * SERVO.grid_a[1] / 2, J2_Z + 8) * _bore(1.7, 16)
    return n


def gripper_jaw(sign) -> Part:
    j = Box(38, 9, 7)                                   # rack block
    j += Pos(17, sign * -0, 8) * Box(8, 9, 12)          # finger tip rises
    j += Pos(21, 0, 2) * Box(6, 9, 8)                   # pad
    return Pos(RAIL_X0 + 19, sign * 6.8, J2_Z - 8.5) * j


# ===========================================================================
def all_parts():
    return {
        "base_housing":   base_housing(),
        "bearing_cap":    bearing_cap(),
        "turret":         turret(),
        "turret_cap":     turret_cap(),
        "upper_link":     upper_link(),
        "upper_link_cap": upper_link_cap(),
        "forearm":        forearm(),
        "horn_ext_j4":    horn_ext_y(J4_X),
        "wrist":          wrist(),
        "horn_ext_j5":    horn_ext_x(),
        "nose":           nose(),
        "jaw_l":          gripper_jaw(+1),
        "jaw_r":          gripper_jaw(-1),
    }


CHAIN = {
    "base_housing": [], "bearing_cap": [],
    "turret": ["J1"], "turret_cap": ["J1"],
    "upper_link": ["J1", "J2"], "upper_link_cap": ["J1", "J2"],
    "forearm": ["J1", "J2", "J3"], "horn_ext_j4": ["J1", "J2", "J3"],
    "wrist": ["J1", "J2", "J3", "J4"],
    "horn_ext_j5": ["J1", "J2", "J3", "J4", "J5"],
    "nose": ["J1", "J2", "J3", "J4", "J5"],
    "jaw_l": ["J1", "J2", "J3", "J4", "J5", "J6"],
    "jaw_r": ["J1", "J2", "J3", "J4", "J5", "J6"],
}

JOINT_AXES = {
    "J1": ((0, 0, 0), (0, 0, 1)),
    "J2": ((0, 0, J2_Z), (0, 1, 0)),
    "J3": ((J3_X, 0, J2_Z), (0, 1, 0)),
    "J4": ((J4_X, 0, J2_Z), (0, 1, 0)),
    "J5": ((J5_X, 0, J2_Z), (1, 0, 0)),
    "J6": ((J5_X + 18, 0, J2_Z), (0, 0, 1)),
}
