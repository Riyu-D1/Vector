"""cad/knuckle/p_upper.py - S2 parts: upper_arm, upper_cover. Copied verbatim."""
import kp
from frames import gbox, mod_pt, ycyl, yprism

TRAP = [(0, 150 + kp.UA_R0), (150, 150 + kp.UA_R1), (150, 150 - kp.UA_R1), (0, 150 - kp.UA_R0)]
TRAP_IN = [(0, 150 + kp.UA_R0 - kp.WALL), (150, 150 + kp.UA_R1 - kp.WALL),
           (150, 150 - kp.UA_R1 + kp.WALL), (0, 150 - kp.UA_R0 + kp.WALL)]


def _outline(y0, y1):
    return (ycyl(0, 150, 2 * kp.UA_R0, y0, y1) + ycyl(150, 150, 2 * kp.UA_R1, y0, y1)
            + yprism(TRAP, y0, y1))


def _inner(y0, y1):
    return (ycyl(0, 150, 2 * kp.UA_R0 - 2 * kp.WALL, y0, y1)
            + ycyl(150, 150, 2 * kp.UA_R1 - 2 * kp.WALL, y0, y1) + yprism(TRAP_IN, y0, y1))


def upper_arm():
    yt, yb = kp.UA_Y                                   # -25.0, -74.8
    u = _outline(yb, yt)
    u -= _inner(yb - 1, yt - kp.WALL)                  # open at -Y, +Y wall 2.4
    u += ycyl(0, 150, 2 * kp.UA_R0, kp.UA_HUB_Y[1], kp.UA_HUB_Y[0])     # J2 hub disc
    u += ycyl(150, 150, kp.J3_SLEEVE_OD, kp.J3_BULK_Y[0], yt)           # J3 sleeve
    u += ycyl(150, 150, kp.J3_SLEEVE_OD, kp.J3_BULK_Y[1], kp.J3_BULK_Y[0])  # J3 bulkhead
    for x, z in kp.UA_PILLARS:
        u += ycyl(x, z, kp.UA_PILLAR_D, yb, yt - kp.WALL)
    # cuts
    u -= ycyl(150, 150, kp.J3_BORE_D, kp.J3_BULK_Y[0], yt + 1)
    u -= ycyl(150, 150, 41.0, kp.J3_BULK_Y[1] - 1, kp.J3_BULK_Y[0] + 1)
    for ang in kp.G10_BACK_ANG:                        # J3 back face, M2.5
        p = mod_pt("J3", kp.G10_BACK_PCD / 2, ang, kp.G4310_10_BACK_Z)
        u -= ycyl(p.X, p.Z, kp.M25_CLEAR, kp.J3_BULK_Y[1] - 1, kp.J3_BULK_Y[0] + 0.7)
    for x, z in kp.UA_PILLARS:                         # magnets
        u -= ycyl(x, z, kp.MAG_D, yb - 1, yb + kp.MAG_L)
    for ang in kp.G36_PIN_ANG:                         # J2 dowel pins
        p = mod_pt("J2", kp.G36_PIN_PCD / 2, ang, 0)
        u -= ycyl(p.X, p.Z, 4.3, -27.6, yt + 1)
    for ang in kp.G36_OUT_ANG:                         # J2 output M3 x6
        p = mod_pt("J2", kp.G36_OUT_PCD / 2, ang, 0)
        u -= ycyl(p.X, p.Z, kp.M3_FIT, kp.UA_HUB_Y[1] - 1, yt + 1)
        u -= ycyl(p.X, p.Z, kp.M3_CB_D, kp.UA_HUB_Y[1] - 1, -28.0)
    r0, r1, d = kp.UA_GROOVE                           # J2 service-loop groove
    u -= ycyl(0, 150, 2 * r1, yt - d, yt + 1) - ycyl(0, 150, 2 * r0, yt - d - 1, yt + 2)
    u -= ycyl(32.0, 150, kp.UA_EXIT_D, kp.UA_HUB_Y[1] - 1, yt - d + 0.5)   # groove exit
    rd, rh = kp.J2_RING                                # J2 output ring recess
    u -= ycyl(0, 150, rd, yt - rh, yt + 1)
    nr0, nr1, nw = kp.J3_NOTCH                         # J3 notch (module angle 180)
    u -= gbox(150 - nr1, 150 - nr0, -28.0, -24.0, 150 - nw / 2, 150 + nw / 2)
    return u


def upper_cover():
    y0, y1 = kp.UA_COVER_Y                             # -74.8, -79.8 (y0 > y1)
    c = _outline(y1, y0)
    for x, z in kp.UA_PILLARS:
        c -= ycyl(x, z, kp.MAG_D, y0 - kp.MAG_L, y0 + 1)
    return c


PARTS = {"upper_arm": upper_arm, "upper_cover": upper_cover}
