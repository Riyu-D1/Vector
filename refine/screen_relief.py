"""refine/screen_relief.py - fast R7 relief-variant screen: build the l5
solid for a given ap7.L5_RELIEF tag, mesh it coarse (cl=3.0), run the
l5_scrann deck, sigscan it.  Trends at cl3 ranked the geometries
consistently (R6 corner ~ tau 4-5 vs funnel ~8+).

Usage: cradlefix/.venv/bin/python screen_relief.py <variant>
"""
import os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FEA = os.path.join(HERE, "fea")
OUT = os.path.join(HERE, "out")
VPY = "/Users/deepakdiwan/Vector-wt/cradlefix/.venv/bin/python"
FPY = "/Users/deepakdiwan/Vector-wt/fea/fea/.venv/bin/python"
GMSH = "/Applications/FreeCAD.app/Contents/Resources/bin/gmsh"
CCX = shutil.which("ccx") or \
    "/Applications/FreeCAD.app/Contents/Resources/bin/ccx"


def sh(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    r = subprocess.run(cmd, **kw)
    if r.returncode:
        print("FAILED rc=%d" % r.returncode)
        sys.exit(1)
    return r


def main(tag):
    step = os.path.join(OUT, "scr_%s.step" % tag)
    msh = os.path.join(FEA, "scr_%s.msh" % tag)
    inp = os.path.join(FEA, "scr_%s_scrann" % tag)
    # 1) export the part under its own name so msh2 writes fix sets fine
    exp = os.path.join(FEA, "_exp_%s.py" % tag)
    with open(exp, "w") as fh:
        fh.write("import sys\nsys.path.insert(0, %r)\n"
                 "import p_wrist7 as PW\n"
                 "from build123d import export_step\n"
                 "s = PW.w_link5()\n"
                 "assert len(s.solids()) == 1\n"
                 "export_step(s, %r)\n"
                 "print('vol', round(s.volume/1e3, 2), 'cc')\n"
                 % (HERE, step))
    sh([VPY, exp])
    # 2) coarse mesh
    geo = os.path.join(FEA, "scr_%s.geo" % tag)
    with open(geo, "w") as fh:
        fh.write('SetFactory("OpenCASCADE");\n'
                 'Merge "%s";\n'
                 'Mesh.ElementOrder = 2;\nMesh.HighOrderOptimize = 2;\n'
                 'Mesh.CharacteristicLengthMax = 3.0;\n'
                 'Mesh.CharacteristicLengthMin = 0.75;\n'
                 'Mesh.CharacteristicLengthFromCurvature = 1;\n'
                 'Mesh.MinimumElementsPerTwoPi = 14;\n'
                 'Mesh 3;\nMesh.MshFileVersion = 2.2;\nSave "%s";\nExit;\n'
                 % (step, msh))
    sh([GMSH, geo], capture_output=True, text=True)
    # 3) deck + solve
    sh([FPY, os.path.join(FEA, "msh2_r3.py"), msh, inp + ".inp",
        "l5_scrann"])
    sh([CCX, "-i", inp], cwd=FEA, capture_output=True, text=True)
    # 4) sigscan
    sh([FPY, os.path.join(FEA, "sigscan_r3.py"), inp + ".frd",
        inp + ".inp", "z"])


if __name__ == "__main__":
    main(sys.argv[1])
