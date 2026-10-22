"""Structural links v2 — lofted 'bone' shells.

Tapered rounded-rect loft, hollow, with a subtle waist mid-span and a
shallow rear cable channel. End faces carry the axial M3 bolt pattern
into the joint rails/feet. Length = span between joint module faces
(the joints own the axis-to-axis distance ends).
"""

import math
from dataclasses import dataclass

from build123d import Box, Cylinder, Pos, Part

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from params import TOL
from lib.geom import lofted, hollow_loft


@dataclass
class LinkPart:
    part: Part
    length: float


def make_link(
    length: float,
    w0: float = 46.0,          # X width at the bottom end
    h0: float = 42.0,          # Y depth at the bottom end
    w1: float = 42.0,
    h1: float = 38.0,
    wall: float = 2.6,
    bolt_pitch_x: float = 30.0,
    bolt_pitch_y: float = 24.0,
) -> LinkPart:
    """Lofted link along +Z. Profiles pinch ~8% at mid-span — the organic
    'bone' look — and the rear face gets a covered-looking cable groove."""
    waist_w = (w0 + w1) / 2 * 0.88
    waist_h = (h0 + h1) / 2 * 0.88

    sections = [
        (0.0,            0.0, w0, h0, min(w0, h0) * 0.30),
        (length * 0.45,  0.0, waist_w, waist_h, waist_w * 0.30),
        (length * 0.85,  0.0, w1 * 0.98, h1 * 0.98, w1 * 0.28),
        (length,         0.0, w1, h1, w1 * 0.28),
    ]
    part = hollow_loft(sections, wall)

    # Cable channel — shallow groove down the rear (−X) face.
    part -= Pos(-w0 / 2 + 1.5, 0, length / 2) * Box(5.0, h0 * 0.55, length - 16)

    # End faces: 4× M3 axial pattern (threads into the joint rail/foot).
    for z in (4.0, length - 4.0):
        for sx in (-1, 1):
            for sy in (-1, 1):
                part -= Pos(sx * bolt_pitch_x / 2, sy * bolt_pitch_y / 2, z) * Cylinder(
                    1.35, 9          # M2.5 tap depth into the end face walls
                )

    return LinkPart(part, length)


if __name__ == "__main__":
    from params import LINKS
    for name, L, w, h in (
        ("upper", LINKS.upper_arm, 46, 42), ("fore", LINKS.forearm, 42, 38)
    ):
        lp = make_link(110, w0=w, h0=h, w1=w - 4, h1=h - 4)
        bb = lp.part.bounding_box()
        print(
            f"{name}: {bb.size.X:.0f}×{bb.size.Y:.0f}×{bb.size.Z:.0f} mm, "
            f"vol {lp.part.volume/1000:.1f} cm³ "
            f"(~{lp.part.volume/1000*1.27*0.4:.0f} g @40% infill)"
        )
