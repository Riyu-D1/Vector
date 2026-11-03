"""l_hotmap.py - sample FEA VM field on an x-z grid over each plate.

For every candidate cut zone, report the p95 von-Mises INSIDE the
footprint (all y). p95 ~ 0 means the region is dead material: cutting it
cannot raise stress or deflection meaningfully.

usage:
  .venv/bin/python l_hotmap.py             # grid dump for both plates
"""
import numpy as np
import pyvista as pv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FEA = os.path.join(HERE, "fea")
OUT = os.path.join(HERE, "out")

for part in ("upper_out", "upper_back"):
    m = pv.read(os.path.join(FEA, part + "_step1.vtu"))
    pts = m.points
    vm = m.point_data["VM"]
    st = pv.read(os.path.join(OUT, part + ".stl"))
    xmin, xmax, ymin, ymax, zmin, zmax = st.bounds
    print("=== %s  x[%.1f,%.1f] y[%.1f,%.1f] z[%.1f,%.1f]" %
          (part, xmin, xmax, ymin, ymax, zmin, zmax))
    # grid of 6x8 mm cells over the x-z extent; p95 VM of nodes inside
    xs = np.arange(xmin + 3, xmax - 3, 6.0)
    zs = np.arange(zmin + 4, zmax - 4, 8.0)
    print("    " + "".join("%6.0f" % x for x in xs))
    for z in zs[::-1]:
        row = []
        for x in xs:
            sel = (np.abs(pts[:, 0] - x) < 3) & (np.abs(pts[:, 2] - z) < 4)
            row.append(np.percentile(vm[sel], 95) if sel.any() else -1)
        print("z=%5.0f " % z + "".join("%6.2f" % v for v in row))
