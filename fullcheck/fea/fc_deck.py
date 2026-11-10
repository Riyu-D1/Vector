"""fullcheck/fea/fc_deck.py - bolted/pinned-BC CalculiX deck generator for
the arm-fullfix per-part SF2 study.

Replaces the genlinks "r<31.5 face patch" NFIX/NLOAD with REAL fastener and
contact surfaces extracted from the part STEPs:

  NFIX  = bolt-hole wall nodes (pinned - shear through the shanks) plus
          washer-land nodes within WASHER_R of each bolt centre on the
          clamped face (models head/nut bearing + preload contact).
  NLOAD = the downstream interface's REAL contact surfaces (bolt-hole
          walls, bearing/ring seats, clamp lands) tied to a *RIGID BODY
          ref node at the joint point; the (F, M) wrench is applied as
          CLOAD dofs 1-6 on the ref node (rigid-body ref nodes accept
          moments).

Selectors on mesh nodes (P = Nx3 node coords):
  bore(c, d, rho, dz): dist-to-axis in [rho-dz, rho+dz] - hole wall band
  face(c, n, s, r):    on the plane n.p=s within radius r of c - clamp land
  ring(c, d, r, tol):  cylindrical surface band radius r around axis d
  ball(c, r):          inside radius r
  box(lo, hi):         inside an AABB
  cyl(c, d, r0, r1):   radial band [r0, r1] about axis (annular face/patch)

Specs are lists of selectors; NFIX/NLOAD = union of each side's list.

Run: python3 fc_deck.py <part>.msh <part>.inp <part> loads.json
"""
import os, sys, json, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


# ---- mesh helpers (verbatim from lighten/fea/msh2gen.py - kept local so
#      no loads.json dependency) ---------------------------------------
def read_msh(path):
    nodes, elems, phys_names = {}, {}, {}
    with open(path) as f:
        lines = [l.strip() for l in f]
    i = 0
    while i < len(lines):
        l = lines[i]
        if l == "$PhysicalNames":
            n = int(lines[i + 1]); i += 2
            for k in range(n):
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
                nids = [int(t) for t in p[3 + ntags:]]
                elems[eid] = (etype, nids, 0)
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


EDGES = ((0, 1), (1, 2), (0, 2), (0, 3), (1, 3), (2, 3))


def reorder_tet(nodes, n):
    posmap = {0: 0, 1: 1, 2: 2, 3: 3}
    conn = list(n)
    if signed_vol(nodes, conn[:4]) < 0.0:
        conn[1], conn[2] = conn[2], conn[1]
        posmap = {0: 0, 1: 2, 2: 1, 3: 3}
    c = [nodes[conn[i]] for i in range(4)]
    mid = {}
    for node_id in n[4:]:
        m = nodes[node_id]
        best, bk = 1e30, None
        for a in range(4):
            for b in range(a + 1, 4):
                pa, pb = posmap[a], posmap[b]
                d = sum((m[i] - (c[pa][i] + c[pb][i]) * 0.5) ** 2 for i in range(3))
                if d < best:
                    best, bk = d, (pa, pb)
        mid[bk] = node_id
    used = set(mid.values())
    for e in EDGES:
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


def _dN(xi):
    x, y, z = xi
    L = [1 - x - y - z, x, y, z]
    dL = [[-1, -1, -1], [1, 0, 0], [0, 1, 0], [0, 0, 1]]
    out = [[(4 * L[i] - 1) * dL[i][j] for j in range(3)] for i in range(4)]
    for a, b in [(0, 1), (1, 2), (0, 2), (0, 3), (1, 3), (2, 3)]:
        out.append([4 * (L[a] * dL[b][j] + L[b] * dL[a][j])
                    for j in range(3)])
    return np.array(out)


_A, _B = 0.58541020, 0.13819660
_GAUSS = [(g[1], g[2], g[3])
          for g in ((_A, _B, _B, _B), (_B, _A, _B, _B),
                    (_B, _B, _A, _B), (_B, _B, _B, _A))]


def gauss_min_det(nodes, n):
    pts = np.array([nodes[i] for i in n])
    return min(float(np.linalg.det(_dN(g).T @ pts)) for g in _GAUSS)

J1 = np.array([0.0, 0.0, 80.8]); J2 = np.array([-20.0, 0.0, 143.5])
J3 = np.array([-20.0, 0.0, 270.2]); J4 = np.array([96.4, 0.0, 216.2])
X = np.array([1.0, 0, 0]); Y = np.array([0.0, 1.0, 0]); Z = np.array([0.0, 0, 1.0])
WASHER_R = 4.5          # M3 washer land reach (ISO 7380 head ~5.5 + margin)


# ---------- selectors ----------
def _dist_ax(P, c, d):
    v = P - np.asarray(c, float)
    d = np.asarray(d, float)
    t = v @ d
    pr = v - np.outer(t, d)
    return np.linalg.norm(pr, axis=1), t

def bore(c, d, rho, tol=0.9):
    def f(P):
        r, _ = _dist_ax(P, c, d)
        return (r >= rho - tol) & (r <= rho + tol)
    return f

def land(c, d, rho, r_ext=WASHER_R, tol=0.9, t0=None, half=None):
    """hole wall + washer land: radial band rho-tol .. r_ext of the bolt
    axis (covers wall nodes and the clamped face nodes near the head).
    Optional axial window |t-t0|<=half bounds the patch along the axis."""
    def f(P):
        r, t = _dist_ax(P, c, d)
        m = (r >= rho - tol) & (r <= r_ext)
        if t0 is not None:
            m &= np.abs(t - t0) <= half
        return m
    return f

def ring(c, d, r, tol=1.0, half=None):
    """annular patch at radius r; optional axial window |t|<=half around
    the plane through c (c sits ON the plane)."""
    def f(P):
        rr, t = _dist_ax(P, c, d)
        m = np.abs(rr - r) <= tol
        if half is not None:
            m &= np.abs(t) <= half
        return m
    return f

def face_plane(c, d, s, r0, r1):
    """nodes within dz of plane d.p=s and radial band [r0,r1] of c."""
    def f(P):
        v = P - np.asarray(c, float)
        dd = np.asarray(d, float)
        t = v @ dd - s
        pr = v - np.outer(v @ dd, dd)
        rr = np.linalg.norm(pr, axis=1)
        return (np.abs(t) <= 0.8) & (rr >= r0) & (rr <= r1)
    return f

def cyl(c, d, r0, r1):
    def f(P):
        rr, _ = _dist_ax(P, c, d)
        return (rr >= r0) & (rr <= r1)
    return f

def box(lo, hi):
    lo, hi = np.asarray(lo), np.asarray(hi)
    def f(P):
        return np.all(P >= lo, 1) & np.all(P <= hi, 1)
    return f

def AND(*fs):
    def f(P):
        m = fs[0](P)
        for g in fs[1:]:
            m &= g(P)
        return m
    return f

def OR(*fs):
    def f(P):
        m = fs[0](P)
        for g in fs[1:]:
            m |= g(P)
        return m
    return f


# ---------- bolt patterns (measured on the STEPs, see arm-fullfix notes) --
def pcd(cx, cy, cz, r, n, a0=0.0, plane="xz"):
    """n bolt centres on a circle in the given plane."""
    out = []
    for k in range(n):
        a = math.radians(a0 + 360.0 * k / n)
        if plane == "xz":
            out.append((cx + r * math.cos(a), cy, cz + r * math.sin(a)))
        elif plane == "xy":
            out.append((cx + r * math.cos(a), cy + r * math.sin(a), cz))
    return out

# J1 output flange: 6x M3 PCD27 at z~89.5 (link1 bottom) - measured
J1_BOLTS = pcd(0, 0, 89.5, 13.5, 6, a0=0, plane="xy")
# J1 horn: 4x M3 PCD14 at z~79.8 (yaw_limit to horn)
J1_HORN = pcd(0, 0, 80.8, 7.0, 4, a0=0, plane="xy")
# J2 link bolts: 6x M3 PCD27 on EACH link1 cheek y=+-37.1 (measured a0=60)
J2_BOLTS_L = pcd(J2[0], -37.1, J2[2], 13.5, 6, a0=60)
J2_BOLTS_R = pcd(J2[0], 37.1, J2[2], 13.5, 6, a0=60)
# J3 link bolts: 6x M3 PCD27 on each dogleg cheek (measured a0=60)
J3_BOLTS_L = pcd(J3[0], -39.1, J3[2], 13.5, 6, a0=60)
J3_BOLTS_R = pcd(J3[0], 39.1, J3[2], 13.5, 6, a0=60)
# module back-screw pattern: 6x csk PCD50 per joint end (measured a0=90)
J2_CSK = pcd(J2[0], 27.1, J2[2], 25.0, 6, a0=90)
J3_CSK = pcd(J3[0], 27.1, J3[2], 25.0, 6, a0=90)
# dogleg<->fore shared screws at the J4-end cluster (r1.5, diamond PCD ~19.8
# around (11.2,216.2)); plus the inner-square r1.75 taps on the fore plates
J4_SVC = [(-2.8, 0, 216.2), (11.2, 0, 202.2), (11.2, 0, 230.2), (25.2, 0, 216.2)]
J4_TAP = [(1.3, 0, 206.3), (1.3, 0, 226.1), (21.1, 0, 206.3), (21.1, 0, 226.1)]
# fore_l2 <-> fore_r2 cross-tie bolts (verified shared holes)
FORE_TIE = [(53.6, 0, 202.7), (83.9, 0, 194.5), (108.9, 0, 194.5), (121.4, 0, 216.2)]
# J4 wrist-cradle bolts on fore_r2 (4x M3x10 into cradle inserts)
J4_CRADLE = [(68.4, 0, 207.2), (68.4, 0, 225.2),
             (90.4, 0, 207.2), (90.4, 0, 225.2)]

SPEC = {
 # --- link1: J1 flange bolts + flange face fixed; J2 cheek bolts + hub
 #     seat carry the whole distal wrench -------------------------------
 "link1": dict(
    fix=[land(c, Z, 1.6) for c in J1_BOLTS] +
        [face_plane((0, 0, 0), Z, 89.0, 0.0, 14.5)],
    load=[bore(c, Y, 1.6) for c in J2_BOLTS_L + J2_BOLTS_R] +
         [ring((J2[0], -37.1, J2[2]), Y, 7.0, 1.2),
          ring((J2[0], 37.1, J2[2]), Y, 7.0, 1.2)]),
 # --- yaw_limit: J1 horn bolts + horn seat fixed; link1 bolts load -----
 "yaw_limit": dict(
    fix=[land(c, Z, 1.6) for c in J1_HORN] +
        [ring((0, 0, 80.8), Z, 7.2, 1.5)],
    load=[bore(c, Z, 1.6) for c in
          pcd(0, 0, 86.0, 13.5, 6, a0=0, plane="xy")]),
 # --- j1_cradle: mount bolts (bounded to the foot face z~24-30) + seat
 #     face fixed; servo-case pocket wall reacts the J1 yaw wrench ------
 "j1_cradle": dict(
    fix=[land((-14.6, 13.4, 23.8), Z, 1.15, t0=3.2, half=3.0),
         land((12.3, -13.4, 23.8), Z, 1.15, t0=3.2, half=3.0),
         AND(box((-45, -45, 24.0), (45, 45, 25.5)),
             cyl((0, 0, 0), Z, 0.0, 45.0))],
    load=[AND(box((-30, -30, 20.0), (30, 30, 70.0)),
              cyl((0, 0, 0), Z, 19.0, 40.0))]),
 # --- base_link: base-plate contact + tower bolts fixed; reinf bolts +
 #     top cradle seat carry the arm -------------------------------------
 "base_link": dict(
    fix=[box((-47, -47, 16.8), (47, 47, 18.4))] +
        [land(c, Z, 2.3, t0=9.5, half=9.5) for c in
         [(32.0, -34.3, 0.0), (32.0, 29.7, 0.0), (-32.0, -34.3, 0.0), (-32.0, 29.7, 0.0)]],
    load=[AND(box((-47, -47, 79.5), (47, 47, 82.0)),
              cyl((0, 0, 0), Z, 0.0, 45.0))] +
        [land(c, Z, 2.25, t0=0.0, half=3.5) for c in
         [(-32.0, -32.0, 81.5), (-32.0, 32.0, 81.5),
          (32.0, -32.0, 81.5), (32.0, 32.0, 81.5)]]),
 # --- base_reinf: corner bolts to base_link fixed; J1 servo case screws
 #     (PCD50 ring) + hub bore carry the arm -----------------------------
 "base_reinf": dict(
    fix=[land(c, Z, 1.8) for c in
         [(-32.0, -32.0, 81.5), (-32.0, 32.0, 81.5),
          (32.0, -32.0, 81.5), (32.0, 32.0, 81.5)]],
    load=[land(c, Z, 1.55) for c in
          [(-12.5, -21.7, 63.6), (-12.5, 21.7, 63.6), (12.5, -21.7, 63.6),
           (12.5, 21.7, 63.6), (25.0, 0.0, 63.6), (-25.0, 0.0, 63.6)]] +
        [ring((0, 0, 81.0), Z, 8.0, 1.5)]),
 # --- base_plate: desk contact face fixed; tower bolts carry arm -------
 "base_plate": dict(
    fix=[AND(box((-95, -95, -1.0), (95, 95, 4.0)),
             cyl((0, 0, 0), Z, 0.0, 95.0))],
    load=[land(c, Z, 2.3) for c in
          [(-32.0, -32.0, 3.3), (-32.0, 32.0, 3.3),
           (32.0, -32.0, 3.3), (32.0, 32.0, 3.3)]] +
         [land(c, Z, 1.6) for c in
          [(-13.4, -13.4, 3.3), (-13.4, 13.4, 3.3),
           (13.4, -13.4, 3.3), (13.4, 13.4, 3.3)]]),
 # --- upper plates: J2 housing grip fixed; J3 housing grip loads -------
 "upper_out": dict(           # no bolt holes: collar ring-grip both ends
    fix=[ring(J2, Y, 28.6, 1.6)],
    load=[ring(J3, Y, 28.6, 1.6)]),
 "upper_back": dict(          # ring seat + 6x csk back screws each end
    fix=[ring(J2, Y, 28.6, 1.6)] + [land(c, Y, 1.7) for c in J2_CSK],
    load=[ring(J3, Y, 28.6, 1.6)] + [bore(c, Y, 1.7) for c in J3_CSK]),
 # --- doglegs: J3 link bolts + hub seat fixed; J4-end shared screws
 #     carry the whole fore-link wrench ----------------------------------
 "dogleg_l": dict(
    fix=[bore(c, Y, 1.6) for c in J3_BOLTS_L] + [ring(J3, Y, 7.0, 1.4)],
    load=[bore(c, Y, 1.5) for c in J4_SVC]),
 "dogleg_r": dict(
    fix=[bore(c, Y, 1.6) for c in J3_BOLTS_R] + [ring(J3, Y, 7.0, 1.4)],
    load=[bore(c, Y, 1.5) for c in J4_SVC]),
 # --- fore plates: dogleg-shared screws + taps fixed (+ cross-ties on
 #     fore_r2); fore_r2 carries the wrist cradle bolts, fore_l2 takes
 #     its share through the cross-tie bores ------------------------------
 "fore_l2": dict(
    fix=[land(c, Y, 1.5) for c in J4_SVC] +
        [land(c, Y, 1.75) for c in J4_TAP],
    load=[bore(c, Y, 1.6) for c in FORE_TIE]),
 "fore_r2": dict(
    fix=[land(c, Y, 1.5) for c in J4_SVC] +
        [land(c, Y, 1.75) for c in J4_TAP] +
        [land(c, Y, 1.6) for c in FORE_TIE],
    load=[bore(c, Y, 1.7) for c in J4_CRADLE]),
 # --- j4_cradle: bolt-plate mount face (y=32.5) to fore_r2 + insert bolt
 #     lands near the face fixed; J4 servo-case pocket wall reacts the
 #     wrist wrench ----------------------------------------------------
 "j4_cradle": dict(
    fix=[face_plane((96.4, 0, 216.2), Y, 32.5, 0.0, 45.0)] +
        [land(c, Y, 1.25, t0=31.0, half=3.0) for c in J4_CRADLE],
    load=[AND(box((58.0, -22.0, 200.0), (97.0, 30.0, 232.0)),
              cyl((96.4, 0, 216.2), Y, 14.0, 30.0))]),
 # --- cyclo housings (module frame, axis=Z): back screws + OD collar
 #     grip fixed; torque enters via the 41 ring-pin bores, radial shear
 #     via the 6808 output-bearing seat ---------------------------------
 "cy2_housing": dict(
    frame="cyc",
    fix=[AND(box((-30, -30, 49.0), (30, 30, 55.0)),
             cyl((0, 0, 0), Z, 27.0, 30.0)),
         land((25.0, 0, 0), Z, 1.25),
         land((-25.0, 0, 0), Z, 1.25),
         land((12.5, -21.7, 0), Z, 1.25),
         land((12.5, 21.7, 0), Z, 1.25),
         land((-12.5, -21.7, 0), Z, 1.25),
         land((-12.5, 21.7, 0), Z, 1.25)],
    loadM=[ring((0, 0, 38.5), Z, 23.5, 1.2, half=5.5)],  # ring-pin bores z33-44
    loadF=[ring((0, 0, 50.0), Z, 26.0, 1.0, half=4.0)]), # 6808 seat z46-54
 "cy3_housing": "same as cy2_housing",
 # --- carriers (module frame): out-pins drive the carrier (load), the
 #     dowel + tapped-bolt stack to out_flange reacts (fix); 685 hub seat
 #     takes radial shear -----------------------------------------------
 "cy2_carrier": dict(
    frame="cyc",
    fix=[land(c, Z, 2.05) for c in
         [(-12.0, 0, 49.3), (6.0, -10.4, 49.3), (6.0, 10.4, 49.3)]] +
        [land(c, Z, 1.15) for c in
         [(-6.8, -11.7, 46.4), (-6.8, 11.7, 46.4), (13.5, 0, 46.4)]],
    loadM=[ring((0, 0, 44.7), Z, 16.5, 1.6, half=2.3)], # out-pin pockets z42.4-47
    loadF=[ring((0, 0, 47.5), Z, 5.6, 1.2, half=4.5)]), # 685 hub seat z43-52
 "cy3_carrier": "same as cy2_carrier",
 # --- out_flange: output face land + dowel bores fixed (to link plates);
 #     3x carrier-bolt taps load ----------------------------------------
 "cy2_out_flange": dict(
    frame="cyc",
    fix=[land(c, Z, 2.05) for c in
         [(-12.0, 0, 52.4), (6.0, -10.4, 52.4), (6.0, 10.4, 52.4)]] +
        [face_plane((0, 0, 0), Z, 54.0, 15.0, 23.0)],
    loadM=[bore(c, Z, 1.7) for c in
           [(-6.8, -11.7, 52.4), (-6.8, 11.7, 52.4), (13.5, 0, 52.4)]],
    loadF=[face_plane((0, 0, 0), Z, 52.4, 0.0, 11.0)]),  # hub face contact
 "cy3_out_flange": "same as cy2_out_flange",
 # --- joint flanges/spacers -------------------------------------------
 "flange_j2": dict(            # link bolts thread into taps; actout face loads
    fix=[bore(c, Y, 1.35) for c in J2_BOLTS_R],
    load=[cyl(J2, Y, 7.0, 10.0)] + [cyl(J2, Y, 3.0, 5.0)]),
 "flange_j3": dict(
    fix=[bore(c, Y, 1.35) for c in J3_BOLTS_R],
    load=[cyl(J3, Y, 7.0, 10.0)] + [cyl(J3, Y, 3.0, 5.0)]),
 "front_spacer_j2": dict(      # link bolts fixed; actout dowels load
    fix=[bore(c, Y, 1.6) for c in
         [(-26.8, -36.6, 131.8), (-26.8, -36.6, 155.2), (-6.5, -36.6, 143.5)]],
    load=[bore(c, Y, 2.05) for c in
          [(-32.0, -36.6, 143.5), (-14.0, -36.6, 133.1), (-14.0, -36.6, 153.9)]]),
 "front_spacer_j3": dict(
    fix=[bore(c, Y, 1.6) for c in
         [(-33.5, -36.6, 270.2), (-13.3, -36.6, 258.5), (-13.3, -36.6, 281.9)]],
    load=[bore(c, Y, 2.05) for c in
          [(-26.0, -36.6, 259.8), (-26.0, -36.6, 280.6), (-8.0, -36.6, 270.2)]]),
 "back_spacer_j2": dict(       # csk screws to housing fixed; 6803 seat loads
    fix=[bore(c, Y, 1.7) for c in J2_CSK],
    load=[ring(J2, Y, 13.0, 1.6)]),
 "back_spacer_j3": dict(
    fix=[bore(c, Y, 1.7) for c in J3_CSK],
    load=[ring(J3, Y, 13.0, 1.6)]),
}
SPEC["cy3_housing"] = SPEC["cy2_housing"]
SPEC["cy3_carrier"] = SPEC["cy2_carrier"]
SPEC["cy3_out_flange"] = SPEC["cy2_out_flange"]


# module (cyclo4) frame <-> arm frame: place = T(jx, 23.4, jz) @ Rx(90).
# arm->module rotation is Rx(90)^T: (x,y,z) -> (x, z, -y).
ACT_BACK_Y = 23.4
def arm2cyc(v):
    v = np.asarray(v, float)
    return np.array([v[0], v[2], -v[1]])

def main(msh, inp, part, loads_json=None):
    loads = json.load(open(loads_json or os.path.join(HERE, "loads.json")))
    ld = loads[part]
    F = np.asarray(ld["F"]); M = np.asarray(ld["M"]); B = np.asarray(ld["B"])
    g = np.asarray(ld["g"]); g = g / np.linalg.norm(g)
    nodes, elems, _ = read_msh(msh)
    S = SPEC[part]
    if S.get("frame") == "cyc":
        # joint home point in module frame: (jx, jz) -> (0,0), y -> 23.4-y
        F, M, g = arm2cyc(F), arm2cyc(M), arm2cyc(g)
        B = np.array([0.0, 0.0, ACT_BACK_Y])
    ids = np.array(sorted(nodes))
    P = np.array([nodes[i] for i in ids])
    def sel(specs):
        m = np.zeros(len(ids), bool)
        for f in specs:
            m |= f(P)
        return ids[m]
    fix = sel(S["fix"])
    assert len(fix), (part, "empty NFIX")
    # one or two rigid load bodies: load (full wrench) OR loadM/loadF split
    bodies = []
    if "load" in S:
        bodies = [("NLOAD", sel(S["load"]), F, M)]
    else:
        bodies = [("NLOADM", sel(S["loadM"]), np.zeros(3), M),
                  ("NLOADF", sel(S["loadF"]), F, np.zeros(3))]
    # clamp lands win where a bolt land and a load surface overlap; a node
    # may be a rigid-body slave only once — earlier bodies keep the node
    # (ccx drops the dof with a *RIGID BODY warning otherwise).
    fixed = set(fix)
    claimed = set(fixed)
    keep = []
    for nm, ns, fv, mv in bodies:
        keep.append((nm, np.array([n for n in ns if n not in claimed]), fv, mv))
        claimed |= set(keep[-1][1])
    bodies = keep
    for nm, ns, _, _ in bodies:
        assert len(ns), (part, nm, "empty")

    tets, ndrop, ninv = [], 0, 0
    for eid, (etype, nids, phys) in sorted(elems.items()):
        if etype == 11:
            n2 = reorder_tet(nodes, nids)
            if None in n2:
                ndrop += 1; continue
            if signed_vol(nodes, n2[:4]) < 1e-4:
                ndrop += 1; continue
            if gauss_min_det(nodes, n2) <= 0.0:
                ninv += 1; continue
            tets.append((eid, n2))
    used = set(int(n) for _, nn in tets for n in nn)
    ids = np.array(sorted(used))
    fix = np.array([n for n in fix if n in used])
    bodies = [(nm, np.array([n for n in ns if n in used]), fv, mv)
              for nm, ns, fv, mv in bodies]
    for nm, ns, _, _ in bodies:
        assert len(ns), (part, nm, "patch emptied by tet drop")

    refs = {}
    w = open(inp, "w").write
    w("*NODE\n")
    for nid in ids:
        x, y, z = nodes[nid]
        w("%d, %.6f, %.6f, %.6f\n" % (nid, x, y, z))
    nxt = max(ids) + 1
    for nm, ns, fv, mv in bodies:
        refs[nm] = nxt
        w("%d, %.6f, %.6f, %.6f\n" % (nxt, *B))
        nxt += 1
    w("*ELEMENT, TYPE=C3D10, ELSET=EALL\n")
    for eid, nids in tets:
        w("%d, %s\n" % (eid, ", ".join(str(n) for n in nids)))
    def wr_nset(nm, ns):
        w("*NSET, NSET=%s\n" % nm)
        ns = sorted(ns)
        for i in range(0, len(ns), 8):
            w(", ".join(str(n) for n in ns[i:i + 8]) + "\n")
    wr_nset("NFIX", fix)
    for nm, ns, _, _ in bodies:
        wr_nset(nm, ns)
    w("*MATERIAL, NAME=PETGCF\n*ELASTIC\n4000.0, 0.35\n*DENSITY\n7.62e-10\n")
    w("*SOLID SECTION, ELSET=EALL, MATERIAL=PETGCF\n")
    for nm, ns, fv, mv in bodies:
        w("*RIGID BODY, NSET=%s, REF NODE=%d\n" % (nm, refs[nm]))
    w("*BOUNDARY\nNFIX, 1, 3, 0.\n")
    w("*STEP\n*STATIC\n")
    w("*DLOAD\nEALL, GRAV, 9810.0, %.5f, %.5f, %.5f\n" % tuple(g))
    for nm, ns, fv, mv in bodies:
        for k in range(3):
            if abs(fv[k]) > 1e-9:
                w("*CLOAD\n%d, %d, %.6f\n" % (refs[nm], k + 1, fv[k]))
            if abs(mv[k]) > 1e-9:
                w("*CLOAD\n%d, %d, %.6f\n" % (refs[nm], k + 4, mv[k]))
    w("*NODE FILE\nU, RF\n*EL FILE\nS\n*END STEP\n")
    print("%s: %d nodes %d C3D10 NFIX=%d %s (%d dropped, %d inverted)"
          % (inp, len(ids), len(tets), len(fix),
             " ".join("%s=%d" % (nm, len(ns)) for nm, ns, _, _ in bodies),
             ndrop, ninv))
    print("  F=%s N  M=%s N.mm at ref %s"
          % (np.round(F, 2).tolist(), np.round(M, 1).tolist(),
             np.round(B, 1).tolist()))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3],
         sys.argv[4] if len(sys.argv) > 4 else None)
