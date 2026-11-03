"""lighten/fea/msh2gen.py - gmsh v2.2 .msh of a plate STEP/STL -> CalculiX
deck. Verbatim from genlinks/fea/msh2gen.py (same conventions as
cad3/fea/msh2housing.py: C3D10 reorder, *RIGID BODY ref node for the
wrench, NFIX/NLOAD patch nsets, patch nodes excluded from stress ranking
in analyze_gen.py) with three D9 deltas:

  1. bc_spec() accepts the variant suffixes _l/_lp/_l2 (upper plates only)
  2. main() takes an optional explicit STL for the lump containment test
     (variants keep the <tag>.stl name, not <part>.stl)
  3. NEW degeneracy check: drops C3D10 whose quadratic Jacobian is
     nonpositive at ccx's 4 Gauss points (the D9 failure mode - knife-edge
     tets on the curved collar edges pass the parent-volume check but
     invert at the integration points; reported, never silently kept).

BC nodes picked by COORDINATE predicates (genlinks spec). The (F, M)
wrench goes in as a pure force F at a ref node offset r = F x M / |F|^2
from B. Hardware lumps -> NLUMP nearest-node *CLOADs.

Run:  python3 msh2gen.py <part>.msh <part>.inp <part> [src.stl]
"""
import os, sys, json, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.dirname(HERE)
sys.path.insert(0, GEN)
OUT = os.path.join(GEN, "out")
LOADS = json.load(open(os.path.join(OUT, "loads.json")))

J1 = np.array([0.0, 0.0, 80.8]); J2 = np.array([-20.0, 0.0, 143.5])
J3 = np.array([-20.0, 0.0, 270.2]); J4 = np.array([96.4, 0.0, 216.2])


def read_msh(path):
    nodes, elems, phys_names = {}, {}, {}
    with open(path) as f:
        lines = [l.strip() for l in f]
    i = 0
    while i < len(lines):
        l = lines[i]
        if l == "$PhysicalNames":
            n = int(lines[i + 1]); i += 2
            for k in range(n):
                dim, tag, name = lines[i].split(None, 2)
                phys_names[(int(dim), int(tag))] = name.strip('"')
                i += 1
        elif l == "$Nodes":
            n = int(lines[i + 1]); i += 2
            for k in range(n):
                p = lines[i].split()
                nodes[int(p[0])] = (float(p[1]), float(p[2]), float(p[3]))
                i += 1
        elif l == "$Elements":
            n = int(lines[i + 1]); i += 2
            for k in range(n):
                p = lines[i].split()
                eid, etype, ntags = int(p[0]), int(p[1]), int(p[2])
                tags = [int(t) for t in p[3:3 + ntags]]
                nids = [int(t) for t in p[3 + ntags:]]
                elems[eid] = (etype, nids, tags[0] if tags else 0)
                i += 1
        else:
            i += 1
    return nodes, elems, phys_names


def signed_vol(nodes, n):
    (x0, y0, z0), (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = (nodes[i] for i in n[:4])
    ax, ay, az = x1 - x0, y1 - y0, z1 - z0
    bx, by, bz = x2 - x0, y2 - y0, z2 - z0
    cx, cy, cz = x3 - x0, y3 - y0, z3 - z0
    return ax * (by * cz - bz * cy) + ay * (bz * cx - bx * cz) + az * (bx * cy - by * cx)


EDGES = ((0, 1), (1, 2), (0, 2), (0, 3), (1, 3), (2, 3))


def reorder_tet(nodes, n):
    posmap = {0: 0, 1: 1, 2: 2, 3: 3}
    conn = list(n)
    if signed_vol(nodes, conn[:4]) < 0.0:
        conn[1], conn[2] = conn[2], conn[1]
        posmap = {0: 0, 1: 2, 2: 1, 3: 3}
    c = [nodes[conn[i]] for i in range(4)]
    mid = {}
    for node_id in n[4:]:
        m = nodes[node_id]
        best, bk = 1e30, None
        for a in range(4):
            for b in range(a + 1, 4):
                pa, pb = posmap[a], posmap[b]
                d = sum((m[i] - (c[pa][i] + c[pb][i]) * 0.5) ** 2 for i in range(3))
                if d < best:
                    best, bk = d, (pa, pb)
        mid[bk] = node_id
    used = set(mid.values())
    for e in EDGES:
        if e not in mid:
            best, bn = 1e30, None
            for node_id in n[4:]:
                if node_id in used:
                    continue
                m = nodes[node_id]
                d = sum((m[i] - (c[e[0]][i] + c[e[1]][i]) * 0.5) ** 2 for i in range(3))
                if d < best:
                    best, bn = d, node_id
            mid[e] = bn
            used.add(bn)
    return conn[:4] + [mid[e] for e in EDGES]


# Jacobian of the quadratic tet at ccx's 4 Gauss points - catches inverted
# C3D10 that parent-volume checks miss (D9 lesson: knife-edge tets on
# curved collar edges invert despite positive corner volume).
def _dN(xi):
    x, y, z = xi
    L = [1 - x - y - z, x, y, z]
    dL = [[-1, -1, -1], [1, 0, 0], [0, 1, 0], [0, 0, 1]]
    out = [[(4 * L[i] - 1) * dL[i][j] for j in range(3)] for i in range(4)]
    for a, b in [(0, 1), (1, 2), (0, 2), (0, 3), (1, 3), (2, 3)]:
        out.append([4 * (L[a] * dL[b][j] + L[b] * dL[a][j])
                    for j in range(3)])
    return np.array(out)


_A, _B = 0.58541020, 0.13819660
_GAUSS = [(g[1], g[2], g[3])
          for g in ((_A, _B, _B, _B), (_B, _A, _B, _B),
                    (_B, _B, _A, _B), (_B, _B, _B, _A))]


def gauss_min_det(nodes, n):
    pts = np.array([nodes[i] for i in n])
    return min(float(np.linalg.det(_dN(g).T @ pts)) for g in _GAUSS)


def rxz(p, j):
    return np.hypot(p[:, 0] - j[0], p[:, 2] - j[2])


def rxy(p, j):
    return np.hypot(p[:, 0] - j[0], p[:, 1] - j[1])


# BC predicates on the RESULT mesh - same geometry zones as genlinks spec.
def bc_spec(name):
    for suf in ("_lp", "_l2", "_l"):
        if name.endswith(suf) and \
                name[:-len(suf)] in ("upper_out", "upper_back"):
            name = name[:-len(suf)]
            break
    if name in ("upper_out", "upper_back"):
        return dict(link="upper_plate",
                    fix=lambda p: rxz(p, J2) < 31.5,
                    load=lambda p: rxz(p, J3) < 31.5, B=J3)
    if name in ("fore_l2", "fore_r2"):
        return dict(link="fore_plate",
                    fix=lambda p: p[:, 0] < 30.0,
                    load=lambda p: rxz(p, J4) < 40.0, B=J4)
    if name == "link1":
        return dict(link="link1",
                    fix=lambda p: (rxy(p, J1) < 15) & (p[:, 2] < 91),
                    load=lambda p: (rxz(p, J2) < 30) & (p[:, 1] < -15), B=J2)
    raise KeyError(name)


def main(msh, inp, part, stl=None):
    nodes, elems, _ = read_msh(msh)
    assert nodes and elems, "empty mesh"
    S = bc_spec(part)
    ld = LOADS["links"][S["link"]]
    F = np.asarray(ld["F"], float)
    M = np.asarray(ld["M"], float)
    B = np.asarray(ld["B"], float)
    g = np.asarray(ld["g"], float) / math.sqrt(sum(v * v for v in ld["g"]))
    ids = np.array(sorted(nodes))
    P = np.array([nodes[i] for i in ids])
    imap = dict(zip(ids, range(len(ids))))
    fix = ids[S["fix"](P)]
    load = ids[S["load"](P)]
    assert len(fix) and len(load), (part, len(fix), len(load))
    assert not set(fix) & set(load)
    # hardware lumps -> nearest surface-ish nodes (all nodes here are fine;
    # stress under them is excluded via NLUMP in analyze_gen.py)
    lump_pairs = []            # (nid, [Fx,Fy,Fz])
    import trimesh
    src = trimesh.load_mesh(stl or os.path.join(OUT, part + ".stl"),
                          force="mesh")
    tree_pts = P
    from scipy.spatial import cKDTree
    tr = cKDTree(tree_pts)
    for mass, ch, fv in ld["lumps"]:
        if src.contains([ch])[0]:
            continue
        _, ii = tr.query(np.asarray(ch), k=6)
        for k in ii:
            lump_pairs.append((int(ids[k]), np.asarray(fv, float) / 6.0))
    # wrench -> pure force at ref node offset r = F x M / |F|^2 from B
    r = np.cross(F, M) / float(F @ F)
    resid = M - np.cross(r, F)
    print("  wrench->offset residual |dM| = %.3f N.mm (|M|=%.0f)"
          % (float(np.linalg.norm(resid)), float(np.linalg.norm(M))))
    ref = max(ids) + 1
    rp = B + r

    # CCX midside order EDGES = 01,12,02,03,13,23 -> n2[4..9]
    tets, nfl, ndrop, ninv = [], 0, 0, 0
    for eid, (etype, nids, phys) in sorted(elems.items()):
        if etype == 11:
            n2 = reorder_tet(nodes, nids)
            # gmsh puts midnodes at exact edge midpoints, so corner
            # sub-tets are always V/8 and can't flag degeneracy; a
            # collapsed parent volume (ccx "nonpositive jacobian") is
            # the real failure mode on knife edges
            if signed_vol(nodes, n2[:4]) < 1e-4:
                ndrop += 1
                continue
            if gauss_min_det(nodes, n2) <= 0.0:
                ninv += 1
                continue
            nfl += n2[:4] != nids[:4]
            tets.append((eid, n2))
    if ndrop:
        print("  dropped %d collapsed tets (corner vol < 1e-4 mm3)" % ndrop)
    if ninv:
        print("  dropped %d inverted tets (nonpositive Gauss Jacobian)" % ninv)
    used = set(int(n) for _, nn in tets for n in nn)
    ids = np.array(sorted(used))
    fix = np.array([n for n in fix if n in used])
    load = np.array([n for n in load if n in used])
    lump_pairs = [(n, f) for n, f in lump_pairs if n in used]
    assert len(fix) and len(load), (part, "patches emptied by tet drop")
    w = open(inp, "w").write
    w("*NODE\n")
    for nid in ids:
        x, y, z = nodes[nid]
        w("%d, %.6f, %.6f, %.6f\n" % (nid, x, y, z))
    w("%d, %.6f, %.6f, %.6f\n" % (ref, *rp))
    w("*ELEMENT, TYPE=C3D10, ELSET=EALL\n")
    for eid, nids in tets:
        w("%d, %s\n" % (eid, ", ".join(str(n) for n in nids)))

    def wr_nset(nm, ns):
        w("*NSET, NSET=%s\n" % nm)
        ns = sorted(ns)
        for i in range(0, len(ns), 8):
            w(", ".join(str(n) for n in ns[i:i + 8]) + "\n")
    wr_nset("NFIX", fix)
    wr_nset("NLOAD", load)
    wr_nset("NLUMP", [n for n, _ in lump_pairs])
    w("*MATERIAL, NAME=PETGCF\n*ELASTIC\n4000.0, 0.35\n*DENSITY\n7.62e-10\n")
    w("*SOLID SECTION, ELSET=EALL, MATERIAL=PETGCF\n")
    w("*RIGID BODY, NSET=NLOAD, REF NODE=%d\n" % ref)
    w("*BOUNDARY\nNFIX, 1, 3, 0.\n")
    w("*STEP\n*STATIC\n")
    w("*DLOAD\nEALL, GRAV, 9810.0, %.5f, %.5f, %.5f\n" % tuple(g))
    for k in range(3):
        if abs(F[k]) > 1e-9:
            w("*CLOAD\n%d, %d, %.6f\n" % (ref, k + 1, F[k]))
    for nid, fv in lump_pairs:
        for k in range(3):
            if abs(fv[k]) > 1e-9:
                w("*CLOAD\n%d, %d, %.6f\n" % (nid, k + 1, fv[k]))
    w("*NODE FILE\nU, RF\n*EL FILE\nS\n*END STEP\n")
    print("%s: %d nodes %d C3D10 (%d reoriented) NFIX=%d NLOAD=%d NLUMP=%d"
          % (inp, len(ids), len(tets), nfl, len(fix), len(load),
             len(set(n for n, _ in lump_pairs))))
    print("  F=%s N  |r|=%.1f mm  ref=%s  g_dir=%s"
          % (np.round(F, 2).tolist(), float(np.linalg.norm(r)),
             np.round(rp, 1).tolist(), np.round(g, 3).tolist()))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3],
         sys.argv[4] if len(sys.argv) > 4 else None)
