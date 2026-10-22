"""Shared geometry helpers for the sleek body language.

- lofted(): organic tapered bodies from rounded-rect sections
- paddle(): extruded 'knuckle + tail' silhouettes (the joint look)
- rbox(): safely-filleted rounded box
- cone(): lofted circular sections (base drum)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from build123d import (
    Axis, Box, BuildPart, BuildSketch, Circle, Cylinder, Locations, Part,
    Plane, Polygon, Pos, RectangleRounded, Rot, extrude, fillet, loft,
)


def lofted(sections, ruled=False):
    """Solid loft through rounded-rect sections: [(z, x_off, w, h, r)]."""
    with BuildPart() as bp:
        for z, x, w, h, r in sections:
            with BuildSketch(Plane.XY.offset(z)):
                with Locations((x, 0)):
                    RectangleRounded(w, h, min(r, min(w, h) / 2 - 0.05))
        loft(ruled=ruled)
    return bp.part


def hollow_loft(sections, wall):
    """Shelled loft: outer minus inset inner loft, open at both ends."""
    s = list(sections)
    inner = [(s[0][0] - 4, s[0][1], s[0][2] - 2 * wall, s[0][3] - 2 * wall, s[0][4])]
    inner += [(z, x, w - 2 * wall, h - 2 * wall, r) for z, x, w, h, r in s[1:-1]]
    inner.append(
        (s[-1][0] + 4, s[-1][1], s[-1][2] - 2 * wall, s[-1][3] - 2 * wall, s[-1][4])
    )
    return lofted(s) - lofted(inner)


def cone(sections):
    """Loft through circular sections: [(z, r)]."""
    with BuildPart() as bp:
        for z, r in sections:
            with BuildSketch(Plane.XY.offset(z)):
                Circle(r)
        loft()
    return bp.part


def rbox(x, y, z, r=None):
    r = min(r if r else 3.0, min(x, y, z) / 2 - 0.05)
    return fillet(Box(x, y, z).edges(), r)


def paddle(disc_r, w1, z1, w2, z2, thick, r=1.4):
    """Extruded XZ silhouette: disc centred at origin + trapezoid tail
    from z1 to z2. Extruded along +Y by `thick`."""
    with BuildPart() as bp:
        with BuildSketch(Plane.XZ):
            Circle(disc_r)
            Polygon((-w1 / 2, z1), (w1 / 2, z1), (w2 / 2, z2), (-w2 / 2, z2))
        extrude(amount=thick)
    part = bp.part
    part = fillet(part.edges(), min(r, thick / 2 - 0.05))
    return Pos(0, -thick / 2, 0) * part   # centre thickness on Y=0


def y_cyl(r, l):
    """Cylinder along the joint axis (+Y)."""
    return Rot(-90, 0, 0) * Cylinder(r, l)
