"""verify/code/msh2j4.py - CalculiX deck for the J4 STS3250 cradle bolt check
(stage V1 task 2, J4).  Native rest world frame; J4 axis || world Y at
x=58.4, z=216.2 (measured from the cradle STEP).

Parts: cradle (out/msh/jt_j4_cradle.msh), fore_r clip (jt_j4_fore_r.msh).
Load path: wrist torque -> rigid servo-case lump (pocket faces -> ref) ->
cradle -> 4x M3 pilots (a,h)=(-6,+-9),(-28,+-9) -> fore_r plate (ground).
Face contact cradle<->plate at y=32.55; B32 bolts + thermal preload;
distributing couplings on washer patch (fore_r outer face y~36.6) and pilot
walls; wrench = 2x weight+payload Fz=-14.64 N at ref a=+105.1 -> M=1.54 N.m.
Run:  python3 msh2j4.py <mshdir> <out.inp>
"""
import sys
import math

sys.path.insert(0, "/Users/deepakdiwan/Vector-wt/ver/cad3/fea")
from msh2housing import read_msh, reorder_tet

PETG = (4000.0, 0.35, 7.62e-10)
BOLT_A = math.pi * 1.5 ** 2
PRELOAD_N = 400.0                     # [U] M3x10 into pilots
ALPHA = 1.1e-5
E_STEEL = 200000.0
DT = PRELOAD_N / (E_STEEL * BOLT_A * ALPHA)

J4X, J4Z = 62.4, 216.2                # measured (pilot cylinders)
Y_FACE = 32.55                        # cradle <-> fore_r interface plane
Y_OUT = 36.6                          # fore_r outer face
BOLT_AX = [(J4X - a, J4Z - h) for a, h in ((-6.0, 9.0), (-6.0, -9.0), (-28.0, 9.0), (-28.0, -9.0))]
F_LOAD = -14.64                       # N, Fz at ref (2 x 0.746 kg x g)
D_CM = 105.1                          # mm along -x from J4 axis (a+ tool dir)


def main(mshdir, inp):
    nodes, tets, tris, tetpart = {}, [], [], {}
    n0 = e0 = 0
    for part in ("cradle", "fore_r"):
        n, e, _ = read_msh("%s/jt_j4_%s.msh" % (mshdir, part))
        remap = {}
        for nid, xyz in n.items():
            remap[nid] = nid + n0
            nodes[nid + n0] = xyz
        for eid, (etype, nids, phys) in e.items():
            ids = [remap[i] for i in nids]
            if etype == 11:
                tets.append((eid + e0, ids)); tetpart[eid + e0] = part
            elif etype in (2, 9):
                tris.append((eid + e0, ids))
        n0 = max(nodes)
        e0 = max(t[0] for t in tets) + 1
    tc = {e: ids[:4] for e, ids in tets}
    FACE_OF = {frozenset((0, 1, 2)): 1, frozenset((0, 1, 3)): 2,
               frozenset((1, 2, 3)): 3, frozenset((0, 2, 3)): 4}
    corner_tets = {}
    for eid, ids in tets:
        for fs in FACE_OF:
            corner_tets[frozenset(ids[i] for i in fs)] = eid
    tri_owner = {}
    for eid, ids in tris:
        te = corner_tets.get(frozenset(ids[:3]))
        if te is not None:
            tri_owner[eid] = tetpart[te]

    def face(eid, ids):
        te = corner_tets.get(frozenset(ids[:3]))
        if te is None:
            return None
        for fs, fno in FACE_OF.items():
            if frozenset(tc[te][i] for i in fs) == frozenset(ids[:3]):
                return (te, fno, ids)
        return None

    surfs = {}
    def add(nm, f):
        if f:
            surfs.setdefault(nm, []).append(f)

    for eid, ids in tris:
        p = tri_owner.get(eid)
        if p is None:
            continue
        xs = [nodes[i] for i in ids[:3]]
        yl = [x[1] for x in xs]
        vert = max(yl) - min(yl) > 0.25      # wall along the bolt (y) axis
        cx, cy, cz = (sum(q) / 3.0 for q in zip(*xs))
        if p == "cradle":
            if not vert and min(yl) > Y_FACE - 0.4:
                add("cr_face", face(eid, ids))           # on fore_r
            elif vert:
                for k, (ax, az) in enumerate(BOLT_AX):
                    if all((x - ax) ** 2 + (z - az) ** 2 < 1.6 ** 2 for x, y, z in xs):
                        if min(yl) > Y_FACE - 8.5:
                            add("pilot%d" % k, face(eid, ids))
                # servo pocket faces: everything inside the pocket region,
                # i.e. cradle surfaces NOT on the outer skin and not pilots
        elif p == "fore_r":
            if not vert and abs(cy - Y_FACE) < 0.4:
                add("fr_face", face(eid, ids))
            elif not vert and min(yl) > Y_OUT - 0.3:
                for k, (ax, az) in enumerate(BOLT_AX):
                    if all((x - ax) ** 2 + (z - az) ** 2 < 3.4 ** 2 for x, y, z in xs):
                        add("fwash%d" % k, face(eid, ids))
            if (all(x[0] < J4X - 39.9 for x in xs) or all(x[0] > J4X + 44.9 for x in xs)
                    or all(x[2] < J4Z - 34.9 for x in xs) or all(x[2] > J4Z + 34.9 for x in xs)):
                add("fr_fix", face(eid, ids))
    # pocket lump: cradle faces inside the servo case envelope that are not
    # the bolt pilots and not the plate face -> rigid body ref.
    # case envelope in (a=x', h=z'): a -35.1..10.1 -> x J4X-10.1..J4X+35.1,
    # lz/2 +-6.2 -> z J4Z-6.3..J4Z+6.3 (case), horn sticks out -b.
    pk = set()
    for eid, ids in tris:
        if tri_owner.get(eid) != "cradle":
            continue
        xs = [nodes[i] for i in ids[:3]]
        cy = sum(x[1] for x in xs) / 3.0
        cx = sum(x[0] for x in xs) / 3.0
        cz = sum(x[2] for x in xs) / 3.0
        if J4X - 10.3 < cx < J4X + 35.3 and J4Z - 6.5 < cz < J4Z + 6.5 and cy < 30.0:
            # inside the case bounding box; exclude the plate face + pilots
            skip = False
            for k, (ax, az) in enumerate(BOLT_AX):
                if all((x - ax) ** 2 + (z - az) ** 2 < 1.7 ** 2 for x, y, z in xs):
                    skip = True
            if not skip and max(x[1] for x in xs) - min(x[1] for x in xs) > 0.2 or True:
                if not all(abs(x[1] - Y_FACE) < 0.4 for x in xs):
                    pk.update(ids[:3])
    n_fix = set()
    for te, fno, ids in surfs.get("fr_fix", []):
        n_fix.update(ids)

    ref0 = max(nodes) + 1
    bolt_beams = []
    nb = 0
    for k, (ax, az) in enumerate(BOLT_AX):
        bolt_beams.append((ref0 + nb, ref0 + nb + 1, (ax, Y_OUT + 1.0, az),
                           (ax, Y_FACE - 7.0, az), "fwash%d" % k, "pilot%d" % k)); nb += 2
    load_ref = ref0 + nb
    mid0 = load_ref + 1
    e_bolt0 = max(t[0] for t in tets) + 1
    bolt_nodes = [b[0] for b in bolt_beams] + [b[1] for b in bolt_beams] \
        + [mid0 + i for i in range(len(bolt_beams))]

    w = open(inp, "w").write
    w("** J4 STS3250 cradle bolt check (V1 task2)\n")
    w("*NODE\n")
    for nid, (x, y, z) in sorted(nodes.items()):
        w("%d, %.6f, %.6f, %.6f\n" % (nid, x, y, z))
    for nh, nt, p1, p2, s1, s2 in bolt_beams:
        w("%d, %.4f, %.4f, %.4f\n" % (nh, p1[0], p1[1], p1[2]))
        w("%d, %.4f, %.4f, %.4f\n" % (nt, p2[0], p2[1], p2[2]))
    w("%d, %.4f, %.4f, %.4f\n" % (load_ref, J4X - D_CM, -20.0, J4Z))
    for i, (nh, nt, p1, p2, s1, s2) in enumerate(bolt_beams):
        w("%d, %.4f, %.4f, %.4f\n"
          % (mid0 + i, *[(a + b) / 2 for a, b in zip(p1, p2)]))
    w("*ELEMENT, TYPE=C3D10, ELSET=EPETG\n")
    for eid, ids in tets:
        w("%d, %s\n" % (eid, ", ".join(str(n) for n in reorder_tet(nodes, ids))))
    w("*ELEMENT, TYPE=B32, ELSET=EBOLT\n")
    for i, (nh, nt, p1, p2, s1, s2) in enumerate(bolt_beams):
        w("%d, %d, %d, %d\n" % (e_bolt0 + i, nh, nt, mid0 + i))

    def wr_nset(nm, ids):
        w("*NSET, NSET=%s\n" % nm)
        ids = sorted(ids)
        for i in range(0, len(ids), 8):
            w(", ".join(str(n) for n in ids[i:i + 8]) + "\n")
    if n_fix:
        wr_nset("N_FIX", n_fix)
    if pk:
        wr_nset("N_PK", pk)
    wr_nset("N_BOLTS", bolt_nodes)
    for nm, faces in sorted(surfs.items()):
        w("*SURFACE, NAME=%s, TYPE=ELEMENT\n" % ("S_" + nm.upper()))
        for te, fno, ids in faces:
            w("%d, S%d\n" % (te, fno))

    w("*MATERIAL, NAME=PETGCF\n*ELASTIC\n%.1f, %.3f\n*DENSITY\n%.4g\n" % PETG)
    w("*MATERIAL, NAME=BOLT\n*ELASTIC\n%.1f, %.3f\n*DENSITY\n7.85e-9\n*EXPANSION\n%.3e\n" % (E_STEEL, 0.29, ALPHA))
    w("*SOLID SECTION, ELSET=EPETG, MATERIAL=PETGCF\n")
    w("*BEAM SECTION, ELSET=EBOLT, MATERIAL=BOLT, SECTION=CIRC\n1.5, 1., 0., 0.\n")
    for nh, nt, p1, p2, s1, s2 in bolt_beams:
        for nn, snm in ((nh, s1), (nt, s2)):
            w("*COUPLING, CONSTRAINT NAME=CP%d, REF NODE=%d, SURFACE=S_%s\n*DISTRIBUTING\n1,3\n"
              % (nn, nn, snm.upper()))
    w("*RIGID BODY, NSET=N_PK, REF NODE=%d\n" % load_ref)
    if surfs.get("cr_face") and surfs.get("fr_face"):
        # preload-clamped face tied directly (4x500N clamp >> service uplift).
        # TIED-contact made 0 springs (surfaces not within its auto-range ->
        # free mechanism); *TIE+tol is safe here - faces are flat plate, not
        # the thin curved pin walls whose snap inverted tets in the cyc model.
        w("*TIE, NAME=T_CRFR, POSITION TOLERANCE=0.5\nS_CR_FACE, S_FR_FACE\n")
    w("*NSET, NSET=NALL, GENERATE\n1, %d\n" % (mid0 + len(bolt_beams) - 1))
    w("*INITIAL CONDITIONS, TYPE=TEMPERATURE\nNALL, 0.\n")
    bcl = "*BOUNDARY\nN_FIX, 1, 3, 0.\n"
    # single combined step: preload (thermal) + service load ramped together -
    # halves the increment count vs the split preload/load sequence
    w("*STEP, NLGEOM\n*STATIC, SOLVER=SPOOLES\n0.2, 1., 1e-6, 0.5\n")
    w(bcl)
    w("*TEMPERATURE\nN_BOLTS, %.3f\n" % (-DT))
    w("*CLOAD\n%d, 3, %.2f\n" % (load_ref, F_LOAD))
    w("*NODE FILE\nU, RF\n*EL FILE\nS\n*CONTACT FILE\nCDIS, CSTR\n*END STEP\n")
    print("%s: %d nodes %d tets | fix %d pk %d" % (inp, max(nodes), len(tets), len(n_fix), len(pk)))
    for nm in sorted(surfs):
        print("  surf %-8s %d faces" % (nm, len(surfs[nm])))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
