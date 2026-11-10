"""refine/fea/run_r9fea.py - R9 verification driver.

R9 = the printed U-yoke second J4 support (msh2_r9.py): the l4 journal
boss rides a d3 dowel pinned in the cradle.  Case plan:

  l4  BC bounds: face/ann/screw/scpilot/scrann/scr2 + scrj (journal,
      full circle) + scrjh (journal, loaded-side semicircle) + scr2j.
      Direction bounds (lat axp axn up roll comb comb2 flop) on BOTH the
      R8 horn-only bound (scrann) and the journal bounds (scrj/scrjh),
      so the journal share is measured per direction.  Payload shares
      p25/p38 on scrann + scrj; p25_roll on all three bounds (the R8
      gate case).
  cr  w_j4_cradle: bolt / face / boltface at p50, boltface payload
      shares + direction set, p25_roll gate.
  l5  R9 geometry: R8 case list re-solved.
  gf  R9 export re-solved (interface unchanged but re-exported).

Usage: python3 run_r9fea.py [mesh|deck|solve|analyze|all] [l4,cr,l5,gf]
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
# part -> (step stem, layer axis for the print orientation)
#   l5 up=h -> z (R8 orientation)   l4/cr up=b -> y   gf up=h -> z
PARTS = {"l5": ("fix_w_link5", "z"), "l4": ("fix_w_link4", "y"),
         "gf": ("fix_w_grip_frame", "z"), "cr": ("fix_w_j4_cradle", "y")}
RTAG = {p: "_r9" for p in PARTS}
CONVERGE_CL = (3.0, 0.8)
DIRS = ("lat", "axp", "axn", "up", "roll", "comb", "comb2", "flop")
BCASES = ("face", "ann", "screw", "scpilot", "scrann", "scr2")
JCASES = ("scrj", "scrjh", "scr2j")


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
    sh([PY, os.path.join(HERE, "msh2_r9.py"), msh,
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
    if part == "cr":
        for bc in ("bolt", "face", "boltface"):
            yield "cr_" + bc
        for p in ("p38", "p25"):
            yield "cr_boltface_" + p
        return
    for bc in BCASES + (JCASES if part == "l4" else ()):
        yield part + "_" + bc
    for bc in (("scrann", "scr2", "scrj", "scrjh")
               if part == "l4" else ("scrann", "scr2")):
        for p in ("p38", "p25"):
            yield "%s_%s_%s" % (part, bc, p)


EXTRA = {
    "l4": (["l4_scrann_%s" % d for d in DIRS]
           + ["l4_scrj_%s" % d for d in DIRS]
           + ["l4_scrjh_%s" % d for d in DIRS]
           + ["l4_scrann_p38_%s" % d for d in ("lat", "roll", "comb")]
           + ["l4_scrj_p38_%s" % d for d in ("lat", "roll", "comb")]
           + ["l4_scrann_p25_roll", "l4_scrj_p25_roll",
              "l4_scrjh_p25_roll", "l4_scr2j_p25_roll"]),
    "cr": (["cr_boltface_%s" % d for d in ("lat", "roll", "comb",
                                           "flop", "up")]
           + ["cr_boltface_p25_roll", "cr_bolt_p25_roll"]),
    "l5": (["l5_scrann_%s" % d for d in DIRS]
           + ["l5_scrann_p38_%s" % d for d in ("lat", "roll", "comb")]
           + ["l5_scrann_p25_roll"]),
    "gf": (["gf_scrann_%s" % d for d in ("lat", "roll", "comb", "up")]
           + ["gf_scrann_p38_lat", "gf_scrann_p25_roll"]),
}


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    only = sys.argv[2].split(",") if len(sys.argv) > 2 else \
        ("l4", "cr", "l5", "gf")
    for part in only:
        step = PARTS[part][0]
        if which in ("mesh", "all"):
            for cl in (CL,) + CONVERGE_CL:
                mesh(step, cl)
        if which in ("deck", "all"):
            for case in cases(part):
                deck(part, case)
            for cl in CONVERGE_CL:
                deck(part, part + ("_scrann" if part != "cr"
                                   else "_boltface"), cl)
        if which in ("solve", "all"):
            for case in cases(part):
                solve(part, case)
            for cl in CONVERGE_CL:
                solve(part, part + ("_scrann" if part != "cr"
                                    else "_boltface"), cl)
        elif which == "analyze":
            for case in cases(part):
                analyze(part, case)
            for cl in CONVERGE_CL:
                analyze(part, part + ("_scrann" if part != "cr"
                                      else "_boltface"), cl)
    if which in ("deck", "all"):
        for part in only:
            for case in EXTRA[part]:
                deck(part, case)
    if which in ("solve", "all"):
        for part in only:
            for case in EXTRA[part]:
                solve(part, case)
    if which == "analyze":
        for part in only:
            for case in list(cases(part)) + EXTRA[part]:
                analyze(part, case)
        for part in only:
            for cl in CONVERGE_CL:
                analyze(part, part + ("_scrann" if part != "cr"
                                      else "_boltface"), cl)
    print("done")
