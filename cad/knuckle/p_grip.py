"""cad/knuckle/p_grip.py - S4 parts: gripper, grip_lid, jaw, jaw_cap. Copied verbatim."""
import kp
from frames import gbox, servo_pt, xcyl, ycyl, yprism

JX, JZ = kp.J6_ORIGIN[0], kp.J6_ORIGIN[2]               # J6 axis (x, z)


def gripper():
    g = gbox(*kp.GR) + gbox(*kp.FINGER_FIX)
    g -= gbox(*kp.GR_POCKET)
    g -= gbox(*kp.GR_SLOT)
    g -= ycyl(JX, JZ, 22.0, kp.GR_POCKET[3] - 0.5, kp.GR[3] + 1)       # J6 horn hole
    bx0 = kp.GR_BACK_X[0]
    for y, z in [(7, 150), (-7, 150), (0, 157), (0, 143)]:            # J5 horn M3 x6
        g -= xcyl(y, z, kp.M3_CLEAR, bx0 - 1, kp.GR_BACK_X[1] + 1)
        g -= xcyl(y, z, kp.M3_CB_D, bx0 + 3.0, kp.GR_BACK_X[1] + 1)
    rd, rh = kp.HORN_RECESS
    g -= xcyl(0, 150, rd, bx0 - 1, bx0 + rh)
    r0, r1, d = kp.GR_GROOVE
    g -= xcyl(0, 150, 2 * r1, bx0 - 1, bx0 + d) - xcyl(0, 150, 2 * r0, bx0 - 2, bx0 + d + 1)
    hy, hz, hd = kp.GR_HOLE
    g -= xcyl(hy, hz, hd, bx0 + d - 0.5, kp.GR_SLOT[0] + 0.5)
    for x, z in kp.GR_PILOTS:
        g -= ycyl(x, z, kp.M2_PILOT, kp.GR[2] - 1, kp.GR[2] + 8)
    return g


def grip_lid():
    l = gbox(*kp.GR_LID) + gbox(*kp.GR_BUMP)
    l -= gbox(*kp.GR_PLUG)
    for x, z in kp.GR_PILOTS:
        l -= ycyl(x, z, kp.M2_CLEAR, kp.GR_LID[2] - 1, kp.GR_LID[3] + 1)
    return l


def jaw():
    y0, y1 = kp.JAW_Y
    fx0, fx1, _, _, fz0, fz1 = kp.FINGER_MOV
    hr = kp.JAW_HUB_D / 2
    j = ycyl(JX, JZ, kp.JAW_HUB_D, y0, y1)
    j += yprism([(JX, JZ + hr), (fx1, fz1), (fx1, fz0), (JX, JZ - hr + 0.0)], y0, y1)
    j += gbox(*kp.FINGER_MOV)
    for lx, lz in [(7, 0), (-7, 0), (0, 7), (0, -7)]:                 # J6 horn M3 x6
        p = servo_pt("J6", lx, kp.SV_HORN_Y[1], lz)
        j -= ycyl(p.X, p.Z, kp.M3_CLEAR, y0 - 1, y1 + 1)
        j -= ycyl(p.X, p.Z, kp.M3_CB_D, y0 + 2.0, y1 + 1)
    j -= ycyl(JX, JZ, kp.JAW_CAP_D, y1 - 2.0, y1 + 1)
    rd, rh = kp.HORN_RECESS
    j -= ycyl(JX, JZ, rd, y0 - 1, y0 + rh)
    return j


def jaw_cap():
    y1 = kp.JAW_Y[1]
    return ycyl(JX, JZ, kp.JAW_CAP_D + kp.PRESS, y1 - 2.0, y1)


PARTS = {"gripper": gripper, "grip_lid": grip_lid, "jaw": jaw, "jaw_cap": jaw_cap}
