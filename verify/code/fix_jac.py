"""verify/code/fix_jac.py - repair inverted C3D10s by straightening edges.
A tet that is inverted only through curved-midside distortion becomes
positive when its midside nodes sit at edge midpoints (pure linear map,
det = corner det > 0). Moves the bad tets' midsides to midpoints and
re-checks every element sharing those nodes.
Usage: fix_jac.py file.msh
"""
import sys
import numpy as np

sys.path.insert(0, "/Users/deepakdiwan/Vector-wt/ver/verify/code")
sys.path.insert(0, "/Users/deepakdiwan/Vector-wt/ver/cad3/fea")
from msh2housing import read_msh, reorder_tet
from check_jac import detJ_tet10

PTS = []
a, b = 0.5854101966249685, 0.1381966011250105
PTS += [(a, b, b), (b, a, b), (b, b, a), (b, b, b)]
PTS += [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)]
PTS += [(0.5, 0, 0), (0.5, 0.5, 0), (0, 0.5, 0),
        (0, 0, 0.5), (0.5, 0, 0.5), (0, 0.5, 0.5)]
EDGES = [(0, 1), (1, 2), (0, 2), (0, 3), (1, 3), (2, 3)]


def mindet(nodes, conn):
    P = np.array([nodes[n] for n in conn])
    return min(detJ_tet10(P, *q) for q in PTS)


def fix(path):
    nodes, elems, _ = read_msh(path)
    tets = {e: reorder_tet(nodes, c) for e, (t, c, p) in elems.items() if t == 11}
    users = {}
    for e, conn in tets.items():
        for n in conn[4:]:
            users.setdefault(n, set()).add(e)
    bad = [e for e, c in tets.items() if mindet(nodes, c) <= 0]
    print("%s: %d bad" % (path, len(bad)))
    for e in bad:
        conn = tets[e]
        for k, (i, j) in enumerate(EDGES):
            n = conn[4 + k]
            ci, cj = nodes[conn[i]], nodes[conn[j]]
            nodes[n] = tuple((a + b) / 2 for a, b in zip(ci, cj))
    # re-verify everything touched
    touched = set()
    for e in bad:
        for n in tets[e][4:]:
            touched.update(users[n])
    still = [e for e in touched if mindet(nodes, tets[e]) <= 0]
    print("  touched %d, still bad %d" % (len(touched), len(still)))
    if still:
        print("  UNREPAIRED:", still[:10])
        return
    # write back (same v2.2 format, preserve all element types)
    with open(path) as f:
        lines = f.read().splitlines()
    out = []
    i = 0
    while i < len(lines):
        out.append(lines[i])
        if lines[i].strip() == "$Nodes":
            n = int(lines[i + 1])
            out.append(lines[i + 1])
            for j in range(n):
                p = lines[i + 2 + j].split(None, 1)
                nid = int(p[0])
                x = nodes[nid]
                out.append("%d %.8f %.8f %.8f" % (nid, *x))
            i += n + 3
            continue
        i += 1
    with open(path, "w") as f:
        f.write("\n".join(out) + "\n")
    print("  written")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        fix(p)
