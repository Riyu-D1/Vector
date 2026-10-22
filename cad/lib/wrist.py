"""Wrist/face module: J4 pitch + J5 roll servos inline, ending in the 'face'
plate — two round eye displays + camera + wrist ESP32 — with the gripper
mounted below the eyes.

Frame: module sits at the end of the forearm; +Z = forward (toward gripper).
"""

import math
from dataclasses import dataclass

from build123d import Box, Cylinder, Pos, Rot, Part

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from params import ServoSpec, ELEC, TOL
from lib.servo import make_servo


@dataclass
class WristParts:
    j4_bracket: Part    # pitch servo cradle (attaches to forearm end)
    j5_shell: Part      # roll servo housing (rotates with J4 output)
    faceplate: Part     # eyes + camera + board mount
    j4_servo: Part
    j5_servo: Part


def make_wrist(servo: ServoSpec) -> WristParts:
    j4 = make_servo(servo)
    j5 = make_servo(servo)

    # --- J4 bracket: cradle at the end of the forearm ----------------------
    bw = servo.body_w + 2 * TOL.wall + 4
    bd = servo.body_d + 2 * TOL.wall + 4
    bh = servo.body_h + 10
    j4_bracket = (
        Box(bw, bd, bh)
        - Pos(0, 0, 5) * Box(servo.body_w + TOL.loose, servo.body_d + TOL.loose, bh)
    )
    # axis clearance + forearm bolt plate on the -Z side
    j4_bracket -= Pos(0, 0, -bh / 2 + 3) * Cylinder(7, 8)
    for sx in (-1, 1):
        for sy in (-1, 1):
            j4_bracket -= Pos(sx * (bw / 2 - 6), sy * (bd / 2 - 6), -bh / 2) * Cylinder(
                1.6, 6
            )

    # --- J5 shell: roll servo housing rotating with J4's output ------------
    shell_l = servo.body_h + 26
    j5_shell = (
        Box(bw, bd + 10, shell_l)
        - Pos(0, 0, 6) * Box(servo.body_w + TOL.loose, servo.body_d + TOL.loose, shell_l)
    )
    # J4 horn flange pocket at -Z end
    j5_shell -= Pos(0, 0, -shell_l / 2 + 2) * Cylinder(11, 5)

    # --- faceplate: the 'face' — eyes, camera, board ------------------------
    fp_w = 3 * ELEC.gc9a01_d + 12    # two eyes + gaps
    fp_h = ELEC.gc9a01_d + 16
    fp_t = 4.0
    faceplate = Box(fp_w, fp_t, fp_h)
    # eye apertures
    for sx in (-1, 1):
        faceplate -= Pos(sx * (ELEC.gc9a01_d + 4) / 2, 0, 2) * Rot(90, 0, 0) * Cylinder(
            (ELEC.gc9a01_d + TOL.slip) / 2, fp_t + 2
        )
        # rear shelf pocket per display
        faceplate -= Pos(sx * (ELEC.gc9a01_d + 4) / 2, -fp_t / 2 - 3, 2) * Rot(90, 0, 0) * Cylinder(
            (ELEC.gc9a01_d + TOL.loose) / 2 + 1, 3
        )
    # camera aperture (center, above eyes)
    faceplate -= Pos(0, 0, fp_h / 2 - 7) * Rot(90, 0, 0) * Cylinder(3.5, fp_t + 2)
    # gripper mount plate lip under the face
    faceplate += Pos(0, -fp_t / 2 - 2, -fp_h / 2 + 2) * Box(fp_w, 4, 6)

    return WristParts(j4_bracket, j5_shell, faceplate, j4.part, j5.part)


if __name__ == "__main__":
    from params import SERVO_SM
    w = make_wrist(SERVO_SM)
    for n, p in (("j4_bracket", w.j4_bracket), ("j5_shell", w.j5_shell), ("faceplate", w.faceplate)):
        bb = p.bounding_box()
        print(f"{n}: {bb.size.X:.0f}×{bb.size.Y:.0f}×{bb.size.Z:.0f} mm")
