"""Shared helpers for the SOMA arm build."""
import os
from build123d import (
    import_step, Pos, Rot, Location, Vector, Axis, Plane,
    Box, Cylinder, Compound, Part, fillet, chamfer,
)

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "reference")

_servo_cache = None

def servo_solid():
    """The real STS3215 solid (extracted from SO-ARM-102 follower asm).

    Local axes: X = 45.2 length, Y = shaft axis (output near +Y), Z = 24.7.
    Returns a Compound (9 solids) located at its native origin.
    """
    global _servo_cache
    if _servo_cache is None:
        _servo_cache = import_step(os.path.join(REF, "sts3215_servo.step"))
    return _servo_cache


def servo_envelope(clear=0.35):
    """Servo pocket solid = servo case envelope + clearance.

    Case box only (45.2 x 24.7 x 35) grown by `clear`; wheels/ears not
    included — the pocket must clear the CASE; wheels pass into the
    cheek recesses separately.
    """
    s = servo_solid()
    bb = s.bounding_box()
    # case box: the largest-face envelope of the three case shells is
    # ~45.2 x ~35 x 24.7; wheel bosses stick out on +/-Y.  Build the
    # pocket as a box around the CASE portion only: Y in [-24.5, +8.5]
    # of the native frame (measured: case shells between wheel bosses).
    cx = Pos(-12.5, 0, 0) * Box(45.2 + 2*clear, 35.0 + 2*clear, 24.7 + 2*clear)
    return cx


def bolt_circle_holes(pcd, n, d, depth, axis="Z", start_deg=0.0):
    """Cut solid: `n` clearance holes diameter d on a PCD circle."""
    import math
    pts = []
    for i in range(n):
        a = math.radians(start_deg + i * 360.0 / n)
        pts.append((pcd / 2 * math.cos(a), pcd / 2 * math.sin(a)))
    holes = None
    for x, y in pts:
        h = Pos(x, y, -depth / 2) * Cylinder(d / 2, depth)
        holes = h if holes is None else holes + h
    if axis == "Y":
        holes = Rot(-90, 0, 0) * holes
    elif axis == "X":
        holes = Rot(0, 90, 0) * holes
    return holes


def insert_boss(r_out, h, insert_d, pilot_d=None):
    """Cylinder boss with a heat-set insert bore from the top."""
    b = Cylinder(r_out, h)
    b -= Pos(0, 0, h / 2 - 6) * Cylinder(insert_d / 2, 6)   # insert bore
    if pilot_d:
        b -= Pos(0, 0, -h / 2) * Cylinder(pilot_d / 2, h)
    return b


def bearing_pocket(od, w, press=-0.1):
    """Cut solid for a bearing seat: bore of (od+press) x width w."""
    return Cylinder((od + press) / 2, w)


def chamfer_outer(part, r):
    try:
        return fillet(part.edges().filter_by(Axis.Z), r)
    except Exception:
        return part
