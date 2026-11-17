"""cad/act2/parts.py - printed 40:1 cycloid actuator parts (module frame, see ap.py).
Copied verbatim from ~/Vector/stages/code/act2/. Change numbers only in ap.py."""
import math
from build123d import Box, Cylinder, Polyline, Pos, Rot, extrude, make_face
import ap
from cyclo import disc_profile


def zc(x, y, d, z0, z1):
    """Cylinder along Z, centre (x, y), from z0 to z1."""
    return Pos(x, y, (z0 + z1) / 2) * Cylinder(d / 2, z1 - z0)


def pc(r, ang, d, z0, z1):
    """zc at polar (r, ang deg)."""
    a = math.radians(ang)
    return zc(r * math.cos(a), r * math.sin(a), d, z0, z1)


def slot(r0, r1, ang, w, z0, z1):
    """Radial slot (stadium) from radius r0 to r1 at angle ang, width w."""
    a = math.radians(ang)
    rm = (r0 + r1) / 2
    b = Pos(rm * math.cos(a), rm * math.sin(a), (z0 + z1) / 2) * Rot(0, 0, ang) * Box(r1 - r0, w, z1 - z0)
    return b + pc(r0, ang, w, z0, z1) + pc(r1, ang, w, z0, z1)


def body():
    b = zc(0, 0, ap.OD, 0, ap.Z_BODY_TOP) + zc(0, 0, ap.PILOT_D, ap.Z_BOSS, 0)
    b -= zc(0, 0, ap.MOT_BORE_D, ap.Z_MOT, ap.Z_FLOOR)
    b -= zc(0, 0, 2 * ap.RING_BORE_R, ap.Z_FLOOR, ap.Z_BODY_TOP)
    for k in range(ap.N_PINS):
        b -= pc(ap.PIN_R, 360.0 * k / ap.N_PINS, ap.GROOVE_D, ap.Z_GROOVE, ap.Z_BODY_TOP + 1)
    for a in ap.BACK_ANG:
        b -= pc(ap.BACK_PCD / 2, a, ap.M3_PILOT, -0.01, ap.Z_MOT - 0.5)
    for a in ap.CAP_SCREW_ANG:
        b -= pc(ap.CAP_SCREW_R, a, ap.M2_PILOT, ap.Z_BODY_TOP - ap.CAP_PILOT_DEPTH, ap.Z_BODY_TOP + 1)
    ex, ey = ap.ENC_POCKET
    b -= Pos(0, 0, (ap.Z_BOSS - 1 + ap.Z_ENC_FLOOR) / 2) * Box(ex, ey, ap.Z_ENC_FLOOR - ap.Z_BOSS + 1)
    b -= zc(0, 0, ap.ENC_HOLE_D, ap.Z_BOSS - 1, ap.Z_MOT + 1)
    for a in ap.MOT_SLOT_ANG:
        b -= slot(*ap.MOT_SLOT_R, a, ap.M3_CLEAR, ap.Z_BOSS - 1, ap.Z_MOT + 1)
        b -= slot(*ap.MOT_SLOT_R, a, ap.MOT_CB_D, ap.Z_BOSS - 1, 2.3)
    b -= pc(ap.WIRE_R, ap.WIRE_ANG, ap.WIRE_D, ap.Z_BOSS - 1, ap.Z_MOT + 1)
    b -= slot(ap.WIRE_R, ap.MOT_BORE_D / 2 + 1, ap.WIRE_ANG, ap.WIRE_D, ap.Z_WIRE_SLOT, ap.Z_MOT + 1)
    return b


def cam():
    c = zc(0, 0, ap.HUB_D, ap.Z_BELL, ap.Z_HUB_TOP)
    c += zc(ap.E, 0, ap.SHOULDER_D, ap.Z_HUB_TOP - 0.01, ap.Z_DISC)
    c += zc(ap.E, 0, ap.B_DISC[0], ap.Z_DISC - 0.01, ap.Z_DISC_TOP)
    c -= zc(0, 0, 8.0, ap.Z_BELL - 1, ap.Z_DISC_TOP + 1)
    for a in ap.BELL_SCREW_ANG:
        c -= slot(*ap.BELL_SCREW_R, a, ap.M3_CLEAR, ap.Z_BELL - 1, ap.Z_DISC_TOP + 1)
    return c


def disc():
    pts = [tuple(p) for p in disc_profile(ap.PIN_R, ap.RP, ap.E, ap.N_PINS, ap.D_MOD)]
    f = make_face(Polyline(*pts, close=True))
    d = Pos(ap.E, 0, ap.Z_DISC) * extrude(f, ap.DISC_T)
    d -= zc(ap.E, 0, ap.B_DISC[1], ap.Z_DISC - 1, ap.Z_DISC_TOP + 1)
    for a in ap.OUTPIN_ANG:
        r = math.radians(a)
        d -= zc(ap.E + ap.OUTPIN_R * math.cos(r), ap.OUTPIN_R * math.sin(r), ap.DISC_HOLE_D,
                ap.Z_DISC - 1, ap.Z_DISC_TOP + 1)
    return d


def out():
    o = zc(0, 0, ap.CAR_D, ap.Z_CAR, ap.Z_CAR_TOP) + zc(0, 0, ap.B_OUT[0], ap.Z_CAR_TOP - 0.01, ap.Z_OUT)
    o -= zc(0, 0, ap.CAR_HOLE_D, ap.Z_CAR - 1, ap.Z_CAR_TOP)
    o -= zc(0, 0, ap.CENTRE_D, ap.Z_CAR_TOP - 0.5, ap.Z_OUT + 1)
    for a in ap.OUTPIN_ANG:
        o -= pc(ap.OUTPIN_R, a, ap.OUTPIN_D, ap.Z_CAR - 1, ap.Z_CAR + ap.OUTPIN_DEPTH)
    for a in ap.OUT_ANG:
        o -= pc(ap.OUT_PCD / 2, a, ap.INS_M3_D, ap.Z_OUT - ap.INS_M3_L, ap.Z_OUT + 1)
    for a in ap.OPIN_ANG:
        o -= pc(ap.OPIN_PCD / 2, a, ap.OPIN_D, ap.Z_OUT - ap.OPIN_DEPTH, ap.Z_OUT + 1)
    return o


def cap():
    z1 = ap.Z_LIP + ap.LIP_T
    c = zc(0, 0, ap.OD, ap.Z_BODY_TOP, z1)
    c -= zc(0, 0, ap.CAP_BORE_D, ap.Z_BODY_TOP - 1, ap.Z_BRG + 0.01)
    c -= zc(0, 0, ap.B_OUT[1], ap.Z_BRG, ap.Z_LIP)
    c -= zc(0, 0, ap.LIP_D, ap.Z_LIP - 0.01, z1 + 1)
    for a in ap.CAP_SCREW_ANG:
        c -= pc(ap.CAP_SCREW_R, a, ap.M2_CLEAR, ap.Z_BODY_TOP - 1, z1 + 1)
    return c


# ---- bought parts as plain solids (buy_*: checked by the gate, never printed) ----
def v_motor():
    return zc(0, 0, ap.MOT_D, ap.Z_MOT, ap.Z_BELL)


def v_ringpins():
    s = None
    for k in range(ap.N_PINS):
        p = pc(ap.PIN_R, 360.0 * k / ap.N_PINS, 2 * ap.RP, ap.Z_GROOVE, ap.Z_BODY_TOP)
        s = p if s is None else s + p
    return s


def v_outpins():
    s = None
    for a in ap.OUTPIN_ANG:
        p = pc(ap.OUTPIN_R, a, ap.OUTPIN_D, ap.Z_CAR + ap.OUTPIN_DEPTH - 12.0, ap.Z_CAR + ap.OUTPIN_DEPTH)
        s = p if s is None else s + p
    return s


def v_bearings():
    d, D, B = ap.B_DISC
    s = zc(ap.E, 0, D, ap.Z_DISC, ap.Z_DISC + 2 * B) - zc(ap.E, 0, d, ap.Z_DISC - 1, ap.Z_DISC + 2 * B + 1)
    d, D, B = ap.B_OUT
    s += zc(0, 0, D, ap.Z_BRG, ap.Z_BRG + B) - zc(0, 0, d, ap.Z_BRG - 1, ap.Z_BRG + B + 1)
    return s


PARTS = {"act_body": body, "act_cam": cam, "act_disc": disc, "act_out": out, "act_cap": cap,
         "buy_motor": v_motor, "buy_ringpins": v_ringpins,
         "buy_outpins": v_outpins, "buy_bearings": v_bearings}
