"""cad/act2/build_act.py - export STEP + STL for every part to out/. Copied verbatim.
Usage (from cad/act2):  python build_act.py [part ...]   (default: all)
Prints  <name>: bbox=(xmin, xmax, ymin, ymax, zmin, zmax) vol=<cm3>"""
import os
import sys
from build123d import export_step, export_stl
from parts import PARTS

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def main(names):
    os.makedirs(OUT, exist_ok=True)
    for n in names or list(PARTS):
        s = PARTS[n]()
        export_stl(s, os.path.join(OUT, n + ".stl"), tolerance=0.02, angular_tolerance=0.2)
        if not n.startswith("buy_"):
            export_step(s, os.path.join(OUT, n + ".step"))
        b = s.bounding_box()
        bb = tuple(round(v, 2) for v in (b.min.X, b.max.X, b.min.Y, b.max.Y, b.min.Z, b.max.Z))
        print(f"{n}: bbox={bb} vol={s.volume / 1000:.1f}")


if __name__ == "__main__":
    main(sys.argv[1:])
