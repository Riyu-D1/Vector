"""refine/fea/msh2_r9.py - R9 CalculiX decks: R3 decks + J4-axis journal.

Same conventions as msh2_r3.py (W frame mm; x=a tool dir, y=b, z=h up).
R9 adds the printed U-yoke second J4 support: a journal boss on the l4
+b cheek riding a d3 steel dowel pinned in the cradle.  The journal is a
RADIAL bearing only - it can react force components in the a-h plane but
NOT the axial (b) force, NOT the J4 drive torque (moment about b).  Deck
model: the bore-wall nodes are fixed in DOFs 1 and 3 (u_a = u_h = 0),
DOF 2 (b) left free - radial contact with axial slip.

l4 fixity suffixes on top of the R3/R8 BC names:
  *_scrj     scrann + journal bore fixed radially over the full circle
             (ideal-engagement bound: the whole bore finds contact)
  *_scrjh    scrann + journal fixed only on the loaded-side semicircle
             (unilateral bound: the bore presses the pin only where the
             applied radial force points it; -F_radial half)
  no suffix  R8 behaviour - horn only (loose-journal / never-engages
             bound: the fin alone must carry the wrench)

cr cases (w_j4_cradle): the pad+flange pin seat takes the journal
reaction.  fix sets:
  cr_bolt    4x M3 pilot-bore walls (screw-shear path only)
  cr_face    +b flange outer face (clamped-face path only)
  cr_boltface  both (assembled bound)
load: journal-reaction bound on the pad bore wall (loaded-side patch);
F_jrn = M_h(horn axis)/43.6 mm couple + 0.5 * |F_radial|.

Run:  python3 msh2_r9.py <part>.msh <out>.inp <case>
"""

import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from msh2tc import read_msh, reorder_tet, signed_vol, gauss_min_det  # noqa

RHOLE = 7.0          # PCD14 hole-centre radius
O45 = RHOLE * np.cos(np.radians(45.0))   # 4.9497
HR = 1.7 + 0.35      # hole radius + capture tol


def _holes(axis_pts):
    """hole-centre predicate factory: axis_pts = list of (coord1,coord2)
    hole centres in the two in-plane axes."""
    def f(d1, d2):
        return np.logical_or.reduce(
            [np.hypot(d1 - c1, d2 - c2) <= HR for c1, c2 in axis_pts])
    return f


def _payload(name):
    """trailing _pNN suffix -> payload share multiplier.
    Decks carry a ~0.5 kg-class wrench = payload force + fixed carried
    stack; the suffix scales ONLY the payload share."""
    for tag, kg in (("_p25", 0.25), ("_p38", 0.38), ("_p50", 0.5)):
        if name.endswith(tag):
            return name[: -len(tag)], kg
    return name, 0.5


# R6: direction table - axis-pure bounds plus pose-matched combined
# gravity directions (wrist5-frame components of g, from pose_wrenches.py /
# checks/pose_wrenches_r6.txt envelope scans):
#   _lat   +b axis-pure lateral bound (b-symmetric part -> one sign)
#   _roll  max-|b| pose family (folded+rolled): g=(+.34,+.94,0)
#   _comb  max 3-axis mix, +h:   g=(-.47,+.814,+.342)
#   _comb2 max 3-axis mix, -h:   g=(-.47,+.814,-.342)
#   _flop  backward-flop family: g=(+.17,0,+.98)
#   _axp/_axn  +-a axial bounds   _up  +h inverted bound
# A trailing 'f' on a direction tag (e.g. _latf) keeps the legacy
# floor-only entry patch (strict entry-concentration sensitivity).
L5_DIRS = {"_lat": (0.0, 1.0, 0.0), "_axp": (1.0, 0.0, 0.0),
           "_axn": (-1.0, 0.0, 0.0), "_up": (0.0, 0.0, 1.0),
           "_roll": (0.342, 0.94, 0.0), "_comb": (-0.47, 0.814, 0.342),
           "_comb2": (-0.47, 0.814, -0.342), "_flop": (0.17, 0.0, 0.98)}


def _wrench_dir(name):
    """trailing direction suffix -> force unit vector at the RB ref node,
    scaled by the case force magnitude.  Default = -z (keel-down gravity
    wrench, the R3/R4 convention).  Returns (case_root, dir, floor_only)."""
    floor_only = False
    if any(name.endswith(t + "f") for t in L5_DIRS):
        floor_only = True
        name = name[:-1]
    for tag, d in L5_DIRS.items():
        if name.endswith(tag):
            return name[: -len(tag)], d, floor_only
    return name, (0.0, 0.0, -1.0), floor_only


def _grav_for(d):
    """R6: self-weight acts along the wrench direction itself - the gravity
    field that produces the distal-mass wrench loads the part the same
    way (pose-matched).  Replaces the R5 '-z except _up' approximation."""
    return d


def gf_case(name, P):
    name, d, _fo = _wrench_dir(name)              # R7: direction bounds too
    name, pay = _payload(name)
    a, b, h = P[:, 0], P[:, 1], P[:, 2]
    r = np.hypot(b, h + 17.0)                      # roll axis (0,-17)
    holes = _holes([(O45, -17.0 + O45), (O45, -17.0 - O45),
                    (-O45, -17.0 + O45), (-O45, -17.0 - O45)])
    shank = holes(b, h) & (a >= 62.65) & (a <= 67.0)
    top2 = _holes([(O45, -17.0 + O45), (-O45, -17.0 + O45)])
    pilot = (a >= 62.8) & (a <= 64.85) & (r >= 3.4) & (r <= 3.75)
    ann = (a <= 62.71) & (r >= 3.55) & (r <= 9.65)
    fix = {
        "face": a <= 63.0,
        "ann": ann | pilot,
        "screw": shank,
        "scpilot": shank | pilot,
        "scrann": shank | ann | pilot,
        "scr2": top2(b, h) & (a >= 62.65) & (a <= 67.0),
    }[name]
    load = a >= 120.0
    F = tuple(f * (9.81 * pay + 1.1) for f in d)
    return fix, load, [((137.4, 0.0, -17.0), F)], _grav_for(d)


def l5_case(name, P):
    case_tag = name                            # full tag incl dir/payload
    name, d, floor_only = _wrench_dir(name)   # R6: dir + entry-patch flag
    name, pay = _payload(name)
    a, b, h = P[:, 0], P[:, 1], P[:, 2]
    holes = _holes([(30.6 + O45, O45), (30.6 + O45, -O45),
                    (30.6 - O45, O45), (30.6 - O45, -O45)])
    shank = holes(a, b) & (h >= -4.15) & (h <= -2.05)
    far2 = _holes([(30.6 + O45, O45), (30.6 + O45, -O45)])
    rr = np.hypot(a - 30.6, b)
    pilot = (h >= -4.3) & (h <= -1.2) & (rr >= 3.4) & (rr <= 3.75)
    ann = (h >= -2.25) & (rr >= 3.55) & (rr <= 9.65)
    fix = {
        "face": (h >= -2.2) & (a >= 23.0) & (a <= 38.2),
        "ann": ann | pilot,
        "screw": shank,
        "scpilot": shank | pilot,
        "scrann": shank | ann | pilot,
        "scr2": far2(a, b) & (h >= -4.15) & (h <= -2.05),
    }[name]
    # J6 pocket floor patch (keel web top h~-52.4 under the case)
    load = (h >= -52.55) & (h <= -52.2) & (a >= 17.0) & (a <= 64.5) \
        & (np.abs(b) <= 12.4)
    # R6: direction-matched empty-pocket entry - a snug case (0.15 mm/side
    # clearance) pressed +-b bears on that SIDE WALL over the case length,
    # not only the floor.  Wall band = pocket side face on the push side;
    # still empty-pocket (no case stiffness credit) and the full wrench is
    # applied either way.  *_latf keeps the floor-only patch as the strict
    # entry-concentration sensitivity.
    if not floor_only and d[1] > 0.3:
        load = load | ((b >= 11.8) & (a >= 17.0) & (a <= 62.0)
                       & (h >= -52.0) & (h <= -8.0))
    elif not floor_only and d[1] < -0.3:
        load = load | ((b <= -11.8) & (a >= 17.0) & (a <= 62.0)
                       & (h >= -52.0) & (h <= -8.0))
    F = tuple(f * (9.81 * pay + 1.965) for f in d)
    # R8: EVERY case now applies the wrench at the true mass-weighted COM
    # of the carried stack + payload.  R7 only did this for the
    # pose-matched tags; the legacy ref (113.7,-30) understates the moment
    # about the horn ~10 % at p50 / ~7 % at p38 (checks/verify_r8.py).
    # The carried masses always gravitate through their COM, regardless
    # of which axis-pure bound direction the deck represents.
    com = _stack_com(pay)
    return fix, load, [((com[0], 0.0, com[2]), F)], _grav_for(d)


# carried stack + payload COM (W frame) as a function of payload kg -
# masses/COMs from mass_r5.py converted to W (AB - 223.1,0,89.5); payload
# applied at the TCP point (137.4,0,-17).
_L5_STACK = [(0.05500, (41.53, 0.00, -29.59)), (0.01598, (94.77, -0.02, -25.68)),
             (0.05500, (95.53, 0.00, -29.59)), (0.00800, (119.70, 0.00, -17.00)),
             (0.01200, (119.90, -12.99, -3.28)), (0.01200, (119.90, 12.99, -30.72)),
             (0.00097, (131.08, 3.00, -16.62)), (0.00097, (131.08, -3.00, -17.38)),
             (0.01939, (100.19, -0.01, -23.81))]


def _stack_com(pay):
    sx = sum(m * c[0] for m, c in _L5_STACK) + pay * 137.4
    sz = sum(m * c[2] for m, c in _L5_STACK) - pay * 17.0
    M = sum(m for m, _ in _L5_STACK) + pay
    return (sx / M, 0.0, sz / M)


def l4_case(name, P):
    name, d, _fo = _wrench_dir(name)              # R8: direction bounds too
    name, pay = _payload(name)
    a, b, h = P[:, 0], P[:, 1], P[:, 2]
    holes = _holes([(O45, O45), (O45, -O45), (-O45, O45), (-O45, -O45)])
    # R8: the J4 horn mounts the plate's INBOARD face (J4_FACE_B=-26.6; the
    # kp horn disc spans b -21.6..-26.6) - the earlier ann at b<=-30.6 put
    # the bearing patch on the free face.  R8 also extends the plate to
    # -32.1 outboard (fore_l at -32.6 leaves 0.5 mm), so the screw shank
    # band runs from the counterbore shoulder -30.1 to the inboard face.
    shank = holes(a, h) & (b >= -30.15) & (b <= -26.6)
    diag2 = _holes([(O45, O45), (-O45, -O45)])
    rr = np.hypot(a, h)
    pilot = (b >= -28.85) & (b <= -25.7) & (rr >= 3.4) & (rr <= 3.75)
    ann = (b >= -26.75) & (rr >= 3.55) & (rr <= 9.65)
    scrann = shank | ann | pilot
    scr2 = diag2(a, h) & (b >= -30.15) & (b <= -26.6)
    # R9 journal bearing: bore-wall nodes on the d3.4 journal (r<=2.15
    # capture), b 14.85..19.05 band, fixed in DOFs 1+3 only (radial
    # contact, axial slip).  scrj = full-circle (ideal engagement);
    # scrjh = loaded-side semicircle (unilateral bound).
    jrn = (b >= 14.85) & (b <= 19.05) & (rr <= 2.15)
    fix = {
        "face": b <= -32.0,
        "ann": ann | pilot,
        "screw": shank,
        "scpilot": shank | pilot,
        "scrann": scrann,
        "scr2": scr2,
        "scrj": scrann,
        "scrjh": scrann,
        "scr2j": scr2,
    }[name]
    # J5 pocket bearing region: fin bottom web top + lower cheek inner
    # faces where the J5 case sits (case face at -2.0, pocket floor -1.4)
    load = (h >= -1.5) & (h <= 0.0) & (a >= 20.0) & (a <= 61.0) \
        & (np.abs(b) <= 12.4)
    # R8b: direction-matched bearing - same rule as l5.  A +-b push
    # presses the J5 case side face (case b +-12.36, a 20.5..65.7,
    # h 0.1..47.8) into the cheek inner wall |b|=12.51; the floor-only
    # patch concentrated the lateral wrench unrealistically (p50 _lat
    # read tau ~21 MPa vs ~6 keel-down).
    if d[1] > 0.3:
        load = load | ((b >= 11.8) & (a >= 20.0) & (a <= 66.0)
                       & (h >= 0.0) & (h <= 48.0))
    elif d[1] < -0.3:
        load = load | ((b <= -11.8) & (a >= 20.0) & (a <= 66.0)
                       & (h >= 0.0) & (h <= 48.0))
    # R8: apply at the true distal-stack COM (was (106,-5) - understated
    # the moment ~13 % at p50); self-weight along the wrench direction.
    com = _stack_com(pay)
    F = tuple(f * (9.81 * pay + 2.255) for f in d)
    # journal patch for the half cases: the semicircle facing the
    # estimated journal REACTION on the part.  R_j ~= -0.5*F_radial
    # (force share) + (M_h/43.6) a-hat + (M_a/43.6) h-hat (bearing couple;
    # only F_b makes those moments) - the couple normally dominates.
    jset = None
    if name in ("scrj", "scr2j"):
        jset = jrn
    elif name == "scrjh":
        Fb_ = d[1] * (9.81 * pay + 2.255)
        Rj = np.array([-0.5 * F[0] + com[0] * Fb_ / 43.6,
                       -0.5 * F[2] - com[2] * Fb_ / 43.6])
        if np.hypot(*Rj) < 1e-9: Rj = np.array([1.0, 0.0])
        jset = jrn & ((a * Rj[0] + h * Rj[1]) >= 0.0)
    return fix, load, [((com[0], 0.0, com[2]), F)], _grav_for(d), jset


def cr_case(name, P):
    """w_j4_cradle: journal reaction on the pin-seat pad bore.

    The pin pushes the pad bore wall outward on its loaded side; the pad
    stub + flange carry it to the 4 M3 fore bolts.  fix sets:
      bolt     - pilot-bore walls only (screw-shear path)
      face     - flange outer face only (clamped-face path)
      boltface - both (assembled bound)
    load patch: pad+flange bore wall (r<=1.95, b 25.5..32.3) on the
    reaction-side semicircle.  Force bound per direction d:
      |F_jrn| <= M_h/43.6 (couple) + |M_a|/43.6 + 0.5*|F_radial|
    applied along the journal-reaction direction (same rule as scrjh).
    """
    name, d, _fo = _wrench_dir(name)
    name, pay = _payload(name)
    a, b, h = P[:, 0], P[:, 1], P[:, 2]
    blt = _holes([(-6.0, 9.0), (-6.0, -9.0), (-28.0, 9.0), (-28.0, -9.0)])
    walls = blt(a, h) & (b >= 24.4) & (b <= 33.6)
    face = (b >= 32.3) & (a >= -34.5) & (a <= 0.5) & (np.abs(h) <= 14.2)
    fix = {"bolt": walls, "face": face, "boltface": walls | face}[name]
    com = _stack_com(pay)
    F = np.array(d) * (9.81 * pay + 2.255)
    Mh = com[0] * F[1]                    # about +h -> a-directed couple
    Ma = -com[2] * F[1]                   # about +a -> h-directed couple
    Fr = np.hypot(F[0], F[2])
    Rj = np.array([-0.5 * F[0] + Mh / 43.6, -0.5 * F[2] + Ma / 43.6])
    if np.hypot(*Rj) < 1e-9: Rj = np.array([1.0, 0.0])
    nx, nz = Rj / np.hypot(*Rj)
    Fm = (abs(Mh) + abs(Ma)) / 43.6 + 0.5 * Fr
    rr = np.hypot(a, h)
    # the pin pushes the pad wall on the side OPPOSITE its reaction on
    # the l4 journal (boss pushes pin -R_j, pin pushes pad -R_j) ->
    # loaded semicircle faces -R_j.
    load = (b >= 25.3) & (b <= 32.3) & (rr <= 1.95) & \
           ((a * nx + h * nz) <= 0.0)
    Fv = (Fm * nx, 0.0, Fm * nz)
    return fix, load, [((0.0, 28.0, 0.0), Fv)], _grav_for(d), None


CASES = {"gf": gf_case, "l5": l5_case, "l4": l4_case, "cr": cr_case}


def main(msh, inp, case):
    part, name = case.split("_", 1)
    nodes, elems, _ = read_msh(msh)
    assert nodes and elems, "empty mesh"
    ids = np.array(sorted(nodes))
    P = np.array([nodes[i] for i in ids])
    out = CASES[part](name, P)
    fix, load, wrenches, grav = out[:4]
    jset = out[4] if len(out) > 4 else None
    fix_ids, load_ids = ids[fix], ids[load]
    jrn_ids = ids[jset] if jset is not None else np.array([], dtype=int)
    assert len(fix_ids) and len(load_ids), (case, len(fix_ids), len(load_ids))
    assert not set(fix_ids) & set(load_ids)
    print("  %s: NFIX=%d NJRN=%d NLOAD=%d" % (case, len(fix_ids),
                                            len(jrn_ids), len(load_ids)))

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
    fix_ids = np.array([n for n in fix_ids if n in used])
    load_ids = np.array([n for n in load_ids if n in used])
    jrn_ids = np.array([n for n in jrn_ids if n in used])
    assert len(fix_ids) and len(load_ids), (case, "patches emptied")
    if jset is not None:
        assert len(jrn_ids), (case, "journal patch emptied")

    ref0 = max(ids) + 1
    w = open(inp, "w").write
    w("*NODE\n")
    for nid in ids:
        x, y, z = nodes[nid]
        w("%d, %.6f, %.6f, %.6f\n" % (nid, x, y, z))
    for k, (B, F) in enumerate(wrenches):
        w("%d, %.6f, %.6f, %.6f\n" % (ref0 + k, *B))
    w("*ELEMENT, TYPE=C3D10, ELSET=EALL\n")
    for eid, nids in tets:
        w("%d, %s\n" % (eid, ", ".join(str(n) for n in nids)))

    def wr_nset(nm, ns):
        w("*NSET, NSET=%s\n" % nm)
        ns = sorted(ns)
        for i in range(0, len(ns), 8):
            w(", ".join(str(n) for n in ns[i:i + 8]) + "\n")
    wr_nset("NFIX", fix_ids)
    if len(jrn_ids):
        wr_nset("NJRN", jrn_ids)
    for k in range(len(wrenches)):
        wr_nset("NLOAD%d" % k, load_ids if k == 0 else [])
    w("*MATERIAL, NAME=PETGCF\n*ELASTIC\n4000.0, 0.35\n*DENSITY\n7.86e-10\n")
    w("*SOLID SECTION, ELSET=EALL, MATERIAL=PETGCF\n")
    for k, (B, F) in enumerate(wrenches):
        w("*RIGID BODY, NSET=NLOAD%d, REF NODE=%d\n" % (k, ref0 + k))
    w("*BOUNDARY\nNFIX, 1, 3, 0.\n")
    if len(jrn_ids):
        # radial journal bearing: u_a = u_h = 0, b (axial) free
        w("NJRN, 1, 1, 0.\nNJRN, 3, 3, 0.\n")
    w("*STEP\n*STATIC\n")
    w("*DLOAD\nEALL, GRAV, 9810.0, %.6f, %.6f, %.6f\n" % grav)
    for k, (B, F) in enumerate(wrenches):
        for j in range(3):
            if abs(F[j]) > 1e-9:
                w("*CLOAD\n%d, %d, %.6f\n" % (ref0 + k, j + 1, F[j]))
    w("*NODE FILE\nU, RF\n*EL FILE\nS\n*END STEP\n")
    print("%s: %d nodes %d C3D10 NFIX=%d NLOAD=%d"
          % (inp, len(ids), len(tets), len(fix_ids), len(load_ids)))
    for k, (B, F) in enumerate(wrenches):
        print("  wrench%d F=%s N at ref %s"
              % (k, np.round(F, 2).tolist(), np.round(B, 1).tolist()))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
