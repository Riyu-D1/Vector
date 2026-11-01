"""cad/act2/build_act.py - export STL + STEP for every part to out/.
Copy of ../knuckle/build.py: MODULES = ["p_act"], vendors live in PARTS,
STEP written next to each STL.
Usage (from cad/act2):  python build_act.py [part ...]   (default: all)
Prints  <name>: bbox=(xmin, xmax, ymin, ymax, zmin, zmax) vol=<cm3>"""
import importlib
import os
import sys

sys.path.insert(0, "../knuckle")

from build123d import export_stl, export_step

import frames

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
MODULES = ["p_act"]


def all_parts():
    parts = {}
    for m in MODULES:
        try:
            mod = importlib.import_module(m)
        except ModuleNotFoundError:
            continue
        parts.update(mod.PARTS)
    return parts


def main(names):
    os.makedirs(OUT, exist_ok=True)
    parts = all_parts()
    for n in names or list(parts):
        s = parts[n]()
        export_stl(s, os.path.join(OUT, n + ".stl"), tolerance=0.02,
                   angular_tolerance=0.2)
        export_step(s, os.path.join(OUT, n + ".step"))
        print(f"{n}: bbox={frames.bb(s)} vol={s.volume / 1000:.1f}")


if __name__ == "__main__":
    main(sys.argv[1:])
