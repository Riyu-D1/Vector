"""cad/knuckle/p_base.py - S1 parts: drum, drum_cap, turret, kn_endcap.
Copied verbatim from ~/Vector/stages/code/. G frame, home pose."""
import math

from build123d import Rot

import kp
from frames import gbox, mod_pt, ycyl, zcyl


def _polar(r, a):
    return r * math.cos(math.radians(a)), r * math.sin(math.radians(a))


def drum():
    a = zcyl(0, 0, kp.SKIRT_D, *kp.SKIRT_Z)
    a += zcyl(0, 0, kp.DRUM_OD, *kp.DRUM_Z)
    a -= zcyl(0, 0, kp.DRUM_ID, kp.FLOOR_Z[1], kp.SHELF_Z[0])
    a -= zcyl(0, 0, kp.FLOOR_HOLE_D, -1, kp.FLOOR_Z[1] + 1)
    bulk = zcyl(0, 0, kp.DRUM_ID, *kp.J1_BULK_Z) - zcyl(0, 0, kp.J1_BULK_HOLE_D, 18, 24)
    a += bulk
    a -= zcyl(0, 0, kp.SHELF_ID, kp.SHELF_Z[0] - 1, kp.SHELF_Z[1] + 0.01)
    a -= zcyl(0, 0, kp.SEAT_D, kp.BRG_Z[0], kp.DRUM_Z[1] + 1)
    for ang in kp.G10_BACK_ANG:                      # J1 back face, M2.5
        p = mod_pt("J1", kp.G10_BACK_PCD / 2, ang, kp.G4305_10_BACK_Z)
        a -= zcyl(p.X, p.Y, kp.M25_CLEAR, 18, 24)
    for px, py in kp.POSTS:                          # M4 hold-downs
        a -= zcyl(px, py, kp.M4_CLEAR, -1, 11)
        a -= zcyl(px, py, kp.M4_CB_D, kp.SKIRT_Z[1] - kp.M4_CB_H, 11)
    a -= Rot(0, 0, kp.CABLE_ANG) * gbox(40, 70, -6, 6, -1, 8)       # cable notch
    a -= Rot(0, 0, kp.CABLE_ANG) * gbox(30, 44, -6, 6, 18, 24)      # bulkhead slot
    for ang in kp.CAP_SCREW_ANG:                     # M3 heat-set inserts
        x, y = _polar(kp.CAP_SCREW_R, ang)
        a -= zcyl(x, y, kp.INS_M3_D, kp.DRUM_Z[1] - kp.INS_M3_L, kp.DRUM_Z[1] + 1)
    return a


def drum_cap():
    c = zcyl(0, 0, kp.DRUM_OD, *kp.CAP_Z) - zcyl(0, 0, kp.CAP_ID, kp.CAP_Z[0] - 1, kp.CAP_Z[1] + 1)
    for ang in kp.CAP_SCREW_ANG:
        x, y = _polar(kp.CAP_SCREW_R, ang)
        c -= zcyl(x, y, kp.M3_CLEAR, kp.CAP_Z[0] - 1, kp.CAP_Z[1] + 1)
        c -= zcyl(x, y, kp.M3_CB_D, kp.CAP_Z[1] - kp.M3_CB_H, kp.CAP_Z[1] + 1)
    return c


def turret():
    t = zcyl(0, 0, kp.HUB_D, kp.HUB_Z[0], kp.SPIGOT_Z[1])
    t += zcyl(0, 0, kp.FLANGE_D, *kp.FLANGE_Z)
    t += zcyl(0, 0, kp.HAT_D, *kp.HAT_Z)
    t += zcyl(0, 0, kp.HAT_D, *kp.LIP_Z) - zcyl(0, 0, kp.LIP_ID, kp.LIP_Z[0] - 1, kp.LIP_Z[1] + 1)
    t += zcyl(0, kp.COLUMN_CY, kp.COLUMN_D, *kp.COLUMN_Z)
    t += ycyl(0, 150, kp.KN_D, *kp.KN_Y)
    # voids
    t -= zcyl(0, 0, kp.SPIGOT_ID, kp.HUB_Z[1], kp.HAT_Z[0])
    t -= zcyl(0, kp.COLUMN_CY, kp.COLUMN_ID, *kp.COLUMN_VOID_Z)
    t -= ycyl(0, 150, kp.KN_BORE_D, kp.KN_Y[0] - 1, kp.KN_BULK_Y[0])
    t -= ycyl(0, 150, kp.KN_BULK_HOLE_D, kp.KN_BULK_Y[0] - 1, kp.KN_BULK_Y[1] + 1)
    t -= ycyl(0, 150, kp.KN_BORE_D, kp.KN_CAV_Y[0], kp.KN_Y[1] + 1)
    for ang in kp.G36_BACK_ANG:                      # J2 back face, M3
        p = mod_pt("J2", kp.G36_BACK_PCD / 2, ang, kp.G36_BACK_Z)
        t -= ycyl(p.X, p.Z, kp.M3_CLEAR, kp.KN_BULK_Y[0] - 0.8, kp.KN_BULK_Y[1] + 0.8)
    t -= ycyl(kp.TUNNEL_X, 150, kp.TUNNEL_D, kp.KN_Y[0] - 1, 30)        # tunnel
    t -= gbox(-34.5, -26.0, 22.0, 30.0, 147.5, 152.5)                   # cavity -> tunnel
    rx, ry, rd, rz0, rz1 = kp.RISER
    t -= zcyl(rx, ry, rd, rz0, rz1)                                     # column -> cavity
    z0, z1, w = kp.SPIGOT_SLOT
    t -= Rot(0, 0, kp.CABLE_ANG) * gbox(20, 35, -w / 2, w / 2, z0, z1)  # spigot slot
    for ang in kp.G10_OUT_ANG:                       # J1 output, M3 x5
        p = mod_pt("J1", kp.G10_OUT_PCD / 2, ang, 0)
        t -= zcyl(p.X, p.Y, kp.M3_FIT, kp.HUB_Z[0] - 1, kp.HUB_Z[1] + 1)
        t -= zcyl(p.X, p.Y, kp.M3_CB_D, kp.HUB_Z[1] - kp.M3_CB_H, kp.HUB_Z[1] + 1)
    return t


def kn_endcap():
    y0, y1, y2 = kp.KN_ENDCAP
    e = ycyl(0, 150, kp.KN_D, y1, y2)
    e += ycyl(0, 150, kp.KN_BORE_D + kp.PRESS, y0, y1) - ycyl(0, 150, kp.KN_BORE_D + kp.PRESS - 4.0, y0 - 1, y1 + 0.01)
    return e


PARTS = {"drum": drum, "drum_cap": drum_cap, "turret": turret, "kn_endcap": kn_endcap}
