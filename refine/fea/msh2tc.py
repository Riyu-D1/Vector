"""toolchg/fea/msh2tc.py - gmsh v2.2 .msh -> CalculiX deck for the D10
coupling parts.  Same conventions as lighten/fea/msh2gen.py (C3D10
reorder, *RIGID BODY ref node wrench, NFIX/NLOAD nsets, degeneracy drop)
but the BC spec is coordinate-only for the two coupling solids.

Parts (coords = W frame mm: x=a tool dir, y=b, z=h up):

  tc_master  NFIX: plate back face  a <= 63.0
             NLOAD: the three lug -a bearing faces: a in [72.0,72.6],
                    radius from the roll axis in [12.5,17.8]
  tc_plate   NFIX: socket back face a >= 78.3 (bonded to the tool body)
             NLOAD: the three catch +a faces: a in [71.8,72.6],
                    radius in [12.5,18.5]

Load (worst static wrist case, [D]): payload 0.5 kg + tool ~0.09 kg at
the TCP (a=149.4, b=0, h=-17) hanging straight down: F = (0,0,-5.7) N
applied at the TCP through a *RIGID BODY patch - the lug/catch couple
then sees the full 0.44 N.m moment.  Conservative: the bore/spigot
radial support is ignored.

Run:  python3 msh2tc.py <part>.msh <part>.inp <part>
"""
import os, sys, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

F_WRENCH = np.array([0.0, 0.0, -5.7])          # N [D] worst static
B_TCP = np.array([149.4, 0.0, -17.0])          # TCP in W mm
G_DIR = np.array([0.0, 0.0, -1.0])


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
    (x0, y0, z0), (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = \
        (nodes[i] for i in n[:4])
    ax, ay, az = x1 - x0, y1 - y0, z1 - z0
    bx, by, bz = x2 - x0, y2 - y0, z2 - z0
    cx, cy, cz = x3 - x0, y3 - y0, z3 - z0
    return ax * (by * cz - bz * cy) + ay * (bz * cx - bx * cz) + \
        az * (bx * cy - by * cx)


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
                d = sum((m[i] - (c[pa][i] + c[pb][i]) * 0.5) ** 2
                        for i in range(3))
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
                d = sum((m[i] - (c[e[0]][i] + c[e[1]][i]) * 0.5) ** 2
                        for i in range(3))
                if d < best:
                    best, bn = d, node_id
            mid[e] = bn
            used.add(bn)
    return conn[:4] + [mid[e] for e in EDGES]


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


H_AX = -17.0

def rax(p):
    return np.hypot(p[:, 1], p[:, 2] - H_AX)


def bc_spec(name):
    if name == "tc_master":
        return dict(fix=lambda p: p[:, 0] <= 63.0,
                    load=lambda p: (p[:, 0] >= 72.0) & (p[:, 0] <= 72.6)
                    & (rax(p) >= 12.5) & (rax(p) <= 17.8))
    if name == "tc_plate":
        return dict(fix=lambda p: p[:, 0] >= 78.3,
                    load=lambda p: (p[:, 0] >= 71.8) & (p[:, 0] <= 72.6)
                    & (rax(p) >= 12.5) & (rax(p) <= 18.5))
    raise KeyError(name)


def main(msh, inp, part):
    nodes, elems, _ = read_msh(msh)
    assert nodes and elems, "empty mesh"
    S = bc_spec(part)
    F = F_WRENCH
    B = B_TCP
    ids = np.array(sorted(nodes))
    P = np.array([nodes[i] for i in ids])
    fix = ids[S["fix"](P)]
    load = ids[S["load"](P)]
    assert len(fix) and len(load), (part, len(fix), len(load))
    assert not set(fix) & set(load)
    print("  %s: NFIX=%d NLOAD=%d" % (part, len(fix), len(load)))

    tets, nfl, ndrop, ninv = [], 0, 0, 0
    for eid, (etype, nids, phys) in sorted(elems.items()):
        if etype == 11:
            n2 = reorder_tet(nodes, nids)
            if signed_vol(nodes, n2[:4]) < 1e-4:
                ndrop += 1
                continue
            if gauss_min_det(nodes, n2) <= 0.0:
                ninv += 1
                continue
            nfl += n2[:4] != nids[:4]
            tets.append((eid, n2))
    if ndrop:
        print("  dropped %d collapsed tets" % ndrop)
    if ninv:
        print("  dropped %d inverted tets" % ninv)
    used = set(int(n) for _, nn in tets for n in nn)
    ids = np.array(sorted(used))
    fix = np.array([n for n in fix if n in used])
    load = np.array([n for n in load if n in used])
    assert len(fix) and len(load), (part, "patches emptied by tet drop")

    ref = max(ids) + 1
    w = open(inp, "w").write
    w("*NODE\n")
    for nid in ids:
        x, y, z = nodes[nid]
        w("%d, %.6f, %.6f, %.6f\n" % (nid, x, y, z))
    w("%d, %.6f, %.6f, %.6f\n" % (ref, *B))
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
    w("*MATERIAL, NAME=PETGCF\n*ELASTIC\n4000.0, 0.35\n*DENSITY\n7.62e-10\n")
    w("*SOLID SECTION, ELSET=EALL, MATERIAL=PETGCF\n")
    w("*RIGID BODY, NSET=NLOAD, REF NODE=%d\n" % ref)
    w("*BOUNDARY\nNFIX, 1, 3, 0.\n")
    w("*STEP\n*STATIC\n")
    w("*DLOAD\nEALL, GRAV, 9810.0, %.5f, %.5f, %.5f\n" % tuple(G_DIR))
    for k in range(3):
        if abs(F[k]) > 1e-9:
            w("*CLOAD\n%d, %d, %.6f\n" % (ref, k + 1, F[k]))
    w("*NODE FILE\nU, RF\n*EL FILE\nS\n*END STEP\n")
    print("%s: %d nodes %d C3D10 (%d reoriented) NFIX=%d NLOAD=%d"
          % (inp, len(ids), len(tets), nfl, len(fix), len(load)))
    print("  F=%s N at TCP %s" % (np.round(F, 2).tolist(),
                                   np.round(B, 1).tolist()))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
