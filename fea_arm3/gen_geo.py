#!/usr/bin/env python3
"""fea_arm3/gen_geo.py - emit the conformal-mesh gmsh script for one case.

All 38 part STEPs are imported, then ONE OpenCASCADE BooleanFragments call
fragments every solid against every other, so touching/interpenetrating
parts share interface faces -> the tet mesh is node-conformal and there is
no *TIE contact anywhere (the F2 failure mode).

Fragment volumes carry plain elementary tags; ownership of each fragment
is recovered AFTER meshing by msh2arm3.py via point-in-solid tests against
the source STL of every part, so no Physical Volumes are needed here.

    python3 gen_geo.py --case AB [--cl 9.0 --clp 4.0]
"""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
INP = HERE / "input"
RUN = HERE / "run"
CASE_DIR = {"AB": INP / "posed_AB", "C": INP / "step_home"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True, choices=sorted(CASE_DIR))
    ap.add_argument("--cl", type=float, default=9.0,
                    help="global max element size, mm (default 9)")
    ap.add_argument("--clp", type=float, default=4.0,
                    help="size inside printed-part bbox fields, mm (0=off)")
    ap.add_argument("--order", type=int, default=1, choices=(1, 2),
                    help="element order: 1=C3D4, 2=C3D10 (default 1)")
    ap.add_argument("--algo3d", type=int, default=1,
                    help="Mesh.Algorithm3D: 1=Delaunay 4=Frontal-Delaunay "
                         "10=HXT (default 1)")
    ap.add_argument("--tolboolean", type=float, default=0.0,
                    help="Geometry.ToleranceBoolean fuzzy mm (0=off)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    mdir = CASE_DIR[a.case]
    steps = sorted(mdir.glob("*.step"))
    assert len(steps) == 38, "expected 38 part STEPs in %s, got %d" % (mdir, len(steps))

    printed_boxes = []
    pj = json.loads((INP / ("parts_%s.json" % a.case)).read_text())
    for name, meta in pj["parts"].items():
        if meta["cls"] == "printed":
            bb = meta["bbox"]
            printed_boxes.append((bb[0], bb[1]))

    L = []
    L.append('SetFactory("OpenCASCADE");')
    L.append("Mesh.MshFileVersion = 2.2;")
    L.append("Mesh.ElementOrder = %d;" % a.order)
    L.append("Mesh.Algorithm3D = %d;" % a.algo3d)
    if a.tolboolean > 0:
        L.append("Geometry.ToleranceBoolean = %g;" % a.tolboolean)
    L.append("")
    for i, s in enumerate(steps, 1):
        L.append('v_%d() = ShapeFromFile("%s");' % (i, s))
    L.append("")
    # one Physical Volume per part: own material + own result row, and the
    # physical tag carries the part name straight into the .msh
    for i, s in enumerate(steps, 1):
        L.append('Physical Volume("p_%s") = v_%d();' % (s.stem, i))
    L.append("")
    if a.clp > 0:
        fids = []
        for k, (lo, hi) in enumerate(printed_boxes, 1):
            fids.append(k)
            L += [
                "Field[%d] = Box;" % k,
                "Field[%d].VIn = %g;" % (k, a.clp),
                "Field[%d].VOut = %g;" % (k, a.cl),
                "Field[%d].XMin = %g;" % (k, lo[0] - 1.0),
                "Field[%d].XMax = %g;" % (k, hi[0] + 1.0),
                "Field[%d].YMin = %g;" % (k, lo[1] - 1.0),
                "Field[%d].YMax = %g;" % (k, hi[1] + 1.0),
                "Field[%d].ZMin = %g;" % (k, lo[2] - 1.0),
                "Field[%d].ZMax = %g;" % (k, hi[2] + 1.0),
                "Field[%d].Thickness = %g;" % (k, 2.0 * a.cl),
            ]
        L += [
            "Field[9000] = Min;",
            "Field[9000].FieldsList = {%s};" % ", ".join(str(k) for k in fids),
            "Background Field = 9000;",
            "",
        ]
    L += [
        "Mesh.CharacteristicLengthMax = %g;" % a.cl,
        "Mesh.CharacteristicLengthMin = 0.8;",
        "Mesh.MinimumElementsPerTwoPi = 8;",
        "Mesh 3;",
        'Save "%s";' % (RUN / ("arm_%s.msh" % a.case)),
        'Printf("GMSH DONE nodes=%g elems=%g", Mesh.NbNodes, '
        'Mesh.NbTetrahedra);',
        "Exit;",
        "",
    ]
    out = Path(a.out) if a.out else HERE / ("arm_%s.geo" % a.case)
    out.write_text("\n".join(L))
    print("WROTE %s (cl=%g clp=%g order=%d algo3d=%d, %d printed fields)"
          % (out, a.cl, a.clp, a.order, a.algo3d,
             len(printed_boxes) if a.clp > 0 else 0))


if __name__ == "__main__":
    main()
