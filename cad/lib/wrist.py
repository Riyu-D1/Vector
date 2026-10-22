"""Wrist/face module v2 — J4 reuses the teardrop pitch joint; J5 is a
rounded pod ending in the 'head': a visor faceplate with two eye displays
+ camera, and the gripper mounting lip below.

J4 (pitch) : standard make_pitch_joint(STS3215) — static side bolts to the
             forearm end, yoke carries the J5 pod.
J5 (roll)  : servo shaft along +Z inside a filleted pod bolted to the J4
             yoke rail; its horn flange carries the faceplate.
Face       : rounded visor panel — eyes recessed, camera between them.
"""

import math
from dataclasses import dataclass

from build123d import Box, Cylinder, Pos, Rot, Part, fillet

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from params import ServoSpec, ELEC, TOL
from lib.geom import rbox
from lib.servo import make_servo


@dataclass
class WristParts:
    j4: object          # JointParts for the pitch joint
    j5_pod: Part        # roll servo housing (bolts to J4 yoke rail)
    neck: Part          # L-bracket on the J5 flange — carries face + gripper
    faceplate: Part     # visor: eyes + camera apertures
    j5_servo: Part
    pod_h: float        # J4 rail → faceplate top
    pod_l: float        # J4 rail → pod top (J5 flange plane)


def make_wrist(servo: ServoSpec) -> WristParts:
    from lib.joint import make_pitch_joint
    j4 = make_pitch_joint(servo, sea=None)

    sp = make_servo(servo)

    # --- J5 pod: rounded shell around the upright servo ---------------------
    pod_w = servo.body_w + 2 * TOL.wall + 2      # X
    pod_d = servo.body_d + 2 * TOL.wall + 2      # Y
    pod_h = servo.body_h + 14
    pod = Pos(0, 0, pod_h / 2) * rbox(pod_w, pod_d, pod_h, 6.0)
    pod -= Pos(0, 0, pod_h / 2 - 3) * Box(
        servo.body_w + TOL.loose, servo.body_d + TOL.loose, servo.body_h + 2
    )
    # Servo open bottom (drops in from below; retained by spline + strap).
    pod -= Pos(0, 0, 0) * Box(servo.body_w - 6, servo.body_d - 6, 8)
    # Spline/horn recess at the top face.
    pod -= Pos(0, 0, pod_h - 4) * Cylinder(12, 6)
    # J4-rail mount holes on the pod's −Z end (matches rail pattern).
    for sx in (-1, 1):
        for sy in (-1, 1):
            pod -= Pos(sx * (pod_w / 2 - 8), sy * (pod_d / 2 - 8), 0) * Cylinder(
                1.7, 8
            )

    # --- neck: L-bracket off the J5 flange → face + gripper -----------------
    # Horizontal foot bolts to the horn flange at the pod top; the vertical
    # leg clears the pod's −Y front face; visor + palm bolt to the leg.
    leg_y = -(pod_d / 2 + 3)                      # just clear of the pod front
    neck = (
        Pos(0, (leg_y + 6) / 2 - 1, 2) * rbox(30, 6 - leg_y, 4, 2)     # foot
        + Pos(0, leg_y, 2 + 17) * rbox(30, 3, 34, 1.4)                 # leg
    )
    for i in range(4):                            # flange bolt circle (r9, M3)
        th = i * math.pi / 2 + math.pi / 4
        neck -= Pos(9 * math.cos(th), 9 * math.sin(th), 2) * Cylinder(1.7, 6)
    neck -= Pos(0, 0, 2) * Cylinder(3.2, 6)       # spline/center clearance
    for z in (8, 22, 30):                         # palm + face mount holes
        for sx in (-1, 1):
            neck -= Pos(sx * 9, leg_y, z) * Rot(90, 0, 0) * Cylinder(1.4, 5)

    # --- faceplate: rounded visor -------------------------------------------
    fp_w = 2 * ELEC.gc9a01_d + 22                # two eyes + center camera
    fp_h = ELEC.gc9a01_d + 14
    fp_t = 5.0
    faceplate = Pos(0, 0, fp_h / 2) * rbox(fp_w, fp_t, fp_h, 8.0)
    # Eye apertures + rear display pockets.
    for sx in (-1, 1):
        ex = sx * (ELEC.gc9a01_d / 2 + 9)
        faceplate -= Pos(ex, 0, fp_h / 2 + 3) * Rot(90, 0, 0) * Cylinder(
            ELEC.gc9a01_d / 2 - 1.5, fp_t + 2
        )
        faceplate -= Pos(ex, -fp_t / 2 - 1, fp_h / 2 + 3) * Rot(90, 0, 0) * Cylinder(
            (ELEC.gc9a01_d + TOL.loose) / 2 + 1, 4
        )
    # Camera aperture — center brow.
    faceplate -= Pos(0, 0, fp_h - 8) * Rot(90, 0, 0) * Cylinder(3.5, fp_t + 2)
    faceplate -= Pos(0, -fp_t / 2 - 1, fp_h - 8) * Box(
        ELEC.usb_cam_w, 4, ELEC.usb_cam_w * 0.8
    )
    # Mount holes on the rear face (matches the neck leg pattern).
    for z in (18, 26):
        for sx in (-1, 1):
            faceplate -= Pos(sx * 9, 0, z) * Rot(90, 0, 0) * Cylinder(1.4, fp_t + 2)

    return WristParts(j4, pod, neck, faceplate, sp.part, pod_h + fp_h, pod_h)


if __name__ == "__main__":
    from params import SERVO_SM
    w = make_wrist(SERVO_SM)
    for n, p in (
        ("j4_bracket", w.j4.bracket), ("j4_yoke", w.j4.yoke),
        ("j5_pod", w.j5_pod), ("faceplate", w.faceplate),
    ):
        bb = p.bounding_box()
        print(f"{n}: {bb.size.X:.0f}×{bb.size.Y:.0f}×{bb.size.Z:.0f} mm")
    print(f"pod_l {w.pod_l:.0f}, pod+face {w.pod_h:.0f}")
