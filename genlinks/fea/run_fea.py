"""genlinks/fea/run_fea.py - one-shot verification pipeline per candidate:
  gmsh tet mesh -> msh2gen .inp -> ccx solve -> analyze_gen report -> .vtu
  -> pyvista HTML + PNGs (fea venv).

Run:  python3 genlinks/fea/run_fea.py <part> [cl]
Outputs under genlinks/fea/: <part>.geo .msh .inp .frd .vtu <part>.html/png
"""
import os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.dirname(HERE)
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


def main(part, cl=2.0, stl=None, tag=None):
    tag = tag or part
    gen = os.path.join(HERE, "gen_geo.py")
    msh = os.path.join(HERE, tag + ".msh")
    inp = os.path.join(HERE, tag + ".inp")
    stem = os.path.join(HERE, tag)
    sh([sys.executable, gen, part, str(cl)] +
       ([stl, tag] if stl else []))
    sh([sys.executable, os.path.join(HERE, "msh2gen.py"), msh, inp, part])
    job = os.path.join(HERE, tag)
    sh([CCX, "-i", job], cwd=HERE)
    frd = job + ".frd"
    if not os.path.exists(frd):
        print("ccx produced no .frd")
        sys.exit(1)
    sh([sys.executable, os.path.join(HERE, "analyze_gen.py"), frd, inp, stem])
    vtu = stem + "_step1.vtu"
    sh([PV, os.path.join(HERE, "view_gen.py"), vtu, tag])
    print("fea done for", tag)


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 2.0,
         sys.argv[3] if len(sys.argv) > 3 else None,
         sys.argv[4] if len(sys.argv) > 4 else None)
