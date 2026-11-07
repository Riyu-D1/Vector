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


def gf_case(name, P):
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
    return fix, load, [((137.4, 0.0, -17.0), (0.0, 0.0, -6.0))]


def l5_case(name, P):
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
    return fix, load, [((113.7, 0.0, -30.0), (0.0, 0.0, -6.87))]


def l4_case(name, P):
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
    return fix, load, [((106.0, 0.0, -5.0), (0.0, 0.0, -7.16))]


CASES = {"gf": gf_case, "l5": l5_case, "l4": l4_case}


def main(msh, inp, case):
    part, name = case.split("_", 1)
    nodes, elems, _ = read_msh(msh)
    assert nodes and elems, "empty mesh"
    ids = np.array(sorted(nodes))
    P = np.array([nodes[i] for i in ids])
    fix, load, wrenches = CASES[part](name, P)
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
    w("*DLOAD\nEALL, GRAV, 9810.0, 0.00000, 0.00000, -1.00000\n")
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
