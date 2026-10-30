#!/usr/bin/env python3
"""fea_arm/msh2arm.py - gmsh v2.2 .msh -> CalculiX .inp for the 38-part arm.

Reads a non-conformal per-part C3D10 mesh (one Physical Volume "p_<part>"
per part), glues touching parts with *TIE pairs resolved from contacts.json
patch points, fixes the base_plate bottom face, couples the fingertip
region to a ref node at the TCP via *RIGID BODY, and emits one gravity +
payload *STATIC step per --steps multiplier.  Connectivity contract:
union-find over emitted ties, every part must reach base_plate (SPEC.md).

    python3 msh2arm.py <mesh.msh> <contacts.json> <parts.json> <out.inp>
                       [--patch-tol 5.0] [--steps 1.0,2.0]
"""
import argparse
import json
import math
import sys

import numpy as np


def read_msh(path):
    nodes = {}
    elems = {}          # eid -> (etype, [nids], phys)
    phys_names = {}
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

EDGES = ((0, 1), (1, 2), (0, 2), (0, 3), (1, 3), (2, 3))   # C3D10 midside order

def reorder_tet(nodes, n):
    """Return tet10 connectivity as [c0..c3, m01, m12, m02, m03, m13, m23]
    (CalculiX C3D10 order), positive volume.  Each extra node is assigned to
    the corner edge whose midpoint it is closest to, so no assumption is made
    about the source convention; if the corner orientation is negative, corner
    1<->2 are swapped and the edge map is remapped accordingly."""
    posmap = {0: 0, 1: 1, 2: 2, 3: 3}
    conn = list(n)
    if signed_vol(nodes, conn[:4]) < 0.0:
        conn[1], conn[2] = conn[2], conn[1]
        posmap = {0: 0, 1: 2, 2: 1, 3: 3}      # old corner k sits at pos posmap[k]
    c = [nodes[conn[i]] for i in range(4)]     # coords at new positions 0..3
    # one-to-one assignment: sort every (extra node, edge) pair by distance
    # to the edge midpoint and take the best still-free pairs, so two nodes
    # can never claim the same edge (distorted tets would else leave an
    # edge unassigned -> KeyError).
    extra = list(n[4:])
    pairs = []
    for ni, node_id in enumerate(extra):
        m = nodes[node_id]
        for a in range(4):
            for b in range(a + 1, 4):
                pa, pb = posmap[a], posmap[b]  # old corners a,b now sit at pa,pb
                d = sum((m[i] - (c[pa][i] + c[pb][i]) * 0.5) ** 2 for i in range(3))
                pairs.append((d, ni, (pa, pb)))
    pairs.sort()
    mid = {}
    used_n, used_e = set(), set()
    for _d, ni, e in pairs:
        if ni in used_n or e in used_e:
            continue
        mid[e] = extra[ni]
        used_n.add(ni)
        used_e.add(e)
    for e in EDGES:                     # greedy can leave an edge free on
        if e not in mid:                # distorted tets -> force-assign nearest
            free = [ni for ni in range(len(extra)) if ni not in used_n]
            if not free:
                mid[e] = extra[0]       # degenerate: reuse any node
                continue
            pa, pb = posmap[e[0]], posmap[e[1]]
            mx, my, mz = ((c[pa][i] + c[pb][i]) * 0.5 for i in range(3))
            ni = min(free, key=lambda i: (nodes[extra[i]][0] - mx) ** 2
                     + (nodes[extra[i]][1] - my) ** 2
                     + (nodes[extra[i]][2] - mz) ** 2)
            mid[e] = extra[ni]
            used_n.add(ni)
    return conn[:4] + [mid[e] for e in EDGES]

# ---------------------------------------------------------------------------
# C3D10 faces: conn positions of the 3 corner nodes -> ccx S-label, plus the
# conn positions of that face's 3 midside nodes.
# (S<k> is the face opposite corner k; conn = [c0..c3, m01, m12, m02, m03,
#  m13, m23].)
FACES = (
    ("S1", (0, 1, 2), (4, 5, 6)),   # {c0,c1,c2} + m01 m12 m02
    ("S2", (0, 1, 3), (4, 7, 8)),   # {c0,c1,c3} + m01 m03 m13
    ("S3", (1, 2, 3), (5, 8, 9)),   # {c1,c2,c3} + m12 m13 m23
    ("S4", (0, 2, 3), (6, 7, 9)),   # {c0,c2,c3} + m02 m03 m23
)
FACE_BY_LABEL = {lab: (cp, mp) for lab, cp, mp in FACES}
# C3D4 uses the same corner triples; midsides are absent (len(conn) == 4).


def d2(p, q):
    return (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2


def boundary_faces(part_tets, nodes):
    """part -> [(eid, 'S<k>', corner_triple, face_centroid)].
    A corner triple is a boundary face when it occurs in exactly ONE tet of
    that part (meshes are non-conformal, so no triple is shared across parts)."""
    bfaces = {}
    for part, tets in part_tets.items():
        count, owner = {}, {}
        for eid, conn in tets:
            for lab, cpos, _mp in FACES:
                trip = tuple(sorted(conn[i] for i in cpos))
                count[trip] = count.get(trip, 0) + 1
                owner.setdefault(trip, []).append((eid, lab))
        fl = []
        for trip, lst in owner.items():
            if count[trip] != 1:
                continue
            eid, lab = lst[0]
            cen = tuple(sum(nodes[n][i] for n in trip) / 3.0 for i in range(3))
            fl.append((eid, lab, trip, cen))
        bfaces[part] = fl
    return bfaces


def face_nodes(conn, lab):
    """C3D10: 3 corners + 3 midsides; C3D4: the 3 corners."""
    cpos, mpos = FACE_BY_LABEL[lab]
    if len(conn) == 4:
        return [conn[i] for i in cpos]
    return [conn[i] for i in cpos] + [conn[i] for i in mpos]


def pick_faces(facelist, pts, tol):
    """Boundary faces of one part whose centroid is within tol of any pt."""
    if not facelist or not pts:
        return []
    t2 = tol * tol
    cen = np.array([f[3] for f in facelist])
    sel = np.zeros(len(facelist), dtype=bool)
    for p in pts:
        sel |= ((cen - p) ** 2).sum(1) <= t2
    return [(eid, lab) for f, s in zip(facelist, sel) if s
            for eid, lab in [(f[0], f[1])]]


def _flat(o, acc):
    if isinstance(o, (list, tuple)):
        for v in o:
            _flat(v, acc)
    else:
        try:
            acc.append(float(o))
        except (TypeError, ValueError):
            pass
    return acc


def part_zmin(part, meta, nodes, part_tets):
    """bbox may be [x0,y0,z0,x1,y1,z1] or [[x,y,z],[x,y,z]]; fallback = nodes."""
    bb = _flat(meta.get(part, {}).get("bbox") or [], [])
    if len(bb) >= 6:
        return min(bb[2], bb[5])
    if len(bb) >= 3:
        return bb[2]
    zs = [nodes[conn[i]][2] for _e, conn in part_tets.get(part, []) for i in range(4)]
    return min(zs) if zs else 0.0


def part_centroid(part, meta, nodes, part_tets):
    c = meta.get(part, {}).get("centroid")
    if c:
        return tuple(float(v) for v in c)
    pts = [nodes[conn[i]] for _e, conn in part_tets.get(part, []) for i in range(4)]
    if not pts:
        return (0.0, 0.0, 0.0)
    return tuple(sum(p[i] for p in pts) / len(pts) for i in range(3))


def part_volume(part, part_tets, nodes):
    return sum(abs(signed_vol(nodes, conn)) / 6.0 for _e, conn in part_tets[part])


def is_vendor(part, meta):
    cls = meta.get(part, {}).get("cls")
    if cls:
        return cls == "vendor"
    return part.startswith("vendor_")


class UF(object):
    def __init__(self):
        self.p = {}

    def find(self, x):
        p = self.p
        p.setdefault(x, x)
        r = x
        while p[r] != r:
            r = p[r]
        while p[x] != r:
            p[x], x = r, p[x]
        return r

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def main():
    ap = argparse.ArgumentParser(
        description="gmsh v2.2 .msh -> CalculiX .inp writer for the "
                    "38-part tied-contact arm (see fea_arm/SPEC.md)")
    ap.add_argument("msh")
    ap.add_argument("contacts")
    ap.add_argument("parts")
    ap.add_argument("out")
    ap.add_argument("--patch-tol", type=float, default=5.0,
                    help="face-centroid to patch-point tolerance, mm (default 5.0)")
    ap.add_argument("--steps", default="1.0,2.0",
                    help="comma-separated load multipliers, e.g. 1.0,2.0")
    args = ap.parse_args()
    mults = [float(t) for t in args.steps.split(",") if t.strip()]
    if not mults:
        sys.exit("FATAL: --steps produced no multipliers")

    contacts = json.load(open(args.contacts)).get("contacts", [])
    pj = json.load(open(args.parts))
    meta = pj.get("parts", {})
    tcp = tuple(float(v) for v in pj.get("tcp", (0.0, 0.0, 0.0)))

    # ---- 1. mesh: keep only etype 11, group by physical volume "p_<part>" --
    nodes, elems, phys_names = read_msh(args.msh)
    if not nodes:
        sys.exit("FATAL: no nodes in %s" % args.msh)
    vol_name = {tag: nm for (dim, tag), nm in phys_names.items() if dim == 3}
    part_tets, conn_of, nskip, ndegen = {}, {}, 0, 0
    for eid, (etype, nids, phys) in sorted(elems.items()):
        if etype not in (4, 11):             # C3D4 / C3D10 tets only
            nskip += 1
            continue
        pname = vol_name.get(phys)
        if pname is None:
            pname = "phys%d" % phys
            print("WARN: eid %d volume tag %d has no PhysicalName -> %s"
                  % (eid, phys, pname))
        if pname.startswith("p_"):
            pname = pname[2:]
        if abs(signed_vol(nodes, nids[:4])) < 1e-6:
            ndegen += 1
            continue
        if etype == 11:
            conn = reorder_tet(nodes, nids)
        else:
            conn = list(nids[:4])
            if signed_vol(nodes, conn) < 0.0:
                conn[1], conn[2] = conn[2], conn[1]
        part_tets.setdefault(pname, []).append((eid, conn))
        conn_of[eid] = conn
    ntet = len(conn_of)
    n4 = sum(1 for c in conn_of.values() if len(c) == 4)
    if not ntet:
        sys.exit("FATAL: no tet elements (etype 4/11) in %s" % args.msh)
    etype_out = "C3D4" if n4 == ntet else ("C3D10" if n4 == 0 else "MIXED")
    print("mesh: %d nodes, %d %s tets in %d parts "
          "(%d non-tet skipped, %d degenerate dropped)"
          % (len(nodes), ntet, etype_out, len(part_tets), nskip, ndegen))
    if ndegen:
        print("WARN: %d zero-volume tets dropped" % ndegen)

    # ---- 3. boundary faces -------------------------------------------------
    bfaces = boundary_faces(part_tets, nodes)
    for part in sorted(part_tets):
        print("  %-24s %4d tets, %4d boundary faces"
              % (part, len(part_tets[part]), len(bfaces[part])))

    # ---- 4. ties -----------------------------------------------------------
    uf = UF()
    ties = []                            # (k, a, b, kind, slave_faces, master_faces)
    for c in contacts:
        pa, pb = c.get("a"), c.get("b")
        kind = c.get("kind", "?")
        if pa not in part_tets or pb not in part_tets:
            print("WARN: contact %s<->%s: part missing in mesh, skipped" % (pa, pb))
            continue
        pts = [tuple(float(v) for v in p) for p in (c.get("pts") or [])]
        if pts:
            sel_pts, tol = pts, args.patch_tol
        else:
            ca, cb = (part_centroid(p, meta, nodes, part_tets) for p in (pa, pb))
            mid = tuple((ca[i] + cb[i]) * 0.5 for i in range(3))
            sel_pts, tol = [mid], 5.0
            print("WARN: contact %s<->%s has no pts; fallback = 5 mm band "
                  "around centroid midpoint (%.2f, %.2f, %.2f)"
                  % ((pa, pb) + mid))
        sl = pick_faces(bfaces[pa], sel_pts, tol)
        ms = pick_faces(bfaces[pb], sel_pts, tol)
        if not sl or not ms:
            print("WARN: contact %s<->%s: empty surface (slave=%d master=%d), skipped"
                  % (pa, pb, len(sl), len(ms)))
            continue
        k = len(ties) + 1
        ties.append((k, pa, pb, kind, sl, ms))
        uf.union(pa, pb)

    # tie-slave node set (MPC slaves may not also be SPC / rigid-body nodes)
    slave_nodes = set()
    for _k, _a, _b, _kd, sl, _ms in ties:
        for eid, lab in sl:
            slave_nodes.update(face_nodes(conn_of[eid], lab))
    # tie-gap report: min slave-node -> master-node distance per tie
    # (ccx ties slave nodes within POSITION TOLERANCE of a master face;
    #  if the closest node pair is already > ~2 mm apart nothing will tie)
    for k, pa, pb, kind, sl, ms in ties:
        sn = set()
        mn = set()
        for eid, lab in sl:
            sn.update(face_nodes(conn_of[eid], lab))
        for eid, lab in ms:
            mn.update(face_nodes(conn_of[eid], lab))
        snv = np.array([nodes[i] for i in sn])
        mnv = np.array([nodes[j] for j in mn])
        best = math.inf
        for chunk in np.array_split(snv, max(1, len(snv) // 400)):
            dm = ((chunk[:, None, :] - mnv[None, :, :]) ** 2).sum(2)
            if dm.size:
                best = min(best, float(dm.min()))
        if best > 4.0:
            print("WARN: T%d %s<->%s min node gap %.2f mm > 4.0 -> likely NO tied nodes"
                  % (k, pa, pb, math.sqrt(best)))

    # ---- 5./6. node sets ---------------------------------------------------
    zmin = part_zmin("base_plate", meta, nodes, part_tets)
    nfix = set()
    for eid, lab, _t, cen in bfaces.get("base_plate", []):
        if cen[2] <= zmin + 1.5:
            nfix.update(face_nodes(conn_of[eid], lab))
    if not nfix:
        print("WARN: NFIX empty (no base_plate boundary faces at z <= %.3f)"
              % (zmin + 1.5))
    nload = set()
    for p in ("finger_u", "finger_d"):
        for eid, lab, _t, cen in bfaces.get(p, []):
            if d2(cen, tcp) <= 9.0 ** 2:
                nload.update(face_nodes(conn_of[eid], lab))
    nload -= slave_nodes          # rigid nset must be disjoint from MPC slaves
    if not nload:
        print("WARN: NLOAD empty; payload ref node %d will be unconstrained"
              % (max(nodes) + 1))

    # ---- 7. materials ------------------------------------------------------
    vendor_rho, printed = {}, []
    for part in sorted(part_tets):
        if not is_vendor(part, meta):
            printed.append(part)
            continue
        rho = meta.get(part, {}).get("rho")
        if rho is None:
            m = meta.get(part, {}).get("mass_kg")
            vol = part_volume(part, part_tets, nodes)
            if m and vol > 0.0:
                rho = (m / 1000.0) / vol        # kg -> t ; mm^3 -> t/mm^3
                print("WARN: rho missing for %s; derived %.3e t/mm^3 from mass"
                      % (part, rho))
            else:
                rho = 7.62e-10
                print("WARN: rho missing for %s; defaulting to %.3e" % (part, rho))
        vendor_rho[part] = float(rho)

    # ---- write deck ----------------------------------------------------------
    refid = max(nodes) + 1

    def wr_nset(w, name, ids):
        w("*NSET, NSET=%s\n" % name)
        ids = sorted(ids)
        for i in range(0, len(ids), 8):
            w(", ".join(str(n) for n in ids[i:i + 8]) + "\n")

    with open(args.out, "w") as f:
        w = f.write
        w("*NODE\n")
        for nid, (x, y, z) in sorted(nodes.items()):
            w("%d, %.6f, %.6f, %.6f\n" % (nid, x, y, z))
        w("%d, %.6f, %.6f, %.6f\n" % ((refid,) + tcp))
        for part in sorted(part_tets):
            w("*ELEMENT, TYPE=%s, ELSET=%s\n" % (etype_out, part))
            for eid, conn in part_tets[part]:
                w("%d, %s\n" % (eid, ", ".join(str(n) for n in conn)))
        w("*ELSET, ELSET=EALL\n")
        allids = sorted(conn_of)
        for i in range(0, len(allids), 8):
            w(", ".join(str(e) for e in allids[i:i + 8]) + "\n")
        if nfix:
            wr_nset(w, "NFIX", nfix)
        if nload:
            wr_nset(w, "NLOAD", nload)
        for k, _a, _b, _kd, sl, ms in ties:
            w("*SURFACE, NAME=T%dS, TYPE=ELEMENT\n" % k)
            for eid, lab in sl:
                w("%d, %s\n" % (eid, lab))
            w("*SURFACE, NAME=T%dM, TYPE=ELEMENT\n" % k)
            for eid, lab in ms:
                w("%d, %s\n" % (eid, lab))
            w("*TIE, NAME=T%d, POSITION TOLERANCE=10.0\nT%dS, T%dM\n"
              % (k, k, k))
        if printed:
            w("*MATERIAL, NAME=MATPRINTED\n*ELASTIC\n4000., 0.35\n"
              "*DENSITY\n7.62e-10\n")
        for part in sorted(vendor_rho):
            w("*MATERIAL, NAME=MAT_%s\n*ELASTIC\n70000., 0.33\n"
              "*DENSITY\n%.6e\n" % (part, vendor_rho[part]))
        for part in sorted(part_tets):
            mat = "MAT_%s" % part if part in vendor_rho else "MATPRINTED"
            w("*SOLID SECTION, ELSET=%s, MATERIAL=%s\n" % (part, mat))
        if nload:
            w("*RIGID BODY, NSET=NLOAD, REF NODE=%d\n" % refid)
        if nfix:
            w("*BOUNDARY\nNFIX, 1, 3, 0.\n")
        for m in mults:
            w("*STEP\n*STATIC\n")
            w("*DLOAD\nEALL, GRAV, %.1f, 0., 0., -1.\n" % (9810.0 * m))
            w("*CLOAD\n%d, 3, %.4f\n" % (refid, -4.905 * m))
            w("*NODE FILE\nU, RF\n*EL FILE\nS\n*END STEP\n")

    # ---- 9./10. report -------------------------------------------------------
    print("tie table:")
    for k, pa, pb, kind, sl, ms in ties:
        print("  T%-3d %-24s <-> %-24s %-11s slave=%-4d master=%-4d"
              % (k, pa, pb, kind, len(sl), len(ms)))
    print("NFIX=%d  NLOAD=%d  ref=%d at tcp %s" % (len(nfix), len(nload), refid, tcp))
    base_root = uf.find("base_plate")
    orphans = [p for p in sorted(part_tets) if uf.find(p) != base_root]
    if orphans:
        print("FATAL: orphan parts %s" % orphans)
        sys.exit(1)
    print("ORPHANS: none")
    print("done: %d nodes, %d C3D10 tets in %d parts, %d ties -> %s"
          % (len(nodes), ntet, len(part_tets), len(ties), args.out))


if __name__ == "__main__":
    main()
