"""cad/knuckle/build.py - export STLs (home pose) to out/. Copied verbatim.
Usage (from cad/knuckle):  python build.py [part ...]   (default: all)
Prints  <name>: bbox=(xmin, xmax, ymin, ymax, zmin, zmax) vol=<cm3>"""
import importlib
import os
import sys

from build123d import export_stl

import frames

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
MODULES = ["p_base", "p_upper", "p_fore", "p_wrist", "p_grip"]
VENDOR = {"vendor_J1": lambda: frames.gim_solid("J1"),
          "vendor_J2": lambda: frames.gim_solid("J2"),
          "vendor_J3": lambda: frames.gim_solid("J3"),
          "vendor_J4": lambda: frames.servo_solid("J4"),
          "vendor_J5": lambda: frames.servo_solid("J5"),
          "vendor_J6": lambda: frames.servo_solid("J6")}


def all_parts():
    parts = {}
    for m in MODULES:
        try:
            mod = importlib.import_module(m)
        except ModuleNotFoundError:
            continue
        parts.update(mod.PARTS)
    parts.update(VENDOR)
    return parts


def main(names):
    os.makedirs(OUT, exist_ok=True)
    parts = all_parts()
    for n in names or list(parts):
        s = parts[n]()
        export_stl(s, os.path.join(OUT, n + ".stl"), tolerance=0.02,
                   angular_tolerance=0.2)
        print(f"{n}: bbox={frames.bb(s)} vol={s.volume / 1000:.1f}")


if __name__ == "__main__":
    main(sys.argv[1:])
