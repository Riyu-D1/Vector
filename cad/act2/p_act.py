"""cad/act2/p_act.py - printed 40:1 cycloid actuator parts (module frame, see ap.py).
Written to the A1 stage spec: helpers verbatim, one function per part, PARTS dict.
Module frame: origin = centre of the BACK face, +Z toward the output face."""
import math, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "knuckle"))
from build123d import Box, Cone, Cylinder, Location, Polygon, Pos, Rot, extrude
from frames import zcyl
import ap, cyc

def pol(r, a):            # polar -> (x, y)
    return r * math.cos(math.radians(a)), r * math.sin(math.radians(a))

def ring(d_out, d_in, z0, z1):
    return zcyl(0, 0, d_out, z0, z1) - zcyl(0, 0, d_in, z0 - 0.01, z1 + 0.01)

def radial_hole(d, r0, r1, ang, z):   # cylinder along the radius from r0 to r1 at angle ang, height z
    c = Rot(0, 90, 0) * Cylinder(d / 2, r1 - r0)          # axis now along X
    return Pos(0, 0, z) * Rot(0, 0, ang) * Pos((r0 + r1) / 2, 0, 0) * c

def radial_csk(ang, z):   # 90-deg countersink at the OD for ISO 10642 M3, apex inward
    c = Rot(0, -90, 0) * Cone(ap.CSK_D / 2, ap.CSK_HOLE / 2, (ap.CSK_D - ap.CSK_HOLE) / 2, align=None)
    return Pos(0, 0, z) * Rot(0, 0, ang) * Pos(ap.OD / 2 - (ap.CSK_D - ap.CSK_HOLE) / 2, 0, 0) * c


def housing():
    N, NP, R, RP, E = cyc.gear()
    h = zcyl(0, 0, ap.OD, 0, ap.Z_FRONT_RING[1])
    h -= zcyl(0, 0, ap.BORE_MOTOR, ap.Z_BACK[1], ap.Z_MID[0])
    h -= zcyl(0, 0, ap.BORE_PIN, ap.Z_MID[0], ap.Z_RINGPIN[1])
    h -= zcyl(0, 0, ap.SEAT_6808, ap.Z_PIN_RING[0], ap.Z_FRONT_RING[1] + 0.01)
    for k in range(NP):
        x, y = pol(R, 360.0 * k / NP)
        h -= zcyl(x, y, 2 * RP + 0.05, ap.Z_RINGPIN[0], ap.Z_RINGPIN[1])
    h -= Pos(0, 0, ap.Z_ENC_POCKET[1] / 2 - 0.005) * \
        Box(ap.ENC_W, ap.ENC_W, ap.Z_ENC_POCKET[1] + 0.01)        # AS5600 pocket, open to back
    h -= zcyl(0, 0, ap.ENC_WINDOW_D, 1.7, ap.Z_BACK[1] + 0.01)   # chip window (was 1.9, gate fallback)
    for k in range(ap.LINK_N):
        x, y = pol(ap.LINK_PCD / 2, ap.LINK_ANG0 + 60 * k)
        h -= zcyl(x, y, ap.LINK_PILOT_D, -0.01, ap.LINK_PILOT_L)
    z0, z1 = ap.Z_BACK[1] - 0.01, ap.Z_MID[0] + 0.01             # axial wire channel
    h -= Rot(0, 0, ap.WIRE_ANG) * Pos((ap.WIRE_R[0] + ap.WIRE_R[1]) / 2, 0, (z0 + z1) / 2) * \
        Box(ap.WIRE_R[1] - ap.WIRE_R[0], ap.WIRE_W, z1 - z0)
    h -= Rot(0, 0, ap.WIRE_ANG) * Pos((22.0 + ap.OD / 2 + 1) / 2, 0, (ap.NOTCH_Z[0] + ap.NOTCH_Z[1]) / 2) * \
        Box(ap.OD / 2 + 1 - 22.0, ap.NOTCH_W, ap.NOTCH_Z[1] - ap.NOTCH_Z[0])   # side notch
    r0, r1 = ap.ENC_W / 2 - 0.5, 22.5                            # back-face groove pocket -> notch
    h -= Rot(0, 0, ap.WIRE_ANG) * Pos((r0 + r1) / 2, 0, (ap.ENC_GROOVE_D - 0.01) / 2) * \
        Box(r1 - r0, ap.ENC_GROOVE_W, ap.ENC_GROOVE_D + 0.01)
    for a in ap.CSK_ANG:
        h -= radial_hole(ap.CSK_HOLE, ap.OD / 2 - 4, ap.OD / 2 + 0.1, a, ap.CSK_Z)
        h -= radial_csk(a, ap.CSK_Z)
    return h


def mid_plate():
    m = zcyl(0, 0, ap.MID_D, *ap.Z_MID)
    m -= zcyl(0, 0, ap.STATOR_HOLE_D, ap.Z_MID[0] - 0.01, ap.Z_MID[1] + 0.01)
    for a in ap.MOT_SCREW_ANG:
        x, y = pol(ap.MOT_PCD / 2, a)
        m -= zcyl(x, y, 3.4, ap.Z_MID[0] - 0.01, ap.Z_MID[1] + 0.01)
        m -= zcyl(x, y, ap.MID_CB_D, ap.Z_MID[1] - ap.MID_CB_H, ap.Z_MID[1] + 0.01)
    for a in ap.CSK_ANG:
        m -= radial_hole(ap.CSK_PILOT, ap.MID_D / 2 - ap.CSK_PILOT_L, ap.MID_D / 2 + 0.1, a, ap.CSK_Z)
    r0, r1 = 6.0 - 0.01, ap.OD / 2 + 0.1                         # back-face wire groove (0.01 into the r6 stator hole: tangent face fix)
    z0, z1 = ap.Z_MID[0] - 0.01, ap.Z_MID[0] + ap.MID_GROOVE[1]
    m -= Rot(0, 0, ap.WIRE_ANG) * Pos((r0 + r1) / 2, 0, (z0 + z1) / 2) * \
        Box(r1 - r0, ap.MID_GROOVE[0], z1 - z0)
    return m


def hub():
    N, NP, R, RP, E = cyc.gear()
    h = zcyl(E, 0, ap.CAM_D, ap.Z_HUB[0], ap.Z_CAM_SPLIT)
    h += zcyl(-E, 0, ap.CAM_D, ap.Z_CAM_SPLIT, ap.Z_STUB0)
    h += zcyl(0, 0, ap.STUB_D, ap.Z_STUB0, ap.Z_HUB[1])
    h -= zcyl(0, 0, ap.HUB_BORE, ap.Z_HUB[0] - 0.01, ap.Z_HUB[0] + ap.HUB_BORE_L)
    h -= radial_hole(ap.GRUB_PILOT, 1.5, ap.CAM_D / 2 + 1, 90, ap.GRUB_Z)
    return h


def disc(second):
    N, NP, R, RP, E = cyc.gear()
    pts = cyc.disc_outline(second=second, m=ap.DISC_M)
    d = extrude(Polygon(*[tuple(map(float, p)) for p in pts], align=None), amount=4.0)
    d -= Cylinder(ap.DISC_BORE / 2, 20)
    hole_d = ap.OUT_PIN_D + 2 * E + 2 * ap.CLR_TOOTH
    for k in range(ap.OUT_PIN_N):
        x, y = pol(ap.OUT_PIN_PCD / 2, ap.OUT_PIN_ANG0 + 60 * k)
        d -= zcyl(x, y, hole_d, -0.01, 4.01)
    if second:
        return Pos(-E, 0, ap.Z_DISC2[0]) * d
    return Pos(E, 0, ap.Z_DISC1[0]) * d


def disc1():
    return disc(False)


def disc2():
    return disc(True)


def carrier():
    c = zcyl(0, 0, ap.PLATE_D, *ap.Z_CARRIER_PLATE)
    c += zcyl(0, 0, ap.SPIGOT_D, *ap.Z_SPIGOT)
    c -= zcyl(0, 0, ap.SEAT_685, ap.Z_685[0] - 0.01, ap.Z_685[1])
    for k in range(ap.OUT_PIN_N):
        x, y = pol(ap.OUT_PIN_PCD / 2, ap.OUT_PIN_ANG0 + 60 * k)
        c -= zcyl(x, y, ap.OUT_PIN_PRESS, ap.Z_CARRIER_PLATE[0] - 0.01, ap.Z_OUTPIN[1])
    for a in ap.OUT_M3_ANG:
        x, y = pol(ap.OUT_M3_PCD / 2, a)
        c -= zcyl(x, y, ap.INS_M3_D, ap.Z_SPIGOT[1] - ap.INS_M3_L, ap.Z_SPIGOT[1] + 0.01)
    for a in ap.OUT_DOWEL_ANG:
        x, y = pol(ap.OUT_DOWEL_PCD / 2, a)
        c -= zcyl(x, y, ap.OUT_DOWEL_HOLE, ap.Z_SPIGOT[1] - ap.OUT_DOWEL_DEPTH, ap.Z_SPIGOT[1] + 0.01)
    return c


def out_flange():
    f = zcyl(0, 0, ap.FLANGE_D, *ap.Z_FLANGE)
    for a in ap.OUT_M3_ANG:
        x, y = pol(ap.OUT_M3_PCD / 2, a)
        f -= zcyl(x, y, 3.4, ap.Z_FLANGE[0] - 0.01, ap.Z_FLANGE[1] + 0.01)
    for a in ap.OUT_DOWEL_ANG:
        x, y = pol(ap.OUT_DOWEL_PCD / 2, a)
        f -= zcyl(x, y, ap.OUT_DOWEL_FLANGE_HOLE, ap.Z_FLANGE[0] - 0.01, ap.Z_FLANGE[1] + 0.01)
    return f


def pin_ring():
    return ring(*ap.PIN_RING, *ap.Z_PIN_RING)


def front_ring():
    return ring(*ap.FRONT_RING, *ap.Z_FRONT_RING)


# ---- bought parts as plain solids (vendor_*: gate.py treats them as bought) ----
def vendor_motor():
    return zcyl(0, 0, ap.MOT_D, *ap.Z_MOTOR) + \
        zcyl(0, 0, ap.SHAFT_D, ap.Z_MOTOR[1], ap.Z_MOTOR[1] + ap.SHAFT_OUT)


def vendor_magnet():
    return zcyl(0, 0, ap.MAG[0], *ap.Z_MAG)


def vendor_ringpins():
    N, NP, R, RP, E = cyc.gear()
    s = None
    for k in range(NP):
        x, y = pol(R, 360.0 * k / NP)
        p = zcyl(x, y, 2 * RP, *ap.Z_RINGPIN)
        s = p if s is None else s + p
    return s


def vendor_outpins():
    s = None
    for k in range(ap.OUT_PIN_N):
        x, y = pol(ap.OUT_PIN_PCD / 2, ap.OUT_PIN_ANG0 + 60 * k)
        p = zcyl(x, y, ap.OUT_PIN_D, *ap.Z_OUTPIN)
        s = p if s is None else s + p
    return s


def vendor_dowels():
    s = None
    for a in ap.OUT_DOWEL_ANG:
        x, y = pol(ap.OUT_DOWEL_PCD / 2, a)
        p = zcyl(x, y, ap.OUT_DOWEL_D, ap.Z_SPIGOT[1] - ap.OUT_DOWEL_DEPTH,
                 ap.Z_FLANGE[1] + ap.OUT_DOWEL_PROUD)
        s = p if s is None else s + p
    return s


def vendor_6808():
    return ring(ap.BRG_OUT[1], ap.BRG_OUT[0], *ap.Z_6808)


def vendor_6702a():
    N, NP, R, RP, E = cyc.gear()
    return Pos(E, 0, 0) * ring(ap.BRG_ECC[1], ap.BRG_ECC[0], *ap.Z_DISC1)


def vendor_6702b():
    N, NP, R, RP, E = cyc.gear()
    return Pos(-E, 0, 0) * ring(ap.BRG_ECC[1], ap.BRG_ECC[0], *ap.Z_DISC2)


def vendor_685():
    return ring(ap.BRG_FRONT[1], ap.BRG_FRONT[0], *ap.Z_685)


def vendor_as5600():    # AS5600 board proxy: fills the encoder pocket (23 x 23 board)
    return Pos(0, 0, (ap.Z_ENC_POCKET[0] + ap.Z_ENC_POCKET[1]) / 2) * \
        Box(ap.ENC_W - 0.4, ap.ENC_W - 0.4, ap.Z_ENC_POCKET[1] - ap.Z_ENC_POCKET[0])


PARTS = {"housing": housing, "mid_plate": mid_plate, "hub": hub,
         "disc1": disc1, "disc2": disc2, "carrier": carrier,
         "out_flange": out_flange, "pin_ring": pin_ring, "front_ring": front_ring,
         "vendor_motor": vendor_motor, "vendor_magnet": vendor_magnet,
         "vendor_ringpins": vendor_ringpins, "vendor_outpins": vendor_outpins,
         "vendor_dowels": vendor_dowels, "vendor_6808": vendor_6808,
         "vendor_6702a": vendor_6702a, "vendor_6702b": vendor_6702b,
         "vendor_685": vendor_685, "vendor_as5600": vendor_as5600}
