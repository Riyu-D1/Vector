"""cad3/fea/msh2housing.py - convert a gmsh v2.2 .msh of input/housing.step to a
CalculiX deck for stage D2 (J2 / J3 actuator housing, real bolt holes).

BCs (act2 module frame: origin = back-face centre, +Z toward output face):
  NFIX : nodes within R_PIN of each of the NP=41 ring-pin bore axes (R=23.5,
         pin groove d 3.05), z in [33.4, 43.6] - the cycloid reaction path:
         the ring pins stand in these bores and react the output torque onto
         the housing body (spread contact, no bolt preload - stated approx).
  NLOAD: nodes within R_W of each of the 6x back-pilot axes (LINK_PCD 50,
         LINK_N 6, ang0 0, pilot d2.5), z in [-0.1, 3.5] - where the arm's
         back_spacer/upper_back bolts land on the housing back face.
         -> *RIGID BODY to a ref node at the downstream centre of action
         (d_app mm along +X, at the patch mid-z).  The (F, M) wrench is
         applied there as a PURE FORCE (same trick as fea_link).
Loads (upgrade1/gravity_up1.py, 0.5 kg, worst-pose joint torque, x2 dynamic):
  J2: sprung net J2 torque 2.52 N.m (spring bypasses the actuator path)
      -> M = 5040 N.mm, F = 31.0 N (carried 1.281 kg incl. J2 internals lumped
      at the pilots; on-axis -> moment ~0, adds shear only)
  J3: unsprung J3 torque 1.837 N.m worst pose (J3 spring direction/pose not
      confirmed at the worst pose -> conservative)
      -> M = 3674 N.mm, F = 23.9 N (carried 0.916 kg + internals 0.300)
Material: PETG-CF E=4000 nu=0.35 rho=7.62e-10 t/mm3 (fea_link convention).

Run:  python3 msh2housing.py run/housing_4_2.msh run/housing_J2.inp J2
"""
import sys, math

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
    (CalculiX C3D10 order), positive volume."""
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
    used = set(mid.values())                     # D2: sliver-tet fallback - an edge left
    for e in EDGES:                              # unfilled takes the nearest spare midside
        if e not in mid:
            best, bn = 1e30, None
            for node_id in n[4:]:
                if node_id in used:
                    continue
                m = nodes[node_id]
                d = sum((m[i] - (c[e[0]][i] + c[e[1]][i]) * 0.5) ** 2 for i in range(3))
                if d < best:
                    best, bn = d, node_id
            mid[e] = bn
            used.add(bn)
    return conn[:4] + [mid[e] for e in EDGES]


# ---------------- housing BC geometry (act2 module frame, ap.py) ----------------
LINK_PCD = 50.0; LINK_N = 6; LINK_ANG0 = 0.0
R_W = 3.8                    # washer patch radius on the back pilots
Z_PILOT = (-0.1, 3.5)
RING_R = 23.5; RING_NP = 41  # N=40 -> NP=41 ring pins (ap.py via cyc.gear)
PIN_WALL = 1.62              # pin-bore wall radius band (bore d 3.05)


def pick_nodes(nodes, elems, pin_tag):
    fix, load = set(), set()
    # NFIX = nodes of the tagged 'pinbores' surface elements near a bore wall
    pins = [(RING_R * math.cos(math.radians(360.0 * k / RING_NP)),
             RING_R * math.sin(math.radians(360.0 * k / RING_NP))) for k in range(RING_NP)]
    cand = set()
    for eid, (etype, nids, phys) in elems.items():
        if etype in (2, 9) and phys == pin_tag:
            cand.update(nids)
    for nid in cand:
        x, y, z = nodes[nid]
        if any((x - hx) ** 2 + (y - hy) ** 2 <= PIN_WALL ** 2 for hx, hy in pins):
            fix.add(nid)
    pilots = [(LINK_PCD / 2 * math.cos(math.radians(LINK_ANG0 + 60 * k)),
               LINK_PCD / 2 * math.sin(math.radians(LINK_ANG0 + 60 * k))) for k in range(LINK_N)]
    for nid, (x, y, z) in nodes.items():
        if Z_PILOT[0] <= z <= Z_PILOT[1]:
            if any((x - hx) ** 2 + (y - hy) ** 2 <= R_W ** 2 for hx, hy in pilots):
                load.add(nid)
    return fix, load

CASES = {
    # M = gravity_up1.py tau @ Q_WORST, 0.5 kg payload, x2 dynamic factor.
    # F = downstream mass (incl. 0.5 kg payload, actuator module counted in
    # its own body block) x 9.81 x 2.  z = pilot patch centroid for the
    # moment-equivalent reference point (module frame z0 = back face).
    #            M (N.mm)   F (N)    z of the load patch centroid
    "J2": dict(M=5130.0, F=31.0, z=1.6),  # 2.565 Nm x2; downstream 1.581 kg
    "J3": dict(M=3674.0, F=23.9, z=1.6),  # ROM-max 1.837 x2 (>reach 1.778,
                                          # conservative); F incl module
}
MATS = {"PETGCF": (4000.0, 0.35)}
RHO = 7.62e-10


def main(msh, inp, case):
    nodes, elems, phys_names = read_msh(msh)
    pin_tag = next(t for (d, t), n in phys_names.items() if n == "pinbores")
    assert len(nodes) > 0 and len(elems) > 0, "empty mesh: %s" % msh
    ld = CASES[case]
    tets, nflipped = [], 0
    for eid, (etype, nids, phys) in sorted(elems.items()):
        if etype == 11:
            n2 = reorder_tet(nodes, nids)
            nflipped += n2[:4] != nids[:4]
            tets.append((eid, n2))
    fix_ids, load_ids = pick_nodes(nodes, elems, pin_tag)
    assert fix_ids, "NFIX empty - no nodes on ring-pin bores"
    assert load_ids, "NLOAD empty - no nodes on back pilots"
    assert not (fix_ids & load_ids)
    ref = max(nodes) + 1
    d_app = ld["M"] / ld["F"]                       # centre of action along +X
    rx, ry, rz = d_app, 0.0, ld["z"]
    E, nu = MATS["PETGCF"]

    w = open(inp, "w").write
    w("*NODE\n")
    for nid, (x, y, z) in sorted(nodes.items()):
        w("%d, %.6f, %.6f, %.6f\n" % (nid, x, y, z))
    w("%d, %.6f, %.6f, %.6f\n" % (ref, rx, ry, rz))
    w("*ELEMENT, TYPE=C3D10, ELSET=EALL\n")
    for eid, nids in tets:
        w("%d, %s\n" % (eid, ", ".join(str(n) for n in nids)))
    def wr_nset(nm, ids):
        w("*NSET, NSET=%s\n" % nm)
        ids = sorted(ids)
        for i in range(0, len(ids), 8):
            w(", ".join(str(n) for n in ids[i:i + 8]) + "\n")
    wr_nset("NFIX", fix_ids); wr_nset("NLOAD", load_ids)
    w("*MATERIAL, NAME=PETGCF\n*ELASTIC\n%.1f, %.3f\n*DENSITY\n%.4g\n" % (E, nu, RHO))
    w("*SOLID SECTION, ELSET=EALL, MATERIAL=PETGCF\n")
    w("*RIGID BODY, NSET=NLOAD, REF NODE=%d\n" % ref)
    w("*BOUNDARY\nNFIX, 1, 3, 0.\n")
    w("*STEP\n*STATIC\n")
    w("*DLOAD\nEALL, GRAV, %.1f, %.4f, %.4f, %.4f\n" % (9810.0, 0.0, -1.0, 0.0))
    w("*CLOAD\n%d, 2, %.4f\n" % (ref, -ld["F"]))
    w("*NODE FILE\nU, RF\n*EL FILE\nS\n*END STEP\n")
    print("inp %s: %d nodes %d C3D10 (%d reoriented) | NFIX=%d NLOAD=%d | case=%s"
          % (inp, len(nodes), len(tets), nflipped, len(fix_ids), len(load_ids), case))
    print("  M %.0f N.mm  F %.1f N  ref=(%.1f, %.1f, %.1f)" % (ld["M"], ld["F"], rx, ry, rz))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
