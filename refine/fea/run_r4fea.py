"""refine/fea/run_r4fea.py - R4 driver: re-verification of the R4 geometry
(junction redesigns on w_link5 plate-cheek + w_link4 tail collar).

Same pipeline as run_r3fea.py but with the payload-scaled deck variants:
  - 6 BC cases x 2 parts at cl=1.5, 0.5 kg-class wrench (unsuffixed = p50)
  - scrann + scr2 at _p38 and _p25 for both parts (payload envelope)
  - scrann convergence at cl 3.0 and 0.8 (tag _c3.0 / _c0.8)
w_grip_frame is unchanged by R4 -> its R3 decks/frd stand (not re-run).

Usage: python3 run_r4fea.py [mesh|deck|solve|analyze|all]
"""
import os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RDIR = os.path.dirname(HERE)
OUT = os.path.join(RDIR, "out")
CCX = shutil.which("ccx") or \
    "/Applications/FreeCAD.app/Contents/Resources/bin/ccx"
GMSH = shutil.which("gmsh") or \
    "/Applications/FreeCAD.app/Contents/Resources/bin/gmsh"
PY = sys.executable

CL = 1.5
PARTS = {"l5": ("fix_w_link5", "x"), "l4": ("fix_w_link4", "y")}
BCASES = ("face", "ann", "screw", "scpilot", "scrann", "scr2")
PAYS = ("p38", "p25")          # extra payloads on the two bound BCs
CONVERGE_CL = (3.0, 0.8)


def sh(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    r = subprocess.run(cmd, **kw)
    if r.returncode:
        print("FAILED rc=%d" % r.returncode)
        sys.exit(1)
    return r


def msh_for(step, cl):
    return os.path.join(HERE, step + ("" if cl == CL else "_cl%g" % cl)
                        + ".msh")


def mesh(step, cl):
    msh = msh_for(step, cl)
    if os.path.exists(msh):
        print("reuse", msh)
        return msh
    geo = os.path.join(HERE, step + ("" if cl == CL else "_cl%g" % cl)
                       + ".geo")
    with open(geo, "w") as fh:
        fh.write('SetFactory("OpenCASCADE");\n'
                 'Merge "%s";\n'
                 'Mesh.ElementOrder = 2;\nMesh.HighOrderOptimize = 2;\n'
                 'Mesh.CharacteristicLengthMax = %.2f;\n'
                 'Mesh.CharacteristicLengthMin = %.2f;\n'
                 'Mesh.CharacteristicLengthFromCurvature = 1;\n'
                 'Mesh.MinimumElementsPerTwoPi = 14;\n'
                 'Mesh 3;\nMesh.MshFileVersion = 2.2;\nSave "%s";\nExit;\n'
                 % (os.path.join(OUT, step + ".step"), cl, cl / 4, msh))
    sh([GMSH, geo], capture_output=True, text=True)
    return msh


def deck(part, case, cl=CL):
    step = PARTS[part][0]
    msh = mesh(step, cl)
    tag = case if cl == CL else case + "_c%g" % cl
    sh([PY, os.path.join(HERE, "msh2_r3.py"), msh,
        os.path.join(HERE, tag + ".inp"), case])


def solve(part, case, cl=CL):
    tag = case if cl == CL else case + "_c%g" % cl
    inp = os.path.join(HERE, tag)
    frd = inp + ".frd"
    if os.path.exists(frd):
        print("skip solved", tag)
    else:
        sh([CCX, "-i", inp], cwd=HERE)
    analyze(part, case, cl)


def analyze(part, case, cl=CL):
    tag = case if cl == CL else case + "_c%g" % cl
    frd = os.path.join(HERE, tag + ".frd")
    if not os.path.exists(frd):
        print("no frd for", tag)
        return
    txt = os.path.join(HERE, tag + "_r4.txt")
    with open(txt, "w") as fh:
        sh([PY, os.path.join(HERE, "analyze_r3.py"), frd,
            os.path.join(HERE, tag + ".inp"), PARTS[part][1],
            os.path.join(HERE, tag)], stdout=fh)
    print(open(txt).read())


def cases(part):
    for bc in BCASES:
        yield part + "_" + bc
    for bc in ("scrann", "scr2"):
        for p in PAYS:
            yield "%s_%s_%s" % (part, bc, p)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for part in PARTS:
        step = PARTS[part][0]
        if which in ("mesh", "all"):
            for cl in (CL,) + CONVERGE_CL:
                mesh(step, cl)
        if which in ("deck", "all"):
            for case in cases(part):
                deck(part, case)
            for cl in CONVERGE_CL:
                deck(part, part + "_scrann", cl)
        if which in ("solve", "all"):
            for case in cases(part):
                solve(part, case)
            for cl in CONVERGE_CL:
                solve(part, part + "_scrann", cl)
        elif which == "analyze":
            for case in cases(part):
                analyze(part, case)
            for cl in CONVERGE_CL:
                analyze(part, part + "_scrann", cl)
    print("done")
