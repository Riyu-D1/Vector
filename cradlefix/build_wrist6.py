"""wrist2/build_wrist6.py - build the D6 wrist v2 parts (layout K "keel") and
the reused vendor parts in the home (L) pose -> wrist2/out/<name>.stl + .step.
Same flow as wrist/build_wrist.py.  Run:  PY build_wrist6.py [names]"""
import os, sys, time
import trimesh
from build123d import export_stl, export_step
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import p_wrist6 as PW

OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
t0 = time.time()
only = set(sys.argv[1:])
n_done = 0
for name, grp, fn in PW.parts():
    if only and name not in only:
        continue
    s = PW.pose(fn(), grp)
    b = s.bounding_box()
    stl = os.path.join(OUT, name + ".stl")
    for at in (0.3, 0.5, 0.4, 0.2, 0.6):
        export_stl(s, stl, tolerance=(0.2 if name.startswith("vendor_") else 0.05), angular_tolerance=at)
        m = trimesh.load_mesh(stl, force="mesh"); m.merge_vertices()
        if m.is_watertight:
            break
    export_step(s, os.path.join(OUT, name + ".step"))
    n_done += 1
    print("%-20s %-3s bbox %.1f x %.1f x %.1f  vol %.1f cm3  wt %s" % (name, grp, b.size.X, b.size.Y, b.size.Z, s.volume / 1000, m.is_watertight), flush=True)
print("BUILD DONE %d parts %.0f s" % (n_done, time.time() - t0))
