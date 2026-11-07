"""refine/build_refine.py - build R1-fixed parts, probe geometry, export
STL+STEP to refine/out/.  Also builds the STOCK (buggy) equivalents so
before/after numbers come from the same script.

Run:  $PYCAD build_refine.py [stock|fixed|both]   (default both)
"""
import os, sys
import numpy as np
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.gp import gp_Pnt
from OCP.TopAbs import TopAbs_IN, TopAbs_ON

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for d in (HERE, os.path.join(ROOT, "cradlefix"), os.path.join(ROOT, "cad", "arm2b"),
          os.path.join(ROOT, "cad", "arm2"), os.path.join(ROOT, "toolchg")):
    sys.path.insert(0, d)

from build123d import export_stl, export_step

OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)


def inside(sd, a, b, h):
    c = BRepClass3d_SolidClassifier(sd, gp_Pnt(a, b, h), 1e-6)
    return c.State() in (TopAbs_IN, TopAbs_ON)


def report(name, s):
    solids = sorted(s.solids(), key=lambda x: -x.volume)
    bb = s.bounding_box()
    print("%-16s solids=%d  vol=%.2f cm3  bbox x %.1f..%.1f  y %.1f..%.1f  z %.1f..%.1f"
          % (name, len(solids), s.volume / 1000, bb.min.X, bb.max.X,
             bb.min.Y, bb.max.Y, bb.min.Z, bb.max.Z))
    for i, so in enumerate(solids[1:], 1):
        sb = so.bounding_box()
        print("    sliver%d %.1f mm3  x %.1f..%.1f y %.1f..%.1f z %.1f..%.1f"
              % (i, so.volume, sb.min.X, sb.max.X, sb.min.Y, sb.max.Y,
                 sb.min.Z, sb.max.Z))
    return solids


def cheek_scan(name, s, a_lo, a_hi, h_lo, h_hi, tag):
    """fraction of (a,h) stations where material exists on each b side of
    the pocket wall band (12.6..14.8)."""
    sd = max(s.solids(), key=lambda x: x.volume).wrapped
    plus = minus = 0
    n = 0
    for a in np.arange(a_lo, a_hi, 4.0):
        for h in np.arange(h_lo, h_hi, 4.0):
            n += 1
            if inside(sd, a, 13.7, h):
                plus += 1
            if inside(sd, a, -13.7, h):
                minus += 1
    print("    %s cheek-band probes (%d pts): +b %d  -b %d"
          % (tag, n, plus, minus))


def main(which="both"):
    import p_wrist7 as R
    sys.path.insert(0, os.path.join(ROOT, "cradlefix"))
    import p_wrist6 as W        # stock (buggy) - imported from cradlefix/

    jobs = []
    if which in ("both", "stock"):
        jobs += [("stock_w_grip_frame", W.w_grip_frame),
                 ("stock_w_link5", W.w_link5),
                 ("stock_w_link4", W.w_link4)]
    if which in ("both", "fixed"):
        jobs += [("fix_w_grip_frame", R.w_grip_frame),
                 ("fix_w_link5", R.w_link5),
                 ("fix_w_link4", R.w_link4)]
        import p_toolchg7 as RT
        import p_toolchg as PT
        jobs += [("stock_tool_grip", PT.tool_grip),
                 ("fix_tool_grip", RT.tool_grip_r)]

    for name, fn in jobs:
        s = fn()
        solids = report(name, s)
        # cheek band probes per part (a/h ranges chosen inside each cage)
        if "grip" in name and "tool" not in name:
            cheek_scan(name, s, 72.0, 112.0, -50.0, -10.0, "cage")
        elif "link5" in name:
            cheek_scan(name, s, 18.0, 60.0, -50.0, -10.0, "cage")
        elif "link4" in name:
            cheek_scan(name, s, 22.0, 60.0, 0.0, 36.0, "fin")
        elif "tool_grip" in name:
            cheek_scan(name, s, 84.0, 124.0, -50.0, -10.0, "cage")
        export_stl(s, os.path.join(OUT, name + ".stl"), tolerance=0.01)
        export_step(s, os.path.join(OUT, name + ".step"))
        print("    wrote out/%s.{stl,step}" % name)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "both")
