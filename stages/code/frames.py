"""cad/knuckle/frames.py - joint frames, vendor solids, small helpers.
Copied verbatim from ~/Vector/stages/code/frames.py. Do not edit."""
import math
import os
from build123d import (Box, Compound, Cylinder, Location, Plane, Pos, Vector,
                       import_step)
import kp

HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.normpath(os.path.join(HERE, "..", "vendor"))
SERVO_STEP = os.path.normpath(os.path.join(HERE, "..", "arm", "reference",
                                           "sts3215_servo.step"))

# STEP file frame -> module frame (origin = output-face centre, +Z out).
_TOP = Location(Plane(origin=(0, 0, -38.22), x_dir=(0, 0, 1), z_dir=(0, 1, 0)))
_BOT = Location(Plane(origin=(0, 0, 120.21), x_dir=(0, 0, -1), z_dir=(0, -1, 0)))
GIM = {  # model: (file, step->module location)
    "4305-10": ("GIM4305-10.STEP", _BOT),
    "4310-10": ("GIM4310-10-GDS.stp", _BOT),
    "4310-36": ("GIM4310-36.STEP", _TOP),
}
JOINT_MODEL = {"J1": "4305-10", "J2": "4310-36", "J3": "4310-10"}

# module frame -> G frame for each GIM joint (home pose)
JOINT_LOC = {
    "J1": Location(Plane(origin=(0, 0, kp.J1_FACE_Z), x_dir=(1, 0, 0), z_dir=(0, 0, 1))),
    "J2": Location(Plane(origin=(0, kp.J2_FACE_Y, 150), x_dir=(1, 0, 0), z_dir=(0, -1, 0))),
    "J3": Location(Plane(origin=(150, kp.J3_FACE_Y, 150), x_dir=(1, 0, 0), z_dir=(0, 1, 0))),
}
# servo (STEP) frame -> G frame for each servo joint (home pose)
SERVO_LOC = {
    "J4": Location(Plane(origin=kp.J4_ORIGIN, x_dir=(1, 0, 0), z_dir=(0, 0, 1))),
    "J5": Location(Plane(origin=kp.J5_ORIGIN, x_dir=(0, 0, 1), z_dir=(0, 1, 0))),
    "J6": Location(Plane(origin=kp.J6_ORIGIN, x_dir=(0, 0, 1), z_dir=(-1, 0, 0))),
}


def mod_pt(joint, r, ang_deg, zm=0.0):
    """G point of module-frame polar point (r, angle, Zm) of a GIM joint."""
    a = math.radians(ang_deg)
    p = JOINT_LOC[joint] * Location((r * math.cos(a), r * math.sin(a), zm))
    return Vector(p.position)


def servo_pt(joint, x, y, z):
    """G point of a servo-frame point of a servo joint."""
    return Vector((SERVO_LOC[joint] * Location((x, y, z))).position)


def gim_solid(joint):
    """Vendor GIM solid placed in G (home pose)."""
    fname, step2mod = GIM[JOINT_MODEL[joint]]
    shape = import_step(os.path.join(VENDOR, fname))
    return Compound([shape]).moved(JOINT_LOC[joint] * step2mod)


def servo_solid(joint):
    """Vendor STS3215 solid (with horn) placed in G (home pose)."""
    return Compound([import_step(SERVO_STEP)]).moved(SERVO_LOC[joint])


def gbox(x0, x1, y0, y1, z0, z1):
    """Axis-aligned box from G min/max corners."""
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(
        x1 - x0, y1 - y0, z1 - z0)


def sbox(joint, x0, x1, y0, y1, z0, z1):
    """Box given in a SERVO frame (min/max), placed in G."""
    return SERVO_LOC[joint] * gbox(x0, x1, y0, y1, z0, z1)


def ycyl(x, z, d, y0, y1):
    """Cylinder along G Y, centre (x, z), from y0 to y1."""
    return Pos(x, (y0 + y1) / 2, z) * (
        Location((0, 0, 0), (90, 0, 0)) * Cylinder(d / 2, abs(y1 - y0)))


def xcyl(y, z, d, x0, x1):
    """Cylinder along G X, centre (y, z), from x0 to x1."""
    return Pos((x0 + x1) / 2, y, z) * (
        Location((0, 0, 0), (0, 90, 0)) * Cylinder(d / 2, abs(x1 - x0)))


def zcyl(x, y, d, z0, z1):
    """Cylinder along G Z, centre (x, y), from z0 to z1."""
    return Pos(x, y, (z0 + z1) / 2) * Cylinder(d / 2, abs(z1 - z0))


def bb(shape):
    """Bounding box rounded to 0.01 mm: (xmin, xmax, ymin, ymax, zmin, zmax)."""
    b = shape.bounding_box()
    return tuple(round(v, 2) for v in (b.min.X, b.max.X, b.min.Y, b.max.Y,
                                       b.min.Z, b.max.Z))


def yprism(pts_xz, y0, y1):
    """Prism along G Y from y0 to y1 (y1 > y0) with outline [(x, z), ...]."""
    from build123d import Polygon, extrude
    pl = Plane(origin=(0, y0, 0), x_dir=(1, 0, 0), z_dir=(0, 1, 0))
    # on this plane local u = G x, local v = -G z
    face = pl * Polygon(*[(x, -z) for x, z in pts_xz], align=None)
    return extrude(face, amount=y1 - y0, dir=(0, 1, 0))


def arc_pts(c_xz, r, y, a0, a1, step=10.0):
    """Waypoints on an arc in the XZ plane (around a Y axis), degrees,
    angle 0 = +X, 90 = +Z.  Returns [(x, y, z), ...] including both ends."""
    n = max(1, int(abs(a1 - a0) / step))
    return [(c_xz[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), y,
             c_xz[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
            for i in range(n + 1)]


def arc_pts_yz(x, r, a0, a1, zc=150.0, step=10.0):
    """Waypoints on an arc in the YZ plane around the roll axis (y=0,
    z=zc); angle 0 = +Y, 90 = +Z."""
    n = max(1, int(abs(a1 - a0) / step))
    return [(x, r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             zc + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
            for i in range(n + 1)]
