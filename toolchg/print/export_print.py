"""toolchg/print/export_print.py - D13 print-pack exporter.

Builds the prototype print parts from the TESTED p_toolchg code plus the
R-fixed fix_tool_grip (refine p_toolchg7, arm-fullfix trimmed rear rim -
ships in place of the stock D13 tool_grip), poses them to the home pose, then orients
each for the STATUS print orientation:

  coupling pair drawn along the a-axis -> print -a face down
  (the -a lead chamfers double as support-free ramps); for the tool
  bodies that is "plate-face down" = the tc_plate socket mouth on the
  bed, body pointing +a/up.  tc_master -a face = horn-plate back face.

So every part is rotated +a -> +Z and dropped to z_min = 0.

Exports STL + STEP into toolchg/print/stl/ and toolchg/print/step/
(gitignored generated artifacts per rule 0.4 / toolchg/.gitignore).

Run from anywhere:  PY export_print.py [names...]
Prints per part: oriented bbox, volume, watertight, mass estimates
(solid and printed at INFILL_EFF) for PRINT.md.
"""
import os, sys, time
import trimesh
from build123d import export_stl, export_step, Pos, Rot

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))     # repo root
sys.path.insert(0, os.path.join(HERE, ".."))      # toolchg/
sys.path.insert(0, os.path.join(ROOT, "refine"))  # refine/
sys.path.insert(0, os.path.join(ROOT, "cradlefix"))
sys.path.insert(0, os.path.join(ROOT, "cad", "arm2b"))
sys.path.insert(0, os.path.join(ROOT, "cad", "arm2"))
import p_toolchg as PW                            # noqa
import p_toolchg7 as PW7                          # noqa
import tc_params as T                             # noqa

STL = os.path.join(HERE, "stl")
STEP = os.path.join(HERE, "step")
os.makedirs(STL, exist_ok=True)
os.makedirs(STEP, exist_ok=True)

NAMES = ("tc_master", "tc_plate", "tool_pen")
only = set(sys.argv[1:])

# arm-fullfix: the pack ships the R-fixed tool cage (refine p_toolchg7),
# not the stock D13 tool_grip.  tool_grip_r() is authored in the tool
# body frame already, so apply rest() like the stock parts entries do.
EXTRA = {"fix_tool_grip": ("w6", lambda: PW.rest(PW7.tool_grip_r()))}

t0 = time.time()
for name, grp, fn in list(PW.parts()) + [
        (n, g, f) for n, (g, f) in EXTRA.items()]:
    if (name not in NAMES and name not in EXTRA) \
            or (only and name not in only):
        continue
    s = PW.pose(fn(), grp)                        # world home pose, a=+X
    s = Rot(0, -90, 0) * s                        # +a -> +Z, -a face down
    b = s.bounding_box()
    s = Pos(-b.min.X, -b.min.Y, -b.min.Z) * s     # min corner -> origin
    b = s.bounding_box()
    stl = os.path.join(STL, name + ".stl")
    for at in (0.3, 0.5, 0.4, 0.2, 0.6):
        export_stl(s, stl, tolerance=0.05, angular_tolerance=at)
        m = trimesh.load_mesh(stl, force="mesh"); m.merge_vertices()
        if m.is_watertight:
            break
    export_step(s, os.path.join(STEP, name + ".step"))
    v = s.volume                                  # mm3
    print("%-10s bbox %5.1f x %5.1f x %5.1f mm  vol %5.1f cm3  wt %s"
          "  m_solid %.1f g  m_print %.1f g"
          % (name, b.size.X, b.size.Y, b.size.Z, v / 1000,
             m.is_watertight, v * T.RHO_PETGCF,
             v * T.RHO_PETGCF * T.INFILL_EFF), flush=True)
print("EXPORT DONE %.0f s" % (time.time() - t0))
