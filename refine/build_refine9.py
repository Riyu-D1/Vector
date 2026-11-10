"""refine/build_refine9.py - build the R9 wrist parts + assembly.

Same convention as build_refine.py (fix_ names into refine/out) but
pointed at p_wrist9/ap9: the +b yoke plate, J4-axis journal boss, cradle
pin seat and the d3 steel dowel pin.  Also exports the posed wrist
assembly (wrist9_asm.step) including the pin and vendor parts.

Run:  $PY build_refine9.py
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for d in (HERE, os.path.join(ROOT, "cradlefix"), os.path.join(ROOT, "cad", "arm2b"),
          os.path.join(ROOT, "cad", "arm2"), os.path.join(ROOT, "toolchg")):
    sys.path.insert(0, d)

from build123d import export_stl, export_step, Compound

OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)


def main():
    import p_wrist9 as R
    import p_wrist7 as R7
    jobs = [("fix_w_grip_frame", R.w_grip_frame),
            ("fix_w_link5", R.w_link5),
            ("fix_w_link4", R.w_link4),
            ("fix_w_j4_cradle", R.w_j4_cradle),
            ("fix_wrist_pin", R.wrist_pin)]
    for name, fn in jobs:
        s = fn()
        print("%-18s vol=%.2f cm3  solids=%d" % (name, s.volume / 1000,
                                                 len(list(s.solids()))))
        export_stl(s, os.path.join(OUT, name + ".stl"), tolerance=0.01)
        export_step(s, os.path.join(OUT, name + ".step"))

    # posed assembly - pose every part to the W (arm assembly) frame via
    # R.pose(s, grp), same convention as wrist2/build_wrist6.py; the ROM
    # sweeps + hole-axis checks read out/<name>.{stl,step} in W pose.
    label = {}
    kids = []
    for name, grp, fn in R.parts():
        s = R.pose(fn(), grp)
        kids.append(s)
        label[id(s)] = name
        if name in ("w_j4_cradle", "w_link4", "w_link5", "w_grip_frame"):
            export_stl(s, os.path.join(OUT, name + ".stl"), tolerance=0.05)
            export_step(s, os.path.join(OUT, name + ".step"))
    pin = R.pose(R.rest(R.wrist_pin()), "fo")
    kids.append(pin)
    label[id(pin)] = "wrist_pin"
    export_stl(pin, os.path.join(OUT, "wrist_pin.stl"), tolerance=0.02)
    export_step(pin, os.path.join(OUT, "wrist_pin.step"))
    asm = Compound(children=kids, label="wrist9_asm")
    for c in asm.children:
        c.label = label.get(id(c), "?")
    export_step(asm, os.path.join(OUT, "wrist9_asm.step"))
    print("wrote out/wrist9_asm.step (%d parts)" % len(kids))


if __name__ == "__main__":
    main()
