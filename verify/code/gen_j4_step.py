"""verify/code/gen_j4_step.py - J4 STS3250 cradle bolt-check assembly
(stage V1 task 2, J4).  Everything is placed in the cradle STEP's native
frame: J4 axis (measured on the pilot cylinders) at x=62.4, z=216.2, || +Y.

Parts:
  cradle   - p_arm2b.j4_cradle() as-built (verify/out/step/j4_cradle.step)
  fore_r   - arm2b fore2("R") (rest frame J4 at -9.7, 197.5) translated by
             (72.1, 0, 18.7) into the cradle frame, then clipped to the bolt pad
Load path (BOM + sanity doc):
  wrist torque -> rigid servo-case lump (pocket faces -> ref) -> cradle ->
  4x M3x10 pilots (a,h)=(-6,+-9),(-28,+-9) -> fore_r plate (ground).
Loads (gravity_up1, x2 on self-weight + 0.5 kg payload):
  m=0.746 kg d_cm=105.1 mm -> F=14.64 N, M=1.54 N.m (governs; shock=1.19).
Run:  $PY gen_j4_step.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VER = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(VER, "cad", "arm2b"))
sys.path.insert(0, os.path.join(VER, "cad", "arm2"))
sys.path.insert(0, os.path.join(VER, "cad", "act2"))

from build123d import import_step, Pos, Rot, Solid, Plane, Compound, export_step, Box, Location
import ap2b as B
import p_arm2b as PB

J4X, J4Z = 62.4, 216.2          # cradle STEP native frame (pilot cylinders)
DX, DZ = J4X - (-9.7), J4Z - 197.5    # rest-frame J4 (-9.7,197.5) -> cradle frame


def clip(s, x0, x1, y0, y1, z0, z1):
    return s & Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * \
        Box(x1 - x0, y1 - y0, z1 - z0)


def main():
    outd = os.path.join(HERE, "..", "out", "step", "jt_j4")
    os.makedirs(outd, exist_ok=True)
    src = os.path.join(HERE, "..", "out", "step", "j4_cradle.step")
    s = import_step(src)
    export_step(s, os.path.join(outd, "cradle.step"))

    fr = PB.fore2("R").moved(Location((DX, 0, DZ)))
    frc = clip(fr, J4X - 40.0, J4X + 45.0, 31.0, 38.0, J4Z - 35.0, J4Z + 35.0)
    export_step(frc, os.path.join(outd, "fore_r.step"))
    print("wrote %s" % outd)


if __name__ == "__main__":
    main()
