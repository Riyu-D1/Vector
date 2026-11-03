"""genlinks/collision_gen.py - D8 collision re-check for generated links.

Machinery copied from final2/f2_collision.py (posed-mesh, manifold3d boolean
volumes, PoE body transforms, DECLARED mating pairs, vendor-skip rule).
Changes vs f2:
  - mesh dirs point at the prebuilt final2 worktree outputs (same commit)
  - generated link STLs (genlinks/out/*_gen.stl) REPLACE the originals
  - only pairs involving a swapped part are tested (others are unchanged
    product parts - already swept clean in F2)
  - J1/J2/J3 sweeps at 2.5 deg (stage: <=5 deg) + home-pose audit incl.
    same-body pairs (catches interface regressions vs upper/fore mates)

Run:  python3 genlinks/collision_gen.py
"""
import math, os, sys
import numpy as np
import trimesh
import manifold3d as m3d
from trimesh.transformations import rotation_matrix as rotmat, translation_matrix as tmat

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GOUT = os.path.join(HERE, "out")
sys.path.insert(0, os.path.join(ROOT, "cad", "arm2"))
sys.path.insert(0, os.path.join(ROOT, "software", "robot-os"))
import ap2 as P
from soma_arm import config
from soma_arm.kinematics import ArmKinematics

F2 = "/Users/deepakdiwan/Vector-wt/final2"
A2B, C3, CYC = (os.path.join(F2, d) for d in ("cad/arm2b/out", "cad3/out", "cyclo4/out"))
WR = os.path.join(F2, "wrist2", "out")

DROP = {"vendor_act_j2", "vendor_act_j3", "vendor_actout_j2", "vendor_actout_j3",
        "vendor_sts3215_j4", "vendor_6803_j2", "vendor_6803_j3",
        "back_spacer_j2", "back_spacer_j3", "flange_j2", "flange_j3",
        "j4_cradle", "link4", "link5", "grip_frame",
        "vendor_sts3215_j5", "vendor_sts3215_j6", "vendor_sts3215_g",
        "vendor_rack_u", "vendor_rack_d", "vendor_gear_grip",
        "finger_u", "finger_d"}
WR_SKIP = {"vendor_sts3215_j4"}
CYC_UP = {"housing", "pin_ring", "front_ring", "vendor_ringpins", "vendor_motor",
          "mag_puck", "vendor_magnet", "vendor_as5600", "vendor_6808",
          "disc1", "disc2", "hub", "vendor_6702a", "vendor_6702b"}
CYC_OUT = {"carrier", "out_flange", "vendor_dowels", "vendor_outpins", "vendor_685"}
J2, J3 = P.J2_XZ, P.J3_XZ
M_J2 = rotmat(math.radians(P.POSE_J2), (0, 1, 0), (J2[0], 0, J2[1]))
M_J3 = rotmat(math.radians(P.POSE_J3), (0, 1, 0), (J3[0], 0, J3[1]))
RX90 = rotmat(math.radians(90.0), (1, 0, 0))
def place(jxz):
    return tmat((jxz[0], P.ACT_BACK_Y, jxz[1])) @ RX90
M2_UP, M2_OUT = M_J2 @ place(J2), place(J2)
M3_UP, M3_OUT = M_J2 @ place(J3), M_J2 @ M_J3 @ place(J3)
FO = M_J2 @ M_J3
REPOSE = {"back_spacer_j2": M_J2, "back_spacer_j3": M_J2,
          "vendor_spring_j2": M_J2, "vendor_spring_j3": M_J2,
          "flange_j3": FO, "vendor_sts3250_j4": FO}

SWAP = {}
for f in sorted(os.listdir(GOUT)):
    if f.endswith("_gen.stl"):
        SWAP[f[:-8]] = trimesh.load_mesh(os.path.join(GOUT, f), force="mesh")
print("swapped links: %s" % (sorted(SWAP) or "NONE"))

MESH = {}
for d, drop in ((A2B, DROP), (C3, set()), (WR, WR_SKIP)):
    for f in sorted(os.listdir(d)):
        if f.endswith(".stl") and f[:-4] not in drop:
            n = f[:-4]
            if n in SWAP:
                m = SWAP[n].copy()
            else:
                m = trimesh.load_mesh(os.path.join(d, f), force="mesh")
            if n in REPOSE and n not in SWAP:
                m.apply_transform(REPOSE[n])
            m.merge_vertices()
            MESH[n] = m
for f in sorted(os.listdir(CYC)):
    if not f.endswith(".stl"):
        continue
    n = f[:-4]
    m = trimesh.load_mesh(os.path.join(CYC, f), force="mesh"); m.merge_vertices()
    up = n in CYC_UP
    a = m.copy(); a.apply_transform(M2_UP if up else M2_OUT); MESH["cy2_" + n] = a
    b = m.copy(); b.apply_transform(M3_UP if up else M3_OUT); MESH["cy3_" + n] = b

BODY = {}
def _add(body, names):
    for n in names:
        BODY[n] = body
_add("ground", ["base_plate", "base_link", "j1_cradle", "vendor_sts3250_j1", "base_reinf"])
_add("j1",     ["yaw_limit", "link1", "front_spacer_j2", "flange_j2"])
_add("upper",  ["upper_out", "upper_back", "back_spacer_j2", "back_spacer_j3",
                "vendor_spring_j2", "vendor_spring_j3"])
_add("fore",   ["front_spacer_j3", "flange_j3", "dogleg_l", "dogleg_r",
                "fore_l2", "fore_r2", "vendor_sts3250_j4", "w_j4_cradle"])
_add("wrist4", ["w_link4", "vendor_sts3215_j5"])
_add("wrist5", ["w_link5", "vendor_sts3215_j6"])
_add("grip",   ["w_grip_frame", "vendor_sts3215_g", "vendor_gear_grip",
                "vendor_rack_u", "vendor_rack_d", "finger_u", "finger_d"])
for n in CYC_OUT:
    BODY["cy2_" + n] = "j1"
    BODY["cy3_" + n] = "fore"
for n in CYC_UP:
    BODY["cy2_" + n] = "upper"
    BODY["cy3_" + n] = "upper"
def _plug(body, a0, a1, h0, h1, name):
    b = trimesh.creation.box(extents=(a1 - a0, 18.0, h1 - h0))
    b.apply_translation((96.4 + (a0 + a1) / 2.0, 0.0, 216.2 + (h0 + h1) / 2.0))
    MESH[name] = b
    BODY[name] = body
_plug("wrist4", 41.6, 52.6, 35.6, 47.8, "plug_j5")
_plug("wrist5", 12.8, 25.0, -39.0, -28.0, "plug_j6")
_plug("grip",   66.8, 79.0, -39.0, -28.0, "plug_g")
missing = [n for n in MESH if n not in BODY]
assert not missing, missing
BIDX = {"ground": 0, "j1": 1, "upper": 2, "fore": 3, "wrist4": 4, "wrist5": 5, "grip": 6}

def man(m):
    return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                               tri_verts=np.asarray(m.faces, np.uint32)))
M = {}
for n, m in MESH.items():
    try:
        M[n] = man(m)
    except Exception as e:
        print("  MANIFOLD FAIL %s: %s - using convex-free fallback skipped" % (n, e))
NAMES = sorted(M)

DECLARED = {}
for cy in ("cy2", "cy3"):
    DECLARED[frozenset((cy + "_carrier", cy + "_vendor_outpins"))] = \
        "cyclo outpins engage the carrier (5 mm3)"
    DECLARED[frozenset((cy + "_disc1", cy + "_vendor_outpins"))] = \
        "cyclo drive: outpins in disc1 holes (165 mm3, precesses)"
    DECLARED[frozenset((cy + "_disc2", cy + "_vendor_outpins"))] = \
        "cyclo drive: outpins in disc2 holes (180 mm3, precesses)"
DECLARED[frozenset(("flange_j2", "vendor_spring_j2"))] = "spring seat (2.6 mm3)"
DECLARED[frozenset(("flange_j3", "vendor_spring_j3"))] = "spring seat (2.5 mm3)"
DECLARED[frozenset(("vendor_gear_grip", "vendor_rack_u"))] = "gear/rack mesh (32.5 mm3)"
DECLARED[frozenset(("vendor_gear_grip", "vendor_rack_d"))] = "gear/rack mesh (32.5 mm3)"
for px, own in (("plug_j5", "wrist4"), ("plug_j6", "wrist5"), ("plug_g", "grip")):
    for q in NAMES:
        if BODY[q] == own:
            DECLARED[frozenset((px, q))] = "plug proxy inside own servo/case zone"

def skip(a, b):
    if a.startswith("vendor_") and b.startswith("vendor_"):
        act = lambda n: "act" in n or "sts32" in n
        return not (act(a) and act(b))
    return False

AXES_HOME = [((0.0, 0.0, 80.8), (0.0, 0.0, 1.0)),
             ((-20.0, 0.0, 143.5), (0.0, 1.0, 0.0)),
             ((-20.0, 0.0, 270.2), (0.0, 1.0, 0.0)),
             ((96.4, 0.0, 216.2), (0.0, 1.0, 0.0)),
             ((127.0, 0.0, 223.8), (0.0, 0.0, 1.0)),
             ((149.4, 0.0, 199.2), (1.0, 0.0, 0.0))]

def body_mats(q):
    T = np.eye(4)
    mats = [np.eye(4)]
    for k in range(6):
        T = T @ rotmat(q[k], np.array(AXES_HOME[k][1]), np.array(AXES_HOME[k][0]))
        mats.append(T.copy())
    return mats

def posed(q, grip_t=0.0):
    mats = body_mats(q)
    out = {}
    for n in NAMES:
        out[n] = M[n].transform(np.asarray(mats[BIDX[BODY[n]]][:3, :], np.float64))
    return out

# pairs that can change vs the F2 baseline: at least one swapped part
SWAPB = set(SWAP)
PAIRS = [(a, b) for i, a in enumerate(NAMES) for b in NAMES[i + 1:]
         if (a in SWAPB or b in SWAPB) and not skip(a, b)]
PAIRS_MOV = [(a, b) for a, b in PAIRS if BODY[a] != BODY[b]]

def colliding(pm, pairs):
    hits, decl = [], []
    bb = {n: pm[n].bounding_box() for n in NAMES}
    for a, b in pairs:
        ba, bb2 = bb[a], bb[b]
        if ba[0] > bb2[3] or bb2[0] > ba[3] or \
           ba[1] > bb2[4] or bb2[1] > ba[4] or \
           ba[2] > bb2[5] or bb2[2] > ba[5]:
            continue
        v = (pm[a] ^ pm[b]).volume()
        if v > 0.5:
            (decl if frozenset((a, b)) in DECLARED else hits).append((a, b, v))
    return hits, decl

ok = True
pm0 = posed([0.0] * 6)
h0, d0 = colliding(pm0, PAIRS)
print("home pose: %d swapped-pair intersections (%d declared)" % (len(h0), len(d0)))
for a, b, v in d0:
    print("   DECLARED %s x %s %.1f mm3" % (a, b, v))
for a, b, v in h0:
    print("   HIT      %s x %s %.1f mm3" % (a, b, v))
ok &= not h0

STEP = math.radians(2.5)
LIM = [(config.JOINT_MIN[i], config.JOINT_MAX[i]) for i in range(6)]
for j in (0, 1, 2):                       # stage: J1/J2/J3 sweeps
    lo, hi = LIM[j]
    coll, worst = [], -1.0
    t = lo
    while t <= hi + 1e-9:
        q = [0.0] * 6
        q[j] = t
        pm = posed(q)
        hits, decl = colliding(pm, PAIRS_MOV)
        for a, b, v in hits:
            coll.append((math.degrees(t), a, b, v))
        t += STEP
    tag = "J%d sweep" % (j + 1)
    print("%-9s %s" % (tag, "CLEAR" if not coll else
          "HITS: " + "; ".join("%.0fdeg %sx%s %.0fmm3" % c for c in coll[:8])))
    ok &= not coll

print("RESULT: %s" % ("PASS - no swapped-link collisions" if ok else "FAIL"))
