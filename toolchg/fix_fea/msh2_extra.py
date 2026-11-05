"""toolchg/fix_fea/msh2_extra.py - D11 added CalculiX decks (D12 copy).

Reuses the tested helpers in toolchg/fea/msh2tc.py (read_msh,
reorder_tet, gauss_min_det, signed_vol) verbatim; only the BC/load spec
is new.  Same conventions: NFIX/NLOAD nsets, *RIGID BODY ref-node wrench.
Identical to toolchg/check/fea/msh2_extra.py except the product-fea
path resolves from toolchg/fix_fea/.

Cases (coords = W frame mm: x=a, y=b, z=h):

  plate_1catch  tc_plate with the whole 0.5kg+tool wrench on ONE catch's
                +a face (single-lug fault case; the capture path).
                NFIX a>=78.3; NLOAD a in [71.8,72.6], r 12.5..18.5,
                phase 118+-30.  F=(0,0,-5.7) at TCP.
  tool_pen      pen tip lateral 5 N.  NFIX = the three catch +a faces
                (the interface the master holds).  NLOAD a>=143 (tip
                cone), ref at TCP, F=(0,5,0).
  tool_grip     NFIX = the three catch +a faces; NLOAD a>=120 (distal
                grip body), ref at TCP, F=(0,0,-5.7) payload wrench.
  tc_rack       NFIX base z<=0.5; NLOAD slot-2 seat surface nodes;
                F=(0,0,-1.2) at the tool axis (80g tool x 1.5 bump).

Run:  python3 msh2_extra.py <part>.msh <part>.inp <case>
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))          # fix_fea
FEA = os.path.join(os.path.dirname(HERE), "fea")           # toolchg/fea
sys.path.insert(0, FEA)
from msh2tc import read_msh, reorder_tet, signed_vol, gauss_min_det  # noqa

H_AX = -17.0

def rax(p):
    return np.hypot(p[:, 1], p[:, 2] - H_AX)

def ph(p):
    return np.degrees(np.arctan2(p[:, 2] - H_AX, p[:, 1])) % 360.0

def catch_faces(p):
    return (p[:, 0] >= 71.8) & (p[:, 0] <= 72.6) & \
           (rax(p) >= 12.5) & (rax(p) <= 18.5)

def floor_face(p):
    # socket floor -a face (a 76.0, r <= 18.2) where the spigot tip bears
    return (p[:, 0] >= 75.9) & (p[:, 0] <= 76.1) & (rax(p) <= 18.2)

CASES = {
    "plate_1catch": dict(
        fix=lambda p: p[:, 0] >= 78.3,
        load=lambda p: catch_faces(p) & (np.abs(ph(p) - 118.0) < 30.0),
        F=np.array([0.0, 0.0, -5.7]), B=np.array([149.4, 0.0, -17.0])),
    "tool_pen": dict(
        fix=lambda p: catch_faces(p),
        load=lambda p: p[:, 0] >= 143.0,
        F=np.array([0.0, 5.0, 0.0]), B=np.array([149.4, 0.0, -17.0])),
    "tool_grip": dict(
        fix=lambda p: catch_faces(p) | floor_face(p),
        load=lambda p: p[:, 0] >= 120.0,
        F=np.array([0.0, 0.0, -5.7]), B=np.array([149.4, 0.0, -17.0])),
    "tc_rack": dict(
        fix=lambda p: p[:, 2] <= 0.5,
        load=lambda p: (p[:, 0] >= 142.0) & (p[:, 0] <= 148.0)
        & (np.hypot(p[:, 1] + 57.0, p[:, 2] - 110.0) >= 19.5)
        & (np.hypot(p[:, 1] + 57.0, p[:, 2] - 110.0) <= 21.2)
        & (p[:, 2] < 110.0),
        F=np.array([0.0, 0.0, -1.2]), B=np.array([145.0, -57.0, 110.0])),
}

def main(msh, inp, case):
    nodes, elems, _ = read_msh(msh)
    assert nodes and elems, "empty mesh"
    S = CASES[case]
    F, B = S["F"], S["B"]
    ids = np.array(sorted(nodes))
    P = np.array([nodes[i] for i in ids])
    fix = ids[S["fix"](P)]
    load = ids[S["load"](P)]
    assert len(fix) and len(load), (case, len(fix), len(load))
    assert not set(fix) & set(load)
    print("  %s: NFIX=%d NLOAD=%d" % (case, len(fix), len(load)))

    tets, ndrop, ninv = [], 0, 0
    for eid, (etype, nids, phys) in sorted(elems.items()):
        if etype == 11:
            n2 = reorder_tet(nodes, nids)
            if signed_vol(nodes, n2[:4]) < 1e-4:
                ndrop += 1
                continue
            if gauss_min_det(nodes, n2) <= 0.0:
                ninv += 1
                continue
            tets.append((eid, n2))
    if ndrop:
        print("  dropped %d collapsed tets" % ndrop)
    if ninv:
        print("  dropped %d inverted tets" % ninv)
    used = set(int(n) for _, nn in tets for n in nn)
    ids = np.array(sorted(used))
    fix = np.array([n for n in fix if n in used])
    load = np.array([n for n in load if n in used])
    assert len(fix) and len(load), (case, "patches emptied by tet drop")

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
    w("*DLOAD\nEALL, GRAV, 9810.0, 0.00000, 0.00000, -1.00000\n")
    for k in range(3):
        if abs(F[k]) > 1e-9:
            w("*CLOAD\n%d, %d, %.6f\n" % (ref, k + 1, F[k]))
    w("*NODE FILE\nU, RF\n*EL FILE\nS\n*END STEP\n")
    print("%s: %d nodes %d C3D10 NFIX=%d NLOAD=%d"
          % (inp, len(ids), len(tets), len(fix), len(load)))
    print("  F=%s N at ref %s" % (np.round(F, 2).tolist(),
                                  np.round(B, 1).tolist()))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
