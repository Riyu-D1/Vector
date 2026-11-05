"""toolchg/fea/run_tcfea.py - one-shot verification per part:
  W-frame STEP -> gmsh tet mesh -> msh2tc .inp -> ccx solve ->
  analyze_tc report -> .vtu -> pyvista HTML + PNGs (fea venv).
Same flow as lighten/fea/run_fea.py.

Run:  python3 run_tcfea.py [tc_master|tc_plate|all] [cl]
Outputs under toolchg/fea/: <tag>.geo/.msh/.inp/.frd/.vtu/.html/.png
(generated - git-ignored)
"""
import os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TC = os.path.dirname(HERE)
sys.path.insert(0, TC)
sys.path.insert(0, os.path.join(TC, "..", "cradlefix"))
sys.path.insert(0, os.path.join(TC, "..", "cad", "arm2b"))
sys.path.insert(0, os.path.join(TC, "..", "cad", "arm2"))
PV = "/Users/deepakdiwan/Vector-wt/fea/fea/.venv/bin/python"
CCX = shutil.which("ccx") or \
    "/Applications/FreeCAD.app/Contents/Resources/bin/ccx"
PYCAD = "/Users/deepakdiwan/Vector-wt/cradlefix/.venv/bin/python"


def sh(cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, **kw)
    if r.returncode:
        print("FAILED rc=%d" % r.returncode)
        sys.exit(1)
    return r


def export_steps(tags):
    code = (
        "import sys; sys.path.insert(0, %r)\n"
        "import p_toolchg as PW\n"
        "from build123d import export_step\n"
        "for t in %r:\n"
        "    s = getattr(PW, t)()\n"
        "    export_step(s, %r + t + '.step')\n"
        "    print(t, 'vol', s.volume)\n" % (TC, tags, HERE + os.sep))
    sh([PYCAD, "-c", code])


def main(tag, cl=1.5):
    step = os.path.join(HERE, tag + ".step")
    msh = os.path.join(HERE, tag + ".msh")
    inp = os.path.join(HERE, tag + ".inp")
    stem = os.path.join(HERE, tag)
    sh([sys.executable, os.path.join(HERE, "gen_geo.py"),
        tag, str(cl), step, tag])
    sh([sys.executable, os.path.join(HERE, "msh2tc.py"), msh, inp, tag])
    sh([CCX, "-i", stem], cwd=HERE)
    frd = stem + ".frd"
    if not os.path.exists(frd):
        print("ccx produced no .frd")
        sys.exit(1)
    sh([sys.executable, os.path.join(HERE, "analyze_tc.py"), frd, inp, stem])
    vtu = stem + "_step1.vtu"
    sh([PV, os.path.join(HERE, "view_tc.py"), vtu, tag])
    print("fea done for", tag)


if __name__ == "__main__":
    tags = (["tc_master", "tc_plate"] if len(sys.argv) < 2
            or sys.argv[1] == "all" else [sys.argv[1]])
    cl = float(sys.argv[2]) if len(sys.argv) > 2 else 1.5
    export_steps(tags)
    for t in tags:
        main(t, cl)
