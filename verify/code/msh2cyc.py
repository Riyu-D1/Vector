"""verify/code/msh2cyc.py - CalculiX deck writer for the cycloidal-stage
contact model (stage V1 task 1).

Model (act2 module frame, ap.py N=40/NP=41/R=23.5/RP=1.5/E=0.42):
  - two cycloid discs (PETG-CF), bores rigid-coupled to ref nodes at their
    centres (the 6702 bearing keeps the bore round + planar);
  - 41 ring pins (steel) in the housing blind bores: lateral surface fixed in
    the bore-supported bands (z<33.8, 37.8..38.1, z>42.1) + bottom faces fixed;
  - 6 output pins (steel) pressed into the carrier: lateral surface fixed in
    the pressed band z>=42.4;
  - frictional node-to-surface contact (mu=0.2 [U]) disc lobes <-> ring pins,
    disc output holes <-> output pins;
  - drive = crank advance: bore ref nodes prescribed along the crank orbit by
    dth (rad) - the true input kinematics (eccentric bearing prescribes the
    disc-centre position); output torque = reaction moment about +Z summed on
    the pinned output-pin nodes; input torque = tangential RF x E.

Run:  python3 msh2cyc.py <mshdir> <out.inp> <phase_deg> <dth_rad> [cl]
"""
import sys
import math

sys.path.insert(0, "/Users/deepakdiwan/Vector-wt/ver/cad3/fea")
from msh2housing import read_msh, reorder_tet

sys.path.insert(0, "/Users/deepakdiwan/Vector-wt/ver/cad/act2")
import ap

E_ECC = ap.GEAR[ap.RATIO]["E"]
R_RING = ap.GEAR[ap.RATIO]["R"]
RP = ap.GEAR[ap.RATIO]["RP"]
N_OUT = ap.OUT_PIN_N
R_OUT = ap.OUT_PIN_PCD / 2.0
A_OUT = ap.OUT_PIN_ANG0
Z_DISC = {1: ap.Z_DISC1, 2: ap.Z_DISC2}

PETG = (4000.0, 0.35, 7.62e-10)
STEEL = (200000.0, 0.29, 7.85e-9)


def read_all(paths):
    """Merge several .msh files into one node/elem space."""
    nodes, tets, tris, parts = {}, [], [], {}
    n0 = e0 = 0
    for part, path in paths:
        n, e, _ = read_msh(path)
        remap = {}
        for nid, xyz in n.items():
            remap[nid] = nid + n0
            nodes[nid + n0] = xyz
        pset = []
        for eid, (etype, nids, phys) in e.items():
            ids = [remap[i] for i in nids]
            if etype == 11:
                tets.append((eid + e0, ids))
                pset.append(eid + e0)
            elif etype in (2, 9):
                tris.append((eid + e0, ids))
        parts[part] = pset
        n0 = max(nodes)
        e0 = max(n0, max(e for e, _ in tets), max(e for e, _ in tris)) + 1
    return nodes, tets, tris, parts


FACE_OF = {frozenset((0, 1, 2)): 1, frozenset((0, 1, 3)): 2,
           frozenset((1, 2, 3)): 3, frozenset((0, 2, 3)): 4}


def surf_faces(nodes, tets, tris, keep_tri, tcorners):
    """Map qualifying surface tris to (tet_id, face_no). keep_tri(corner_xyz)->bool."""
    corner_tets = {}   # frozenset(corners) -> (eid, face)
    for eid, ids in tets:
        c = ids[:4]
        for fs, fno in FACE_OF.items():
            key = frozenset(c[i] for i in fs)
            corner_tets.setdefault(key, (eid, fno))
    out = []
    for eid, ids in tris:
        c = ids[:3]
        if keep_tri([nodes[i] for i in c]):
            k = frozenset(c)
            if k in corner_tets:
                out.append(corner_tets[k])
    return out


def pin_axes():
    return [(R_RING * math.cos(2 * math.pi * k / 41.0),
             R_RING * math.sin(2 * math.pi * k / 41.0)) for k in range(41)]


def out_axes():
    return [(R_OUT * math.cos(math.radians(A_OUT + 60 * k)),
             R_OUT * math.sin(math.radians(A_OUT + 60 * k))) for k in range(N_OUT)]


def near_axis(x, y, axes, r, tol):
    return any((x - ax) ** 2 + (y - ay) ** 2 <= (r + tol) ** 2 for ax, ay in axes)


def main(mshdir, inp, th_deg, dth, cl=1.0, tie=False, single=False):
    th = math.radians(th_deg)
    cx, cy = E_ECC * math.cos(th), E_ECC * math.sin(th)
    centres = {1: (cx, cy), 2: (-cx, -cy)}
    paths = [("disc1", mshdir + "/disc1.msh")]
    if not single:
        paths.append(("disc2", mshdir + "/disc2.msh"))
    paths += [("ringpins", mshdir + "/ringpins.msh"), ("outpins", mshdir + "/outpins.msh")]
    DISCS = [1] if single else [1, 2]
    nodes, tets, tris, parts = read_all(paths)
    coords = {i: n for i, n in nodes.items()}
    tc = {e: ids[:4] for e, ids in tets}
    part_of = {}
    for p, es in parts.items():
        for e in es:
            part_of[e] = p
    dtets = {p: [e for e in parts[p]] for p in parts}
    tet_part = part_of

    # classify surface tris by which part's tet owns them
    corner_tets = {}
    for eid, ids in tets:
        c = ids[:4]
        for fs in FACE_OF:
            corner_tets[frozenset(c[i] for i in fs)] = (eid,)
    tri_owner = {}
    for eid, ids in tris:
        k = frozenset(ids[:3])
        if k in corner_tets:
            tri_owner[eid] = (part_of.get(corner_tets[k][0]), corner_tets[k][0])

    pins = pin_axes()
    outs = out_axes()

    # ---- contact surfaces (element faces), S2S: slave = finer pin mesh ----
    rpin_faces, opin_faces = [], []
    lobe_faces, hole_faces = {1: [], 2: []}, {1: [], 2: []}
    for eid, ids in tris:
        own = tri_owner.get(eid)
        if not own:
            continue
        p, te = own
        c = ids[:3]
        xs = [nodes[i] for i in c]
        if p == "ringpins":
            # lateral surface: all corners ~RP from a pin axis
            if all(near_axis(x, y, pins, RP, 0.12) for x, y, z in xs):
                for fs, fno in FACE_OF.items():
                    if frozenset(tc[te][i] for i in fs) == frozenset(c):
                        rpin_faces.append((te, fno))
        elif p == "outpins":
            # lateral surface, only the free span z < 42.6 can touch disc holes
            if all(near_axis(x, y, outs, RP, 0.12) and z <= 42.6 for x, y, z in xs):
                for fs, fno in FACE_OF.items():
                    if frozenset(tc[te][i] for i in fs) == frozenset(c):
                        opin_faces.append((te, fno))
        elif p in ("disc1", "disc2"):
            di = int(p[-1])
            cx0, cy0 = centres[di]
            zs = [x[2] for x in xs]
            if max(zs) - min(zs) < 0.25:      # flat top/bottom face tri
                continue
            rr = [math.hypot(x[0] - cx0, x[1] - cy0) for x in xs]
            if min(rr) > 19.0:                 # outer rim (lobe flank)
                for fs, fno in FACE_OF.items():
                    if frozenset(tc[te][i] for i in fs) == frozenset(c):
                        lobe_faces[di].append((te, fno))
                continue
            for k in range(N_OUT):
                hx = cx0 + R_OUT * math.cos(math.radians(A_OUT + 60 * k))
                hy = cy0 + R_OUT * math.sin(math.radians(A_OUT + 60 * k))
                if all((x[0] - hx) ** 2 + (x[1] - hy) ** 2 <= (2.07 + 0.5) ** 2 for x in xs):
                    for fs, fno in FACE_OF.items():
                        if frozenset(tc[te][i] for i in fs) == frozenset(c):
                            hole_faces[di].append((te, fno))
                    break

    # ---- BC node sets ----
    fix_ring, fix_out, bores = set(), set(), {1: set(), 2: set()}
    pin_band = lambda z: z <= 33.80 + 1e-9 or 37.80 - 1e-9 <= z <= 38.10 + 1e-9 or z >= 42.10 - 1e-9
    for eid, ids in tris:
        own = tri_owner.get(eid)
        if not own:
            continue
        p = own[0]
        xs = [nodes[i] for i in ids[:3]]
        if p == "ringpins":
            if all(near_axis(x, y, pins, RP, 0.12) for x, y, z in xs):
                for i in ids[:3]:
                    if pin_band(nodes[i][2]):
                        fix_ring.add(i)
            for i in ids[:3]:
                if nodes[i][2] <= 33.55:      # bottom face
                    fix_ring.add(i)
        elif p == "outpins":
            if all(near_axis(x, y, outs, RP, 0.12) for x, y, z in xs):
                for i in ids[:3]:
                    if nodes[i][2] >= 42.35:
                        fix_out.add(i)
            for i in ids[:3]:
                if nodes[i][2] >= 45.95:      # top face
                    fix_out.add(i)
        elif p in ("disc1", "disc2"):
            di = int(p[-1]); cx0, cy0 = centres[di]
            if all(abs(math.hypot(x - cx0, y - cy0) - 10.5) < 0.12 for x, y, z in xs):
                bores[di].update(ids[:3])

    assert rpin_faces and opin_faces, "empty pin surface"
    assert all(lobe_faces[d] and hole_faces[d] for d in DISCS), "empty disc surface"
    assert fix_ring and fix_out and all(bores[d] for d in DISCS), "empty BC nset"

    ref = max(nodes) + 1
    refs = {d: ref + d - 1 for d in DISCS}
    eall = [e for e, _ in tets]

    w = open(inp, "w").write
    w("** cycloid contact stage V1: phase %.4f deg, crank advance %.4f rad\n" % (th_deg, dth))
    w("*NODE\n")
    for nid, (x, y, z) in sorted(nodes.items()):
        w("%d, %.6f, %.6f, %.6f\n" % (nid, x, y, z))
    for d in DISCS:
        w("%d, %.6f, %.6f, %.6f\n" % (refs[d], centres[d][0], centres[d][1], sum(Z_DISC[d]) / 2))
    w("*ELEMENT, TYPE=C3D10, ELSET=E%s\n" % "PETG")
    for eid, ids in tets:
        if part_of.get(eid) in ("disc1", "disc2"):
            w("%d, %s\n" % (eid, ", ".join(str(n) for n in reorder_tet(nodes, ids))))
    for pname in ("ringpins", "outpins"):
        w("*ELEMENT, TYPE=C3D10, ELSET=E%s\n" % pname.upper())
        for eid, ids in tets:
            if part_of.get(eid) == pname:
                w("%d, %s\n" % (eid, ", ".join(str(n) for n in reorder_tet(nodes, ids))))
    def wr_nset(nm, ids):
        w("*NSET, NSET=%s\n" % nm)
        ids = sorted(ids)
        for i in range(0, len(ids), 8):
            w(", ".join(str(n) for n in ids[i:i + 8]) + "\n")
    wr_nset("NRING", fix_ring); wr_nset("NOUTP", fix_out)
    for d in DISCS:
        wr_nset("NBORE%d" % d, bores[d])

    w("*SURFACE, NAME=SRING, TYPE=ELEMENT\n")
    for te, fno in rpin_faces:
        w("%d, S%d\n" % (te, fno))
    w("*SURFACE, NAME=SOUTP, TYPE=ELEMENT\n")
    for te, fno in opin_faces:
        w("%d, S%d\n" % (te, fno))
    for di in DISCS:
        w("*SURFACE, NAME=MLOB%d, TYPE=ELEMENT\n" % di)
        for te, fno in lobe_faces[di]:
            w("%d, S%d\n" % (te, fno))
        w("*SURFACE, NAME=MHL%d, TYPE=ELEMENT\n" % di)
        for te, fno in hole_faces[di]:
            w("%d, S%d\n" % (te, fno))

    w("*MATERIAL, NAME=PETGCF\n*ELASTIC\n%.1f, %.3f\n*DENSITY\n%.4g\n" % PETG)
    w("*MATERIAL, NAME=STEEL\n*ELASTIC\n%.1f, %.3f\n*DENSITY\n%.4g\n" % STEEL)
    w("*SOLID SECTION, ELSET=EPETG, MATERIAL=PETGCF\n")
    w("*SOLID SECTION, ELSET=ERINGPINS, MATERIAL=STEEL\n")
    w("*SOLID SECTION, ELSET=EOUTPINS, MATERIAL=STEEL\n")

    for d in DISCS:
        w("*RIGID BODY, NSET=NBORE%d, REF NODE=%d\n" % (d, refs[d]))
    w("*BOUNDARY\nNRING, 1, 3, 0.\nNOUTP, 1, 3, 0.\n")
    for d in DISCS:
        w("%d, 3, 5, 0.\n" % refs[d])      # axial + pitch/roll held by the 6702
    pairs = [("SRING", "MLOB%d" % d) for d in DISCS] \
        + [("SOUTP", "MHL%d" % d) for d in DISCS]
    if tie:
        # stage fallback: TIED contact (hard contact failed to solve ->
        # documented in STATUS).  TIED overclosure glues the pairs at the
        # CURRENT gap - *TIE is unusable here because its position-tolerance
        # snap (>=0.15mm) inverts thin surface tets.
        w("*SURFACE INTERACTION, NAME=CT\n*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=TIED\n")
        for a, b in pairs:
            w("*CONTACT PAIR, INTERACTION=CT, TYPE=SURFACE TO SURFACE\n%s, %s\n" % (a, b))
    else:
        w("*SURFACE INTERACTION, NAME=CT\n*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=HARD\n*FRICTION\n0.2\n")
        for a, b in pairs:
            w("*CONTACT PAIR, INTERACTION=CT, TYPE=SURFACE TO SURFACE\n%s, %s\n" % (a, b))
    # crank-orbit drive: centre moves along its orbit by dth (true input kinematics).
    # step 1 seats the contacts with disc yaw locked; step 2 releases yaw
    # (output-side compliance DOF) and ramps the remaining drive.
    ux = [0.0] * 3
    uy = [0.0] * 3
    for s, f in ((1, 0.70), (2, 1.0)):
        dd = dth * f
        ux[s] = E_ECC * (math.cos(th + dd) - math.cos(th))
        uy[s] = E_ECC * (math.sin(th + dd) - math.sin(th))
    w("*STEP, NLGEOM\n*STATIC, SOLVER=ITERATIVE CHOLESKY\n0.15, 1., 1e-6, 0.35\n")
    w("*BOUNDARY\n")
    for d in DISCS:
        sg = 1.0 if d == 1 else -1.0
        w("%d, 6, 6, 0.\n" % refs[d])
        w("%d, 1, 1, %.6f\n%d, 2, 2, %.6f\n" % (refs[d], sg * ux[1], refs[d], sg * uy[1]))
    w("*CONTACT FILE\nCDIS, CSTR\n*NODE FILE\nU, RF\n*EL FILE\nS\n*END STEP\n")
    w("*STEP, NLGEOM\n*STATIC, SOLVER=ITERATIVE CHOLESKY\n0.15, 1., 1e-6, 0.35\n")
    w("*BOUNDARY\n")
    for d in DISCS:
        sg = 1.0 if d == 1 else -1.0
        w("%d, 1, 1, %.6f\n%d, 2, 2, %.6f\n" % (refs[d], sg * ux[2], refs[d], sg * uy[2]))
    w("*CONTACT FILE\nCDIS, CSTR\n*NODE FILE\nU, RF\n*EL FILE\nS\n*END STEP\n")
    print("inp %s: %d nodes %d tets | rpin faces %d opin faces %d" %
          (inp, len(nodes) + 3, len(tets), len(rpin_faces), len(opin_faces)))
    print("  lobe faces %s hole faces %s | fix ring %d outp %d | bores %s" %
          ([len(lobe_faces[d]) for d in DISCS], [len(hole_faces[d]) for d in DISCS],
           len(fix_ring), len(fix_out), [len(bores[d]) for d in DISCS]))
    print("  refs %s  drive (%.4f, %.4f)" % (refs, ux[2], uy[2]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]),
         float(sys.argv[5]) if len(sys.argv) > 5 and sys.argv[5].replace(".", "").isdigit() else 1.0,
         ("tie" in sys.argv), ("one" in sys.argv))
