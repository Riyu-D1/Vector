"""refine/fea/run_r3fea.py - R3 horn-mount FEA driver.

Meshes the three horn-loaded wrist parts (fix_* STEP in refine/out),
writes the msh2_r3.py decks (face/ann/screw/scpilot/scrann/scr2 BC set),
solves (ccx) and analyses (analyze_r3.py).  Outputs land in refine/fea/.

Usage: python3 run_r3fea.py [mesh|deck|solve|all] [substr-filter]
"""
import os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RDIR = os.path.dirname(HERE)
OUT = os.path.join(RDIR, "out")
CCX = shutil.which("ccx") or \
    "/Applications/FreeCAD.app/Contents/Resources/bin/ccx"

CL = 1.5
PARTS = {"gf": ("fix_w_grip_frame", "z"),
         "l5": ("fix_w_link5", "x"),
         "l4": ("fix_w_link4", "y")}
BCASES = ("face", "ann", "screw", "scpilot", "scrann", "scr2")


def sh(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    r = subprocess.run(cmd, **kw)
    if r.returncode:
        print("FAILED rc=%d" % r.returncode)
        sys.exit(1)
    return r


def mesh(step, cl=CL):
    msh = os.path.join(HERE, step + ("" if cl == CL else "_cl%g" % cl)
                       + ".msh")
    if os.path.exists(msh):
        print("reuse", msh)
        return msh
    geo = os.path.join(HERE, step + ".geo")
    gmsh = shutil.which("gmsh") or \
        "/Applications/FreeCAD.app/Contents/Resources/bin/gmsh"
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
    sh([gmsh, geo], capture_output=True, text=True)
    return msh


def deck(part, bcase, mshpath=None):
    step = PARTS[part][0]
    mshpath = mshpath or mesh(step)
    tag = "%s_%s" % (part, bcase)
    sh([sys.executable, os.path.join(HERE, "msh2_r3.py"), mshpath,
        os.path.join(HERE, tag + ".inp"), "%s_%s" % (part, bcase)])


def solve(part, bcase):
    tag = "%s_%s" % (part, bcase)
    sh([CCX, "-i", os.path.join(HERE, tag)], cwd=HERE)
    frd = os.path.join(HERE, tag + ".frd")
    if not os.path.exists(frd):
        print("ccx produced no .frd for", tag)
        return
    sh([sys.executable, os.path.join(HERE, "analyze_r3.py"), frd,
        os.path.join(HERE, tag + ".inp"), PARTS[part][1],
        os.path.join(HERE, tag)])


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    filt = sys.argv[2] if len(sys.argv) > 2 else ""
    for part in PARTS:
        if filt and filt not in part:
            continue
        step = PARTS[part][0]
        if which in ("mesh", "all"):
            mesh(step)
        if which in ("deck", "all"):
            for bc in BCASES:
                deck(part, bc)
        if which in ("solve", "all"):
            for bc in BCASES:
                if os.path.exists(os.path.join(HERE, "%s_%s.frd"
                                               % (part, bc))):
                    print("skip solved", part, bc)
                    continue
                solve(part, bc)
    print("done")
