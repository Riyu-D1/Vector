"""verify/code/msh2joint.py - CalculiX deck writer for the bolted whole-joint
models (stage V1 task 2).  Module frame (z = joint axis, z0 = housing back).

Parts (verify/out/msh/jt_<j>_<part>.msh, module frame):
  housing, carrier, out_flange, dowels, front_spacer, link_clip,
  back_spacer, upper_clip
Load path (BOM cad/arm2/BOM.md):
  back stack : 6x M3x10 csk  upper_back -> back_spacer -> housing pilots
  front stack: 3x M3x14/16   link cheek -> front_spacer -> out_flange ->
               carrier inserts + 3x d4 dowels (carrier -> spacer)
  6808 bearing: lumped rigid (carrier spigot + housing seat -> one ref)
Model:
  face contacts S2S hard + friction mu=0.2 [U] on every mating interface
  incl. dowel/hole walls; bolts = B31 beams with thermal preload (-dT);
  bolt ends distributing-coupled to washer patch / pilot wall so the
  hole ligaments stay deformable; wrench applied at a ref coupled to the
  load-side clip far face; fix-side clip cut faces grounded.
Loads (gravity_up1 0.5 kg worst pose x2): J2 M=5130 F=31.0; J3 M=3674 F=23.9.
Run:  python3 msh2joint.py <mshdir> <out.inp> J2|J3
"""
import sys
import math

sys.path.insert(0, "/Users/deepakdiwan/Vector-wt/ver/cad3/fea")
from msh2housing import read_msh, reorder_tet
sys.path.insert(0, "/Users/deepakdiwan/Vector-wt/ver/cad/act2")
import ap

PETG = (4000.0, 0.35, 7.62e-10)
STEEL = (200000.0, 0.29, 7.85e-9)
BOLT_A = math.pi * 1.5 ** 2
PRELOAD_N = 500.0                     # [U] achievable M3 preload
ALPHA = 1.1e-5
DT = PRELOAD_N / (STEEL[0] * BOLT_A * ALPHA)

LINK_AX = [(ap.LINK_PCD / 2 * math.cos(math.radians(60 * k)),
            ap.LINK_PCD / 2 * math.sin(math.radians(60 * k))) for k in range(6)]
M3_AX = [(ap.OUT_M3_PCD / 2 * math.cos(math.radians(a)),
          ap.OUT_M3_PCD / 2 * math.sin(math.radians(a))) for a in ap.OUT_M3_ANG]
DOW_AX = [(ap.OUT_DOWEL_PCD / 2 * math.cos(math.radians(a)),
           ap.OUT_DOWEL_PCD / 2 * math.sin(math.radians(a))) for a in ap.OUT_DOWEL_ANG]

Z_BACK, Z_BSUP, Z_UOUT = 0.0, -4.7, -8.7
Z_OFC = 55.0
# wrench = 2 x (self-weight + 0.5 kg payload at TCP) from gravity_up1 PARTS:
# J2 m=1.581 kg d_cm=212.7 mm -> F=31.0 N M=6.60 N.m
# J3 m=0.916 kg d_cm=194.4 mm -> F=18.0 N M=3.49 N.m
CASES = {
    "J2": dict(F=31.0, D_CM=212.7, Z_FSL=59.0, Z_LOUT=62.0,
               load="upper", fix="link"),
    "J3": dict(F=18.0, D_CM=194.4, Z_FSL=60.0, Z_LOUT=65.0,
               load="link", fix="upper"),
}
PARTS = ["housing", "carrier", "out_flange", "dowels", "front_spacer",
         "link_clip", "back_spacer", "upper_clip"]


def main(mshdir, inp, which):
    ld = CASES[which]
    Z_FSL, Z_LOUT = ld["Z_FSL"], ld["Z_LOUT"]
    nodes, tets, tris, tetpart = {}, [], [], {}
    n0 = e0 = 0
    for part in PARTS:
        n, e, _ = read_msh("%s/jt_%s_%s.msh" % (mshdir, which.lower(), part))
        remap = {}
        for nid, xyz in n.items():
            remap[nid] = nid + n0
            nodes[nid + n0] = xyz
        for eid, (etype, nids, phys) in e.items():
            ids = [remap[i] for i in nids]
            if etype == 11:
                tets.append((eid + e0, ids))
                tetpart[eid + e0] = part
            elif etype in (2, 9):
                tris.append((eid + e0, ids))
        n0 = max(nodes)
        e0 = max(t[0] for t in tets) + 1
    tc = {e: ids[:4] for e, ids in tets}

    FACE_OF = {frozenset((0, 1, 2)): 1, frozenset((0, 1, 3)): 2,
               frozenset((1, 2, 3)): 3, frozenset((0, 2, 3)): 4}
    corner_tets = {}
    for eid, ids in tets:
        c = ids[:4]
        for fs in FACE_OF:
            corner_tets[frozenset(c[i] for i in fs)] = eid
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
        c = ids[:3]
        xs = [nodes[i] for i in c]
        zl = [x[2] for x in xs]
        rr = [math.hypot(x[0], x[1]) for x in xs]
        vert = max(zl) - min(zl) > 0.25
        cx, cy, cz = (sum(q) / 3.0 for q in zip(*xs))
        if p == "housing":
            if not vert and max(zl) < 0.2 and max(rr) < 29.0:
                add("h_back", face(eid, ids))
            elif vert and all(abs(r - 26.05) < 0.4 for r in rr) and min(zl) > 45.0:
                add("h_seat", face(eid, ids))
            elif vert and min(zl) > -0.2 and max(zl) < 3.6:
                for k, (ax, ay) in enumerate(LINK_AX):
                    if all((x - ax) ** 2 + (y - ay) ** 2 < 1.6 ** 2 for x, y, z in xs):
                        add("pilot%d" % k, face(eid, ids))
        elif p == "carrier":
            if vert and all(abs(r - 19.97) < 0.4 for r in rr) and min(zl) > 45.0:
                add("c_spig", face(eid, ids))
            elif not vert and min(zl) > 52.15 and max(zl) < 52.6 and max(rr) < 20.5:
                add("c_top", face(eid, ids))
            elif vert and min(zl) > 45.9:
                for k, (ax, ay) in enumerate(M3_AX):
                    if all((x - ax) ** 2 + (y - ay) ** 2 < 2.6 ** 2 for x, y, z in xs):
                        add("ins%d" % k, face(eid, ids))
                for k, (ax, ay) in enumerate(DOW_AX):
                    if all((x - ax) ** 2 + (y - ay) ** 2 < 2.4 ** 2 for x, y, z in xs):
                        add("cdow%d" % k, face(eid, ids))
        elif p == "back_spacer":
            if not vert and min(zl) > -0.4:
                add("bs_up", face(eid, ids))
            elif not vert and max(zl) < -4.3:
                add("bs_dn", face(eid, ids))
        elif p == "upper_clip":
            if not vert and abs(cz - Z_BSUP) < 0.4:
                add("uc_dn", face(eid, ids))
            if min(zl) < Z_UOUT + 0.15:
                for k, (ax, ay) in enumerate(LINK_AX):
                    if all((x - ax) ** 2 + (y - ay) ** 2 < 3.4 ** 2 for x, y, z in xs):
                        add("uwash%d" % k, face(eid, ids))
            if which == "J2" and all(x[0] > 54.5 for x in xs):
                add("u_far", face(eid, ids))
            if which == "J3" and all(x[0] < -24.9 for x in xs):
                add("u_fix", face(eid, ids))
        elif p == "out_flange":
            if not vert and min(zl) > Z_OFC - 0.3:
                add("of_up", face(eid, ids))
            elif not vert and abs(cz - 52.4) < 0.3:
                add("of_dn", face(eid, ids))
            elif vert:
                for k, (ax, ay) in enumerate(DOW_AX):
                    if all((x - ax) ** 2 + (y - ay) ** 2 < 2.4 ** 2 for x, y, z in xs):
                        add("ofdow%d" % k, face(eid, ids))
        elif p == "front_spacer":
            if not vert and abs(cz - Z_OFC) < 0.3:
                add("fs_dn", face(eid, ids))
            elif not vert and abs(cz - Z_FSL) < 0.4:
                add("fs_up", face(eid, ids))
            elif vert:
                for k, (ax, ay) in enumerate(DOW_AX):
                    if all((x - ax) ** 2 + (y - ay) ** 2 < 2.5 ** 2 for x, y, z in xs):
                        add("fsdow%d" % k, face(eid, ids))
        elif p == "link_clip":
            if not vert and abs(cz - Z_FSL) < 0.4 and max(rr) < 30.0:
                add("lk_dn", face(eid, ids))
            if min(zl) > Z_LOUT - 0.25:
                for k, (ax, ay) in enumerate(M3_AX):
                    if all((x - ax) ** 2 + (y - ay) ** 2 < 3.4 ** 2 for x, y, z in xs):
                        add("lwash%d" % k, face(eid, ids))
            if which == "J3" and all(x[0] > 22.0 for x in xs):
                add("lk_far", face(eid, ids))
            if which == "J2" and (all(abs(x[0]) > 29.9 for x in xs)
                                  or all(abs(x[1]) > 29.9 for x in xs)):
                add("lk_fix", face(eid, ids))
        elif p == "dowels":
            if vert:
                k = min(range(3), key=lambda i: (cx - DOW_AX[i][0]) ** 2 + (cy - DOW_AX[i][1]) ** 2)
                if cz < 52.35:
                    add("dpr%d" % k, face(eid, ids))
                elif cz < 54.95:
                    add("dof%d" % k, face(eid, ids))
                else:
                    add("dfs%d" % k, face(eid, ids))

    # nset = all surface-tri nodes (corners + mid-edge)
    def surf_nodes(nm):
        s = set()
        for te, fno, ids in surfs.get(nm, []):
            s.update(ids)
        return s

    n_fix = surf_nodes("lk_fix" if ld["fix"] == "link" else "u_fix")
    n_brg = surf_nodes("h_seat") | surf_nodes("c_spig")
    dow_n = {}
    for eid, ids in tris:
        if tri_owner.get(eid) != "dowels":
            continue
        c = ids[:3]
        k = min(range(3), key=lambda i: (nodes[c[0]][0] - DOW_AX[i][0]) ** 2
               + (nodes[c[0]][1] - DOW_AX[i][1]) ** 2)
        dow_n.setdefault(k, set()).update(ids)
    stab = []
    for k, lst in dow_n.items():
        seen = sorted(lst)
        stab += [seen[0], seen[len(seen) // 2]]

    # ---- bolt beams ----
    ref0 = max(nodes) + 1
    bolt_beams = []          # (n_head, n_tip, p_head, p_tip, surf_head, surf_tip)
    nb = 0
    for k, (ax, ay) in enumerate(LINK_AX):
        bolt_beams.append((ref0 + nb, ref0 + nb + 1, (ax, ay, Z_UOUT - 1.0),
                           (ax, ay, 1.8), "uwash%d" % k, "pilot%d" % k)); nb += 2
    for k, (ax, ay) in enumerate(M3_AX):
        bolt_beams.append((ref0 + nb, ref0 + nb + 1, (ax, ay, Z_LOUT + 1.0),
                           (ax, ay, 47.0), "lwash%d" % k, "ins%d" % k)); nb += 2
    brg_ref = ref0 + nb
    load_ref = brg_ref + 1
    gnd0 = load_ref + 1
    mid0 = gnd0 + 2 * len(stab)
    d_app = ld["D_CM"]
    zref = (Z_UOUT + Z_BSUP) / 2 if ld["load"] == "upper" else (Z_FSL + Z_LOUT) / 2
    e_bolt0 = max(t[0] for t in tets) + 1
    bolt_nodes = [b[0] for b in bolt_beams] + [b[1] for b in bolt_beams] \
        + [mid0 + i for i in range(len(bolt_beams))]

    w = open(inp, "w").write
    w("** bolted joint %s  (V1 task2)\n" % which)
    w("*NODE\n")
    for nid, (x, y, z) in sorted(nodes.items()):
        w("%d, %.6f, %.6f, %.6f\n" % (nid, x, y, z))
    for nh, nt, p1, p2, s1, s2 in bolt_beams:
        w("%d, %.4f, %.4f, %.4f\n" % (nh, p1[0], p1[1], p1[2]))
        w("%d, %.4f, %.4f, %.4f\n" % (nt, p2[0], p2[1], p2[2]))
    w("%d, 0., 0., 48.9\n" % brg_ref)
    w("%d, %.4f, 0., %.4f\n" % (load_ref, d_app, zref))
    for i in range(2 * len(stab)):
        w("%d, 0., 0., 0.\n" % (gnd0 + i))
    for i, (nh, nt, p1, p2, s1, s2) in enumerate(bolt_beams):
        w("%d, %.4f, %.4f, %.4f\n"
          % (mid0 + i, *[(a + b) / 2 for a, b in zip(p1, p2)]))
    w("*ELEMENT, TYPE=C3D10, ELSET=EPETG\n")
    for eid, ids in tets:
        if tetpart[eid] != "dowels":
            w("%d, %s\n" % (eid, ", ".join(str(n) for n in reorder_tet(nodes, ids))))
    w("*ELEMENT, TYPE=C3D10, ELSET=EDOWEL\n")
    for eid, ids in tets:
        if tetpart[eid] == "dowels":
            w("%d, %s\n" % (eid, ", ".join(str(n) for n in reorder_tet(nodes, ids))))
    w("*ELEMENT, TYPE=B32, ELSET=EBOLT\n")
    for i, (nh, nt, p1, p2, s1, s2) in enumerate(bolt_beams):
        w("%d, %d, %d, %d\n" % (e_bolt0 + i, nh, nt, mid0 + i))
    w("*ELEMENT, TYPE=SPRING2, ELSET=ESPR\n")
    for i, nid in enumerate(stab):
        w("%d, %d, %d, 1\n" % (e_bolt0 + len(bolt_beams) + 2 * i, nid, gnd0 + 2 * i))
        w("%d, %d, %d, 2\n" % (e_bolt0 + len(bolt_beams) + 2 * i + 1, nid, gnd0 + 2 * i + 1))

    def wr_nset(nm, ids):
        w("*NSET, NSET=%s\n" % nm)
        ids = sorted(ids)
        for i in range(0, len(ids), 8):
            w(", ".join(str(n) for n in ids[i:i + 8]) + "\n")
    if n_fix:
        wr_nset("N_FIX", n_fix)
    if n_brg:
        wr_nset("N_BRG", n_brg)
    wr_nset("N_BOLTS", bolt_nodes)
    for nm, faces in sorted(surfs.items()):
        w("*SURFACE, NAME=%s, TYPE=ELEMENT\n" % ("S_" + nm.upper()))
        for te, fno, ids in faces:
            w("%d, S%d\n" % (te, fno))

    w("*MATERIAL, NAME=PETGCF\n*ELASTIC\n%.1f, %.3f\n*DENSITY\n%.4g\n" % PETG)
    w("*MATERIAL, NAME=STEEL\n*ELASTIC\n%.1f, %.3f\n*DENSITY\n%.4g\n" % STEEL)
    w("*MATERIAL, NAME=BOLT\n*ELASTIC\n%.1f, %.3f\n*DENSITY\n%.4g\n*EXPANSION\n%.3e\n" % (STEEL[0], STEEL[1], STEEL[2], ALPHA))
    w("*SOLID SECTION, ELSET=EPETG, MATERIAL=PETGCF\n")
    w("*SOLID SECTION, ELSET=EDOWEL, MATERIAL=STEEL\n")
    w("*BEAM SECTION, ELSET=EBOLT, MATERIAL=BOLT, SECTION=CIRC\n1.5, 1., 0., 0.\n")
    w("*SPRING, ELSET=ESPR\n0.5\n")

    for nh, nt, p1, p2, s1, s2 in bolt_beams:
        for nn, snm in ((nh, s1), (nt, s2)):
            w("*COUPLING, CONSTRAINT NAME=CP%d, REF NODE=%d, SURFACE=S_%s\n*DISTRIBUTING\n1,3\n"
              % (nn, nn, snm.upper()))
    far = "u_far" if ld["load"] == "upper" else "lk_far"
    w("*COUPLING, CONSTRAINT NAME=CLOADF, REF NODE=%d, SURFACE=S_%s\n*DISTRIBUTING\n1,3\n"
      % (load_ref, far.upper()))
    w("*RIGID BODY, NSET=N_BRG, REF NODE=%d\n" % brg_ref)

    # flat bolted faces are preload-clamped -> *TIE (guaranteed, cheap);
    # the small pilot/dowel shear interfaces keep real hard contact.
    flats = [("bs_up", "h_back"), ("uc_dn", "bs_dn"), ("of_dn", "c_top"),
             ("fs_dn", "of_up"), ("lk_dn", "fs_up")]
    small = []
    for k in range(3):
        small += [("dpr%d" % k, "cdow%d" % k), ("dof%d" % k, "ofdow%d" % k),
                  ("dfs%d" % k, "fsdow%d" % k)]
    flats = [(a, b) for a, b in flats if surfs.get(a) and surfs.get(b)]
    small = [(a, b) for a, b in small if surfs.get(a) and surfs.get(b)]
    for i, (a, b) in enumerate(flats):
        w("*TIE, NAME=TF%d, POSITION TOLERANCE=0.5\nS_%s, S_%s\n" % (i, a.upper(), b.upper()))
    w("*SURFACE INTERACTION, NAME=CT\n*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=HARD\n*FRICTION\n0.2\n")
    for a, b in small:
        w("*CONTACT PAIR, INTERACTION=CT, TYPE=SURFACE TO SURFACE\nS_%s, S_%s\n" % (a.upper(), b.upper()))

    w("*NSET, NSET=NALL, GENERATE\n1, %d\n" % (mid0 + len(bolt_beams) - 1))
    w("*INITIAL CONDITIONS, TYPE=TEMPERATURE\nNALL, 0.\n")
    bcl = "*BOUNDARY\nN_FIX, 1, 3, 0.\n" + "".join(
        "%d, 1, 3, 0.\n" % (gnd0 + i) for i in range(2 * len(stab)))
    for step, cload in ((1, False), (2, True)):
        w("*STEP, NLGEOM\n*STATIC, SOLVER=ITERATIVE CHOLESKY\n0.2, 1., 1e-6, 0.5\n")
        w(bcl)
        w("*TEMPERATURE\nN_BOLTS, %.3f\n" % (-DT))
        if cload:
            w("*CLOAD\n%d, 2, %.2f\n" % (load_ref, -ld["F"]))
        w("*NODE FILE\nU, RF\n*EL FILE\nS\n*CONTACT FILE\nCDIS, CSTR\n*END STEP\n")
    print("%s: %d nodes %d tets | fix %d brg %d | pairs %d"
          % (inp, max(nodes), len(tets), len(n_fix), len(n_brg), len(flats) + len(small)))
    for nm in sorted(surfs):
        print("  surf %-8s %d faces" % (nm, len(surfs[nm])))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3].upper())
