"""Reusable pitch-joint module: servo cradle + (optional) SEA cartridge +
bearing-supported output yoke.

Joint frame:
    axis   = local Y
    +Y     = drive side (servo spline / SEA cartridge side)
    -Y     = idler side (servo stub bearing)
    +Z     = toward the distal link
    -Z     = toward the proximal link (bracket foot)

Static half : 'bracket' — U-frame; servo clamps between cheeks; the +Y
              cheek carries the encoder/bearing ring for SEA joints.
Moving half : 'yoke' — plates bolt to the SEA output hub (or the horn
              flange on rigid joints) on +Y and ride the stub bearing on -Y.
"""

from dataclasses import dataclass, field
import math

from build123d import (
    Box, Cylinder, Pos, Rot, Axis, Part, Compound, fillet,
)

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from params import ServoSpec, SEASpec, BEARINGS, TOL
from lib.servo import make_servo
from lib.sea import make_cartridge, SEAParts


@dataclass
class JointParts:
    bracket: Part            # static
    yoke: Part               # moving output yoke (link attaches here)
    servo: Part              # envelope
    sea: SEAParts | None     # SEA cartridge pieces (None on rigid joints)
    axis_gap: float          # distance between cheek inner faces
    frame_offset: float      # -Z distance: axis → bracket foot face


def make_pitch_joint(
    servo: ServoSpec,
    sea: SEASpec | None = None,
    cheek_t: float = 4.0,
    foot_h: float = 14.0,
    idler_bearing: str = "6704",
) -> JointParts:
    sp = make_servo(servo)

    # --- how far each side of the axis the cheeks must clear ----------------
    # +Y stack: spline boss (+ spring+hub+cap depth if SEA)
    sea_stack = (sea.disc_t + 4.0 + 5.0) if sea else 0.0
    drive_side = servo.spline_h + sea_stack + 2.0
    # -Y stack: body depth? no — body is BETWEEN the cheeks along Y.
    gap = servo.body_d + drive_side + 4.0   # +Y cartridge room + rear stub room

    half_gap = gap / 2
    cheek_h = servo.body_h + 20.0   # cheek height covers body + margins

    # --- static bracket -----------------------------------------------------
    cheek_w = servo.body_w + 16.0   # X width

    drive_cheek = Pos(0, half_gap + cheek_t / 2, -cheek_h / 2 + 10) * Box(
        cheek_w, cheek_t, cheek_h
    )
    idler_cheek = Pos(0, -half_gap - cheek_t / 2, -cheek_h / 2 + 10) * Box(
        cheek_w, cheek_t, cheek_h
    )
    foot = Pos(0, 0, -cheek_h + 10 + foot_h / 2 - 2) * Box(
        cheek_w, gap + 2 * cheek_t, foot_h
    )
    bracket = drive_cheek + idler_cheek + foot

    # Servo body sits in the gap; spline face toward +Y inner cheek face.
    servo_y = servo.body_d / 2 + drive_side - half_gap
    bracket -= Pos(0, servo_y, 10 - 4) * Box(
        servo.body_w + TOL.loose, servo.body_d + TOL.loose, servo.body_h + 2 * TOL.loose
    )  # body clearance through the top opening — clamp by cheek pinch

    # Axis bore through both cheeks.
    bracket -= Pos(0, 0, 0) * Rot(-90, 0, 0) * Cylinder(8.0, gap + 2 * cheek_t + 4)

    # +Y cheek outer face: encoder/bearing ring for SEA joints,
    # plain bearing seat otherwise.
    ring_r = (sea.disc_r + TOL.loose + TOL.wall) if sea else 14.0
    ring = Pos(0, half_gap, 0) * Rot(-90, 0, 0) * Cylinder(
        ring_r + 4.0, 5.0
    ) - Pos(0, half_gap, 0) * Rot(-90, 0, 0) * Cylinder(ring_r, 5.0)
    bracket += ring

    # -Y cheek: idler bearing bore aligned on axis.
    ib_id, ib_od, ib_w = BEARINGS[idler_bearing]
    bracket -= Pos(0, -half_gap - cheek_t, 0) * Rot(-90, 0, 0) * Cylinder(
        (ib_od + TOL.slip) / 2, ib_w + 1.0
    )

    # Bracket→proximal-link mounting: 4× M3 on the foot corners.
    for sx in (-1, 1):
        for sy in (-1, 1):
            bracket -= Pos(
                sx * (cheek_w / 2 - 6),
                sy * (gap / 2 + cheek_t - 8),
                -cheek_h + 10 + foot_h - 2,
            ) * Cylinder(1.6, 6)

    # --- moving yoke --------------------------------------------------------
    # Two plates straddling the bracket, joined by a top rail at +Z.
    yoke_plate_t = 4.0
    yoke_h = servo.body_h + 30.0
    yoke_gap = gap + 2 * cheek_t + 2 * TOL.loose

    yoke_drive = Pos(0, yoke_gap / 2 + yoke_plate_t / 2, yoke_h / 2 - 6) * Box(
        cheek_w + 8, yoke_plate_t, yoke_h
    )
    yoke_idle = Pos(0, -yoke_gap / 2 - yoke_plate_t / 2, yoke_h / 2 - 6) * Box(
        cheek_w + 8, yoke_plate_t, yoke_h
    )
    yoke_top = Pos(0, 0, yoke_h - 6 + 4) * Box(
        cheek_w + 8, yoke_gap + 2 * yoke_plate_t, 8
    )
    yoke = yoke_drive + yoke_idle + yoke_top

    # Clearance bores on axis through both yoke plates.
    yoke -= Pos(0, 0, 0) * Rot(-90, 0, 0) * Cylinder(9.0, yoke_gap + 2 * yoke_plate_t + 6)

    # Drive plate: SEA output-hub bolt circle OR horn bolt pattern.
    bolt_r = (sea.disc_r - sea.ring_w / 2) if sea else 10.0
    for i in range(4):
        th = i * math.pi / 2
        yoke -= Pos(
            bolt_r * math.cos(th),
            yoke_gap / 2 + yoke_plate_t / 2,
            bolt_r * math.sin(th),
        ) * Rot(-90, 0, 0) * Cylinder(1.6, yoke_plate_t + 2)

    # Yoke→distal-link bolt circle on the top rail.
    for sx in (-1, 1):
        for sy in (-1, 1):
            yoke -= Pos(
                sx * (cheek_w / 2 - 2), sy * (yoke_gap / 2 - 8),
                yoke_h - 6 + 4,
            ) * Cylinder(1.6, 10)

    return JointParts(
        bracket=bracket,
        yoke=yoke,
        servo=sp.part,
        sea=make_cartridge(sea, servo.spline_d) if sea else None,
        axis_gap=gap,
        frame_offset=cheek_h - 10,
    )


if __name__ == "__main__":
    from params import SERVO_XL, SERVO_LG, SERVO_SM, SEA_J2, SEA_J3
    for label, sv, sea in (
        ("J2", SERVO_XL, SEA_J2), ("J3", SERVO_LG, SEA_J3),
        ("J4", SERVO_SM, None),
    ):
        j = make_pitch_joint(sv, sea)
        bb = j.bracket.bounding_box()
        print(
            f"{label}: bracket {bb.size.X:.0f}×{bb.size.Y:.0f}×{bb.size.Z:.0f} mm, "
            f"yoke vol {j.yoke.volume/1000:.1f} cm³, sea={'yes' if j.sea else 'no'}"
        )
