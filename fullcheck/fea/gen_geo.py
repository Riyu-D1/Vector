"""lighten/fea/gen_geo.py - write a gmsh .geo for one plate STEP (preferred:
true BREP curves) or STL and run gmsh -> v2.2 .msh (2nd order C3D10,
curvature-adaptive).  Adapted from genlinks/fea/gen_geo.py: OpenCASCADE
factory added for STEP import; src resolves absolute, cwd-relative or
inside lighten/out.

Run:  python3 gen_geo.py <part> [cl] [src.step|.stl] [tag]
"""
import os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
GMSH = shutil.which("gmsh") or \
    "/Applications/FreeCAD.app/Contents/Resources/bin/gmsh"

GEO = """// lighten auto: mesh <src> -> C3D10 tet mesh
SetFactory("OpenCASCADE");
Merge "<src>";
Mesh.ElementOrder = 2;
Mesh.HighOrderOptimize = 2;
Mesh.CharacteristicLengthMax = <cl>;
Mesh.CharacteristicLengthMin = <clm>;
Mesh.CharacteristicLengthFromCurvature = 1;
Mesh.MinimumElementsPerTwoPi = 14;
Mesh 3;
Mesh.MshFileVersion = 2.2;
Save "<msh>";
Exit;
"""


def main(part, cl=2.0, src=None, tag=None):
    if src is None:
        for ext in (".step", ".stl"):
            cand = os.path.join(OUT, part + ext)
            if os.path.exists(cand):
                src = cand
                break
        assert src, "no .step/.stl for %s in %s" % (part, OUT)
    elif not os.path.isabs(src) and not os.path.exists(src):
        src = os.path.join(OUT, src)
    tag = tag or part
    msh = os.path.join(HERE, tag + ".msh")
    geo = os.path.join(HERE, tag + ".geo")
    with open(geo, "w") as fh:
        fh.write(GEO.replace("<src>", os.path.abspath(src))
                 .replace("<msh>", msh)
                 .replace("<clm>", "%.2f" % (cl / 4)).replace("<cl>", "%.2f" % cl))
    r = subprocess.run([GMSH, geo], capture_output=True, text=True)
    print(r.stdout[-1500:] if len(r.stdout) > 1500 else r.stdout)
    if r.returncode or not os.path.exists(msh):
        print("GMSH FAILED rc=%s\n%s" % (r.returncode, r.stderr[-800:]))
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 2.0,
         sys.argv[3] if len(sys.argv) > 3 else None,
         sys.argv[4] if len(sys.argv) > 4 else None)
