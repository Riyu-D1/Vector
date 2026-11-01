"""cad/arm2/p_arm2.py - A2a part geometry (J1..J3 chain).  Every part is returned in the
reBot world frame, folded rest pose, already shortened (J3 at ap2.J3_XZ).  build_arm2.py
applies the home pose.  reBot parts are imported from rebot_src/ and only cut / plugged /
shifted - never redrawn."""
import os, math
from build123d import (import_step, Solid, Plane, Box, Pos, Rot, Align, Compound,
                       Vector, Location, Axis, extrude, Face, Part)
import ap2 as P
A = P.A
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "rebot_src")
MIN = (Align.MIN, Align.MIN, Align.MIN)

def rebot(name):
    s = import_step(os.path.join(SRC, name + ".step"))
    sol = s.solids()
    return sol[0] if len(sol) == 1 else Compound(sol)

def cyl_y(x, z, d, y0, y1):
    return Solid.make_cylinder(d / 2, y1 - y0, Plane(origin=(x, y0, z), z_dir=(0, 1, 0)))

def cyl_z(x, y, d, z0, z1):
    return Solid.make_cylinder(d / 2, z1 - z0, Plane(origin=(x, y, z0), z_dir=(0, 0, 1)))

def box(x0, x1, y0, y1, z0, z1):
    return Pos(x0, y0, z0) * Box(x1 - x0, y1 - y0, z1 - z0, align=MIN)

def pcd_xz(c, pcd, ang):
    return [(c[0] + pcd / 2 * math.cos(math.radians(a)), c[1] + pcd / 2 * math.sin(math.radians(a))) for a in ang]

def link_angles():
    return [A.LINK_ANG0 + i * 360.0 / A.LINK_N for i in range(A.LINK_N)]

def sx(shape, dx):
    return Pos(dx, 0, 0) * shape

# ---------------- base / J1 ----------------
def servo_box(clr=0.0):
    zh = P.J1_HORN_Z - P.SV_HORN_Y[1]
    b = box(P.SV_X[0] - clr, P.SV_X[1] + clr, -P.SV_Z - clr, P.SV_Z + clr, zh + P.SV_Y[0] - clr, zh + P.SV_Y[1] + clr)
    return Rot(0, 0, P.J1_YAW) * b

def plug_box(clr, z_top_extra=0.0):
    zh = P.J1_HORN_Z - P.SV_HORN_Y[1]
    b = box(P.SV_PLUG_X[0] - clr, P.SV_PLUG_X[1] + clr, -P.SV_PLUG_Z - clr, P.SV_PLUG_Z + clr,
            zh + P.SV_PLUG_Y[0] - clr, zh + P.SV_Y[0] + z_top_extra)
    return Rot(0, 0, P.J1_YAW) * b

def vendor_sts3250():
    zh = P.J1_HORN_Z - P.SV_HORN_Y[1]
    s = servo_box(0.0) + plug_box(0.0, 0.0) + cyl_z(0, 0, P.SV_HORN_D, zh + P.SV_HORN_Y[0], zh + P.SV_HORN_Y[1])
    return s

def base_link():
    s = rebot("01_BASE_Link") - rebot("02_Base_Reinforcement_Part")   # reBot CAD overlaps these by 39 mm3
    return s - servo_box(P.SV_CLR).moved(Location((0, 0, 0))) - Rot(0, 0, P.J1_YAW) * box(
        P.SV_X[0] - P.SV_CLR, P.SV_X[1] + P.SV_CLR, -P.SV_Z - P.SV_CLR, P.SV_Z + P.SV_CLR, 70.0, 90.0) - plug_box(0.3, 1.0)

def j1_cradle():
    zh = P.J1_HORN_Z - P.SV_HORN_Y[1]
    top = zh + P.SV_Y[1]
    c = cyl_z(0, 0, P.CRADLE_D, P.CRADLE_Z0, top)
    c = c - servo_box(P.SV_CLR) - Rot(0, 0, P.J1_YAW) * box(
        P.SV_X[0] - P.SV_CLR, P.SV_X[1] + P.SV_CLR, -P.SV_Z - P.SV_CLR, P.SV_Z + P.SV_CLR, top - 1, top + 5) - plug_box(0.3, 1.0)
    px = (P.SV_PLUG_X[0] + P.SV_PLUG_X[1]) / 2
    a = math.radians(P.J1_YAW)
    c = c - cyl_z(px * math.cos(a), px * math.sin(a), P.CABLE_D, P.CRADLE_Z0 - 1, zh + P.SV_PLUG_Y[0] + 1)
    return c - rebot("01_BASE_Link")

def yaw_limit():
    s = rebot("02_Arm_Yaw_Limit")
    bb = s.bounding_box()
    s = s + cyl_z(0, 0, 14.4, bb.min.Z, bb.max.Z)
    s = s - cyl_z(0, 0, P.HORN_RECESS[0], bb.min.Z - 1, bb.min.Z + P.HORN_RECESS[1])
    for i in range(4):
        a = math.radians(P.J1_YAW + 90 * i); x, y = P.SV_HORN_PCD / 2 * math.cos(a), P.SV_HORN_PCD / 2 * math.sin(a)
        s = s - cyl_z(x, y, P.YAW_HORN_HOLE, bb.min.Z - 1, bb.max.Z + 1) - cyl_z(x, y, P.YAW_CB[0], bb.max.Z - P.YAW_CB[1], bb.max.Z + 1)
    return s

# ---------------- J2 / J3 joint stack ----------------
def vendor_act(c):
    """printed actuator housing proxy (rotates with the upper arm)"""
    return cyl_y(c[0], c[1], A.OD, P.ACT_HOUSING_END_Y, P.ACT_BACK_Y)

def vendor_actout(c):
    """actuator out_flange + dowels proxy (rotates with the next link)"""
    s = cyl_y(c[0], c[1], A.FLANGE_D, P.ACT_OUT_Y, P.ACT_HOUSING_END_Y + 0.0)
    for x, z in pcd_xz(c, A.OUT_DOWEL_PCD, A.OUT_DOWEL_ANG):
        s = s + cyl_y(x, z, A.OUT_DOWEL_D, P.ACT_OUT_Y - A.OUT_DOWEL_PROUD, P.ACT_OUT_Y)
    return s

def vendor_6803(c):
    return cyl_y(c[0], c[1], P.BRG_6803[1], *P.BRG_6803_Y) - cyl_y(c[0], c[1], P.BRG_6803[0], P.BRG_6803_Y[0] - 1, P.BRG_6803_Y[1] + 1)

def front_spacer(which):
    """reBot 02_Motor_Front_Spacer: all holes plugged, re-drilled to the actuator output pattern"""
    s = rebot("02_Motor_Front_Spacer_" + which)
    bb = s.bounding_box()
    c0 = ((bb.min.X + bb.max.X) / 2, (bb.min.Z + bb.max.Z) / 2)
    for x, z in pcd_xz(c0, 27.0, [30.0 + 60 * i for i in range(6)]) + pcd_xz(c0, 27.0, [60.0 * i for i in range(6)]) + pcd_xz(c0, 24.0, [30.0, 150.0, 270.0]) + pcd_xz(c0, 24.0, [90.0, 210.0, 330.0]):
        s = s + cyl_y(x, z, P.PLUG_D, bb.min.Y, bb.max.Y)
    s = s - cyl_y(c0[0], c0[1], 14.0, bb.min.Y - 1, bb.max.Y + 1)
    for x, z in pcd_xz(c0, A.OUT_M3_PCD, A.OUT_M3_ANG):
        s = s - cyl_y(x, z, P.FRONT_SP_M3, bb.min.Y - 1, bb.max.Y + 1)
    for x, z in pcd_xz(c0, A.OUT_DOWEL_PCD, A.OUT_DOWEL_ANG):
        s = s - cyl_y(x, z, P.FRONT_SP_DOWEL, bb.min.Y - 1, bb.max.Y + 1)
    if which == "J3":
        s = s + s.moved(Location((0, -P.J3_FRONT_SP_EXTRA, 0)))
    return s

def flange(which, extra):
    """reBot 02_FLANGE: d14 bore plugged, drilled FLANGE_BORE; optionally thickened toward +Y"""
    s = rebot("02_FLANGE_" + which)
    if extra:
        s = s + s.moved(Location((0, extra, 0)))
    bb = s.bounding_box(); c0 = ((bb.min.X + bb.max.X) / 2, (bb.min.Z + bb.max.Z) / 2)
    s = s + cyl_y(c0[0], c0[1], 14.4, bb.min.Y, bb.max.Y)
    return s - cyl_y(c0[0], c0[1], P.FLANGE_BORE, bb.min.Y - 1, bb.max.Y + 1)

def back_spacer(c):
    y0, y1 = P.BACK_SP_Y
    s = cyl_y(c[0], c[1], P.BACK_SP_D, y0, y1) - cyl_y(c[0], c[1], P.LIP_D, y0 - 1, y1 + 1) - cyl_y(c[0], c[1], P.SEAT_6803, P.BRG_6803_Y[0], y1 + 1)
    for x, z in pcd_xz(c, A.LINK_PCD, link_angles()):
        s = s - cyl_y(x, z, P.M3_CLR, y0 - 1, y1 + 1)
    return s

def stadium(y0, y1, r):
    (x2, z), (x3, _) = P.J2_XZ, P.J3_XZ
    return cyl_y(x2, z, 2 * r, y0, y1) + cyl_y(x3, z, 2 * r, y0, y1) + box(x2, x3, y0, y1, z - r, z + r)

def window(y0, y1):
    (x2, z), (x3, _) = P.J2_XZ, P.J3_XZ
    a, b = x2 + P.WIN_INSET, x3 - P.WIN_INSET
    return cyl_y(a, z, 2 * P.WIN_R, y0 - 1, y1 + 1) + cyl_y(b, z, 2 * P.WIN_R, y0 - 1, y1 + 1) + box(a, b, y0 - 1, y1 + 1, z - P.WIN_R, z + P.WIN_R)

def upper_out():
    y0, y1 = P.UP_OUT_Y
    s = stadium(y0, y1, P.UP_R) - window(y0, y1)
    for c in (P.J2_XZ, P.J3_XZ):
        s = s + (cyl_y(c[0], c[1], 2 * P.UP_R, *P.UP_COLLAR_Y))
        s = s - cyl_y(c[0], c[1], P.RING_D, y0 - 1, P.UP_COLLAR_Y[1] + 1)
    return s

def upper_back():
    y0, y1 = P.UP_BACK_Y
    s = stadium(y0, y1, P.UP_R) - window(y0, y1)
    h = (P.CSK_D - P.M3_CLR) / 2
    for c in (P.J2_XZ, P.J3_XZ):
        s = s - cyl_y(c[0], c[1], P.UP_BACK_HOLE, y0 - 1, y1 + 1)
        for x, z in pcd_xz(c, A.LINK_PCD, link_angles()):
            cone = Solid.make_cone(P.M3_CLR / 2, P.CSK_D / 2, h, Plane(origin=(x, y1 - h, z), z_dir=(0, 1, 0)))
            s = s - cyl_y(x, z, P.M3_CLR, y0 - 1, y1 + 1) - cone - cyl_y(x, z, P.CSK_D, y1, y1 + 1)
    return s

def fore_plate(side):
    """flat 4 mm forearm plate = reBot 03_Link3 J3-end sheet (shifted DX_UP) + J4-end sheet (shifted DX_FORE) + bridge"""
    src = rebot("03_Link3_" + side)
    y0, y1 = P.FORE_L_Y if side == "L" else P.FORE_R_Y
    def piece(ysec, keep, dx):
        from build123d import section
        sec = section(src, Plane(origin=(0, ysec, 0), z_dir=(0, 1, 0)))
        fs = [f for f in sec.faces() if keep(f.bounding_box())]
        out = None
        for f in fs:
            f2 = f.moved(Location((dx, y0 - ysec, 0)))
            e = extrude(f2, amount=y1 - y0, dir=(0, 1, 0))
            out = e if out is None else out + e
        return out
    j3 = piece(P.FORE_SEC_J3[side], lambda b: b.min.X > P.FORE_J3_XMIN, P.DX_UP)
    j4 = piece(P.FORE_SEC_J4[side], lambda b: b.max.X < P.FORE_J4_XMAX, P.DX_FORE)
    return j3 + j4 + box(P.FORE_BRIDGE_X[0], P.FORE_BRIDGE_X[1], y0, y1, *P.FORE_BAND_Z)

# ---------------- part table ----------------
# group: 'fix' = base + Link1 (J1 not swept), 'up' = moves with J2, 'fo' = moves with J3
def parts():
    J2, J3 = P.J2_XZ, P.J3_XZ
    d = P.DX_UP
    return [
        ("base_plate", "fix", lambda: rebot("01_BASE_Plate")),
        ("base_link", "fix", base_link),
        ("j1_cradle", "fix", j1_cradle),
        ("vendor_sts3250_j1", "fix", vendor_sts3250),
        ("base_reinf", "fix", lambda: rebot("02_Base_Reinforcement_Part")),
        ("yaw_limit", "fix", yaw_limit),
        ("link1", "fix", lambda: rebot("03_Link1")),
        ("front_spacer_j2", "fix", lambda: front_spacer("J2")),
        ("flange_j2", "fix", lambda: flange("J2", 0.0)),
        ("vendor_actout_j2", "fix", lambda: vendor_actout(J2)),
        ("vendor_act_j2", "up", lambda: vendor_act(J2)),
        ("back_spacer_j2", "up", lambda: back_spacer(J2)),
        ("vendor_6803_j2", "up", lambda: vendor_6803(J2)),
        ("upper_out", "up", upper_out),
        ("upper_back", "up", upper_back),
        ("vendor_act_j3", "up", lambda: vendor_act(J3)),
        ("back_spacer_j3", "up", lambda: back_spacer(J3)),
        ("vendor_6803_j3", "up", lambda: vendor_6803(J3)),
        ("front_spacer_j3", "fo", lambda: sx(front_spacer("J3"), d)),
        ("flange_j3", "fo", lambda: sx(flange("J3", P.J3_FLANGE_EXTRA), d)),
        ("vendor_actout_j3", "fo", lambda: vendor_actout(J3)),
        ("dogleg_l", "fo", lambda: rebot("02_Lower_Upper_Link_L").moved(Location((d, P.DOGLEG_DY["L"], 0)))),
        ("dogleg_r", "fo", lambda: rebot("02_Lower_Upper_Link_R").moved(Location((d, P.DOGLEG_DY["R"], 0)))),
        ("fore_l", "fo", lambda: fore_plate("L")),
        ("fore_r", "fo", lambda: fore_plate("R")),
    ]

def pose(shape, group, a2=P.POSE_J2, a3=P.POSE_J3):
    """home (L) pose: J2 group rotated a2 about J2, J3 group additionally a3 about J3"""
    ax2 = Axis((P.J2_XZ[0], 0, P.J2_XZ[1]), (0, 1, 0))
    if group == "fix":
        return shape
    if group == "fo":
        ax3 = Axis((P.J3_XZ[0], 0, P.J3_XZ[1]), (0, 1, 0))
        shape = shape.rotate(ax3, a3)
    return shape.rotate(ax2, a2)
