"""lighten/l_mass.py - D9 mass report: stock vs lightened candidates.

Print mass = solid volume x 1.31 g/cm3 (final/PRINT_LIST.md convention:
6-wall spec on 4 mm plates => effectively solid). Adopted = none.
"""
import os, trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
RHO = 1.31e-3          # PETG-CF g/mm3 (final/PRINT_LIST.md)

print("%-20s %8s %8s %9s" % ("variant", "cm3", "g", "saved g"))
for name in ("upper_out", "upper_back"):
    base = None
    for tag in ("", "_l", "_lp", "_l2"):
        p = os.path.join(OUT, name + tag + ".stl")
        v = trimesh.load_mesh(p, force="mesh").volume / 1000.0
        g = v * 1000 * RHO
        if not tag:
            base = g
        print("%-20s %8.2f %8.2f %+9.2f" % (name + (tag or " (stock)"),
                                            v, g, base - g))
print()
print("adopted: NONE (all lightened variants failed the D9 gate)")
print("mass saved: 0.00 g")
