"""refine/fea/run_refinefea.py - refinement FEA driver.

Re-exports stock vs R-fixed geometry, meshes (gmsh C3D10), builds decks
(msh2_extra.py cases), solves (ccx), analyses (analyze_tc.py), renders
(view_tc.py).  All outputs land in refine/fea/.

Cases:
  stock_tool_grip / fix_tool_grip     - D11 'tool_grip' case verbatim:
      NFIX catch faces + socket floor; NLOAD a>=120; F=(0,0,-5.7) N at
      tool-grip TCP (149.4,0,-17).  Directly comparable to the F9 result.
  stock_w_grip_frame / fix_w_grip_frame - new 'grip_frame' case:
      NFIX a<=63 (J6 horn plate face; screwed-flange approximated as
      full-face fixity [U]); NLOAD a>=120; same wrench at gripper TCP
      (137.4,0,-17).

Run:  python3 run_refinefea.py [export|mesh|deck|solve|all]
"""
import os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))          # refine/fea
RDIR = os.path.dirname(HERE)                               # refine/
ROOT = os.path.dirname(RDIR)                               # repo root
OUT = os.path.join(RDIR, "out")
PYCAD = "/Users/deepakdiwan/Vector-wt/cradlefix/.venv/bin/python"
PV = "/Users/deepakdiwan/Vector-wt/fea/fea/.venv/bin/python"
CCX = shutil.which("ccx") or \
    "/Applications/FreeCAD.app/Contents/Resources/bin/ccx"

# step name -> (module path setup, callable) ; case name -> (step, case)
EXPORT_CODE = (
    "import sys, os\n"
    "for d in (%r, %r, %r, %r, %r):\n"
    "    sys.path.insert(0, d)\n"
    "import p_wrist6 as W6, p_wrist7 as W7\n"
    "import p_toolchg as T6, p_toolchg7 as T7\n"
    "from build123d import export_step\n"
    "parts = {\n"
    " 'stock_w_grip_frame': W6.w_grip_frame,\n"
    " 'stock_w_link5': W6.w_link5,\n"
    " 'stock_w_link4': W6.w_link4,\n"
    " 'stock_tool_grip': T6.tool_grip,\n"
    " 'fix_w_grip_frame': W7.w_grip_frame,\n"
    " 'fix_w_link5': W7.w_link5,\n"
    " 'fix_w_link4': W7.w_link4,\n"
    " 'fix_tool_grip': T7.tool_grip_r,\n"
    "}\n"
    "for name, fn in parts.items():\n"
    "    s = fn()\n"
    "    ns = len(list(s.solids()))\n"
    "    export_step(s, %r + '/' + name + '.step')\n"
    "    print('%%-20s solids=%%d vol=%%.2f cm3' %% (name, ns, s.volume/1000))\n"
    % (RDIR, os.path.join(ROOT, "cradlefix"), os.path.join(ROOT, "toolchg"),
       os.path.join(ROOT, "cad", "arm2b"), os.path.join(ROOT, "cad", "arm2"), OUT))

DECKS = {"stock_tool_grip": ("stock_tool_grip", "tool_grip"),
         "fix_tool_grip": ("fix_tool_grip", "tool_grip"),
         "stock_w_grip_frame": ("stock_w_grip_frame", "grip_frame"),
         "fix_w_grip_frame": ("fix_w_grip_frame", "grip_frame")}
CL = 1.5

def sh(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    r = subprocess.run(cmd, **kw)
    if r.returncode:
        print("FAILED rc=%d" % r.returncode)
        sys.exit(1)
    return r

def export():
    sh([PYCAD, "-c", EXPORT_CODE])

def mesh(step):
    sh([sys.executable, os.path.join(HERE, "gen_geo.py"), step, str(CL),
        os.path.join(OUT, step + ".step"), step])

def deck(tag, step, case):
    sh([sys.executable, os.path.join(HERE, "msh2_extra.py"),
        os.path.join(HERE, step + ".msh"),
        os.path.join(HERE, tag + ".inp"), case])

def solve(tag):
    sh([CCX, "-i", os.path.join(HERE, tag)], cwd=HERE)
    frd = os.path.join(HERE, tag + ".frd")
    if not os.path.exists(frd):
        print("ccx produced no .frd for", tag)
        sys.exit(1)
    sh([sys.executable, os.path.join(HERE, "analyze_tc.py"),
        frd, os.path.join(HERE, tag + ".inp"), os.path.join(HERE, tag)])
    if os.path.exists(os.path.join(HERE, "view_tc.py")):
        sh([PV, os.path.join(HERE, "view_tc.py"),
            os.path.join(HERE, tag + "_step1.vtu"), tag])

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("export", "all"):
        export()
    if which in ("mesh", "all"):
        for step in DECKS:
            mesh(step)
    if which in ("deck", "all"):
        for tag, (step, case) in DECKS.items():
            deck(tag, step, case)
    if which in ("solve", "all"):
        for tag in DECKS:
            solve(tag)
    print("done")
