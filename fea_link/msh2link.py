"""fea_link/msh2link.py - convert a gmsh v2.2 .msh of link_fea.step to a
CalculiX deck for stage F4 (link alone, real whole-arm loads).

Boundary conditions (numbers from cad/arm2/ap2.py + ap.py and loads.json).
NOTE: link_fea.step contains TWO disjoint solids (upper_out at y -32..-25 and
upper_back + the two back_spacers at y +23..+32); in the real arm the actuator
housings bridge them, so each solid is constrained through its own real mount
faces:
  NFIX : (a) nodes within R_W of each of the 6x M3 hole axes (LINK_PCD 50,
         LINK_N 6, ang0 0) at the J2 end inside the bolt stack
         y in [22.9, 32.6] (back_spacer_j2 23.4..28.1 + upper_back 28.1..32.1)
         -> real hole faces + a washer-sized patch, NOT the whole face;
         (b) the J2 RING_D bore of upper_out (r 28.575, y -33.2..-24.0)
         -> the housing-grip face (upper_out's real J2 mount).
  NLOAD: the same two sets at the J3 end (x +126.7) -> *RIGID BODY to a ref
         node at the downstream centre of action ref_app (loads.json); the
         resultant is applied there as a PURE FORCE - the rigid arm back to
         the J3 bolt faces reproduces the (F, M) wrench exactly.
  The J2-side carried mass (vendor_act_j2 + vendor_6803_j2, 0.3075 kg at
  lever arm ~0 from the J2 axis) reacts at the fixed J2 patches - it adds
  ~0 link stress and is not applied as a separate load (see STATUS).

Steps: AB writes 2 steps (case A 1x, case B 2x).  C writes 1 step (home pose).
Material: PETGCF E=4000 nu=0.35 rho=7.62e-10  |  PLA E=2500 nu=0.35 (pessimistic).

Run:  python3 fea_link/msh2link.py run/link_5_2.msh run/link_5.inp AB PETGCF
"""
import sys, json, math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read_msh(path):
    nodes = {}
    elems = {}          # eid -> (etype, [nids], phys)
    phys_names = {}
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


EDGES = ((0, 1), (1, 2), (0, 2), (0, 3), (1, 3), (2, 3))   # C3D10 midside order


def reorder_tet(nodes, n):
    """Return tet10 connectivity as [c0..c3, m01, m12, m02, m03, m13, m23]
    (CalculiX C3D10 order), positive volume.  Each extra node is assigned to
    the corner edge whose midpoint it is closest to, so no assumption is made
    about the source convention; if the corner orientation is negative, corner
    1<->2 are swapped and the edge map is remapped accordingly."""
    posmap = {0: 0, 1: 1, 2: 2, 3: 3}
    conn = list(n)
    if signed_vol(nodes, conn[:4]) < 0.0:
        conn[1], conn[2] = conn[2], conn[1]
        posmap = {0: 0, 1: 2, 2: 1, 3: 3}      # old corner k sits at pos posmap[k]
    c = [nodes[conn[i]] for i in range(4)]     # coords at new positions 0..3
    mid = {}
    for node_id in n[4:]:
        m = nodes[node_id]
        best, bk = 1e30, None
        for a in range(4):
            for b in range(a + 1, 4):
                pa, pb = posmap[a], posmap[b]  # old corners a,b now sit at pa,pb
                d = sum((m[i] - (c[pa][i] + c[pb][i]) * 0.5) ** 2 for i in range(3))
                if d < best:
                    best, bk = d, (pa, pb)
        mid[bk] = node_id
    return conn[:4] + [mid[e] for e in EDGES]


# ---------------- F4 node-set geometry ----------------
LINK_PCD = 50.0          # 6x M3 bolt circle (ap.py LINK_PCD)
LINK_N = 6
R_W = 3.8                # washer patch radius (M3 washer ~7 / csk 6.4)
Y_STACK = (22.9, 32.6)   # back_spacer (23.4..28.1) + upper_back (28.1..32.1)
UP_SPAN = 126.7
R_BORE = (27.3, 29.9)    # J2 RING_D 57.15 bore (r 28.575) +-1.2
Y_BORE = (-33.2, -24.0)  # upper_out plate + collar at J2

def hole_axes(cx):
    return [(cx + LINK_PCD / 2 * math.cos(math.radians(60 * k)),
             LINK_PCD / 2 * math.sin(math.radians(60 * k))) for k in range(LINK_N)]

def pick_nodes(nodes):
    fix, load = set(), set()
    j2h, j3h = hole_axes(0.0), hole_axes(UP_SPAN)
    for nid, (x, y, z) in nodes.items():
        if Y_STACK[0] <= y <= Y_STACK[1]:
            if any((x - hx) ** 2 + (z - hz) ** 2 <= R_W ** 2 for hx, hz in j2h):
                fix.add(nid); continue
            if any((x - hx) ** 2 + (z - hz) ** 2 <= R_W ** 2 for hx, hz in j3h):
                load.add(nid); continue
        elif Y_BORE[0] <= y <= Y_BORE[1]:
            if R_BORE[0] <= math.hypot(x, z) <= R_BORE[1]:
                fix.add(nid)
            elif R_BORE[0] <= math.hypot(x - UP_SPAN, z) <= R_BORE[1]:
                load.add(nid)
    return fix, load


MATS = {"PETGCF": (4000.0, 0.35), "PLA": (2500.0, 0.35)}
RHO = 7.62e-10           # t/mm3 (1.27 g/cm3 x 0.6 fill, same as parts_AB.json)


def main(msh, inp, case, mat):
    nodes, elems, phys_names = read_msh(msh)
    assert len(nodes) > 0 and len(elems) > 0, "empty mesh: %s" % msh
    loads = json.loads((HERE / "input" / "loads.json").read_text())[case]
    tets = []
    nflipped = 0
    for eid, (etype, nids, phys) in sorted(elems.items()):
        if etype == 11:
            n2 = reorder_tet(nodes, nids)
            nflipped += n2[:4] != nids[:4]
            tets.append((eid, n2))
    fix_ids, load_ids = pick_nodes(nodes)
    assert fix_ids, "NFIX empty - no nodes found on J2 mounts"
    assert load_ids, "NLOAD empty - no nodes found on J3 mounts"
    assert not (fix_ids & load_ids)
    r3 = max(nodes) + 1                    # ref node at the J3 axis
    E, nu = MATS[mat]

    w = open(inp, "w").write
    w("*NODE\n")
    for nid, (x, y, z) in sorted(nodes.items()):
        w("%d, %.6f, %.6f, %.6f\n" % (nid, x, y, z))
    w("%d, %.6f, %.6f, %.6f\n" % ((r3,) + tuple(loads["ref_app"])))
    w("*ELEMENT, TYPE=C3D10, ELSET=EALL\n")
    for eid, nids in tets:
        w("%d, %s\n" % (eid, ", ".join(str(n) for n in nids)))
    def wr_nset(nm, ids):
        w("*NSET, NSET=%s\n" % nm)
        ids = sorted(ids)
        for i in range(0, len(ids), 8):
            w(", ".join(str(n) for n in ids[i:i + 8]) + "\n")
    wr_nset("NFIX", fix_ids); wr_nset("NLOAD", load_ids)
    w("*MATERIAL, NAME=%s\n*ELASTIC\n%.1f, %.3f\n*DENSITY\n%.4g\n" % (mat, E, nu, RHO))
    w("*SOLID SECTION, ELSET=EALL, MATERIAL=%s\n" % mat)
    w("*RIGID BODY, NSET=NLOAD, REF NODE=%d\n" % r3)
    w("*BOUNDARY\nNFIX, 1, 3, 0.\n")
    steps = (("A", 1.0), ("B", 2.0)) if case == "AB" else (("C", 1.0),)
    if mat == "PLA":
        steps = steps[:1]
    for tag, mult in steps:
        gmag = math.sqrt(sum(v * v for v in loads["grav"])) * mult
        gdir = [v * mult / gmag for v in loads["grav"]]
        w("*STEP\n*STATIC\n")
        w("*DLOAD\nEALL, GRAV, %.1f, %.4f, %.4f, %.4f\n" % (gmag, *gdir))
        cl = ""
        for dof, v in sorted(loads["j3_cload"].items(), key=lambda kv: int(kv[0])):
            cl += "%d, %s, %.4f\n" % (r3, dof, v * mult)
        w("*CLOAD\n" + cl)
        w("*NODE FILE\nU, RF\n*EL FILE\nS\n*END STEP\n")
    print("inp %s: %d nodes %d C3D10 (%d reoriented) | NFIX=%d NLOAD=%d "
          "| case=%s mat=%s | ref_J3=%d"
          % (inp, len(nodes), len(tets), nflipped, len(fix_ids), len(load_ids),
             case, mat, r3))
    print("  load ref node at %s" % loads["ref_app"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
