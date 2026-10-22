"""J1 turntable base: waist-yaw servo in a round housing, turret plate on a
large bearing, electronics bay underneath.

Frame: J1 axis = +Z through the base center. Turret plate = the rotating top
that carries the J2 shoulder towers.
"""

import math
from dataclasses import dataclass

from build123d import Box, Cylinder, Pos, Rot, Part

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from params import ServoSpec, BEARINGS, TOL


@dataclass
class BaseParts:
    housing: Part   # static base shell with electronics bay + bearing seat
    turret: Part    # rotating output plate (shoulder mounts here)
    servo: Part     # envelope
    bearing_r: float


def make_base(servo: ServoSpec, dia: float = 140.0, h: float = 55.0) -> BaseParts:
    from lib.servo import make_servo
    sp = make_servo(servo)

    b_id, b_od, b_w = BEARINGS["6808"]   # 40×52×7 turntable bearing
    wall = 3.0

    # Housing: floor + wall ring + top ring with bearing seat.
    floor = Cylinder(dia / 2, 4)
    wall_ring = Pos(0, 0, h / 2) * (
        Cylinder(dia / 2, h) - Cylinder(dia / 2 - wall, h)
    )
    top_ring = Pos(0, 0, h - 6) * (
        Cylinder(dia / 2, 6) - Cylinder((b_od + TOL.slip) / 2, 6)
    )
    housing = floor + wall_ring + top_ring

    # Servo cavity + spline clearance; servo vertical, spline up.
    housing -= Pos(0, 0, h - 6 - servo.body_h / 2) * Box(
        servo.body_w + TOL.loose, servo.body_d + TOL.loose, servo.body_h + 4
    )
    housing -= Pos(servo.body_w / 2, 0, h - 6 - servo.body_h / 2) * Box(
        20, servo.body_d, servo.body_h  # cable/connector relief side channel
    )

    # Rear panel cutout for USB + power inlet.
    housing -= Pos(-dia / 2 + 2, 0, h / 2) * Box(6, 60, 30)

    # Feet pads recess.
    for i in range(4):
        th = i * math.pi / 2 + math.pi / 4
        housing -= Pos(
            (dia / 2 - 15) * math.cos(th), (dia / 2 - 15) * math.sin(th), -0.5
        ) * Cylinder(6, 2)

    # Turret: rotating plate on the bearing, driven by the horn adapter.
    turret_t = 6.0
    turret = Pos(0, 0, h - 2 + turret_t / 2) * Cylinder(dia / 2 - 8, turret_t)
    # Horn bolt circle + center spline clearance.
    turret -= Pos(0, 0, h - 2 + turret_t / 2) * Cylinder(6.0 / 2, turret_t + 2)
    for i in range(4):
        th = i * math.pi / 2 + math.pi / 4
        turret -= Pos(
            9 * math.cos(th), 9 * math.sin(th), h - 2 + turret_t / 2
        ) * Cylinder(1.6, turret_t + 2)
    # Shoulder tower mounts: two M3 pairs fore/aft (J2 bracket feet).
    for sx in (-1, 1):
        for sy in (-1, 1):
            turret -= Pos(
                sx * 20, sy * 16, h - 2 + turret_t / 2
            ) * Cylinder(1.6, turret_t + 2)
    # Central hub descending into the bearing inner race.
    turret += Pos(0, 0, h - 2 - b_w / 2) * Cylinder((b_id - TOL.slip) / 2, b_w)

    return BaseParts(housing, turret, sp.part, b_od / 2)


if __name__ == "__main__":
    from params import SERVO_SM
    b = make_base(SERVO_SM)
    bb = b.housing.bounding_box()
    print(f"base housing {bb.size.X:.0f}×{bb.size.Y:.0f}×{bb.size.Z:.0f} mm")
    print(f"turret vol {b.turret.volume/1000:.1f} cm³")
