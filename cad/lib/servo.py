"""Parametric serial-servo envelope models.

Mounting strategy: the printed bracket *clamps* the servo body (the way
SO-100/SO-101 brackets grip the STS3215 case), so the model only needs an
accurate envelope — body box, spline boss, rear idler stub. Exact tab-hole
patterns are intentionally NOT modeled; brackets clamp the body shell, which
keeps the design tolerant of whichever servo is finally purchased.

Part coordinate frame:
    origin = center of the output spline face
    +Z     = out of the servo, along the output axis (horn side)
    -Z     = into the servo body / idler stub side
    X      = along the servo's long axis (body length)
    Y      = across the body
"""

from dataclasses import dataclass
from build123d import Box, Cylinder, Pos, Axis, fillet

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from params import ServoSpec


@dataclass
class ServoPart:
    """A modeled servo plus the metadata assembly code needs."""
    part: object
    spec: ServoSpec
    shaft_offset_x: float   # output-axis offset along the body length


def make_servo(spec: ServoSpec, shaft_offset_x: float = -8.0) -> ServoPart:
    """Build an envelope-accurate servo.

    shaft_offset_x: output-axis offset along the body from center — serial
    servos put the spline toward one end. VERIFY against the real part.
    """
    # Body box, spline face at z = 0, body extends -Z.
    body = Pos(0, 0, -spec.body_h / 2) * Box(
        spec.body_w, spec.body_d, spec.body_h
    )
    body = fillet(body.edges().filter_by(Axis.Z), 1.2)

    # Output spline boss on the top face.
    spline = Pos(shaft_offset_x, 0, 0) * Cylinder(spec.spline_d / 2, spec.spline_h)

    # Rear idler stub (dual-axis servos) — the joint's far-side bearing/post
    # grips this to make the joint rigid instead of cantilevered.
    stub = Pos(shaft_offset_x, 0, -spec.body_h - 2.0) * Cylinder(
        spec.stub_d / 2, 2.0
    )

    # Cable exit pocket keeps the envelope honest for bracket design.
    cable = Pos(-spec.body_w / 2 - 1.5, 0, -spec.body_h + 8) * Box(3, 8, 8)

    return ServoPart(body + spline + stub + cable, spec, shaft_offset_x)


if __name__ == "__main__":
    from params import SERVO_SM, SERVO_LG, SERVO_XL
    for s in (SERVO_SM, SERVO_LG, SERVO_XL):
        sp = make_servo(s)
        bb = sp.part.bounding_box()
        print(
            f"{s.name:14s} bbox "
            f"{bb.size.X:.1f} × {bb.size.Y:.1f} × {bb.size.Z:.1f} mm  "
            f"mass(spec) {s.mass_g:.0f} g"
        )
