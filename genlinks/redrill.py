"""genlinks/redrill.py - restore interface holes in a generated STL.

The extract pipeline (voxel contour + Taubin smooth) shrinks bores ~0.4-0.7 mm
in radius and closes sub-voxel through-holes entirely. For each enclosed void
detected inside the keep zones on the SOURCE mesh (report.detect_voids),
subtract a cylinder at the source axis/radius through the result so the
interface comes back exactly. Axis direction = thinnest principal direction of
the keep region (plate normal y for plates; link1 J2 ear normal is y too).

Run:  python3 genlinks/redrill.py <part> [...]
"""
import os, sys, math
import numpy as np
import trimesh
import manifold3d as m3d

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = os.path.join(HERE, "out")
import gen_parts as GP
from report import detect_voids


def cyl_y(cx, cz, r, y0, y1):
    h = y1 - y0
    c = trimesh.creation.cylinder(radius=r, height=h, sections=64)
    c.apply_transform(trimesh.transformations.rotation_matrix(
        math.radians(90), (1, 0, 0)))          # z-axis cyl -> y-axis
    c.apply_translation((cx, (y0 + y1) / 2.0, cz))
    return c


def to_man(m):
    return m3d.Manifold(m3d.Mesh(
        vert_properties=np.asarray(m.vertices, np.float32),
        tri_verts=np.asarray(m.faces, np.uint32)))


def main(part):
    src = trimesh.load_mesh(os.path.join(OUT, part + ".stl"), force="mesh")
    gen = trimesh.load_mesh(os.path.join(OUT, part + "_gen.stl"), force="mesh")
    S = GP.spec(part)
    hs = detect_voids(src, S["keep"])
    hg = detect_voids(gen, S["keep"])
    y0, y1 = src.bounds[0][1] - 2.0, src.bounds[1][1] + 2.0
    gm = to_man(gen)
    drilled = []
    for cx, cz, r in hs:
        dg = [math.hypot(cx - a, cz - b) for a, b, _ in hg]
        ok = dg and min(dg) < 3.0 and abs(hg[int(np.argmin(dg))][2] - r) < 0.3
        if ok:
            continue
        gm = gm - to_man(cyl_y(cx, cz, r + 0.05, y0, y1))
        drilled.append((round(cx, 1), round(cz, 1), round(r, 1)))
    if drilled:
        mm = gm.to_mesh()
        out = trimesh.Trimesh(vertices=np.asarray(mm.vert_properties)[:, :3],
                              faces=np.asarray(mm.tri_verts), process=False)
        out.export(os.path.join(OUT, part + "_gen.stl"))
        print("%s: re-drilled %d holes %s -> vol %.1f mm3 watertight %s"
              % (part, len(drilled), drilled, out.volume, out.is_watertight))
    else:
        print("%s: all %d holes preserved, no re-drill" % (part, len(hs)))


if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
