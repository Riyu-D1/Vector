"""cad/arm2/build_arm2.py - build every A2a part in the home (L) pose -> out/<name>.stl + .step
prints one line per part: name group bbox X Y Z vol_cm3"""
import os, sys, time
import trimesh
from build123d import export_stl, export_step
import p_arm2 as PA
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)
t0 = time.time()
for name, grp, fn in PA.parts():
    s = PA.pose(fn(), grp)
    b = s.bounding_box()
    stl = os.path.join(OUT, name + ".stl")
    for at in (0.3, 0.5, 0.4, 0.2, 0.6):          # some reBot STEP faces only mesh watertight at some angular tolerances
        export_stl(s, stl, tolerance=(0.2 if name.startswith("vendor_") else 0.05), angular_tolerance=at)
        m = trimesh.load_mesh(stl, force="mesh"); m.merge_vertices()
        if m.is_watertight:
            break
    export_step(s, os.path.join(OUT, name + ".step"))
    print("%-20s %-3s bbox %.1f x %.1f x %.1f  vol %.1f cm3  wt %s" % (name, grp, b.size.X, b.size.Y, b.size.Z, s.volume / 1000, m.is_watertight), flush=True)
print("BUILD DONE %d parts %.0f s" % (len(PA.parts()), time.time() - t0))
