"""cad3/fea/msh2cradle.py - convert a gmsh v2.2 .msh of input/j4_cradle.step to a
CalculiX deck for stage D2 (J4 bracket with STS3250, real bolt holes).

Mesh frame = A2b home pose (arm frame): J4 servo horn axis = +Y through
(96.4, -, 216.2); wrist hangs +X; gravity -Z.  Cradle geometry posed from
p_arm2b.j4_cradle() (W frame -> rest -> pose J3 -90).

BCs:
  NFIX : nodes within R_W of each of the 4 cradle bolt axes (J4_BOLTS, d2.5
         pilots, axes +Y, posed positions x in {43.7, 61.7}, z in {33.1, 55.1},
         y in [24.0, 33.6]) - the real bolt holes into fore_r2 (washer patches,
         no preload - stated approximation).
  NLOAD: nodes inside the servo pocket (posed STS3250 case box + 0.3 margin:
         x 61.0..106.8, y -26.4..23.5, z 203.5..228.9) - the pocket wall nodes
         the servo case bears on -> *RIGID BODY to a ref node at the centre of
         action (d_app mm +X of the J4 axis at the pocket's y/z centroid).
         The (F, M) wrench is applied there as a PURE FORCE.
Loads (upgrade1/gravity_up1.py, 0.5 kg, worst-pose J4 torque, x2 dynamic):
  M = 1602 N.mm about +Y (J4 torque 0.801 x2); F = 16.1 N down
  (wrist4+wrist5+grip+payload = 0.746 kg + servo 0.0745 kg in the pocket, x2).
Material: PETG-CF E=4000 nu=0.35 rho=7.62e-10 t/mm3.

Run:  python3 msh2cradle.py run/cradle_3_1.5.msh run/cradle.inp
"""
import sys, math
from msh2housing import read_msh, reorder_tet

# ---------------- cradle BC geometry (posed frame) ----------------
BOLT_XZ = ((68.4, 225.2), (90.4, 225.2), (68.4, 207.2), (90.4, 207.2))
R_W = 3.8
Y_BOLT = (24.0, 33.6)
POCKET = (61.0, 106.8, -26.4, 23.5, 203.5, 228.9)   # x0 x1 y0 y1 z0 z1
J4_X = 96.4
M_NMM = 1602.0
F_N = 16.1
MAT_E, MAT_NU, RHO = 4000.0, 0.35, 7.62e-10


def pick_nodes(nodes):
    fix, load = set(), set()
    for nid, (x, y, z) in nodes.items():
        if Y_BOLT[0] <= y <= Y_BOLT[1] and \
                any((x - hx) ** 2 + (z - hz) ** 2 <= R_W ** 2 for hx, hz in BOLT_XZ):
            fix.add(nid); continue
        if POCKET[0] <= x <= POCKET[1] and POCKET[2] <= y <= POCKET[3] and POCKET[4] <= z <= POCKET[5]:
            load.add(nid)
    return fix, load


def main(msh, inp):
    nodes, elems, _ = read_msh(msh)
    assert len(nodes) > 0 and len(elems) > 0, "empty mesh: %s" % msh
    tets, nflipped = [], 0
    for eid, (etype, nids, phys) in sorted(elems.items()):
        if etype == 11:
            n2 = reorder_tet(nodes, nids)
            nflipped += n2[:4] != nids[:4]
            tets.append((eid, n2))
    fix_ids, load_ids = pick_nodes(nodes)
    assert fix_ids, "NFIX empty - no nodes on cradle bolt holes"
    assert load_ids, "NLOAD empty - no nodes in servo pocket"
    assert not (fix_ids & load_ids)
    # pocket centroid (of NLOAD nodes) for the ref node's y/z
    ly = sorted(load_ids)
    cy = sum(nodes[n][1] for n in ly) / len(ly)
    cz = sum(nodes[n][2] for n in ly) / len(ly)
    ref = max(nodes) + 1
    rx = J4_X + M_NMM / F_N
    w = open(inp, "w").write
    w("*NODE\n")
    for nid, (x, y, z) in sorted(nodes.items()):
        w("%d, %.6f, %.6f, %.6f\n" % (nid, x, y, z))
    w("%d, %.6f, %.6f, %.6f\n" % (ref, rx, cy, cz))
    w("*ELEMENT, TYPE=C3D10, ELSET=EALL\n")
    for eid, nids in tets:
        w("%d, %s\n" % (eid, ", ".join(str(n) for n in nids)))
    def wr_nset(nm, ids):
        w("*NSET, NSET=%s\n" % nm)
        ids = sorted(ids)
        for i in range(0, len(ids), 8):
            w(", ".join(str(n) for n in ids[i:i + 8]) + "\n")
    wr_nset("NFIX", fix_ids); wr_nset("NLOAD", load_ids)
    w("*MATERIAL, NAME=PETGCF\n*ELASTIC\n%.1f, %.3f\n*DENSITY\n%.4g\n" % (MAT_E, MAT_NU, RHO))
    w("*SOLID SECTION, ELSET=EALL, MATERIAL=PETGCF\n")
    w("*RIGID BODY, NSET=NLOAD, REF NODE=%d\n" % ref)
    w("*BOUNDARY\nNFIX, 1, 3, 0.\n")
    w("*STEP\n*STATIC\n")
    w("*DLOAD\nEALL, GRAV, %.1f, %.4f, %.4f, %.4f\n" % (9810.0, 0.0, 0.0, -1.0))
    w("*CLOAD\n%d, 3, %.4f\n" % (ref, -F_N))
    w("*NODE FILE\nU, RF\n*EL FILE\nS\n*END STEP\n")
    print("inp %s: %d nodes %d C3D10 (%d reoriented) | NFIX=%d NLOAD=%d | cradle"
          % (inp, len(nodes), len(tets), nflipped, len(fix_ids), len(load_ids)))
    print("  M %.0f N.mm  F %.1f N  ref=(%.1f, %.1f, %.1f)" % (M_NMM, F_N, rx, cy, cz))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
