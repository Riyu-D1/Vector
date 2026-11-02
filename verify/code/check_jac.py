"""verify/code/check_jac.py - C3D10 jacobian check as ccx sees it.
Applies the same reorder_tet as the deck writers, then evaluates detJ at
the 4 C3D10 Gauss points plus a denser sweep to catch mid-node inversions.
Usage: check_jac.py file.msh [file2.msh ...]
"""
import os
import sys
import numpy as np

sys.path.insert(0, "/Users/deepakdiwan/Vector-wt/ver/cad3/fea")
from msh2housing import read_msh, reorder_tet


def detJ_tet10(P, xi, eta, zeta):
    """det of d(xyz)/d(nat) for the 10-node tet at natural point.
    ccx corner coords A(0,0,0) B(1,0,0) C(0,1,0) D(0,0,1);
    node order c0..c3,m01,m12,m02,m03,m13,m23."""
    L = [1 - xi - eta - zeta, xi, eta, zeta]
    dL = np.array([[-1, -1, -1], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
    dN = np.zeros((10, 3))
    for i in range(4):
        dN[i] = (4 * L[i] - 1) * dL[i]
    for k, (a, b) in enumerate([(0, 1), (1, 2), (0, 2), (0, 3), (1, 3), (2, 3)]):
        dN[4 + k] = 4 * (dL[a] * L[b] + L[a] * dL[b])
    J = np.einsum("ni,nj->ij", P, dN)
    return np.linalg.det(J)


def check(path):
    nodes, elems, _ = read_msh(path)
    tets = [(eid, nids) for eid, (t, nids, ph) in elems.items() if t == 11]
    a, b = 0.5854101966249685, 0.1381966011250105
    pts = [(a, b, b), (b, a, b), (b, b, a), (b, b, b),
           (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1),
           (0.5, 0, 0), (0.5, 0.5, 0), (0, 0.5, 0),
           (0, 0, 0.5), (0.5, 0, 0.5), (0, 0.5, 0.5)]
    for xi in (0.15, 0.3, 0.45, 0.6):
        for eta in (0.15, 0.3, 0.45, 0.6):
            for zeta in (0.15, 0.3, 0.45, 0.6):
                if xi + eta + zeta < 0.95:
                    pts.append((xi, eta, zeta))
    bad, worst, wid = [], 1e30, None
    for eid, conn in tets:
        ccx = reorder_tet(nodes, conn)
        P = np.array([nodes[n] for n in ccx])
        mn = min(detJ_tet10(P, *q) for q in pts)
        if mn <= 0:
            bad.append((eid, mn))
        if mn < worst:
            worst, wid = mn, eid
    print("%s tets=%d nonpos=%d worst=%.3g @%d"
          % (os.path.basename(path), len(tets), len(bad), worst, wid))
    return bad


if __name__ == "__main__":
    for p in sys.argv[1:]:
        check(p)
