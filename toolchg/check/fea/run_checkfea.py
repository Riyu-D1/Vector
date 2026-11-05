"""toolchg/check/fea/run_checkfea.py - D11 FEA driver.

Re-run of the D10 CalculiX pipeline on tc_master + tc_plate (product
msh2tc.py decks), plus the four added cases (msh2_extra.py decks).
All outputs land under toolchg/check/fea/ (product dirs untouched).

Run:  python3 run_checkfea.py [all|re-run|extra|<case>]
"""
import os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))          # check/fea
TC = os.path.dirname(os.path.dirname(HERE))                # toolchg/
ROOT = os.path.dirname(TC)                                 # repo root
PROD_FEA = os.path.join(TC, "fea")
PYCAD = "/Users/deepakdiwan/Vector-wt/cradlefix/.venv/bin/python"
PV = "/Users/deepakdiwan/Vector-wt/fea/fea/.venv/bin/python"
CCX = shutil.which("ccx") or \
    "/Applications/FreeCAD.app/Contents/Resources/bin/ccx"

RERUN = ["tc_master", "tc_plate"]              # product decks
EXTRA = {"plate_1catch": ("tc_plate", 1.5),
         "tool_pen": ("tool_pen", 1.5),
         "tool_grip": ("tool_grip", 1.5),
         "tc_rack": ("tc_rack", 2.0)}

def sh(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    r = subprocess.run(cmd, **kw)
    if r.returncode:
        print("FAILED rc=%d" % r.returncode)
        sys.exit(1)
    return r

def export_step(part):
    code = (
        "import sys; sys.path.insert(0, %r)\n"
        "import p_toolchg as PW\n"
        "from build123d import export_step\n"
        "s = getattr(PW, %r)()\n"
        "if len(list(s.solids())) > 1:\n"
        "    s = max(s.solids(), key=lambda x: x.volume)\n"
        "export_step(s, %r)\n"
        "print('vol', s.volume)\n"
        % (TC, part, os.path.join(HERE, part + ".step")))
    sh([PYCAD, "-c", code])

def mesh(part, cl):
    sh([sys.executable, os.path.join(HERE, "gen_geo.py"),
        part, str(cl), os.path.join(HERE, part + ".step"), part])

def solve_analyze(tag):
    inp = os.path.join(HERE, tag + ".inp")
    sh([CCX, "-i", os.path.join(HERE, tag)], cwd=HERE)
    frd = os.path.join(HERE, tag + ".frd")
    if not os.path.exists(frd):
        print("ccx produced no .frd for", tag)
        sys.exit(1)
    sh([sys.executable, os.path.join(PROD_FEA, "analyze_tc.py"),
        frd, inp, os.path.join(HERE, tag)])
    sh([PV, os.path.join(HERE, "view_tc.py"),
        os.path.join(HERE, tag + "_step1.vtu"), tag])

def rerun(part):
    mesh(part, 1.5)
    sh([sys.executable, os.path.join(PROD_FEA, "msh2tc.py"),
        os.path.join(HERE, part + ".msh"),
        os.path.join(HERE, part + ".inp"), part])
    solve_analyze(part)

def extra(case):
    part, cl = EXTRA[case]
    mesh(part, cl)
    inp = os.path.join(HERE, part + ".msh")
    tag = case if part != "tc_plate" else case
    sh([sys.executable, os.path.join(HERE, "msh2_extra.py"),
        os.path.join(HERE, part + ".msh"),
        os.path.join(HERE, tag + ".inp"), case])
    solve_analyze(tag)

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    parts = {p for _, (p, _) in EXTRA.items()} | set(RERUN)
    for p in sorted(parts):
        if not os.path.exists(os.path.join(HERE, p + ".step")):
            export_step(p)
    if which in ("all", "re-run"):
        for p in RERUN:
            rerun(p)
    if which in ("all", "extra"):
        for c in EXTRA:
            extra(c)
    if which in EXTRA:
        extra(which)
    print("fea check done")
