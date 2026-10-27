"""cad/knuckle/gate.py - pass/fail checks used by every stage gate.
Copied verbatim from ~/Vector/stages/code/gate.py. Do not edit.
Usage (from cad/knuckle):  python gate.py out/a.stl out/b.stl ...
Prints one line per STL, then one line per interfering pair, then
GATE PASS or GATE FAIL.  Add --pairs-only-with=<stem> to test only pairs
that include that part.  Add --allow=a:b (repeatable) to skip one more pair;
every use of --allow must be written in docs/STATUS-knuckle.md with why."""
import itertools
import sys

import manifold3d as m3d
import numpy as np
import trimesh

MAX_DIM = 240.0     # Bambu A1 rule from the brief
MIN_WALL = 1.6
WALL_PCT = 2.0      # percentile of inward ray hits that must be >= MIN_WALL
INTERF_MAX = 0.5    # mm^3
# press-fit pairs (plug is PRESS=0.05 bigger on purpose): these may overlap
# up to PRESS_MAX mm^3 (the press band), more = a real collision
PRESS_PAIRS = {("turret", "kn_endcap"), ("forearm", "fa_endcap"),
               ("forearm", "fa_elbow_cap"), ("head", "cup_cap"),
               ("jaw", "jaw_cap")}
PRESS_MAX = 40.0


def load(path):
    m = trimesh.load_mesh(path, force="mesh")
    m.merge_vertices()
    return m


def min_wall(m, n=3000, seed=1):
    pts, fi = trimesh.sample.sample_surface(m, n, seed=seed)
    nrm = m.face_normals[fi]
    origins = pts - nrm * 0.01
    locs, ray_i, _ = m.ray.intersects_location(origins, -nrm, multiple_hits=False)
    if len(ray_i) == 0:
        return 0.0
    d = np.linalg.norm(locs - origins[ray_i], axis=1)
    return float(np.percentile(d, WALL_PCT))


def _raw_manifold(m):
    mesh = m3d.Mesh(vert_properties=np.asarray(m.vertices, dtype=np.float32),
                    tri_verts=np.asarray(m.faces, dtype=np.uint32))
    return m3d.Manifold(mesh)


def solid_meshes(m):
    """Watertight pieces of a mesh. Vendor STEP meshes are not manifold:
    each connected piece is used as-is if manifold, else its convex hull.
    Pieces under 1 mm are dropped (screws/text)."""
    if _raw_manifold(m).status().name == "NoError":
        return [m]
    out = []
    for c in m.split(only_watertight=False):
        if max(c.extents) < 1.0:
            continue
        if _raw_manifold(c).status().name == "NoError":
            out.append(c)
        else:
            h = c.convex_hull
            if h.volume > 1e-3:
                out.append(h)
    return out


def to_manifold(m):
    pieces = [_raw_manifold(c) for c in solid_meshes(m)]
    pieces = [p for p in pieces if p.status().name == "NoError"]
    if not pieces:
        raise ValueError("no manifold piece")
    return m3d.Manifold.batch_boolean(pieces, m3d.OpType.Add) if len(pieces) > 1 else pieces[0]


VENDOR_DEPTH_MAX = 0.3   # mm a vendor surface may sit inside a printed part


def vendor_depth(part, vendor, n=20000):
    """Vendor STEP meshes are not closed, so instead of a volume we sample the
    vendor's real surface and find samples that sit deeper than
    VENDOR_DEPTH_MAX inside the (closed) printed part: a sample is "deep" if it
    and its 6 neighbours shifted +-VENDOR_DEPTH_MAX along X, Y, Z are all inside.
    Returns (VENDOR_DEPTH_MAX or 0.0, number_of_deep_samples)."""
    lo = np.maximum(part.bounds[0], vendor.bounds[0]) - 0.01
    hi = np.minimum(part.bounds[1], vendor.bounds[1]) + 0.01
    pts, _ = trimesh.sample.sample_surface(vendor, n, seed=2)
    pts = np.vstack([pts, vendor.vertices])
    pts = pts[np.all((pts >= lo) & (pts <= hi), axis=1)]
    if len(pts) == 0:
        return 0.0, 0
    pts = pts[part.contains(pts)]
    for ax in range(3):
        for sgn in (-1.0, 1.0):
            if len(pts) == 0:
                return 0.0, 0
            q = pts.copy()
            q[:, ax] += sgn * VENDOR_DEPTH_MAX
            pts = pts[part.contains(q)]
    return (VENDOR_DEPTH_MAX if len(pts) else 0.0), int(len(pts))


def overlap(a, b):
    v = (to_manifold(a) ^ to_manifold(b)).volume()
    return float(v)


def main(argv):
    only = None
    paths = []
    allow = set()
    for a in argv:
        if a.startswith("--pairs-only-with="):
            only = a.split("=", 1)[1]
        elif a.startswith("--allow="):
            allow.add(tuple(a.split("=", 1)[1].split(":", 1)))
        else:
            paths.append(a)
    ok = True
    meshes = {}
    for p in paths:
        m = load(p)
        stem = p.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        meshes[stem] = m
        ext = m.bounds[1] - m.bounds[0]
        is_vendor = stem.startswith("vendor_")
        wt = bool(m.is_watertight)
        mw = 99.0 if is_vendor else min_wall(m)
        big = float(max(ext))
        good = (wt or is_vendor) and (is_vendor or (big <= MAX_DIM and mw >= MIN_WALL))
        ok &= good
        print(f"{stem}: watertight={wt} bbox={ext[0]:.1f}x{ext[1]:.1f}x{ext[2]:.1f} "
              f"max={big:.1f} minwall={mw:.2f} {'OK' if good else 'BAD'}")
    for (na, a), (nb, b) in itertools.combinations(meshes.items(), 2):
        if only and only not in (na, nb):
            continue
        if na.startswith("vendor_") and nb.startswith("vendor_"):
            continue
        if (na, nb) in allow or (nb, na) in allow:
            continue
        lo = np.maximum(a.bounds[0], b.bounds[0])
        hi = np.minimum(a.bounds[1], b.bounds[1])
        if np.any(lo >= hi):
            continue
        if na.startswith("vendor_") or nb.startswith("vendor_"):
            part, ven = (b, a) if na.startswith("vendor_") else (a, b)
            try:
                dmax, nbad = vendor_depth(part, ven)
            except Exception as e:
                print(f"INTERF {na} x {nb}: ERROR {e}")
                ok = False
                continue
            if nbad:
                ok = False
                print(f"INTERF {na} x {nb}: {nbad} vendor surface pts > {dmax:.1f} mm inside part BAD")
            continue
        try:
            v = overlap(a, b)
        except Exception as e:  # never silently pass
            print(f"INTERF {na} x {nb}: ERROR {e}")
            ok = False
            continue
        limit = PRESS_MAX if ((na, nb) in PRESS_PAIRS or (nb, na) in PRESS_PAIRS) else INTERF_MAX
        if v > limit:
            ok = False
            print(f"INTERF {na} x {nb}: {v:.2f} mm3 BAD")
        elif v > INTERF_MAX:
            print(f"PRESS {na} x {nb}: {v:.2f} mm3 ok (press fit)")
    print("GATE PASS" if ok else "GATE FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
