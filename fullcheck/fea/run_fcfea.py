"""fullcheck/fea/run_fcfea.py - per-part bolted/pinned SF2 pipeline:
STEP -> gmsh C3D10 (two densities) -> fc_deck deck -> ccx -> fc_analyze.

  python3 run_fcfea.py <part> [cl] [finecl]
default cl=2.0 fine=1.0.  Results <part>[_f].{msh,inp,frd,log} in
fullcheck/fea/.
"""
import os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CCX = shutil.which("ccx") or \
    "/Applications/FreeCAD.app/Contents/Resources/bin/ccx"

DIRS = [os.path.join(ROOT, "cad", "arm2b", "out"),
        os.path.join(ROOT, "cad3", "out"),
        os.path.join(ROOT, "cyclo4", "out")]
# print-bed normal in the mesh frame (z=up flat, y=side plates)
NORMAL = {"base_plate": "0,0,1", "base_link": "0,0,1", "j1_cradle": "0,0,1",
          "base_reinf": "0,0,1", "yaw_limit": "0,0,1", "link1": "0,1,0",
          "upper_out": "0,1,0", "upper_back": "0,1,0",
          "dogleg_l": "0,1,0", "dogleg_r": "0,1,0",
          "fore_l2": "0,1,0", "fore_r2": "0,1,0", "j4_cradle": "0,0,1",
          "flange_j2": "0,1,0", "flange_j3": "0,1,0",
          "front_spacer_j2": "0,1,0", "back_spacer_j2": "0,1,0",
          "front_spacer_j3": "0,1,0", "back_spacer_j3": "0,1,0",
          "cy2_housing": "0,0,1", "cy3_housing": "0,0,1",
          "cy2_carrier": "0,0,1", "cy3_carrier": "0,0,1",
          "cy2_out_flange": "0,0,1", "cy3_out_flange": "0,0,1"}
ALIAS = {"cy2_housing": "housing", "cy3_housing": "housing",
         "cy2_carrier": "carrier", "cy3_carrier": "carrier",
         "cy2_out_flange": "out_flange", "cy3_out_flange": "out_flange"}

def step_of(part):
    base = ALIAS.get(part, part)
    for d in DIRS:
        p = os.path.join(d, base + ".step")
        if os.path.exists(p):
            return p
    p = os.path.join(DIRS[0], base + ".stl")
    assert os.path.exists(p), part
    return p

def solid_step(part, src):
    """Re-export as a bare MANIFOLD_SOLID_BREP: several arm2b STEPs wrap the
    solid in compounds that gmsh imports shell-only (no 3D elements)."""
    if src.lower().endswith(".stl"):
        return src
    out = os.path.join(HERE, "step_norm", part + ".step")
    if os.path.exists(out) and os.path.getmtime(out) > os.path.getmtime(src):
        return out
    os.makedirs(os.path.dirname(out), exist_ok=True)
    venv = "/Users/deepakdiwan/Vector-wt/cradlefix/.venv/bin/python"
    code = ("from build123d import import_step, export_step; "
            "s = import_step(%r); "
            "export_step(s.solids()[0], %r)" % (src, out))
    r = subprocess.run([venv, "-c", code], capture_output=True, text=True)
    if r.returncode or not os.path.exists(out):
        print("solid_step failed:", r.stderr[-400:]); sys.exit(1)
    return out

def sh(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    r = subprocess.run(cmd, **kw)
    if r.returncode:
        print("FAILED rc=%d" % r.returncode); sys.exit(1)
    return r

def one(part, cl, tag):
    src = solid_step(part, step_of(part))
    sh([sys.executable, os.path.join(HERE, "gen_geo.py"),
        tag, str(cl), src, tag])
    sh([sys.executable, os.path.join(HERE, "fc_deck.py"),
        os.path.join(HERE, tag + ".msh"),
        os.path.join(HERE, tag + ".inp"), part])
    sh([CCX, "-i", os.path.join(HERE, tag)], cwd=HERE)
    frd = os.path.join(HERE, tag + ".frd")
    if not os.path.exists(frd):
        print("ccx produced no .frd"); sys.exit(1)
    sh([sys.executable, os.path.join(HERE, "fc_analyze.py"),
        frd, os.path.join(HERE, tag + ".inp"), NORMAL[part]])

if __name__ == "__main__":
    part = sys.argv[1]
    cl = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    fine = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    print("==== %s @cl=%.1f ====" % (part, cl))
    one(part, cl, part)
    if fine > 0:
        print("==== %s @cl=%.1f (convergence mesh) ====" % (part, fine))
        one(part, fine, part + "_f")
