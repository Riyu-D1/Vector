"""Pitch-joint module v2 — 'teardrop knuckle' styling.

Static side ('bracket'): a pair of paddle plates in the bend plane (XZ) —
a round knuckle at the axis flowing into a tapered tail that wraps the
servo case down to a rounded foot. The servo stands with its case along Z
and shaft along the joint axis (Y), spline toward +Y (drive side), rear
stub into the -Y idler bearing.

Moving side ('yoke'): a matching collar — two plates outside the bracket
joined by a rounded top rail carrying the distal-link bolt pattern.

The knuckle face reads as:  yoke plate → SEA spring ring / horn flange →
small centre cap. Layered hub = intended visual.
"""

from dataclasses import dataclass
import math

from build123d import Box, Cylinder, Pos, Rot, Part, fillet, Location

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from params import ServoSpec, SEASpec, BEARINGS, TOL
from lib.geom import paddle, rbox, y_cyl
from lib.servo import make_servo
from lib.sea import make_cartridge, make_horn_flange, SEAParts


@dataclass
class JointParts:
    bracket: Part            # static half (mounts to proximal structure)
    yoke: Part               # moving half (carries the distal link)
    servo: Part
    servo_loc: Location      # local→joint transform for the servo part
    sea: SEAParts | None
    foot_drop: float         # axis → bracket foot bottom (−Z)
    rail_top: float          # axis → yoke rail top (+Z)
    span_y: float            # total width across the joint axis


def make_pitch_joint(
    servo: ServoSpec,
    sea: SEASpec | None = None,
    cheek_t: float = 4.0,
    plate_t: float = 3.5,
    foot_h: float = 12.0,
    idler_bearing: str = "6704",
) -> JointParts:
    # --- servo-in-joint layout ---------------------------------------------
    # Joint-frame servo orientation: local (x,y,z) → joint (y, z, x), with a
    # 180° spin about the shaft so the case hangs mostly BELOW the axis.
    gap = servo.body_h + 1.0            # span between paddle inner faces
    case_x = servo.body_d + TOL.loose   # slim dim across the bend plane
    case_z = servo.body_w               # case length down the tail
    shaft_drop = 8.0                    # spline offset → case mostly below
    case_bottom = -shaft_drop - case_z / 2
    case_top = -shaft_drop + case_z / 2
    foot_z = case_bottom - foot_h - 4.0

    servo_loc = Pos(0, gap / 2, -8.0) * Rot(0, -90, 0) * Rot(-90, 0, 0) * Rot(
        0, 0, 180
    )
    sp = make_servo(servo)

    # --- bracket: two paddles + rounded foot --------------------------------
    r_disc = (sea.disc_r + 4.0) if sea else 22.0
    tail_w = case_x + 2 * TOL.wall + 2.0          # wrap the case sides
    foot_w = tail_w + 10.0

    cheek_drive = Pos(0, gap / 2 + cheek_t / 2, 0) * paddle(
        r_disc, tail_w, -2.0, foot_w, foot_z + foot_h, cheek_t
    )
    cheek_idler = Pos(0, -gap / 2 - cheek_t / 2, 0) * paddle(
        r_disc, tail_w, -2.0, foot_w, foot_z + foot_h, cheek_t
    )
    foot = Pos(0, 0, foot_z + foot_h / 2) * rbox(
        foot_w + 6, gap + 2 * cheek_t, foot_h, 3.0
    )
    bracket = cheek_drive + cheek_idler + foot

    # Servo case pocket between the tails (leaves walls on the tails).
    bracket -= Pos(0, 0, (case_top + case_bottom) / 2) * Box(
        case_x, gap + 0.4, case_top - case_bottom + 4
    )

    # Axis bores.
    bracket -= y_cyl(6.0, gap + 2 * cheek_t + 8)          # spline/stub clearance
    bracket -= Pos(0, gap / 2, 0) * y_cyl(               # +Y: spline boss reach
        servo.spline_d / 2 + 1.5, cheek_t + 2
    )
    ib_id, ib_od, ib_w = BEARINGS[idler_bearing]          # −Y: idler bearing seat
    bracket -= Pos(0, -gap / 2 - cheek_t, 0) * y_cyl(
        (ib_od + TOL.slip) / 2, ib_w + 0.5
    )
    bracket -= Pos(0, -gap / 2, 0) * y_cyl(
        servo.stub_d / 2 + 0.5, cheek_t / 2 + 1.0        # stub enters the race
    )

    # Cap mount holes on the +Y cheek rim (SEA joints).
    if sea:
        cap_r = sea.disc_r - sea.ring_w - TOL.wall / 2 - 4.0
        for i in range(3):
            th = i * 2 * math.pi / 3 + math.pi / 6
            bracket -= Pos(
                cap_r * math.cos(th), gap / 2 + cheek_t - 1,
                cap_r * math.sin(th),
            ) * y_cyl(1.3, cheek_t)                     # M2.5 tap into cheek

    # Case pinch bolts through both tails near the case bottom.
    for z in (case_bottom + 8, case_bottom + 22):
        for x in (-tail_w / 2 + 4, tail_w / 2 - 4):
            bracket -= Pos(x, 0, z) * y_cyl(1.6, gap + 2 * cheek_t + 4)

    # Foot → proximal-link bolt pattern (4× M3).
    for sx in (-1, 1):
        for sy in (-1, 1):
            bracket -= Pos(
                sx * (foot_w / 2 - 3), sy * (gap / 2 + cheek_t - 9),
                foot_z,
            ) * Cylinder(1.7, 8)

    # --- yoke collar ---------------------------------------------------------
    yoke_in = gap + 2 * cheek_t + 0.6                     # clears bracket faces
    r_yoke = r_disc + cheek_t + 0.4
    rail_z = r_yoke + 6.0                                 # top of the collar

    plate_drive = Pos(0, yoke_in / 2 + plate_t / 2, 0) * paddle(
        r_yoke, tail_w + 6, -4.0, foot_w + 6, rail_z, plate_t
    )
    plate_idler = Pos(0, -yoke_in / 2 - plate_t / 2, 0) * paddle(
        r_yoke, tail_w + 6, -4.0, foot_w + 6, rail_z, plate_t
    )
    rail = Pos(0, 0, rail_z + 4) * rbox(
        foot_w + 6, yoke_in + 2 * plate_t, 8.0, 3.0
    )
    yoke = plate_drive + plate_idler + rail

    # Axis bores through the plates.
    yoke -= y_cyl(9.0, yoke_in + 2 * plate_t + 6)

    # Drive plate bolt circle: SEA output flange rim OR rigid horn flange.
    bolt_r = (sea.disc_r - 3.0) if sea else 9.0
    bolt_d = 1.4 if sea else 1.7
    for i in range(4):
        th = i * math.pi / 2 + math.pi / 4
        yoke -= Pos(
            bolt_r * math.cos(th), yoke_in / 2, bolt_r * math.sin(th)
        ) * y_cyl(bolt_d, plate_t + 2)

    # Rail → distal-link bolt pattern (4× M3, axial).
    for sx in (-1, 1):
        for sy in (-1, 1):
            yoke -= Pos(
                sx * (foot_w / 2 - 3), sy * (yoke_in / 2 + plate_t - 9),
                rail_z + 4,
            ) * Cylinder(1.7, 10)

    return JointParts(
        bracket=bracket,
        yoke=yoke,
        servo=sp.part,
        servo_loc=servo_loc,
        sea=make_cartridge(sea, servo.spline_d) if sea else None,
        foot_drop=-foot_z,
        rail_top=rail_z + 8,
        span_y=yoke_in + 2 * plate_t,
    )


if __name__ == "__main__":
    from params import SERVO_XL, SERVO_LG, SERVO_SM, SEA_J2, SEA_J3
    for label, sv, sea in (
        ("J2", SERVO_XL, SEA_J2), ("J3", SERVO_LG, SEA_J3),
        ("J4", SERVO_SM, None),
    ):
        j = make_pitch_joint(sv, sea)
        for nm, p in (("bracket", j.bracket), ("yoke", j.yoke)):
            bb = p.bounding_box()
            print(
                f"{label} {nm:7s} {bb.size.X:.0f}×{bb.size.Y:.0f}×{bb.size.Z:.0f} mm "
                f"vol {p.volume/1000:.1f} cm³"
            )
        svb = (j.servo_loc * j.servo).bounding_box()
        print(
            f"    servo in joint: z {svb.min.Z:.0f}..{svb.max.Z:.0f}, "
            f"y {svb.min.Y:.0f}..{svb.max.Y:.0f}"
        )
        print(f"    foot_drop {j.foot_drop:.0f}, rail_top {j.rail_top:.0f}")
