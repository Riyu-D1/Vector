"""verify/code/analyze.py - extract headline numbers from a solved .frd.

Usage: python3 analyze.py <frd> <inp> [--step N]
  inp is the matching deck (used for elset->part map, bolt end nodes,
  and the N_FIX / NRING / NOUTP reaction sets).
Prints per-part max von-Mises + location, peak contact stress, bolt axial
forces from beam elongation (F = EA/L * dL), and reaction force/moment on
the ground nsets.
"""
import sys
import math
import numpy as np

sys.path.insert(0, "/Users/deepakdiwan/Vector-wt/fea/fea_link")
from frd2vtu import read_frd, vonmises

E_STEEL = 200000.0


def parse_inp(path):
    """Return elsets (name->[eid]), elems (eid->conn), nsets, surfs."""
    elsets, nsets, surfs, elems = {}, {}, {}, {}
    with open(path) as f:
        lines = [l.rstrip("\n") for l in f]
    i = 0
    mode = None
    name = None
    while i < len(lines):
        l = lines[i].strip()
        if l.startswith("*"):
            u = l.upper()
            if u.startswith("*ELEMENT"):
                mode = "elem"
                name = u.split("ELSET=")[1].split(",")[0].strip()
                elsets[name] = []
            elif u.startswith("*NSET"):
                mode = "nset"
                name = u.split("NSET=")[1].split(",")[0].strip()
                nsets[name] = []
            elif u.startswith("*SURFACE,") or (u.startswith("*SURFACE ") and "TYPE=ELEMENT" in u):
                mode = "surf"
                name = u.split("NAME=")[1].split(",")[0].strip()
                surfs[name] = []
            elif u.startswith("*ELSET"):
                mode = "elset"
                name = u.split("ELSET=")[1].split(",")[0].strip()
                elsets.setdefault(name, [])
            else:
                mode = None
            i += 1
            continue
        if mode and l:
            p = [x.strip() for x in l.split(",") if x.strip()]
            if mode == "elem":
                elems[int(p[0])] = [int(x) for x in p[1:]]
                elsets[name].append(int(p[0]))
            elif mode == "nset":
                nsets[name] += [int(x) for x in p]
            elif mode == "surf":
                surfs[name].append((int(p[0]), p[1]))
            elif mode == "elset":
                elsets[name] += [int(x) for x in p]
        i += 1
    return elsets, nsets, surfs, elems


def main(frd, inp, want=None):
    nodes, elems, steps = read_frd(frd)
    elsets, nsets, surfs, ielems = parse_inp(inp)
    names = [s["name"].upper() for s in steps]
    print("%s: %d nodes %d elems | fields %s" % (frd.split("/")[-1], len(nodes), len(elems), sorted(set(names))))
    # use last step's blocks (or the requested one)
    blocks = {}
    for s in steps:
        blocks.setdefault(s["name"].upper().split()[0], []).append(s["data"])
    disp = blocks.get("DISP", [{}])[-1]
    stress = blocks.get("STRESS", [{}])[-1]
    cstr = blocks.get("CSTR", [{}])[-1]
    rf = blocks.get("RF", [{}])[-1]
    vm = {n: vonmises(s[:6]) for n, s in stress.items() if len(s) >= 6}
    # node -> part via element membership (solid elems only)
    partof = {}
    for nm, eids in elsets.items():
        for e in eids:
            if len(ielems.get(e, [])) >= 4:
                for n in ielems[e]:
                    partof.setdefault(n, nm)
    stats = {}
    for n, v in vm.items():
        p = partof.get(n, "?")
        c, m, at = stats.get(p, (0, -1, n))
        stats[p] = (c + 1, max(m, v), at if v <= m else n)
    print("per-part peak VM:")
    for p in sorted(stats):
        c, m, at = stats[p]
        x = nodes.get(at, (0, 0, 0))
        print("  %-10s nodes=%7d  max=%8.2f MPa at (%.1f %.1f %.1f) #%d"
              % (p, c, m, x[0], x[1], x[2], at))
    if cstr:
        cp = {n: max(abs(q) for q in v) for n, v in cstr.items() if v}
        top = sorted(cp.items(), key=lambda kv: -kv[1])[:6]
        print("peak contact stress:")
        for n, v in top:
            x = nodes[n]
            print("  %8.2f at (%.1f %.1f %.1f) #%d" % (v, x[0], x[1], x[2], n))
    if disp:
        du = sorted(((np.linalg.norm(u[:3]), n) for n, u in disp.items()
                     if len(u) >= 3 and n in vm), reverse=True)[:4]
        print("peak |u|:  " + "; ".join("%.3f@(%.0f,%.0f,%.0f)" % (
            m, nodes[n][0], nodes[n][1], nodes[n][2]) for m, n in du))
    # bolt axial forces: EBOLT elems, end-node axial elongation
    if "EBOLT" in elsets and disp:
        print("bolt axial forces (EA/L*dL):")
        for e in elsets["EBOLT"]:
            c = ielems[e]
            n1, n2 = c[0], c[1]
            a = np.array(nodes[n1]); b = np.array(nodes[n2])
            axis = b - a
            L = np.linalg.norm(axis)
            axis /= L
            dl = np.dot(np.array(disp.get(n2, [0, 0, 0])[:3])
                        - np.array(disp.get(n1, [0, 0, 0])[:3]), axis)
            F = E_STEEL * math.pi * 1.5 ** 2 * dl / L
            print("  beam %d L=%.1f dL=%.5f -> F=%.1f N" % (e, L, dl, F))
    # reactions on ground sets
    for ns in ("N_FIX", "NRING", "NOUTP"):
        if ns in nsets and rf:
            F = np.zeros(3)
            for n in nsets[ns]:
                F += np.array(rf.get(n, [0, 0, 0])[:3])
            M = np.zeros(3)
            for n in nsets[ns]:
                r = np.array(nodes.get(n, [0, 0, 0]))
                M += np.cross(r, np.array(rf.get(n, [0, 0, 0])[:3]))
            print("reaction %s: F=(%.1f %.1f %.1f) N  Mz=%.0f Nmm"
                  % (ns, F[0], F[1], F[2], M[2]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
