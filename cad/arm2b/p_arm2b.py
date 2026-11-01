"""cad/arm2b/p_arm2b.py - A2b part geometry: wrist J4-J6 (3x STS3215) + STS3215-driven gripper.
Every A2b part is drawn in the wrist frame W (see ap2b.py) and moved to the reBot rest frame by rest();
build_arm2b.py then applies the A2a home pose (all wrist groups pose like A2a 'fo').
reBot parts (racks) are imported from rebot_src/ and only cut / moved - never redrawn."""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "arm2"))
from build123d import import_step, Solid, Plane, Pos, Rot, Location, Compound
import ap2 as P2
import p_arm2 as PA
import ap2b as B
box = PA.box
SRC = os.path.join(HERE, "rebot_src")
J4X, J4Z = P2.J4_XZ

def rest(s):
    """W -> reBot rest frame: X = J4X - a, Y = b, Z = J4Z - h"""
    return Pos(J4X, 0, J4Z) * Rot(0, 180, 0) * s

def cyl(p, d, axis, t0, t1):
    """cylinder of diameter d along W axis 'a'|'b'|'h' through point p (2 other coords), from t0 to t1"""
    if axis == "a":
        return Solid.make_cylinder(d / 2, t1 - t0, Plane(origin=(t0, p[0], p[1]), z_dir=(1, 0, 0)))
    if axis == "b":
        return Solid.make_cylinder(d / 2, t1 - t0, Plane(origin=(p[0], t0, p[1]), z_dir=(0, 1, 0)))
    return Solid.make_cylinder(d / 2, t1 - t0, Plane(origin=(p[0], p[1], t0), z_dir=(0, 0, 1)))

def pcd(c, ang=B.HORN_ANG, d=B.SV_HORN_PCD):
    return [(c[0] + d / 2 * math.cos(math.radians(x)), c[1] + d / 2 * math.sin(math.radians(x))) for x in ang]

# ---------------- STS3215 in W ----------------
def servo_loc(key):
    o, ly, lx = B.SERVOS[key]
    lz = (lx[1] * ly[2] - lx[2] * ly[1], lx[2] * ly[0] - lx[0] * ly[2], lx[0] * ly[1] - lx[1] * ly[0])
    return Location(Plane(origin=o, x_dir=lx, z_dir=lz))

def servo_kp(clr=0.0, plug_clr=None, horn=True):
    """STS3215 case + cable plug (+ horn) in the kp servo frame"""
    pc = clr if plug_clr is None else plug_clr
    s = box(B.SV_X[0] - clr, B.SV_X[1] + clr, B.SV_Y[0] - clr, B.SV_Y[1] + clr, -B.SV_Z - clr, B.SV_Z + clr)
    s = s + box(B.SV_PLUG_X[0] - pc, B.SV_PLUG_X[1] + pc, B.SV_PLUG_Y[0] - pc, B.SV_PLUG_Y[1], -B.SV_PLUG_Z - pc, B.SV_PLUG_Z + pc)
    if horn:
        s = s + Solid.make_cylinder(B.SV_HORN_D / 2 + clr, B.SV_HORN_Y[1] - B.SV_HORN_Y[0] + clr,
                                    Plane(origin=(0, B.SV_HORN_Y[0] - 0.5, 0), z_dir=(0, 1, 0)))
    return s

def servo_w(key, clr=0.0, plug_clr=None, horn=True):
    return servo_loc(key) * servo_kp(clr, plug_clr, horn)

def vendor_servo(key):
    return lambda: rest(servo_w(key))

def pocket(key):
    return servo_w(key, B.SV_CLR, 0.3)

# ---------------- forearm J4 end ----------------
def fore2(side):
    s = PA.fore_plate(side)
    y0, y1 = P2.FORE_L_Y if side == "L" else P2.FORE_R_Y
    s = s + PA.cyl_y(J4X, J4Z, B.FORE_PLUG_D, y0, y1)
    if side == "R":
        for a, h in B.J4_BOLTS:
            s = s - PA.cyl_y(J4X - a, J4Z - h, B.M3_CLR, y0 - 1, y1 + 1)
    return s

def j4_cradle():
    w = B.SV_Z + B.SV_CLR + B.SV_WALL
    s = box(B.J4_CRADLE_A0, 0.0, B.J4_CRADLE_B[0], B.J4_CRADLE_B[1], -w, w) - pocket("j4")
    s = s - box(-22.3, -10.7, 11.0, 23.5, 0.0, w + 1)              # cable slot out of the plug pocket (top)
    for a, h in B.J4_BOLTS:
        s = s - cyl((a, h), B.M3_PILOT, "b", B.J4_CRADLE_B[1] - 8.0, B.J4_CRADLE_B[1] + 1)
    return rest(s)

def horn_holes(c, axis, t0, t1, cb_from, cb_t, rec_from, rec_t):
    """4x M3 through the horn plate + head counterbores + centre-screw recess.  c = horn axis point (2 coords)."""
    cut = None
    for p in pcd(c):
        x = cyl(p, B.HORN_HOLE, axis, t0 - 1, t1 + 1) + cyl(p, B.HORN_CB[0], axis, *sorted((cb_from, cb_t)))
        cut = x if cut is None else cut + x
    return cut + cyl(c, B.HORN_RECESS[0], axis, *sorted((rec_from, rec_t)))

# ---------------- link4: J4 horn -> J5 case ----------------
def link4():
    b0, b1 = B.L4_B
    p = cyl((0, 0), 2 * B.L4_R, "b", b0, b1) + box(B.L4_STRUT[0], B.L4_STRUT[1], b0, b1, B.L4_STRUT[2], B.L4_STRUT[3])
    w = B.SV_Z + B.SV_CLR + B.SV_WALL
    top = B.J5_FACE_H + B.SV_HORN_Y[1] - B.SV_Y[0] + B.SV_CLR + B.SV_WALL            # 55.06
    blk = box(B.A_J5 - w, B.A_J5 + w, b0, B.J5_OPEN_B, B.J5_POCKET_H0, top)
    s = p + blk - pocket("j5")
    wi = B.SV_Z + B.SV_CLR; hb = B.SERVOS["j5"][0][2] - B.SV_Y[1] - B.SV_CLR          # J5 case face 16.56
    s = s - box(B.A_J5 - wi, B.A_J5 + wi, -B.SV_X[1] - B.SV_CLR, B.J5_OPEN_B + 1, B.J5_POCKET_H0 - 1, hb + 0.05)   # open bottom (no 1.4 floor)
    s = s - box(B.A_J5 - w - 1, B.A_J5 + w + 1, B.L4_WIN[0], B.L4_WIN[1], B.L4_WIN[2], B.L4_WIN[3])
    s = s - horn_holes((0, 0), "b", b0, b1, b0 - 1, b0 + B.HORN_CB[1], b1 - B.HORN_RECESS[1], b1 + 1)
    return rest(s)

# ---------------- link5: J5 horn -> J6 case ----------------
def link5():
    h0, h1 = B.L5_TOP
    wo = B.SV_Z + B.SV_CLR + B.SV_WALL; wi = B.SV_Z + B.SV_CLR
    a0 = B.SERVOS["j6"][0][0] + B.SV_Y[0] - B.SV_CLR - B.SV_WALL                     # 22.55
    s = box(a0, B.L5_FRONT_A, -wo, wo, h0, h1)
    for sg in (1, -1):
        s = s + box(a0 + B.SV_WALL, B.L5_FRONT_A, *sorted((sg * wi, sg * wo)), B.L5_CHEEK_H0, h0)
    s = s + box(a0, a0 + B.SV_WALL, -wo, wo, B.L5_BACK_H0, h1)
    s = s - pocket("j6")
    s = s - horn_holes((B.A_J5, 0), "h", h0, h1, h0 - 1, h0 + B.HORN_CB[1], h1 - B.HORN_RECESS[1], h1 + 1)
    return rest(s)

# ---------------- gripper ----------------
def grip_frame():
    wo = B.SV_Z + B.SV_CLR + B.SV_WALL; wi = B.SV_Z + B.SV_CLR
    a0, a1 = B.GB_A
    s = box(a0, a1, -wo, wo, -B.GB_H, B.GB_H)
    for sg in (1, -1):
        s = s + box(a1, B.BR_A[0], *sorted((sg * wi, sg * wo)), *B.GW_H)
    hc = B.CH_H[1]
    s = s + box(B.BR_A[0], B.BR_A[1], -B.BR_B, B.BR_B, -hc, hc)
    for sg in (1, -1):
        s = s + box(B.BR_A[0], B.CH_A1, -B.BR_B, B.BR_B, *sorted((sg * B.CH_H[0], sg * B.CH_H[1])))
        s = s + box(B.LIP[0], B.CH_A1, -B.BR_B, B.BR_B, *sorted((sg * B.LIP[1], sg * B.CH_H[0])))
    s = s - cyl((0, 0), B.BR_HOLE, "a", B.BR_A[0] - 1, B.BR_A[1] + 1)
    s = s - pocket("g")
    s = s - horn_holes((0, 0), "a", a0, a1, B.GB_CB_A, a1 + 1, a0 - 1, a0 + B.HORN_RECESS[1])
    return rest(s)

def vendor_gear():
    return rest(cyl((0, 0), B.GEAR[0], "a", B.GEAR[1], B.GEAR[2]))

def rack(which, open_mm=0.0):
    """reBot 02_Rack_<U|D> (rest frame, gear axis Z 195) -> W, cut to 36 mm; open_mm moves it to open the fingers"""
    s = import_step(os.path.join(SRC, "02_Rack_%s.step" % which)).solids()[0]
    s = Pos(B.RACK_X_REF, 0, -B.RACK_AXIS_Z) * Rot(0, 0, 180) * s     # a = ref - X, b = -Y, h = Z - 195
    lo, hi = B.RACK_U_B if which == "U" else B.RACK_D_B
    s = s & box(-1000, 1000, lo, hi, -1000, 1000)
    sg = 1 if which == "U" else -1
    return Pos(0, sg * open_mm, 0) * s

def finger(which, open_mm=0.0):
    sg = 1 if which == "U" else -1
    bi = sg * B.FINGER_GAP; bo = sg * (B.FINGER_GAP + B.FINGER_T)
    s = box(B.FINGER_A[0], B.FINGER_A[1], *sorted((bi, bo)), -B.FINGER_H, B.FINGER_H)
    s = s + box(B.TAB_A0, B.FINGER_A[0] + 0.01, *sorted((bi, bo)), *sorted((sg * B.TAB_H[0], sg * B.TAB_H[1])))
    return Pos(0, sg * open_mm, 0) * s

# ---------------- part table ----------------
# wrist groups: 'w4' turns with J4, 'w5' with J4+J5, 'w6' with J4+J5+J6; at home they pose like A2a 'fo'
def parts():
    a2a = [p for p in PA.parts() if p[0] not in ("fore_l", "fore_r")]
    return a2a + [
        ("fore_l2", "fo", lambda: fore2("L")),
        ("fore_r2", "fo", lambda: fore2("R")),
        ("j4_cradle", "fo", j4_cradle),
        ("vendor_sts3215_j4", "fo", vendor_servo("j4")),
        ("link4", "w4", link4),
        ("vendor_sts3215_j5", "w4", vendor_servo("j5")),
        ("link5", "w5", link5),
        ("vendor_sts3215_j6", "w5", vendor_servo("j6")),
        ("grip_frame", "w6", grip_frame),
        ("vendor_sts3215_g", "w6", vendor_servo("g")),
        ("vendor_gear_grip", "w6", vendor_gear),
        ("vendor_rack_u", "w6", lambda: rest(rack("U"))),
        ("vendor_rack_d", "w6", lambda: rest(rack("D"))),
        ("finger_u", "w6", lambda: rest(finger("U"))),
        ("finger_d", "w6", lambda: rest(finger("D"))),
    ]

def pose(shape, group, **kw):
    return PA.pose(shape, "fo" if group.startswith("w") else group, **kw)
