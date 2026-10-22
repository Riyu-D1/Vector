"""Underactuated tendon gripper v2 — curved claw fingers + rounded palm.

Fingers are lofted tapered claws curving inward; two shallow notches on
the back leave flexure webs (the 'knuckles'). Tendon channel runs the
length; fingertip pad recesses take the silicone/BMP390 pads.

Palm: rounded plate with finger pivots, tendon port, idler mount.
The sprung idler keeps the AS5600-read grip-force path from v1.
"""

import math
from dataclasses import dataclass

from build123d import Box, Cylinder, Pos, Rot, Part

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from params import ELEC, TOL
from lib.geom import lofted, rbox


@dataclass
class GripperParts:
    palm: Part
    finger_l: Part
    finger_r: Part
    spool: Part
    idler_arm: Part


def make_finger(mirror: bool = False) -> Part:
    """Tapered claw: lofted sections curving inward (+x_off curls toward
    the palm centre for the right finger; mirrored for the left)."""
    s = -1 if mirror else 1
    sections = [
        (0.0,  0.0,     15.0, 8.0, 3.4),
        (20.0, 0.0,     13.5, 7.2, 3.0),
        (38.0, 2.2 * s, 11.5, 6.4, 2.8),
        (56.0, 7.0 * s, 9.5,  5.4, 2.4),
    ]
    finger = lofted(sections)

    # Flexure notches on the back (−Y) face — leave ~1 mm inner webs.
    for z, x in ((24, 0.4 * s), (44, 3.4 * s)):
        finger -= Pos(x, -4.2, z) * Box(11, 4.0, 2.2)

    # Fingertip pad recess (silicone / BMP390).
    finger -= Pos(6.2 * s, 0, 51) * Box(3, ELEC.bmp390_w - 4, ELEC.bmp390_w - 4)

    # Tendon channel along the length.
    finger -= Pos(1.6 * s, 0, 27) * Cylinder(1.0, 62)

    # Root pivot bore.
    finger -= Pos(0, 0, 4) * Rot(90, 0, 0) * Cylinder(1.6, 10)
    return finger


def make_gripper(servo_spline_d: float = 5.9, spread: float = 32.0) -> GripperParts:
    pw, pt, ph = 62.0, 7.0, 26.0
    palm = Pos(0, 0, ph / 2) * rbox(pw, pt, ph, 6.0)
    for sx in (-1, 1):                            # finger root pivots
        palm -= Pos(sx * spread / 2, 0, ph - 5) * Rot(90, 0, 0) * Cylinder(1.6, pt + 2)
    palm -= Pos(0, 0, 4) * Rot(90, 0, 0) * Cylinder(2.2, pt + 2)   # tendon port
    for sx in (-1, 1):                            # mount to the wrist lip
        palm -= Pos(sx * (pw / 2 - 10), 0, 6) * Rot(90, 0, 0) * Cylinder(1.7, pt + 2)
    # Idler pivot post on the palm back.
    palm += Pos(0, pt / 2 - 1, 6) * Rot(90, 0, 0) * Cylinder(2.4, 4)

    finger_l = Pos(-spread / 2, 0, ph - 2) * make_finger(mirror=True)
    finger_r = Pos(spread / 2, 0, ph - 2) * make_finger(mirror=False)

    spool = Cylinder(9.0, 8.0)
    spool -= Cylinder((servo_spline_d - TOL.press) / 2, 3.0)
    spool -= Pos(0, 0, 2.0) * (Cylinder(9.5, 3.0) - Cylinder(7.5, 3.0))
    spool -= Cylinder(1.5, 10)

    arm_l = 22.0
    idler = Pos(arm_l / 2, 0, 0) * rbox(arm_l, 4.0, 5.0, 2.0)
    idler += Pos(arm_l, 0, 0) * Rot(90, 0, 0) * Cylinder(4.0, 4.4)   # roller
    idler -= Pos(arm_l, 0, 0) * Rot(90, 0, 0) * Cylinder(1.6, 6)
    idler += Pos(-2, 0, -3) * Rot(90, 0, 0) * Cylinder(3.0, 4.0)     # magnet boss
    idler -= Pos(-2, 0, -4.5) * Rot(90, 0, 0) * Cylinder(3.1, 3.2)

    return GripperParts(palm, finger_l, finger_r, spool, idler)


if __name__ == "__main__":
    g = make_gripper()
    for n, p in (
        ("palm", g.palm), ("finger_l", g.finger_l),
        ("finger_r", g.finger_r), ("spool", g.spool), ("idler", g.idler_arm),
    ):
        bb = p.bounding_box()
        print(f"{n}: {bb.size.X:.0f}×{bb.size.Y:.0f}×{bb.size.Z:.0f} mm")
