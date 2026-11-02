"""verify/code/gap.py - geometric sanity on a built deck.
Reports radial ranges of each contact surface and the min node distance
between each slave/master pair.
Usage: gap.py deck.inp
"""
import sys
import numpy as np
from scipy.spatial import cKDTree

F = {1: (0, 1, 2), 2: (0, 1, 3), 3: (1, 2, 3), 4: (0, 2, 3)}


def parse(path):
    nodes, elems, surfs = {}, {}, {}
    mode = None
    name = None
    for ln in open(path):
        ln = ln.strip()
        if ln.startswith("*"):
            u = ln.upper()
            mode = name = None
            if u == "*NODE":
                mode = "n"
            elif u.startswith("*ELEMENT,"):
                mode = "e"
            elif u.startswith("*SURFACE,"):
                mode = "s"
                name = u.split("NAME=")[1].split(",")[0].strip()
                surfs[name] = []
            continue
        p = [x.strip() for x in ln.split(",") if x.strip()]
        if not p:
            continue
        if mode == "n":
            nodes[int(p[0])] = [float(x) for x in p[1:4]]
        elif mode == "e":
            elems[int(p[0])] = [int(x) for x in p[1:]]
        elif mode == "s":
            surfs[name].append((int(p[0]), int(p[1][1:])))
    return nodes, elems, surfs


def fnodes(nodes, elems, faces):
    s = set()
    for te, f in faces:
        for i in F[f]:
            s.add(elems[te][i])
    return np.array([nodes[n] for n in s])


nodes, elems, surfs = parse(sys.argv[1])
for nm in sorted(surfs):
    P = fnodes(nodes, elems, surfs[nm])
    r = np.hypot(P[:, 0], P[:, 1])
    print("%-7s %5d faces %6d nodes | r %.1f..%.1f z %.1f..%.1f"
          % (nm, len(surfs[nm]), len(P), r.min(), r.max(), P[:, 2].min(), P[:, 2].max()))
for a, b in (("SRING", "MLOB1"), ("SOUTP", "MHL1")):
    if a in surfs and b in surfs:
        A = fnodes(nodes, elems, surfs[a])
        B = fnodes(nodes, elems, surfs[b])
        d, _ = cKDTree(B).query(A[::5])
        d2, _ = cKDTree(A).query(B[::5])
        print("%s->%s min %.3f med %.3f | reverse min %.3f"
              % (a, b, d.min(), np.median(d), d2.min()))
