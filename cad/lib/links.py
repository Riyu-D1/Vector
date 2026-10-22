"""Structural links between joint axes — ribbed shells with a cable channel.

Each link is a hollowed beam: two end plates (bolt patterns matching the
joint yokes/brackets) + a ribbed shell with a longitudinal cable groove.
"""

import math
from dataclasses import dataclass

from build123d import Box, Cylinder, Pos, Rot, Part

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from params import TOL


@dataclass
class LinkPart:
    part: Part
    length: float


def make_link(
    length: float,
    width: float,
    height: float,
    wall: float = TOL.wall,
    bolt_pitch_x: float = 40.0,
    bolt_pitch_y: float = 30.0,
    n_ribs: int = 3,
    cable_w: float = 8.0,
) -> LinkPart:
    """Link aligned along +Z between two joint axes.

    length = axis-to-axis distance. End plates straddle each axis with a
    4× M3 pattern; the shell is hollowed to save weight, with transverse
    ribs for stiffness and a side groove for the cable run.
    """
    end_t = 5.0
    inner_len = length - 2 * end_t

    # Hollow shell.
    shell = Pos(0, 0, length / 2) * Box(width, height, inner_len + 0.01)
    shell -= Pos(0, 0, length / 2) * Box(
        width - 2 * wall, height - 2 * wall, inner_len + 4
    )
    # Transverse ribs restore stiffness.
    rib_t = 3.0
    for i in range(n_ribs):
        z = end_t + inner_len * (i + 1) / (n_ribs + 1)
        shell += Pos(0, 0, z) * Box(
            width - 2 * wall + 0.01, height - 2 * wall + 0.01, rib_t
        )

    # Cable groove along one edge — open slot running the length.
    shell -= Pos(width / 2 - wall / 2 - cable_w / 2, 0, length / 2) * Box(
        cable_w, height - 2 * wall, inner_len
    )

    # End plates (bolt to yokes/brackets).
    for z, _ in ((end_t / 2, "bottom"), (length - end_t / 2, "top")):
        plate = Pos(0, 0, z) * Box(width + 8, height + 8, end_t)
        shell += plate
        for sx in (-1, 1):
            for sy in (-1, 1):
                shell -= Pos(
                    sx * bolt_pitch_x / 2, sy * bolt_pitch_y / 2, z
                ) * Cylinder(1.6, end_t + 2)

    return LinkPart(shell, length)


if __name__ == "__main__":
    from params import LINKS
    for name, L in (("upper", LINKS.upper_arm), ("fore", LINKS.forearm)):
        lp = make_link(L, width=44, height=40)
        bb = lp.part.bounding_box()
        print(
            f"{name}: {bb.size.X:.0f}×{bb.size.Y:.0f}×{bb.size.Z:.0f} mm, "
            f"vol {lp.part.volume/1000:.1f} cm³ (~{lp.part.volume/1000*1.27*0.4:.0f} g @40% infill)"
        )
