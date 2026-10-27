"""Parametric build123d parts for the SOMA 5010 cycloidal actuator.

Axes: actuator axis = +Z, output flange toward +Z.
Z-map (mm above rear end-cap face):

    0.0 .. 3.0    end cap (ESC + encoder posts, cable slot)
    3.0 .. 10.5   B-G431B-ESC1
    11.0 .. 12.6  AS5600 board
    14.5 .. 16.5  motor-shell floor (stator lands + shaft-tip hole)
    16.5 .. 49.2  MAD 5010 EEE motor (32.7)
    47.5 .. 51.5  motor-shaft puck (bolts to rotor top)
    51.5 .. 54.0  housing bottom floor
    54.0 .. 70.0  ring pins (16 x 6 mm)
    55.0 .. 60.0  cycloidal disc 1
    61.0 .. 66.0  cycloidal disc 2   (gap 60..61)
    67.0 .. 71.0  output pin plate (pins hang to 53.5)
    71.0 .. 85.0  output hub in stacked 6809 pair (71..78 + 78..85)
    81.0 .. 85.0  output flange plate (face = Z_MAX = 85)

Bearing note: the BOM lists 2x 6809ZZ "between output shaft and housing".
A lower spigot cannot pass through the disc zone (pins + wobbling discs
occupy r < 30), so both 6809s are a stacked pair on the top hub — stiffer
moment support anyway.  Documented in README.
"""

import math
import numpy as np
from build123d import (
    Plane, Mode, Part, Compound, Pos, Rot, Location,
    Cylinder, Box, Polygon, extrude,
)

from params import P, GearSpec, MR106, B6701, B6809
from cycloid import disc_profile

CLR = P.fd_clearance       # 0.2 mm radial FDM clearance
PRESS = P.press_clearance  # press-fit undersize on seats

# ---- Z-map ----------------------------------------------------------------
Z_FLOOR0, Z_FLOOR1 = 14.5, 16.5
Z_MOTOR1 = Z_FLOOR1 + P.motor.height            # 49.2
Z_PUCK0, Z_PUCK1 = 47.5, 51.5
Z_HFLOOR0, Z_HFLOOR1 = 51.5, 54.0
Z_PIN0, Z_PIN1 = 54.0, 70.0
Z_DISC1, Z_DISC2 = 55.0, 61.0                   # d1 55-60, d2 61-66
Z_PLATE0, Z_PLATE1 = 67.0, 71.0
Z_BRG1 = (71.0, 78.0)                           # lower of 6809 pair
Z_BRG2 = (78.0, 85.0)                           # upper of pair
Z_FL0, Z_FL1 = 81.0, 85.0                       # flange face = 85
Z_PINBOT = 53.5
Z_MAX = Z_FL1


def cz(r, h, z):
    """Cylinder centred on origin, bottom face at z."""
    return Pos(0, 0, z + h / 2) * Cylinder(r, h)


# ---------------------------------------------------------------------------
# Cycloidal disc (printed)
# ---------------------------------------------------------------------------

def cycloidal_disc(gear: GearSpec = P.gear) -> Part:
    xs, ys = disc_profile(720, gear)
    pin_hole_d = MR106.od + 2 * gear.eccentricity + 2 * 0.15      # ~13.3
    bore = B6701.od - PRESS                                       # 17.95
    pts = [(float(x), float(y)) for x, y in zip(xs, ys)]
    disc = extrude(Polygon(*pts), gear.disc_thickness)
    disc -= cz(bore / 2, gear.disc_thickness + 2, -1)
    r = P.out_pin_bcd / 2
    for i in range(P.n_out_pins):
        a = math.radians(60 * i)
        disc -= Pos(r * math.cos(a), r * math.sin(a), -1) * \
            Cylinder(pin_hole_d / 2, gear.disc_thickness + 2)
    return disc


# ---------------------------------------------------------------------------
# Housing (printed)
# ---------------------------------------------------------------------------

def housing(p: P = P) -> Part:
    g = p.gear
    od = p.housing_od
    id_r = od / 2 - p.wall                                  # 31
    z0, z1 = Z_HFLOOR0, Z_MAX + 0.5                         # 51.5 .. 85.5

    part = cz(od / 2, z1 - z0, z0)
    part -= cz(id_r, z1 - z0 + 2, z0 - 1)

    # bottom floor (web between motor bay and gear bay) + shaft hole
    floor = cz(id_r, Z_HFLOOR1 - Z_HFLOOR0, Z_HFLOOR0)
    floor -= cz(4.4, Z_HFLOOR1 - Z_HFLOOR0 + 2, Z_HFLOOR0 - 1)
    part += floor

    # pin-seat ring: land under the pins at Z_PIN0 (pin bottoms rest on it)
    part += (cz(id_r, 0.5, Z_PIN0 - 0.5) - cz(28.0, 1.0, Z_PIN0 - 0.5))

    # ring-gear grooves: axial slots cut into the wall at the pin circle.
    # each pin sits half in the wall (groove) and half exposed to the bore.
    for i in range(g.ring_pins):
        a = math.radians(360 * i / g.ring_pins)
        # groove (pin pocket)
        part -= Pos(g.pin_pitch_r * math.cos(a),
                    g.pin_pitch_r * math.sin(a),
                    (Z_PIN0 + Z_PIN1) / 2) * \
            Cylinder(g.pin_radius + CLR, Z_PIN1 - Z_PIN0 + 0.4)
        # radial opening from bore face (id_r) inward to pin centre + a bit
        r_out = id_r + 0.3                       # 31.3 (through wall face)
        r_in = g.pin_pitch_r - g.pin_radius      # 26
        rm = (r_out + r_in) / 2
        part -= Pos(rm * math.cos(a), rm * math.sin(a),
                    (Z_PIN0 + Z_PIN1) / 2) * \
            Rot(0, 0, math.degrees(a)) * \
            Box(r_out - r_in + 0.1, 2 * (g.pin_radius + CLR),
                Z_PIN1 - Z_PIN0 + 0.4)

    # bulkhead shelves carrying the stacked 6809 pair
    for (a0, a1) in (Z_BRG1, Z_BRG2):
        part += (cz(id_r, a1 - a0, a0) -
                 cz(B6809.od / 2 + CLR, a1 - a0 + 0.2, a0 - 0.1))

    # top rim ring above the upper bearing (retains it)
    part += (cz(od / 2, Z_MAX + 0.5 - Z_BRG2[1], Z_BRG2[1]) -
             cz(B6809.bore / 2 + 1.0, Z_MAX + 0.5 - Z_BRG2[1] + 0.2,
                Z_BRG2[1] - 0.1))

    # 4 x M3.4 through-holes on shell BCD (M3x55 clamp bolts)
    rb = p.shell_bolt_bcd / 2
    for i in range(p.shell_bolts):
        a = math.radians(90 * i + 45)
        part -= Pos(rb * math.cos(a), rb * math.sin(a), z0 + (z1 - z0) / 2) * \
            Cylinder(1.7, z1 - z0 + 2)
    # cable exit slot at rear rim
    part -= Pos(od / 2 - 4.0, 0, z0 + 2.5) * Box(8, 8, 6)
    return part


# ---------------------------------------------------------------------------
# Input shaft (printed, eccentric)
# ---------------------------------------------------------------------------

def input_shaft(p: P = P) -> Part:
    e = p.gear.eccentricity
    z_tip = 14.8
    part = cz(4.0, Z_PUCK1 - z_tip, z_tip)
    # square drive inside the puck
    part += Pos(0, 0, (Z_PUCK0 + Z_PUCK1) / 2) * Box(7.8, 7.8,
                                                   Z_PUCK1 - Z_PUCK0)
    # rise through housing floor to cam1
    part += cz(4.0, Z_DISC1 - Z_PUCK1, Z_PUCK1)
    # cam 1: concentric support boss + eccentric journal (OD 12 for 6701)
    part += cz(8.6, 1.5, Z_DISC1 - 1.0)                       # boss
    part += Pos(e, 0, 0) * cz(6.0, 4.6, Z_DISC1 + 0.2)        # journal +e
    part += Pos(e, 0, 0) * cz(7.0, 0.8, Z_DISC1 + 4.6)        # retainer lip
    # shaft between cams
    part += cz(4.0, Z_DISC2 - (Z_DISC1 + 5), Z_DISC1 + 5)
    # cam 2 (offset -e)
    part += cz(8.6, 1.5, Z_DISC2 - 1.0)
    part += Pos(-e, 0, 0) * cz(6.0, 4.6, Z_DISC2 + 0.2)
    part += Pos(-e, 0, 0) * cz(7.0, 0.8, Z_DISC2 + 4.6)
    # top pilot (MR106 in output hub) z=66..75.5
    part += cz(2.95, 9.5, Z_DISC2 + 5)
    # magnet pocket cut into the bottom face (magnet face flush at z_tip)
    part -= cz(p.encoder.magnet_d / 2 + 0.1, p.encoder.magnet_t + 0.3,
               z_tip)
    return part


# ---------------------------------------------------------------------------
# Output shaft (printed)
# ---------------------------------------------------------------------------

def output_shaft(p: P = P) -> Part:
    hub_r = B6809.bore / 2                      # 22.5
    part = cz(p.out_flange_od / 2, Z_FL1 - Z_FL0, Z_FL0)     # flange
    part += cz(hub_r - PRESS, Z_FL0 - Z_PLATE0, Z_PLATE0)    # hub+plate body
    rb = p.out_pin_bcd / 2
    for i in range(p.n_out_pins):
        a = math.radians(60 * i)
        x, y = rb * math.cos(a), rb * math.sin(a)
        part += Pos(x, y, 0) * cz(p.out_pin_d / 2 - 0.05,
                                  Z_PLATE0 - Z_PINBOT, Z_PINBOT)
        # M3.4 through-hole + insert pocket at the pin tip (roller retained
        # by an M3x25 screw + washer from below)
        part -= Pos(x, y, 0) * cz(1.7, Z_PLATE1 - Z_PINBOT + 0.4,
                                  Z_PINBOT - 0.2)
        part -= Pos(x, y, 0) * cz(2.3, 4.4, Z_PLATE1 - 4.4)
    # 8 x M3 holes on face BCD (arm interface), blind
    rb2 = p.face_bolt_bcd / 2
    for i in range(p.face_bolts):
        a = math.radians(45 * i + 22.5)
        part -= Pos(rb2 * math.cos(a), rb2 * math.sin(a), 0) * \
            cz(1.25, 6.0, Z_FL1 - 6.0)
    # MR106 pilot seat + pilot through-hole in the hub/plate centre
    part -= cz((MR106.od + CLR) / 2, 5.0, Z_PLATE1 + 1.0)
    part -= cz(3.1, Z_PLATE1 - Z_PLATE0 + 0.4, Z_PLATE0 - 0.2)
    # lighten hub: annular pocket keeping an OD16 core for the pilot seat
    part -= (cz(18.0, Z_FL0 - Z_PLATE1 - 0.8, Z_PLATE1 + 0.8) -
             cz(8.0, Z_FL0 - Z_PLATE1 - 0.6, Z_PLATE1 + 0.8))
    return part


# ---------------------------------------------------------------------------
# Motor shell (printed)
# ---------------------------------------------------------------------------

def motor_shell(p: P = P) -> Part:
    od = p.housing_od
    id_r = od / 2 - p.wall
    z0, z1 = 0.0, Z_HFLOOR0                                    # 0 .. 51.5
    # rear bay floor plate (full), then thin skin up to floor level
    part = cz(od / 2, Z_FLOOR1 - z0, z0)
    part -= cz(id_r, Z_FLOOR1 - 3.5 - z0, z0 + 3.5)            # bay cavity
    # centre hole through the floor for the shaft tip + magnet
    part -= cz(4.4, Z_FLOOR1 - z0 + 2, z0 - 1)
    # stator M3 lands on 25 + 30 BCD
    for bcd in (p.motor.stator_bcd1, p.motor.stator_bcd2):
        for i in range(4):
            a = math.radians(90 * i + 45)
            part -= Pos(bcd / 2 * math.cos(a), bcd / 2 * math.sin(a), 0) * \
                cz(1.25, Z_FLOOR1 - Z_FLOOR0 + 0.4, Z_FLOOR0 - 0.2)
    # 4 pillars floor->housing bottom, M3 insert pockets on top
    for i in range(p.shell_bolts):
        a = math.radians(90 * i + 45)
        r_in = id_r + 0.5
        rm = (od / 2 + r_in) / 2
        part += Pos(rm * math.cos(a), rm * math.sin(a),
                    (Z_FLOOR1 + z1) / 2) * Rot(0, 0, math.degrees(a)) * \
            Box(od / 2 - r_in, 15.0, z1 - Z_FLOOR1)
        part -= Pos(rm * math.cos(a), rm * math.sin(a), 0) * \
            cz(2.3, 4.4, z1 - 4.4)
    # skin between pillars over the motor
    part += (cz(od / 2, z1 - Z_FLOOR1, Z_FLOOR1) -
             cz(id_r, z1 - Z_FLOOR1 + 0.2, Z_FLOOR1 - 0.1))
    # windows between pillars (wiring + cooling)
    for i in range(p.shell_bolts):
        a = math.radians(90 * i)
        part -= Pos(id_r * math.cos(a), id_r * math.sin(a), Z_FLOOR1 + 17) * \
            Rot(0, 0, math.degrees(a)) * Box(9, 28, 24)
    # cable slot at rear rim
    part -= Pos(od / 2 - 4.0, 0, 2.5) * Box(8, 8, 6)
    # 4 x M3.4 clamp-bolt through-holes at rear face
    rb = p.shell_bolt_bcd / 2
    for i in range(4):
        a = math.radians(90 * i + 45)
        part -= Pos(rb * math.cos(a), rb * math.sin(a), 0) * \
            cz(1.7, Z_FLOOR1 + 2, -1)
    return part


# ---------------------------------------------------------------------------
# End cap (printed)
# ---------------------------------------------------------------------------

def end_cap(p: P = P) -> Part:
    od = p.housing_od
    part = cz(od / 2, 3.0, 0.0)
    hp = p.esc.hole_pitch / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            part += Pos(sx * hp, sy * hp, 0) * cz(3.0, 2.0, 3.0)
            part -= Pos(sx * hp, sy * hp, 0) * cz(0.9, 2.2, 2.9)
    eh = p.encoder.hole_pitch / 2
    for sx in (-1, 1):
        part += Pos(sx * eh, 0, 0) * cz(2.5, 8.0, 3.0)
        part -= Pos(sx * eh, 0, 0) * cz(0.9, 8.2, 2.9)
    part -= Pos(od / 2 - 4.0, 0, 1.5) * Box(8, 8, 3.2)
    rb = p.shell_bolt_bcd / 2
    for i in range(4):
        a = math.radians(90 * i + 45)
        part -= Pos(rb * math.cos(a), rb * math.sin(a), 0) * \
            cz(1.7, 3.2, -0.1)
    return part


# ---------------------------------------------------------------------------
# Motor-shaft puck (printed)
# ---------------------------------------------------------------------------

def motor_shaft(p: P = P) -> Part:
    part = cz(22.0, Z_PUCK1 - Z_PUCK0, Z_PUCK0)
    for i in range(4):
        a = math.radians(90 * i + 45)
        part -= Pos(14.5 * math.cos(a), 14.5 * math.sin(a), 0) * \
            cz(4.5, Z_PUCK1 - Z_PUCK0 + 0.4, Z_PUCK0 - 0.2)
    part -= Pos(0, 0, (Z_PUCK0 + Z_PUCK1) / 2) * \
        Box(8.0, 8.0, Z_PUCK1 - Z_PUCK0 + 0.4)
    for bcd, n in ((p.motor.rotor_bcd1, 2), (p.motor.rotor_bcd2, 4)):
        for i in range(n):
            a = math.radians(360 * i / n + 45)
            part -= Pos(bcd / 2 * math.cos(a), bcd / 2 * math.sin(a), 0) * \
                cz(1.7, Z_PUCK1 - Z_PUCK0 + 0.4, Z_PUCK0 - 0.2)
    return part


# ---------------------------------------------------------------------------
# Standard (bought) parts for the assembly STEP
# ---------------------------------------------------------------------------

def bearing(b) -> Part:
    out = Cylinder(b.od / 2, b.w) - Cylinder(b.od / 2 - 1.2, b.w + 0.2)
    inn = Cylinder(b.bore / 2 + 1.2, b.w) - Cylinder(b.bore / 2, b.w + 0.2)
    return out + inn


def roller() -> Part:
    return bearing(MR106)


def ring_pin(g: GearSpec = P.gear) -> Part:
    return cz(g.pin_radius, Z_PIN1 - Z_PIN0, Z_PIN0)


def motor() -> Part:
    st = cz(28.0, 30.7, Z_FLOOR1)
    ro = cz(28.0, 3.0, Z_FLOOR1 + 30.7)
    hub = cz(6.0, 6.0, Z_FLOOR1 + 28.0)
    return st + ro + hub


def esc_board(p: P = P) -> Part:
    return Pos(0, 0, 6.0) * Box(p.esc.board_w, p.esc.board_w, 1.6)


def encoder_board(p: P = P) -> Part:
    return Pos(0, 0, 11.8) * Box(p.encoder.board_w, p.encoder.board_w, 1.6)


def magnet(p: P = P) -> Part:
    return cz(p.encoder.magnet_d / 2, p.encoder.magnet_t, 14.8)


def hex_standoff() -> Part:
    """M4x12 hex standoff: support post under the input-shaft tip."""
    s = cz(4.0, Z_FLOOR0 - 3.5, 3.5)
    s -= cz(1.7, Z_FLOOR0 - 3.0, 3.2)
    return s


PRINTED = {
    "housing": housing,
    "cycloidal_disc_x2": cycloidal_disc,
    "input_shaft": input_shaft,
    "output_shaft": output_shaft,
    "motor_shell": motor_shell,
    "end_cap": end_cap,
    "motor_shaft": motor_shaft,
}

if __name__ == "__main__":
    for name, fn in PRINTED.items():
        pt = fn()
        bb = pt.bounding_box()
        print(f"{name:18s} vol={pt.volume/1000:6.1f} cm3  bbox="
              f"{bb.max.X-bb.min.X:5.1f} x {bb.max.Y-bb.min.Y:5.1f} x "
              f"{bb.max.Z-bb.min.Z:5.1f}")
