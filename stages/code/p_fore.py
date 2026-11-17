"""cad/knuckle/p_fore.py - S3 parts: forearm, fa_endcap, fa_elbow_cap. Copied verbatim."""
import kp
from frames import gbox, mod_pt, sbox, xcyl, ycyl

CY = kp.FA_TUBE_CY


def forearm():
    y0, y1 = kp.FA_Y
    f = ycyl(150, 150, kp.FA_CAP_D, y0, y1) + xcyl(CY, 150, kp.FA_TUBE_D, 150, kp.FA_END_X)
    f += gbox(*kp.BLISTER_OUT)
    # hollow: cap interior + tube bore (bore kept above the hub plane y=-17.2)
    f -= ycyl(150, 150, kp.FA_CAP_D - 2 * kp.WALL, kp.FA_HUB_Y[1], y1 - kp.WALL)
    f -= xcyl(CY, 150, kp.FA_TUBE_ID, 150, kp.FA_FILLER_X[0]) & gbox(
        150, kp.FA_FILLER_X[0] + 0.01, kp.FA_HUB_Y[1], 40, 100, 200)
    # J4 servo pocket + end insertion slot + side hole
    f -= sbox("J4", kp.SV_X[0] - kp.SLIP, kp.SV_X[1] + kp.SLIP, kp.SV_Y[0] - kp.SLIP,
              kp.SV_Y[1] + kp.SLIP, kp.SV_Z[0] - kp.SLIP, kp.SV_Z[1] + kp.SLIP)
    f -= gbox(290.0, kp.FA_END_X + 1, -17.0, 19.0, 137.49, 162.51)
    f -= ycyl(280, 150, kp.J4_HOLE_D, 18.9, y1 + 1)
    f -= gbox(*kp.BLISTER_IN)
    f -= gbox(*kp.PASS)
    f -= gbox(*kp.CHANNEL)
    # J3 output: M3 x6 from inside, counterbore to y=-21.2
    for ang in kp.G10_OUT_ANG:
        p = mod_pt("J3", kp.G10_OUT_PCD / 2, ang, 0)
        f -= ycyl(p.X, p.Z, kp.M3_FIT, y0 - 1, kp.FA_HUB_Y[1] + 1)
        f -= ycyl(p.X, p.Z, kp.M3_CB_D, -21.2, kp.FA_HUB_Y[1] + 1)
    r0, r1, d = kp.FA_GROOVE
    f -= ycyl(150, 150, 2 * r1, y0 - 1, y0 + d) - ycyl(150, 150, 2 * r0, y0 - 2, y0 + d + 1)
    f -= ycyl(150 + 29.0, 150, 4.0, y0 + d - 0.8, kp.FA_HUB_Y[1] + 1)   # groove -> inside
    f -= ycyl(150, 150, kp.FA_ELBOW_CAP_D, y1 - kp.WALL - 0.4, y1 + 1)  # elbow access
    return f


def fa_endcap():
    x0, x1 = kp.FA_ENDCAP_X
    e = xcyl(CY, 150, kp.FA_TUBE_D, x0, x1)
    e += gbox(290.41, x0 + 0.01, -17.025, 19.025, 137.465, 162.535)  # press block
    return e


def fa_elbow_cap():
    y1 = kp.FA_Y[1]
    return ycyl(150, 150, kp.FA_ELBOW_CAP_D + kp.PRESS, y1 - kp.WALL, y1)


PARTS = {"forearm": forearm, "fa_endcap": fa_endcap, "fa_elbow_cap": fa_elbow_cap}
