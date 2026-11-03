"""genlinks/fea/gen_geo.py - write a gmsh .geo for one optimized link STL and
run gmsh -> v2.2 .msh (2nd order tets, curvature-adaptive).

Run:  python3 gen_geo.py <part> [cl]       (default cl=2.0)
"""
import os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
GMSH = shutil.which("gmsh") or \
    "/Applications/FreeCAD.app/Contents/Resources/bin/gmsh"

GEO = """// genlinks auto: remesh <part>_gen.stl -> C3D10 tet mesh
Merge "<stl>";
Surface Loop(1) = {1};
Volume(1) = {1};
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


def main(part, cl=2.0, stl=None, tag=None):
    stl = os.path.abspath(stl) if stl else os.path.join(OUT, part + "_gen.stl")
    tag = tag or part
    msh = os.path.join(HERE, tag + ".msh")
    geo = os.path.join(HERE, tag + ".geo")
    with open(geo, "w") as fh:
        fh.write(GEO.replace("<stl>", stl).replace("<msh>", msh)
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
