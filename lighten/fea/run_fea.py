"""lighten/fea/run_fea.py - one-shot verification pipeline per variant:
  STEP (preferred) -> gmsh tet mesh -> msh2gen .inp -> ccx solve ->
  analyze_gen report -> .vtu -> pyvista HTML + PNGs (fea venv).
Adapted from genlinks/fea/run_fea.py: sources derived from the variant
tag (<tag>.step for meshing, <tag>.stl for the lump containment test in
msh2gen).

Run:  python3 lighten/fea/run_fea.py <tag> [cl]     e.g. upper_out_l2
Outputs under lighten/fea/: <tag>.geo .msh .inp .frd .vtu .html/.png
"""
import os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
PV = "/Users/deepakdiwan/Vector-wt/fea/fea/.venv/bin/python"
CCX = shutil.which("ccx") or \
    "/Applications/FreeCAD.app/Contents/Resources/bin/ccx"


def sh(cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, **kw)
    if r.returncode:
        print("FAILED rc=%d" % r.returncode)
        sys.exit(1)
    return r


def main(tag, cl=2.0):
    step = os.path.join(OUT, tag + ".step")
    stl = os.path.join(OUT, tag + ".stl")
    src = step if os.path.exists(step) else stl
    msh = os.path.join(HERE, tag + ".msh")
    inp = os.path.join(HERE, tag + ".inp")
    stem = os.path.join(HERE, tag)
    sh([sys.executable, os.path.join(HERE, "gen_geo.py"),
        tag, str(cl), src, tag])
    sh([sys.executable, os.path.join(HERE, "msh2gen.py"),
        msh, inp, tag, stl])
    sh([CCX, "-i", stem], cwd=HERE)
    frd = stem + ".frd"
    if not os.path.exists(frd):
        print("ccx produced no .frd")
        sys.exit(1)
    sh([sys.executable, os.path.join(HERE, "analyze_gen.py"), frd, inp, stem])
    vtu = stem + "_step1.vtu"
    sh([PV, os.path.join(HERE, "view_gen.py"), vtu, tag])
    print("fea done for", tag)


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 2.0)
