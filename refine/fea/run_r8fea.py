"""refine/fea/run_r8fea.py - R8 verification driver.

Final bounded pass: the lofted w_link5 relief (L5_LOFT swept-envelope
table) + the outboard-thickened w_link4 (L4_B -> -32.1, swept case-front
clearance).  Decks from msh2_r3.py now apply every wrench at the true
mass-weighted carried-stack COM (fixes the ~10 % legacy-ref moment
under-statement) and self-weight follows the wrench direction.

Case plan:
  l5 (new geometry): full re-mesh + re-solve of the R5/R7 case set
      (6 BC + p25/p38 on scrann/scr2 + cl 3.0/0.8 convergence +
      the full direction-bound set).
  l4 (new geometry): full re-mesh + re-solve + NEW direction bounds
      (l4_case now accepts the direction suffixes).
  gf (geometry unchanged vs R7): REUSE mesh, re-deck + re-solve the
      whole set because the COM wrench changes every case.

Usage: python3 run_r8fea.py [mesh|deck|solve|analyze|all] [l4,gf,l5]
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
# part -> (step, layer axis for the print orientation)
#   w_link5: up=h -> z   w_link4: up=b -> y   w_grip_frame: up=h -> z
PARTS = {"l5": ("fix_w_link5", "z"), "l4": ("fix_w_link4", "y"),
         "gf": ("fix_w_grip_frame", "z")}
RTAG = {"l5": "_r8", "l4": "_r8", "gf": "_r8"}
REMESH = ("l4", "l5")                       # gf mesh reused (geometry same)
BCASES = ("face", "ann", "screw", "scpilot", "scrann", "scr2")
PAYS = ("p38", "p25")
CONVERGE_CL = (3.0, 0.8)
DIRS = ("lat", "axp", "axn", "up", "roll", "comb", "comb2", "flop")
L5_NEW = (["l5_scrann_%s" % d for d in DIRS[:1] + ("latf",) + DIRS[1:]]
          + ["l5_screw_up", "l5_screw_lat"]
          + ["l5_scrann_p38_%s" % d for d in ("lat", "roll", "comb")]
          + ["l5_scrann_p25_roll"])
L4_NEW = (["l4_scrann_%s" % d for d in DIRS]
          + ["l4_scrann_p38_%s" % d for d in ("lat", "roll", "comb")]
          + ["l4_scrann_p25_roll"])
GF_NEW = ["gf_scrann_%s" % d for d in ("lat", "roll", "comb", "up")] \
    + ["gf_scrann_p38_lat"]


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
    geo = msh[:-4] + ".geo"
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
    txt = os.path.join(HERE, tag + RTAG[part] + ".txt")
    with open(txt, "w") as fh:
        sh([PY, os.path.join(HERE, "analyze_r3.py"), frd,
            os.path.join(HERE, tag + ".inp"), PARTS[part][1]], stdout=fh)
        sh([PY, os.path.join(HERE, "sigscan_r3.py"), frd,
            os.path.join(HERE, tag + ".inp"), PARTS[part][1]], stdout=fh)
    print(open(txt).read())


def cases(part):
    for bc in BCASES:
        yield part + "_" + bc
    for bc in ("scrann", "scr2"):
        for p in PAYS:
            yield "%s_%s_%s" % (part, bc, p)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    only = sys.argv[2].split(",") if len(sys.argv) > 2 else ("l4", "gf", "l5")
    for part in only:
        step = PARTS[part][0]
        if which in ("mesh", "all"):
            for cl in (CL,) + (CONVERGE_CL if part in REMESH else ()):
                mesh(step, cl)
        if which in ("deck", "all"):
            for case in cases(part):
                deck(part, case)
            if part in REMESH:
                for cl in CONVERGE_CL:
                    deck(part, part + "_scrann", cl)
        if which in ("solve", "all"):
            for case in cases(part):
                solve(part, case)
            if part in REMESH:
                for cl in CONVERGE_CL:
                    solve(part, part + "_scrann", cl)
        elif which == "analyze":
            for case in cases(part):
                analyze(part, case)
            if part in REMESH:
                for cl in CONVERGE_CL:
                    analyze(part, part + "_scrann", cl)
    extra = {"l5": L5_NEW, "l4": L4_NEW, "gf": GF_NEW}
    if which in ("deck", "all"):
        for part in only:
            for case in extra[part]:
                deck(part, case)
    if which in ("solve", "all"):
        for part in only:
            for case in extra[part]:
                solve(part, case)
    if which == "analyze":
        for part in only:
            for case in list(cases(part)) + extra[part]:
                analyze(part, case)
        for part in REMESH:
            if part in only:
                for cl in CONVERGE_CL:
                    analyze(part, part + "_scrann", cl)
    print("done")
