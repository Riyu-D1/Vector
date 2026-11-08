"""refine/fea/msh2_r3.py - R3 CalculiX decks: realistic horn-mount load paths.

Replaces the [U] full-face horn fixity of msh2_extra.py with a bounded set
of screw/horn contact models.  Same helpers/conventions as msh2_extra.py
(reuses msh2tc.py verbatim).  All coordinates in the W frame mm
(x=a tool dir, y=b, z=h up).

Interface dims (ap2b/ap2, [S kp/vendor proxy]):
  horn disc OD 19.2 -> contact annulus r <= 9.6 on the plate face
  pilot recess d7.0 x 2.2 -> pilot cylinder r ~ 3.5
  4x M3 clearance d3.4 on PCD14 (hole centres at r=7, 45 deg pattern)
  counterbore d6.2 x 2.0 -> the screw shank bears only on the
  non-counterbore band of the hole wall.

Cases per part (<tag> = fix_w_grip_frame / fix_w_link5 / fix_w_link4):
  <p>_face     - whole contact face fixed (previous optimistic bound)
  <p>_ann      - flange annulus r[3.6,9.6] + pilot surface only: pure
                bearing/friction path, screws do nothing
  <p>_screw    - 4 hole walls on the shank band only: pure screw-shear
                path, flange does nothing
  <p>_scpilot  - shank band + pilot cylinder: screws+locator, no flange
  <p>_scrann   - shank band + annulus + pilot: realistic assembled joint
  <p>_scr2     - only the 2 most-loaded holes (fault bound: two screws
                carrying the whole wrench)

Loads (arm horizontal, tool forward = worst local wrench on the part):
  w_grip_frame: RB on a>=120 at TCP (137.4,0,-17), Fz = -(4.905+1.1) N
      (0.5 kg payload + ~0.11 kg carried fingers/racks/gear/g-servo,
      lumped at TCP -> conservative moment arm, stated).
  w_link5:      RB on the J6 pocket floor at (113.7,0,-30), Fz = -6.87 N
      (0.5 kg at TCP + ~0.20 kg distal stack at its centroid ->
      moment-matched single force at x_eq 113.7).
  w_link4:      RB on the J5 pocket floor at (106,0,-5), Fz = -7.16 N
      (0.5 kg at TCP + ~0.23 kg distal stack at its centroid ->
      moment-matched x_eq 106).

Run:  python3 msh2_r3.py <part>.msh <out>.inp <case>
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
    return fix, load, [((137.4, 0.0, -17.0), (0.0, 0.0, -(9.81 * pay + 1.1)))], (0.0, 0.0, -1.0)


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
    # R6: for pose-matched cases (_roll/_comb/_comb2/_flop) the force is
    # applied at the true mass-weighted COM of the carried stack + payload
    # (pose_wrenches.py:wrench -> r_eq), so the transmitted moment matches
    # the actual gravity wrench; the legacy ref (113.7,-30) understates it
    # ~12 % at p50 and is kept for the axis-pure bounds + _latf sensitivity.
    POSE_DIRS = ("roll", "comb", "comb2", "flop")
    tag = next((t for t in POSE_DIRS if case_tag.endswith("_" + t) or
                case_tag.endswith("_" + t + "f")), None)
    if tag is not None:
        com = _stack_com(pay)
        return fix, load, [((com[0], 0.0, com[2]), F)], _grav_for(d)
    return fix, load, [((113.7, 0.0, -30.0), F)], _grav_for(d)


# carried stack + payload COM (W frame) as a function of payload kg -
# masses/COMs from mass_r5.py converted to W (AB - 223.1,0,89.5); payload
# applied at the TCP point (137.4,0,-17).
_L5_STACK = [(0.05500, (41.53, 0.00, -29.59)), (0.01379, (98.52, -0.03, -26.09)),
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
    name, pay = _payload(name)
    a, b, h = P[:, 0], P[:, 1], P[:, 2]
    holes = _holes([(O45, O45), (O45, -O45), (-O45, O45), (-O45, -O45)])
    shank = holes(a, h) & (b >= -28.65) & (b <= -26.6)
    diag2 = _holes([(O45, O45), (-O45, -O45)])
    rr = np.hypot(a, h)
    pilot = (b >= -28.85) & (b <= -25.7) & (rr >= 3.4) & (rr <= 3.75)
    ann = (b <= -30.6) & (rr >= 3.55) & (rr <= 9.65)
    fix = {
        "face": b <= -30.6,
        "ann": ann | pilot,
        "screw": shank,
        "scpilot": shank | pilot,
        "scrann": shank | ann | pilot,
        "scr2": diag2(a, h) & (b >= -28.65) & (b <= -26.6),
    }[name]
    # J5 pocket bearing region: fin bottom web top + lower cheek inner
    # faces where the J5 case sits (case face at -2.0, pocket floor -1.4)
    load = (h >= -1.5) & (h <= 0.0) & (a >= 20.0) & (a <= 61.0) \
        & (np.abs(b) <= 12.4)
    return fix, load, [((106.0, 0.0, -5.0), (0.0, 0.0, -(9.81 * pay + 2.255)))], (0.0, 0.0, -1.0)


CASES = {"gf": gf_case, "l5": l5_case, "l4": l4_case}


def main(msh, inp, case):
    part, name = case.split("_", 1)
    nodes, elems, _ = read_msh(msh)
    assert nodes and elems, "empty mesh"
    ids = np.array(sorted(nodes))
    P = np.array([nodes[i] for i in ids])
    fix, load, wrenches, grav = CASES[part](name, P)
    fix_ids, load_ids = ids[fix], ids[load]
    assert len(fix_ids) and len(load_ids), (case, len(fix_ids), len(load_ids))
    assert not set(fix_ids) & set(load_ids)
    print("  %s: NFIX=%d NLOAD=%d" % (case, len(fix_ids), len(load_ids)))

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
    assert len(fix_ids) and len(load_ids), (case, "patches emptied")

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
    for k in range(len(wrenches)):
        wr_nset("NLOAD%d" % k, load_ids if k == 0 else [])
    w("*MATERIAL, NAME=PETGCF\n*ELASTIC\n4000.0, 0.35\n*DENSITY\n7.62e-10\n")
    w("*SOLID SECTION, ELSET=EALL, MATERIAL=PETGCF\n")
    for k, (B, F) in enumerate(wrenches):
        w("*RIGID BODY, NSET=NLOAD%d, REF NODE=%d\n" % (k, ref0 + k))
    w("*BOUNDARY\nNFIX, 1, 3, 0.\n")
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
