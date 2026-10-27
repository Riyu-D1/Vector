"""Assembly builder: places every part, exports STEP + per-part STL.

Also produces `gear_demo(angle_deg)` — the gearbox stack with the input
shaft rotated, used by the interference sweep in check.py.
"""

import math
import numpy as np
from build123d import Part, Compound, Pos, Rot, Location, export_step, export_stl

from params import P, MR106, B6701, B6809
from cycloid import disc_pose
import parts as pt


def build(input_deg: float = 0.0) -> Compound:
    """Full assembly. input_deg rotates the input shaft (and wobbles discs,
    spins output by -input/15) so the mechanism can be posed for checks."""
    g = P.gear
    a = math.radians(input_deg)
    ex, ey, phi = disc_pose(a, g)
    out_deg = math.degrees(-a / g.disc_lobes)

    comp = []
    comp += [Pos(0, 0, 0) * pt.housing()]
    comp += [Pos(0, 0, 0) * pt.motor_shell()]
    comp += [Pos(0, 0, 0) * pt.end_cap()]
    comp += [Rot(0, 0, input_deg) * pt.input_shaft()]
    comp += [Pos(0, 0, 0) * pt.motor_shaft()]
    comp += [Rot(0, 0, out_deg) * pt.output_shaft()]
    # discs: disc1 phase +e, disc2 phase -e (180 deg)
    d1 = pt.cycloidal_disc()
    comp += [Pos(ex, ey, pt.Z_DISC1) * Rot(0, 0, math.degrees(phi)) * d1]
    d2 = pt.cycloidal_disc()
    comp += [Pos(-ex, -ey, pt.Z_DISC2) * Rot(0, 0, math.degrees(phi)) * d2]
    # 16 ring pins
    for i in range(g.ring_pins):
        b = math.radians(360 * i / g.ring_pins)
        comp += [Pos(g.pin_pitch_r * math.cos(b),
                     g.pin_pitch_r * math.sin(b), 0) * pt.ring_pin()]
    # 2 x 6701 eccentric bearings (on the journals)
    comp += [Pos(ex, ey, 0) * Pos(0, 0, pt.Z_DISC1 + 0.5) * pt.bearing(B6701)]
    comp += [Pos(-ex, -ey, 0) * Pos(0, 0, pt.Z_DISC2 + 0.5) * pt.bearing(B6701)]
    # 2 x 6809 on the output hub
    comp += [Pos(0, 0, pt.Z_BRG1[0]) * pt.bearing(B6809)]
    comp += [Pos(0, 0, pt.Z_BRG2[0]) * pt.bearing(B6809)]
    # 6 output-pin rollers (one per pin per disc = 12) + 1 pilot MR106
    rb = P.out_pin_bcd / 2
    for i in range(P.n_out_pins):
        b = math.radians(60 * i)
        x, y = rb * math.cos(b), rb * math.sin(b)
        comp += [Rot(0, 0, out_deg) * Pos(x, y, 0) *
                 Pos(0, 0, pt.Z_DISC1 + 1.0) * pt.roller()]
        comp += [Rot(0, 0, out_deg) * Pos(x, y, 0) *
                 Pos(0, 0, pt.Z_DISC2 + 1.0) * pt.roller()]
    comp += [Pos(0, 0, pt.Z_PLATE1 + 1.0) * pt.roller()]          # pilot
    # standard parts
    comp += [pt.motor(), pt.esc_board(), pt.encoder_board(),
             pt.magnet(), pt.hex_standoff()]
    return Compound(children=comp)


def gear_demo(input_deg: float):
    """Just the mechanism (housing + pins + discs + shafts + rollers)."""
    g = P.gear
    a = math.radians(input_deg)
    ex, ey, phi = disc_pose(a, g)
    out_deg = math.degrees(-a / g.disc_lobes)
    comp = [pt.housing(), Rot(0, 0, input_deg) * pt.input_shaft(),
            Rot(0, 0, out_deg) * pt.output_shaft(),
            Pos(ex, ey, pt.Z_DISC1) * Rot(0, 0, math.degrees(phi)) *
            pt.cycloidal_disc(),
            Pos(-ex, -ey, pt.Z_DISC2) * Rot(0, 0, math.degrees(phi)) *
            pt.cycloidal_disc()]
    for i in range(g.ring_pins):
        b = math.radians(360 * i / g.ring_pins)
        comp.append(Pos(g.pin_pitch_r * math.cos(b),
                        g.pin_pitch_r * math.sin(b), 0) * pt.ring_pin())
    return Compound(children=comp)


def main():
    import os
    out = os.path.join(os.path.dirname(__file__), "export")
    os.makedirs(out, exist_ok=True)
    # STLs: every printed part (disc once, exported twice-named for BOM)
    for name, fn in pt.PRINTED.items():
        p = fn()
        export_stl(p, os.path.join(out, f"{name}.stl"))
        print("stl", name)
    asm = build()
    export_step(asm, os.path.join(out, "actuator_assembly.step"))
    print("step actuator_assembly.step")


if __name__ == "__main__":
    main()
