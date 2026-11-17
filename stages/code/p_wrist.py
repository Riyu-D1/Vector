"""cad/knuckle/p_wrist.py - S4 parts: head, cup_cap, pod_front. Copied verbatim."""
import kp
from frames import gbox, xcyl, ycyl

HX, HZ = 280.0, 150.0                                   # J4 axis (x, z)
HORN = [(HX + 7, HZ), (HX - 7, HZ), (HX, HZ + 7), (HX, HZ - 7)]


def head():
    h = ycyl(HX, HZ, kp.CUP_D, *kp.CUP_Y) + ycyl(HX, HZ, kp.BOSS_D, *kp.BOSS_Y)
    h += gbox(*kp.SEG_A) + gbox(*kp.SEG_B) + gbox(*kp.POD)
    px0, px1, py0, py1, pz0, pz1 = kp.POD_POCKET
    h -= gbox(px0, px1 + 0.5, py0, py1, pz0, pz1)
    h -= gbox(*kp.POD_PLUG)
    cx0, cx1, cy0, cy1, cz0, cz1 = kp.POD_CHANNEL
    h -= gbox(cx0, cx1 + 0.5, cy0, cy1, cz0, cz1)
    h -= gbox(*kp.P1)
    h -= gbox(*kp.P2)
    r0, r1, d = kp.CUP_GROOVE
    y0 = kp.CUP_Y[0]
    h -= ycyl(HX, HZ, 2 * r1, y0 - 1, y0 + d) - ycyl(HX, HZ, 2 * r0, y0 - 2, y0 + d + 1)
    for x, z in HORN:                                   # J4 horn M3 x6
        h -= ycyl(x, z, kp.M3_CLEAR, kp.BOSS_Y[0] - 1, kp.CUP_Y[1] + 1)
        h -= ycyl(x, z, kp.M3_CB_D, 24.0, kp.CUP_Y[1] + 1)
    cd, ct = kp.CUP_CAP
    h -= ycyl(HX, HZ, cd, kp.CUP_Y[1] - ct, kp.CUP_Y[1] + 1)
    rd, rh = kp.HORN_RECESS
    h -= ycyl(HX, HZ, rd, kp.BOSS_Y[0] - 1, kp.BOSS_Y[0] + rh)
    for y, z in kp.POD_M2:                              # pod_front M2 pilots
        h -= xcyl(y, z, kp.M2_PILOT, 358.0, kp.POD[1] + 1)
    return h


def cup_cap():
    cd, ct = kp.CUP_CAP
    return ycyl(HX, HZ, cd + kp.PRESS, kp.CUP_Y[1] - ct, kp.CUP_Y[1])


def pod_front():
    x0, x1 = kp.POD_FRONT
    p = gbox(x0, x1, kp.POD[2], kp.POD[3], kp.POD[4], kp.POD[5])
    p -= xcyl(0, 150, 22.0, x0 - 1, x1 + 1)
    p -= xcyl(14.5, 150, 4.0, x0 - 1, x1 + 1)
    for y, z in kp.POD_M2:
        p -= xcyl(y, z, kp.M2_CLEAR, x0 - 1, x1 + 1)
    return p


PARTS = {"head": head, "cup_cap": cup_cap, "pod_front": pod_front}
