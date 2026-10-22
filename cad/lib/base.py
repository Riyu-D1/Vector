"""J1 turntable base v2 — tapered drum + flush turret.

Silhouette: a swept drum, wider at the desk, easing in at the top rim —
the 'charger base' look. The turret is a filleted low cap sitting flush
in the bearing seat. Electronics bay + servo inside; USB/power panel at
the rear.
"""

import math
from dataclasses import dataclass

from build123d import Axis, Box, Cylinder, Pos, Rot, Part, fillet

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from params import ServoSpec, BEARINGS, TOL
from lib.geom import cone


@dataclass
class BaseParts:
    housing: Part
    turret: Part
    servo: Part
    servo_loc: object
    top_z: float
    bearing_r: float


def make_base(servo: ServoSpec, dia: float = 132.0, h: float = 52.0) -> BaseParts:
    from lib.servo import make_servo
    sp = make_servo(servo)

    b_id, b_od, b_w = BEARINGS["6808"]          # 40×52×7 turntable bearing
    wall = 3.0

    # Tapered drum: foot ring → eased main body → rim.
    r_base, r_top = dia / 2, dia / 2 - 8.0
    drum = cone([
        (0.0, r_base),
        (4.0, r_base - 2),
        (h - 8, r_top + 3),
        (h, r_top),
    ])
    # Fillet the top rim while the drum is still solid (post-hollow the
    # 3 mm inner rim can't take the radius).
    drum = fillet(
        drum.edges().filter_by_position(Axis.Z, h - 0.5, h + 0.1), 2.5
    )
    housing = drum - Pos(0, 0, h / 2 + 3) * Cylinder(r_top - wall, h)
    # Solid floor stays ~4 mm.
    housing = housing - Pos(0, 0, -2) * Cylinder(r_base + 1, 4)

    # Turret bearing seat: recessed ring in the top.
    seat_z = h - 4
    housing -= Pos(0, 0, seat_z) * Cylinder((b_od + TOL.slip) / 2 + 3, 5)
    housing -= Pos(0, 0, seat_z) * Cylinder((b_od + TOL.slip) / 2, b_w + 1)

    # Servo cavity — upright, spline up into the turret.
    housing -= Pos(0, 0, seat_z - servo.body_h / 2) * Box(
        servo.body_w + TOL.loose, servo.body_d + TOL.loose, servo.body_h + 4
    )
    housing -= Pos(servo.body_w / 2, 0, seat_z - servo.body_h / 2) * Box(
        18, servo.body_d, servo.body_h            # connector relief channel
    )
    # Stub post on the floor (dual-shaft servos get bottom support).
    housing += Pos(0, 0, 4 + 3) * Cylinder(servo.stub_d / 2 - TOL.slip, 6)

    # Rear panel (−X, behind the reach direction +X): USB-C + barrel inlet.
    housing -= Pos(-(r_top - 4), 0, h / 2) * Box(8, 30, 18)

    # Foot pad recesses.
    for i in range(4):
        th = i * math.pi / 2 + math.pi / 4
        housing -= Pos(
            (r_base - 14) * math.cos(th), (r_base - 14) * math.sin(th), -0.5
        ) * Cylinder(6, 2)

    # Turret: low filleted cap riding the bearing; horn adapter below.
    turret_t = 5.0
    turret = Pos(0, 0, h - 1 + turret_t / 2) * Cylinder(r_top - 4, turret_t)
    turret = fillet(turret.edges(), 1.5)
    turret -= Pos(0, 0, h - 1 + turret_t / 2) * Cylinder(3.0, turret_t + 2)
    for i in range(4):                          # horn bolt circle
        th = i * math.pi / 2 + math.pi / 4
        turret -= Pos(
            9 * math.cos(th), 9 * math.sin(th), h - 1 + turret_t / 2
        ) * Cylinder(1.6, turret_t + 2)
    for sx in (-1, 1):                          # J2 foot bolts (matches foot)
        for sy in (-1, 1):
            turret -= Pos(
                sx * (20), sy * (16), h - 1 + turret_t / 2
            ) * Cylinder(1.7, turret_t + 2)
    # Descending hub into the bearing inner race.
    turret += Pos(0, 0, seat_z - b_w / 2 + 0.5) * Cylinder((b_id - TOL.slip) / 2, b_w)

    servo_loc = Pos(0, 0, seat_z - 2) * Rot(0, 0, 0)  # spline face up at seat
    return BaseParts(housing, turret, sp.part, servo_loc, h - 1 + turret_t, b_od / 2)


if __name__ == "__main__":
    from params import SERVO_SM
    b = make_base(SERVO_SM)
    bb = b.housing.bounding_box()
    print(f"base housing {bb.size.X:.0f}×{bb.size.Y:.0f}×{bb.size.Z:.0f} mm")
    print(f"turret vol {b.turret.volume/1000:.1f} cm³")
