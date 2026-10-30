#!/usr/bin/env python3
"""fea_arm3/msh2arm3.py - conformal gmsh v2.2 .msh -> CalculiX .inp.

The .msh comes from ONE BooleanFragments model of all 38 posed parts
(gen_geo.py), so touching parts already share nodes on their interface
faces: there is NO *TIE anywhere.  Each tet carries the elementary tag of
its fragment volume; the owning PART of every fragment is recovered by a
point-in-solid test on the case's source STLs (posed_<case>/<part>.stl),
which is what assigns each part its own ELSET / material / report row.

Connectivity: a corner-triangle appearing in tets of two different parts
is a fused interface -> union-find.  Any island that remains disconnected
(clearance gaps where parts do not actually touch) is glued to its
contact partner with a *RIGID BODY spider at the interface patch named by
contacts_<case>.json -- the stage-sanctioned *RIGID BODY glue.

    python3 msh2arm3.py <mesh.msh> <contacts.json> <parts.json> <stl_dir>
                        <out.inp> [--steps 1.0,2.0] [--link-d 8.0]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import trimesh


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
                # tags[0] = physical tag (-> $PhysicalNames "p_<part>")
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
    """tet10 -> [c0..c3, m01, m12, m02, m03, m13, m23] (ccx C3D10), +vol."""
    posmap = {0: 0, 1: 1, 2: 2, 3: 3}
    conn = list(n)
    if signed_vol(nodes, conn[:4]) < 0.0:
        conn[1], conn[2] = conn[2], conn[1]
        posmap = {0: 0, 1: 2, 2: 1, 3: 3}
    c = [nodes[conn[i]] for i in range(4)]
    extra = list(n[4:])
    pairs = []
    for ni, node_id in enumerate(extra):
        m = nodes[node_id]
        for a in range(4):
            for b in range(a + 1, 4):
                pa, pb = posmap[a], posmap[b]
                d = sum((m[i] - (c[pa][i] + c[pb][i]) * 0.5) ** 2 for i in range(3))
                pairs.append((d, ni, (pa, pb)))
    pairs.sort()
    mid, used_n, used_e = {}, set(), set()
    for _d, ni, e in pairs:
        if ni in used_n or e in used_e:
            continue
        mid[e] = extra[ni]
        used_n.add(ni)
        used_e.add(e)
    for e in EDGES:
        if e not in mid:
            free = [ni for ni in range(len(extra)) if ni not in used_n]
            if not free:
                mid[e] = extra[0]
                continue
            pa, pb = posmap[e[0]], posmap[e[1]]
            mx, my, mz = ((c[pa][i] + c[pb][i]) * 0.5 for i in range(3))
            ni = min(free, key=lambda i: (nodes[extra[i]][0] - mx) ** 2
                     + (nodes[extra[i]][1] - my) ** 2
                     + (nodes[extra[i]][2] - mz) ** 2)
            mid[e] = extra[ni]
            used_n.add(ni)
    return conn[:4] + [mid[e] for e in EDGES]


FACES = ((0, 1, 2), (0, 1, 3), (1, 2, 3), (0, 2, 3))   # corner triples


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
    ap = argparse.ArgumentParser()
    ap.add_argument("msh")
    ap.add_argument("contacts")
    ap.add_argument("parts")
    ap.add_argument("stl_dir")
    ap.add_argument("out")
    ap.add_argument("--steps", default="1.0,2.0")
    ap.add_argument("--link-d", type=float, default=8.0,
                    help="rigid-link patch radius around contact pts, mm")
    args = ap.parse_args()
    mults = [float(t) for t in args.steps.split(",") if t.strip()]
    if not mults:
        sys.exit("FATAL: no steps")

    pj = json.loads(Path(args.parts).read_text())
    meta = pj["parts"]
    tcp = tuple(float(v) for v in pj["tcp"])
    contacts = json.loads(Path(args.contacts).read_text()).get("contacts", [])
    partnames = set(meta)

    # ---- 1. mesh -> tets grouped by Physical Volume tag ------------------
    nodes, elems, phys_names = read_msh(args.msh)
    assert nodes, "no nodes in %s" % args.msh
    vol_name = {tag: nm for (dim, tag), nm in phys_names.items() if dim == 3}
    vol_tets = {}
    nskip = 0
    for eid, (etype, nids, ptag) in sorted(elems.items()):
        if etype not in (4, 11):
            nskip += 1
            continue
        if etype == 11:
            conn = reorder_tet(nodes, nids)
        else:
            conn = list(nids[:4])
            if signed_vol(nodes, conn) < 0.0:
                conn[1], conn[2] = conn[2], conn[1]
        if abs(signed_vol(nodes, conn[:4])) < 1e-6:
            nskip += 1
            continue
        vol_tets.setdefault(ptag, []).append((eid, conn))
    assert vol_tets, "no tets in %s" % args.msh
    n4 = sum(1 for ts in vol_tets.values() for _e, c in ts if len(c) == 4)
    n10 = sum(1 for ts in vol_tets.values() for _e, c in ts if len(c) == 10)
    etype_out = "C3D4" if n10 == 0 else ("C3D10" if n4 == 0 else "MIXED")
    print("mesh: %d nodes, %d tets (%s) in %d volumes (%d skipped)"
          % (len(nodes), n4 + n10, etype_out, len(vol_tets), nskip))

    # ---- 2. volume tag -> owning part ------------------------------------
    # primary: Physical Volume name "p_<part>".  fallback (no phys name):
    # point-in-solid on the case's STLs (fragmented-mesh mode).
    stldir = Path(args.stl_dir)
    pmeshes = {}
    for name in sorted(partnames):
        f = stldir / (name + ".stl")
        if not f.is_file():
            sys.exit("FATAL: missing %s" % f)
        pmeshes[name] = trimesh.load_mesh(str(f), force="mesh")

    def owner_of(pt):
        """part whose solid contains pt; vendor wins overlaps, then alpha."""
        hits = []
        for name in partnames:
            try:
                d = trimesh.proximity.signed_distance(pmeshes[name], [pt])[0]
            except Exception:
                d = float(pmeshes[name].nearest.signed_distance([pt])[0])
            if d <= 0.15:                       # inside or grazing the wall
                hits.append((d, name))
        if not hits:
            best = min(partnames, key=lambda nm: abs(
                trimesh.proximity.signed_distance(pmeshes[nm], [pt])[0]))
            return best, True
        hits.sort(key=lambda t: t[0])           # most-negative first
        if len(hits) == 1:
            return hits[0][1], False
        for _d, nm in hits:
            if meta[nm]["cls"] == "vendor":
                return nm, False
        return hits[0][1], False

    part_tets = {}
    vol_owner = {}                                   # vtag -> part
    vols_of = {}                                     # part -> [vtag]
    n_named = n_fallback = 0
    for vtag, tets in sorted(vol_tets.items()):
        nm = vol_name.get(vtag)
        if nm and nm.startswith("p_") and nm[2:] in partnames:
            own = nm[2:]
            n_named += 1
        else:
            votes, fb = {}, False
            for eid, conn in tets[:5]:
                cen = tuple(sum(nodes[n][k] for n in conn[:4]) / 4.0
                            for k in range(3))
                o, f = owner_of(cen)
                votes[o] = votes.get(o, 0) + 1
                fb = fb or f
            own = max(votes, key=votes.get)
            if fb:
                n_fallback += 1
                print("WARN: vol %d owner %s by nearest-surface fallback"
                      % (vtag, own))
            if len(votes) > 1:
                print("  vol %d votes %s -> %s" % (vtag, votes, own))
        vol_owner[vtag] = own
        vols_of.setdefault(own, []).append(vtag)
        part_tets.setdefault(own, []).extend(tets)
    print("ownership: %d named volumes, %d inferred" % (n_named, n_fallback))
    for o in sorted(partnames - set(part_tets)):
        print("WARN: part %s owns no mesh volumes" % o)
    for p in sorted(part_tets):
        print("  %-24s %6d tets in vols %s" % (p, len(part_tets[p]),
                                             sorted(vols_of[p])))

    # ---- 3. faces: global boundary + fused interfaces ----------------------
    # trip -> [(eid, vtag)]; count 1 = exterior boundary, >1 distinct vtag =
    # fused interface (shared mesh nodes), >1 same vtag = interior face.
    trip_owner = {}
    for vtag, tets in vol_tets.items():
        for eid, conn in tets:
            for fp in FACES:
                trip = tuple(sorted(conn[i] for i in fp))
                trip_owner.setdefault(trip, []).append((eid, vtag))
    uf = UF()
    n_shared = 0
    bfaces = {v: [] for v in vol_tets}               # vtag -> [(eid, trip)]
    for trip, lst in trip_owner.items():
        vtags = {v for _e, v in lst}
        if len(lst) == 1:
            bfaces[lst[0][1]].append((lst[0][0], trip))
        elif len(vtags) > 1:
            n_shared += 1
            vs = sorted(vtags)
            for o in vs[1:]:
                uf.union(vs[0], o)
    print("fused interface faces: %d" % n_shared)

    def bcen(trip):
        return tuple(sum(nodes[n][i] for n in trip) / 3.0 for i in range(3))

    def islands():
        """vtag islands -> printable part sets."""
        g = {}
        for v in vol_tets:
            g.setdefault(uf.find(v), set()).add(vol_owner[v])
        return sorted(g.values(), key=len, reverse=True)

    isl = islands()
    print("islands (fused connectivity): %d" % len(isl))
    for ps in isl:
        print("   island: %s" % ", ".join(sorted(ps)))

    # part -> its boundary faces (over its owned fragments)
    def part_bfaces(part):
        out = []
        for v in vols_of.get(part, []):
            out.extend(bfaces[v])
        return out

    bcen_cache = {}

    def part_bcen(part):
        """cached np array of boundary-face centroids for `part`."""
        if part not in bcen_cache:
            bf = part_bfaces(part)
            bcen_cache[part] = (np.array([bcen(t) for _e, t in bf])
                                if bf else np.zeros((0, 3)))
        return bcen_cache[part]

    # ---- 4. NFIX / NLOAD ---------------------------------------------------
    base_bf = part_bfaces("base_plate")
    zmin = min(nodes[n][2] for _e, t in base_bf for n in t)
    nfix = set()
    for eid, trip in base_bf:
        if bcen(trip)[2] <= zmin + 1.5:
            nfix.update(trip)
    print("NFIX nodes: %d (base_plate boundary z<=%.2f)" % (len(nfix), zmin + 1.5))
    if not nfix:
        sys.exit("FATAL: NFIX empty")

    nload = set()
    for p in ("finger_u", "finger_d"):
        for eid, trip in part_bfaces(p):
            c = bcen(trip)
            if sum((c[i] - tcp[i]) ** 2 for i in range(3)) <= 9.0 ** 2:
                nload.update(trip)
    print("NLOAD nodes: %d (fingertip faces within 9 mm of TCP %s)"
          % (len(nload), tcp))
    if not nload:
        sys.exit("FATAL: NLOAD empty")

    # ---- 5. rigid links across remaining islands ---------------------------
    links = []
    taken = set(nfix) | set(nload)

    def patch_nodes(part, pts, d):
        """boundary nodes of `part` near pts -> (node set, face vtags)."""
        out, vsel = set(), set()
        pts_arr = np.asarray(pts)
        for v in vols_of.get(part, []):
            bf = bfaces[v]
            if not bf:
                continue
            cen = np.array([bcen(t) for _e, t in bf])
            sel = (((cen[:, None, :] - pts_arr[None, :, :]) ** 2).sum(2)
                   <= d * d).any(1)
            for (eid, trip), s in zip(bf, sel):
                if s:
                    out.update(trip)
                    vsel.add(v)
        return out - taken, vsel

    link_pts = []
    for c in contacts:
        pa, pb = c.get("a"), c.get("b")
        if pa not in part_tets or pb not in part_tets:
            continue
        if all(uf.find(va) == uf.find(vb)
               for va in vols_of.get(pa, []) for vb in vols_of.get(pb, [])):
            continue
        pts = [np.array(p, float) for p in (c.get("pts") or [])]
        if not pts:
            continue
        cen = np.mean(pts, axis=0)
        sa, va = patch_nodes(pa, pts, args.link_d)
        sb, vb = patch_nodes(pb, pts, args.link_d)
        for dw in (12.0, 18.0, 25.0):
            if len(sa) and len(sb):
                break
            sa, va = patch_nodes(pa, pts, dw)
            sb, vb = patch_nodes(pb, pts, dw)
        if not sa or not sb:
            print("WARN: link %s<->%s empty patch (a=%d b=%d) -- skipped"
                  % (pa, pb, len(sa), len(sb)))
            continue
        links.append((pa, pb, cen, sa | sb, c.get("kind", "?")))
        taken |= sa | sb
        for x in va | vb:
            uf.union(next(iter(va)), x)
    link_pts = [c for _a, _b, c, _n, _k in links]

    isl = islands()
    for _round in range(10):
        isl = islands()
        if len(isl) <= 1:
            break
        if _round == 0:
            print("WARN: %d islands after contact links; nearest-node fallback"
                  % len(isl))
        big, small = isl[0], isl[-1]            # biggest vs smallest island
        # candidate part pairs (small x big) sorted by min boundary gap;
        # first feasible pair wins. nodes already owned by another rigid
        # body are excluded: ccx allows a node in only one *RIGID BODY.
        cands = []
        for pa in small:
            on = sorted({n for e, t in part_bfaces(pa) for n in t} - taken)
            if len(on) < 4:
                continue
            opos = np.array([nodes[n] for n in on])
            for pb in big:
                qn = sorted({n for e, t in part_bfaces(pb) for n in t} - taken)
                if len(qn) < 4:
                    continue
                qpos = np.array([nodes[n] for n in qn])
                dm2 = ((opos[:, None, :] - qpos[None, :, :]) ** 2).sum(2)
                cands.append((float(dm2.min()), pa, pb))
        if not cands:
            # small island's boundary is fully owned by existing rigid
            # bodies (node may sit in only one *RIGID BODY). Extend the
            # existing body that already owns island nodes with free
            # boundary nodes from the big island -> weld through that body.
            isl_nodes = set()
            for p in small:
                for _e, t in part_bfaces(p):
                    isl_nodes.update(t)
            host = None
            for j, (_a, _b, _c, ns, _k) in enumerate(links):
                if ns & isl_nodes:
                    host = j
                    break
            if host is None:
                sys.exit("FATAL: island %s owns no rigid body to extend"
                         % sorted(small))
            big_free = set()
            for p in big:
                big_free |= {n for e, t in part_bfaces(p) for n in t}
            big_free -= taken
            if len(big_free) < 4:
                sys.exit("FATAL: no free big-island nodes to extend link")
            bf_pos = np.array([nodes[n] for n in sorted(big_free)])
            hn = sorted(links[host][3])
            hpos = np.array([nodes[n] for n in hn])
            dd = ((bf_pos[:, None, :] - hpos[None, :, :]) ** 2).sum(2).min(1)
            idx = np.argsort(dd)[:40]
            ext = {sorted(big_free)[k] for k in idx}
            links[host][3].update(ext)
            taken |= ext
            print("   fallback extend R%d +%d nodes (island boundary exhausted)"
                  % (host + 1, len(ext)))
            anchor = next(v for p in small for v in vols_of.get(p, []))
            touched = {p for p in big
                       if ext & {n for e, t in part_bfaces(p) for n in t}}
            for p in small | touched:
                for vv in vols_of.get(p, []):
                    uf.union(anchor, vv)
            continue
        cands.sort()
        d2, pa, pb = cands[0]
        on = sorted({n for e, t in part_bfaces(pa) for n in t} - taken)
        qn = sorted({n for e, t in part_bfaces(pb) for n in t} - taken)
        opos = np.array([nodes[n] for n in on])
        qpos = np.array([nodes[n] for n in qn])
        dm = np.sqrt(((opos[:, None, :] - qpos[None, :, :]) ** 2).sum(2))
        K = 40
        ia = np.argsort(dm.min(1))[:K]
        ib = np.argsort(dm.min(0))[:K]
        sa = {on[k] for k in ia}
        sb = {qn[k] for k in ib}
        cen = (opos[list(ia)].mean(0) + qpos[list(ib)].mean(0)) / 2.0
        links.append((pa, pb, cen, sa | sb, "fallback-gap %.2fmm" % (d2 ** 0.5)))
        taken |= sa | sb
        link_pts.append(cen)
        print("   fallback link %s<->%s gap=%.2fmm" % (pa, pb, d2 ** 0.5))
        for v in vols_of.get(pa, []) + vols_of.get(pb, []):
            uf.union(vols_of[pa][0], v)
    if len(islands()) > 1:
        sys.exit("FATAL: %d islands remain after 10 fallback links"
                 % len(islands()))

    for i, (pa, pb, cen, ns, kind) in enumerate(links):
        print("LINK %d %-20s<->%-20s %-14s nodes=%d at (%.1f, %.1f, %.1f)"
              % (i + 1, pa, pb, kind, len(ns), cen[0], cen[1], cen[2]))

    base_vols = set(vols_of.get("base_plate", []))
    base_root = uf.find(next(iter(base_vols))) if base_vols else None
    orphan_vols = sorted(v for v in vol_tets if uf.find(v) != base_root)
    orphan_parts = sorted({vol_owner[v] for v in orphan_vols})
    if orphan_parts:
        sys.exit("FATAL: orphan parts after links: %s (vols %s)"
                 % (orphan_parts, orphan_vols))

    # ---- 6. materials ------------------------------------------------------
    vendor_rho, printed = {}, []
    for part in sorted(part_tets):
        if meta[part]["cls"] == "vendor":
            vendor_rho[part] = float(meta[part]["rho"])
        else:
            printed.append(part)

    # ---- 7. write deck -----------------------------------------------------
    refid = max(nodes) + 1
    ref_ids = [refid] + [refid + 1 + k for k in range(len(links))]

    def wr_nset(w, name, ids):
        w("*NSET, NSET=%s\n" % name)
        ids = sorted(ids)
        for i in range(0, len(ids), 8):
            w(", ".join(str(n) for n in ids[i:i + 8]) + "\n")

    eout = 0
    with open(args.out, "w") as f:
        w = f.write
        w("*NODE\n")
        for nid, (x, y, z) in sorted(nodes.items()):
            w("%d, %.6f, %.6f, %.6f\n" % (nid, x, y, z))
        w("%d, %.6f, %.6f, %.6f\n" % ((refid,) + tcp))
        for k, cen in enumerate(link_pts):
            w("%d, %.6f, %.6f, %.6f\n" % (refid + 1 + k, cen[0], cen[1], cen[2]))
        for part in sorted(part_tets):
            w("*ELEMENT, TYPE=%s, ELSET=%s\n" % (etype_out, part))
            for _eid, conn in part_tets[part]:
                eout += 1
                w("%d, %s\n" % (eout, ", ".join(str(n) for n in conn)))
        w("*ELSET, ELSET=EALL\n")
        for i0 in range(1, eout + 1, 8):
            w(", ".join(str(e) for e in range(i0, min(i0 + 8, eout + 1))) + "\n")
        wr_nset(w, "NFIX", nfix)
        wr_nset(w, "NLOAD", nload)
        for k, (_pa, _pb, _c, ns, _kd) in enumerate(links):
            wr_nset(w, "R%d" % (k + 1), ns)
        if printed:
            w("*MATERIAL, NAME=MATPRINTED\n*ELASTIC\n4000., 0.35\n"
              "*DENSITY\n7.62e-10\n")
        for part in sorted(vendor_rho):
            w("*MATERIAL, NAME=MAT_%s\n*ELASTIC\n70000., 0.33\n"
              "*DENSITY\n%.6e\n" % (part, vendor_rho[part]))
        for part in sorted(part_tets):
            mat = "MAT_%s" % part if part in vendor_rho else "MATPRINTED"
            w("*SOLID SECTION, ELSET=%s, MATERIAL=%s\n" % (part, mat))
        w("*RIGID BODY, NSET=NLOAD, REF NODE=%d\n" % refid)
        for k in range(len(links)):
            w("*RIGID BODY, NSET=R%d, REF NODE=%d\n" % (k + 1, ref_ids[k + 1]))
        w("*BOUNDARY\nNFIX, 1, 3, 0.\n")
        for m in mults:
            w("*STEP\n*STATIC\n")
            w("*DLOAD\nEALL, GRAV, %.1f, 0., 0., -1.\n" % (9810.0 * m))
            w("*CLOAD\n%d, 3, %.4f\n" % (refid, -4.905 * m))
            w("*NODE FILE\nU, RF\n*EL FILE\nS\n*END STEP\n")

    print("done: %d nodes, %d %s tets in %d parts, %d rigid links -> %s"
          % (len(nodes), eout, etype_out, len(part_tets), len(links), args.out))
    print("ORPHANS: none")


if __name__ == "__main__":
    main()
