"""Underactuated 2-finger tendon gripper + sprung-idler force sensor.

- Two 2-phalange fingers with printed flexure knuckles wrap objects.
- One servo spool pulls a single Dyneema tendon split to both fingers.
- The tendon passes over a sprung idler: the idler arm deflects ∝ tendon
  tension → AS5600 on the idler pivot reads real grip force.

Frame: palm plate at origin, fingers extend +Z, tendon runs −Z back to
the wrist servo.
"""

import math
from dataclasses import dataclass

from build123d import Box, Cylinder, Pos, Rot, Part

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from params import ELEC, TOL


@dataclass
class GripperParts:
    palm: Part
    finger_l: Part
    finger_r: Part
    spool: Part
    idler_arm: Part


def make_finger(mirror: bool = False) -> Part:
    """Two-phalange flexure finger: rigid segments joined by 0.8 mm flexure
    webs; a tendon channel runs down the inner face. TPU skin over the pad."""
    seg_len = 28.0
    w, t = 12.0, 5.0
    parts = []
    z = 0.0
    for i in range(2):
        seg = Pos(0, 0, z + seg_len / 2) * Box(w, t, seg_len)
        parts.append(seg)
        # knuckle flexure gap (thin web left at back face)
        z += seg_len
        if i == 0:
            web = Pos(0, t / 2 - 0.8, z + 0.4) * Box(w, 0.8, 1.6)
            parts.append(web)
            z += 1.6
    finger = parts[0]
    for p in parts[1:]:
        finger += p
    # fingertip pad recess (silicone/BMP390 sits here)
    finger -= Pos(0, -t / 2 - 1.5, 2 * seg_len - 6) * Box(ELEC.bmp390_w, 3, ELEC.bmp390_w)
    # tendon channel
    finger -= Pos(0, 0, seg_len) * Cylinder(1.0, 2 * seg_len + 6)
    return Rot(0, 0, 180) * finger if mirror else finger


def make_gripper(servo_spline_d: float = 5.9, spread: float = 34.0) -> GripperParts:
    # Palm plate: tendon exit port, finger pivots, mounts to wrist lip.
    pw, pt, ph = 70.0, 6.0, 30.0
    palm = Box(pw, pt, ph)
    # finger root pivots
    for sx in (-1, 1):
        palm -= Pos(sx * spread / 2, 0, ph / 2 - 4) * Rot(90, 0, 0) * Cylinder(1.6, pt + 2)
    # tendon port center-bottom
    palm -= Pos(0, 0, -ph / 2 + 4) * Cylinder(2.2, pt + 4)
    # mount bolt slots to the wrist lip
    for sx in (-1, 1):
        palm -= Pos(sx * (pw / 2 - 8), 0, -ph / 2 + 6) * Cylinder(1.6, pt + 2)

    finger_l = Pos(-spread / 2, 0, ph / 2) * make_finger(False)
    finger_r = Pos(spread / 2, 0, ph / 2) * make_finger(True)

    # Servo spool: spline bore + winding groove.
    spool = Cylinder(9.0, 8.0)
    spool -= Cylinder((servo_spline_d - TOL.press) / 2, 3.0)
    spool -= Pos(0, 0, 2.0) * (Cylinder(9.5, 3.0) - Cylinder(7.5, 3.0))
    spool -= Cylinder(1.5, 10)  # center bolt

    # Sprung idler arm: lever on a pivot; tendon rides over the roller at tip;
    # pivot carries the AS5600 magnet — deflection reads tendon tension.
    arm_l = 24.0
    idler = Pos(arm_l / 2, 0, 0) * Box(arm_l, 4.0, 6.0)
    idler += Pos(arm_l, 0, 0) * Rot(90, 0, 0) * Cylinder(4.0, 4.4)   # roller
    idler -= Pos(arm_l, 0, 0) * Rot(90, 0, 0) * Cylinder(1.6, 6)     # roller pin
    idler += Pos(-2, 0, -3) * Rot(90, 0, 0) * Cylinder(3.0, 4.0)     # magnet boss
    idler -= Pos(-2, 0, -4.5) * Rot(90, 0, 0) * Cylinder(3.1, 3.2)   # magnet pocket

    return GripperParts(palm, finger_l, finger_r, spool, idler)


if __name__ == "__main__":
    g = make_gripper()
    for n, p in (("palm", g.palm), ("finger_l", g.finger_l), ("spool", g.spool), ("idler", g.idler_arm)):
        bb = p.bounding_box()
        print(f"{n}: {bb.size.X:.0f}×{bb.size.Y:.0f}×{bb.size.Z:.0f} mm")
