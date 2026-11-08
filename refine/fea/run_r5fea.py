"""refine/fea/run_r5fea.py - R5/R6 driver: w_link5 orientation fix (up=h ->
layer axis z) + load-direction bounds + re-verification of the trimmed
w_link4 / w_grip_frame.  R6: l5 cage redesign (closed skins, outer-face
longeron/aft rib) -> l5 joins REMESH; direction-matched entry patches and
pose-matched combined cases (_roll/_comb/_comb2/_flop) added in msh2_r3.py.

Case plan:
  l5 (geometry UNCHANGED vs R4 - only the layer axis changes, a->h):
    - all 6 BC frds are still valid -> RE-ANALYZE only, at axis z
      (sigscan over every filtered node: max tensile/compressive
      sigma_n(z), in-layer VM, interlayer tau).
    - NEW direction-bound decks on the nominal mesh:
        l5_scrann_{lat,axp,axn,up}   p50 wrench in +b/+a/-a/+h
        l5_screw_up                inverted pose on screw-only support
        l5_scrann_p38_{lat,axp,up} payload-scaled direction bounds
  l4 (trimmed windows): full re-mesh + re-solve of the R4 case set.
  gf (new cheek window): full re-mesh + re-solve of the R4 case set.

Usage: python3 run_r5fea.py [mesh|deck|solve|analyze|all]
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
# part -> (step, layer axis for the R5 print orientation)
#   w_link5: up=h  -> z     w_link4: up=b -> y     w_grip_frame: up=h -> z
PARTS = {"l5": ("fix_w_link5", "z"), "l4": ("fix_w_link4", "y"),
         "gf": ("fix_w_grip_frame", "z")}
RTAG = {"l5": "_r6", "l4": "_r5", "gf": "_r5"}   # report file suffix per part
# parts whose geometry changed -> new mesh/solve required
REMESH = ("l4", "gf", "l5")
BCASES = ("face", "ann", "screw", "scpilot", "scrann", "scr2")
PAYS = ("p38", "p25")          # extra payloads on the two bound BCs
CONVERGE_CL = (3.0, 0.8)
# R6: l5 load-direction + pose-matched bounds on the redesigned cage
DIR_P50 = ("lat", "latf", "axp", "axn", "up", "roll", "comb", "comb2", "flop")
DIR_P38 = ("lat", "roll", "comb")
L5_NEW = (["l5_scrann_%s" % d for d in DIR_P50]
          + ["l5_screw_up", "l5_screw_lat"]
          + ["l5_scrann_p38_%s" % d for d in DIR_P38]
          + ["l5_scrann_p25_roll"])


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
    txt = os.path.join(HERE, tag + RTAG[part] + ".txt")
    with open(txt, "w") as fh:
        sh([PY, os.path.join(HERE, "analyze_r3.py"), frd,
            os.path.join(HERE, tag + ".inp"), PARTS[part][1],
            os.path.join(HERE, tag)], stdout=fh)
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
    # optional part subset: all/l4/gf/l5
    only = sys.argv[2].split(",") if len(sys.argv) > 2 else ("l4", "gf", "l5")
    for part in only:
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
    # l5: direction-bound decks on the existing mesh
    if which in ("deck", "all"):
        for case in L5_NEW:
            deck("l5", case)
    if which in ("solve", "all"):
        for case in L5_NEW:
            solve("l5", case)
    if which == "analyze":
        # re-analyze the full l5 set (old frds + new direction frds)
        for case in list(cases("l5")) + L5_NEW:
            analyze("l5", case)
        for cl in CONVERGE_CL:
            analyze("l5", "l5_scrann", cl)
    print("done")
