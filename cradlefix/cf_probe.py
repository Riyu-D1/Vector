"""cradlefix/cf_probe.py - D7 wrist-envelope collision probe.

Loads the TESTED final2/f2_collision.py mesh set + pose machinery verbatim
(the same exec-prefix trick f2_mc_hist.py uses), then sweeps the compound
wrist envelope on a <=2.5 deg grid:

  GRID A  J4 x J5 in [-70,+70]^2 at 2.5 deg (J6=0, grip=0)
          -> pairs upstream x wrist4/wrist5, wrist4 x wrist5, plus pairs
             into the grip measured at J6 0.
  GRID B  J5 x J6 at 2.5 deg, J4 in {-70,0,+70}
          -> pairs into the grip body (upstream x grip need J4; wrist4/5 x
             grip are J4-invariant -> run once at J4=0).
  GRID C  J6 at 2.5 deg x grip stroke {0,4,8,12.5} mm, J5 in {-70,0,+70}
          -> wrist5 x grip + intra-grip pairs across the stroke.

Every undeclared hit is reported as  pair | n hit poses | worst vol mm3 |
worst pose | intersection centre in world, W (a,b,h) and the downstream
part's home coords.

Run:  python3 cradlefix/cf_probe.py [A|B|C|all|pose q4 q5 [q6 [gt]]]
env:  CF_WRIST_DIR = wrist STL dir (default wrist2/out; cradlefix/out = fixed).
"""
import math, os, sys, time
import numpy as np
import trimesh
import manifold3d as m3d
from trimesh.transformations import rotation_matrix as rotmat

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ---- exec the tested loader/pose code from final2/f2_collision.py ----
src = open(os.path.join(ROOT, "final2", "f2_collision.py")).read()
src = src.replace(
    'WR = os.path.join(ROOT, "wrist2", "out")',
    'WR = os.environ.get("CF_WRIST_DIR", os.path.join(ROOT, "wrist2", "out"))')
src = src.split("# home-pose declaration audit")[0]
g = {"__name__": "probe", "__file__": os.path.join(ROOT, "final2", "f2_collision.py")}
exec(compile(src, "f2_collision.py", "exec"), g)

MESH = g["MESH"]; M = g["M"]; NAMES = g["NAMES"]; BODY = g["BODY"]; BIDX = g["BIDX"]
DECLARED = g["DECLARED"]; skip = g["skip"]; LIM = g["LIM"]
body_mats = g["body_mats"]

WJ = np.array([96.4, 0.0, 216.2])          # W frame origin in world (home)

def w_of(p):
    return np.asarray(p) - WJ

GRIP_GROUP = {"finger_u": "U", "vendor_rack_u": "U",
              "finger_d": "D", "vendor_rack_d": "D", "vendor_gear_grip": "G"}

def wrist_pairs():
    """group by intervening joints, not name order:
    p45 = pairs whose relative pose depends only on {J4,J5} (max body <=5);
    pG  = pairs into the grip body (max body =6) - J5xJ6 (+J4 for upstream)."""
    p45, pG, pGI = [], [], []
    for i, a in enumerate(NAMES):
        for b in NAMES[i + 1:]:
            if BODY[a] == BODY[b] or skip(a, b):
                continue
            ia, ib = sorted((BIDX[BODY[a]], BIDX[BODY[b]]))
            if ib <= 5:
                p45.append((a, b))
            else:
                pG.append((a, b))
    pGI = [(a, b) for i, a in enumerate(NAMES) for b in NAMES[i + 1:]
           if BODY[a] == BODY[b] == "grip" and not skip(a, b)
           and GRIP_GROUP.get(a) != GRIP_GROUP.get(b)]
    return p45, pG, pGI

P45, PG, PGI = wrist_pairs()
ALLP = P45 + PG + PGI

def _move_grip(out, mats, grip_t):
    if not grip_t:
        return out
    Rg = mats[6][:3, :3]
    du = Rg @ np.array([0.0, 1.0, 0.0])
    for n, sgn in (("finger_u", 1), ("finger_d", -1),
                   ("vendor_rack_u", 1), ("vendor_rack_d", -1)):
        if n in out:
            out[n] = out[n].translate((sgn * grip_t * du).tolist())
    if "vendor_gear_grip" in out:
        c_h = np.append(np.asarray(MESH["vendor_gear_grip"].bounds).mean(axis=0), 1.0)
        c_w = (mats[6] @ c_h)[:3]
        R = rotmat(math.radians(grip_t / 12.5 * 90.0), Rg @ np.array([1.0, 0.0, 0.0]), c_w)
        out["vendor_gear_grip"] = out["vendor_gear_grip"].transform(np.asarray(R[:3], np.float64))
    return out

def scan(q4s, q5s, q6s, gts, pairs, tag):
    """grid sweep; fixed bodies transformed once, moving bodies per pose."""
    want = set()
    for a, b in pairs:
        want.add(a); want.add(b)
    multi = lambda v: len(v) > 1
    fixed, moving = {}, {}
    mats0 = body_mats([0.0, 0.0, 0.0, q4s[0], q5s[0], q6s[0]])
    for n in want:
        k = BIDX[BODY[n]]
        still = (k <= 3 or (k == 4 and not multi(q4s)) or
                 (k == 5 and not (multi(q4s) or multi(q5s))) or
                 (k == 6 and not (multi(q4s) or multi(q5s) or multi(q6s))))
        if still:
            fixed[n] = M[n].transform(np.asarray(mats0[k][:3, :], np.float64))
        else:
            moving[n] = k
    res, nposes = {}, 0
    t0 = time.time()
    for q4 in q4s:
        for q5 in q5s:
            for q6 in q6s:
                q = [0.0, 0.0, 0.0, q4, q5, q6]
                mats = body_mats(q)
                pm = dict(fixed)
                for n, k in moving.items():
                    pm[n] = M[n].transform(np.asarray(mats[k][:3, :], np.float64))
                for gt in gts:
                    pm = _move_grip(pm, mats, gt)
                    bb = {n: pm[n].bounding_box() for n in pm}
                    for a, b in pairs:
                        if a not in pm or b not in pm:
                            continue
                        ba, bb2 = bb[a], bb[b]
                        if ba[0] > bb2[3] or bb2[0] > ba[3] or ba[1] > bb2[4] or bb2[1] > ba[4] or ba[2] > bb2[5] or bb2[2] > ba[5]:
                            continue
                        inter = pm[a] ^ pm[b]
                        v = inter.volume()
                        if v <= 0.5 or frozenset((a, b)) in DECLARED:
                            continue
                        mm2 = inter.to_mesh()
                        vs = np.asarray(mm2.vert_properties)[:, :3]
                        ctr = vs.mean(axis=0) if len(vs) else np.asarray(inter.bounding_box()).reshape(2, 3).mean(axis=0)
                        home = np.linalg.inv(mats[BIDX[BODY[b]]]) @ np.append(ctr, 1.0)
                        k2 = (a, b)
                        if k2 not in res:
                            res[k2] = [1, v, np.round(np.degrees(q), 2).tolist() + [gt],
                                       (ctr, w_of(ctr), home[:3] - WJ)]
                        else:
                            res[k2][0] += 1
                            if v > res[k2][1]:
                                res[k2][1:] = [v, np.round(np.degrees(q), 2).tolist() + [gt],
                                               (ctr, w_of(ctr), home[:3] - WJ)]
                    nposes += 1
    print("== %s: %d poses %.0f s ==" % (tag, nposes, time.time() - t0))
    if not res:
        print("   CLEAN - no undeclared hits")
    for (a, b), (cnt, v, q, info) in sorted(res.items(), key=lambda kv: -kv[1][0]):
        print("   %-42s hits %-4d worst %.1f mm3 at q=%s" % ("%s x %s" % (a, b), cnt, v, q))
        print("        ctr world %s  W(a,b,h) %s  %s-home %s"
              % (np.round(info[0], 1).tolist(), np.round(info[1], 1).tolist(), b,
                 np.round(info[2], 1).tolist()))
    return res

STEP = math.radians(2.5)
def grid(lo, hi):
    return np.arange(lo, hi + 1e-9, STEP)

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode == "pose":
        q4 = math.radians(float(sys.argv[2])); q5 = math.radians(float(sys.argv[3]))
        q6 = math.radians(float(sys.argv[4])) if len(sys.argv) > 4 else 0.0
        gt = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
        want = set()
        for a, b in ALLP:
            want.add(a); want.add(b)
        q = [0.0, 0.0, 0.0, q4, q5, q6]
        mats = body_mats(q)
        pm = {n: M[n].transform(np.asarray(mats[BIDX[BODY[n]]][:3, :], np.float64)) for n in want}
        pm = _move_grip(pm, mats, gt)
        bb = {n: pm[n].bounding_box() for n in pm}
        found = False
        for a, b in ALLP:
            ba, bb2 = bb[a], bb[b]
            if ba[0] > bb2[3] or bb2[0] > ba[3] or ba[1] > bb2[4] or bb2[1] > ba[4] or ba[2] > bb2[5] or bb2[2] > ba[5]:
                continue
            inter = pm[a] ^ pm[b]
            v = inter.volume()
            if v <= 0.5:
                continue
            tag = " (declared)" if frozenset((a, b)) in DECLARED else ""
            mm2 = inter.to_mesh()
            vs = np.asarray(mm2.vert_properties)[:, :3]
            ctr = vs.mean(axis=0) if len(vs) else np.asarray(inter.bounding_box()).reshape(2, 3).mean(axis=0)
            home = np.linalg.inv(mats[BIDX[BODY[b]]]) @ np.append(ctr, 1.0)
            print("%s x %s  %.1f mm3%s  ctr world %s  W %s  %s-home %s"
                  % (a, b, v, tag, np.round(ctr, 1).tolist(), np.round(w_of(ctr), 1).tolist(),
                     b, np.round(home[:3] - WJ, 1).tolist()))
            found = found or not tag
        print("pose q4 %+.1f q5 %+.1f q6 %+.1f gt %.1f: %s"
              % (math.degrees(q4), math.degrees(q5), math.degrees(q6), gt,
                 "only-declared" if not found else "HITS"))
        return
    if mode in ("A", "all"):
        scan(grid(LIM[3][0], LIM[3][1]), grid(LIM[4][0], LIM[4][1]), [0.0], [0.0],
             P45 + PG, "GRID A J4xJ5 (J6=0, grip=0)")
    if mode in ("B", "all"):
        pG_up = [(a, b) for a, b in PG if min(BIDX[BODY[a]], BIDX[BODY[b]]) <= 3]
        pG_dn = [(a, b) for a, b in PG if min(BIDX[BODY[a]], BIDX[BODY[b]]) >= 4]
        for q4 in (LIM[3][0], LIM[3][0] / 2, 0.0, -LIM[3][0] / 2, LIM[3][1]):
            scan([q4], grid(LIM[4][0], LIM[4][1]), grid(LIM[5][0], LIM[5][1]), [0.0],
                 pG_up, "GRID B J5xJ6 upstream x grip, J4=%+.0f" % math.degrees(q4))
        scan([0.0], grid(LIM[4][0], LIM[4][1]), grid(LIM[5][0], LIM[5][1]), [0.0],
             pG_dn, "GRID B wrist4/5 x grip, J4=0")
    if mode in ("C", "all"):
        p56 = [(a, b) for a, b in PG if min(BIDX[BODY[a]], BIDX[BODY[b]]) >= 4] + PGI
        for q5 in (LIM[4][0], 0.0, LIM[4][1]):
            scan([0.0], [q5], grid(LIM[5][0], LIM[5][1]), [0.0, 4.0, 8.0, 12.5],
                 p56, "GRID C J6xstroke, J5=%+.0f" % math.degrees(q5))

if __name__ == "__main__":
    main()
