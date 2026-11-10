"""fullcheck/fc_mcclass.py - classify the Monte-Carlo collision families.

Replays the same seeded pose set as fc_collision.py (rng 20261103, 1200
poses) and bins every undeclared hit into a named family so the report
can quote real counts instead of one "1377 hits" number.

Run: $PY fullcheck/fc_mcclass.py
"""
import math, os, sys, collections
import numpy as np
import trimesh
import manifold3d as m3d
from trimesh.transformations import rotation_matrix as rotmat, translation_matrix as tmat

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "cad", "arm2"))
sys.path.insert(0, os.path.join(ROOT, "software", "robot-os"))
import ap2 as P
from soma_arm import config

A2B, C3, CYC = (os.path.join(ROOT, d) for d in ("cad/arm2b/out", "cad3/out", "cyclo4/out"))
WR = os.path.join(ROOT, "refine", "out")

DROP = {"vendor_act_j2", "vendor_act_j3", "vendor_actout_j2", "vendor_actout_j3",
        "vendor_sts3215_j4", "vendor_6803_j2", "vendor_6803_j3",
        "back_spacer_j2", "back_spacer_j3", "flange_j2", "flange_j3",
        "j4_cradle", "link4", "link5", "grip_frame",
        "vendor_sts3215_j5", "vendor_sts3215_j6", "vendor_sts3215_g",
        "vendor_rack_u", "vendor_rack_d", "vendor_gear_grip",
        "finger_u", "finger_d"}
WR_PARTS = ["w_j4_cradle", "w_link4", "w_link5", "wrist_pin", "w_grip_frame",
            "vendor_sts3215_j5", "vendor_sts3215_j6", "vendor_sts3215_g",
            "vendor_gear_grip", "vendor_rack_u", "vendor_rack_d",
            "finger_u", "finger_d"]
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

MESH = {}
for d, drop in ((A2B, DROP), (C3, set()), (WR, set())):
    for f in sorted(os.listdir(d)):
        n = f[:-4]
        if f.endswith(".stl") and n not in drop and \
           (d is not WR or n in WR_PARTS):
            m = trimesh.load_mesh(os.path.join(d, f), force="mesh")
            if n in REPOSE:
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
                "fore_l2", "fore_r2", "vendor_sts3250_j4", "w_j4_cradle", "wrist_pin"])
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
_plug("grip", 66.8, 79.0, -39.0, -28.0, "plug_g")
missing = [n for n in MESH if n not in BODY]
assert not missing, missing
BIDX = {"ground": 0, "j1": 1, "upper": 2, "fore": 3, "wrist4": 4, "wrist5": 5, "grip": 6}

def man(m):
    return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                               tri_verts=np.asarray(m.faces, np.uint32)))
M = {n: man(m) for n, m in MESH.items()}
NAMES = sorted(M)

DECLARED = set()
for cy in ("cy2", "cy3"):
    for pair in (("carrier", "vendor_outpins"), ("disc1", "vendor_outpins"),
                 ("disc2", "vendor_outpins")):
        DECLARED.add(frozenset((cy + "_" + pair[0], cy + "_" + pair[1])))
for p in (("flange_j2", "vendor_spring_j2"), ("flange_j3", "vendor_spring_j3"),
          ("vendor_gear_grip", "vendor_rack_u"), ("vendor_gear_grip", "vendor_rack_d"),
          ("wrist_pin", "w_j4_cradle"), ("wrist_pin", "w_link4")):
    DECLARED.add(frozenset(p))
for px, own in (("plug_j5", "wrist4"), ("plug_j6", "wrist5"), ("plug_g", "grip")):
    for q in NAMES:
        if BODY[q] == own:
            DECLARED.add(frozenset((px, q)))

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
    out = {n: M[n].transform(np.asarray(mats[BIDX[BODY[n]]][:3, :], np.float64))
           for n in NAMES}
    if grip_t:
        Rg = mats[6][:3, :3]
        du = Rg @ np.array([0.0, 1.0, 0.0])
        for n, sgn in (("finger_u", 1), ("finger_d", -1),
                       ("vendor_rack_u", 1), ("vendor_rack_d", -1)):
            out[n] = out[n].translate((sgn * grip_t * du).tolist())
        c_h = np.append(np.asarray(MESH["vendor_gear_grip"].bounds).mean(axis=0), 1.0)
        c_w = (mats[6] @ c_h)[:3]
        R = rotmat(math.radians(grip_t / 12.5 * 90.0), Rg @ np.array([1.0, 0.0, 0.0]), c_w)
        out["vendor_gear_grip"] = out["vendor_gear_grip"].transform(np.asarray(R[:3], np.float64))
    return out

PAIRS = [(a, b) for i, a in enumerate(NAMES) for b in NAMES[i + 1:]
         if not skip(a, b) and BODY[a] != BODY[b]]
LIM = [(config.JOINT_MIN[i], config.JOINT_MAX[i]) for i in range(6)]

def fam(a, b, q):
    s = {a, b}
    if s == {"base_reinf", "yaw_limit"} or s == {"base_link", "yaw_limit"}:
        return "J1 yaw hard stop (q1 < -152 deg, designed stop)"
    if "cy2" in a or "cy2" in b:
        return "wrist folds into J2 cyclo (J2<-100,J3>+20)"
    if BODY[a] == "ground" or BODY[b] == "ground" or \
       BODY[a] == "j1" or BODY[b] == "j1":
        return "arm into base/j1 (extreme fold)"
    if BIDX[BODY[a]] >= 3 and BIDX[BODY[b]] >= 3:
        return "wrist-internal compounded fold"
    return "other"

rng = np.random.default_rng(20261103)
hits_by_fam = collections.Counter()
poses_hit = collections.Counter()
wrist_poses = []
total = 0
for it in range(1200):
    q = [rng.uniform(lo, hi) for lo, hi in LIM]
    gt = rng.uniform(0.0, 12.5)
    pm = posed(q, gt)
    bb = {n: pm[n].bounding_box() for n in NAMES}
    pose_hits = set()
    for a, b in PAIRS:
        ba, bb2 = bb[a], bb[b]
        if ba[0] > bb2[3] or bb2[0] > ba[3] or \
           ba[1] > bb2[4] or bb2[1] > ba[4] or \
           ba[2] > bb2[5] or bb2[2] > ba[5]:
            continue
        v = (pm[a] ^ pm[b]).volume()
        if v > 0.5 and frozenset((a, b)) not in DECLARED:
            total += 1
            f = fam(a, b, q)
            hits_by_fam[f] += 1
            pose_hits.add(f)
            if f == "wrist-internal compounded fold":
                wrist_poses.append((it, [round(math.degrees(x)) for x in q], a, b, round(v, 1)))
    for f in pose_hits:
        poses_hit[f] += 1

print("== MC 1200 poses, undeclared hits by family ==")
for f, c in hits_by_fam.most_common():
    print("   %5d hits in %4d poses  %s" % (c, poses_hit[f], f))
print("   %5d TOTAL hits" % total)
print("\nwrist-internal poses (sample):")
for it, q, a, b, v in wrist_poses[:20]:
    print("   pose %d q=%s  %s x %s %.0f mm3" % (it, q, a, b, v))
# how many wrist-internal hits survive the D9 J6 sublimit (J5<0 -> |J6|<110)?
sublim = [x for x in wrist_poses
          if not (x[1][4] < 0 and abs(x[1][5]) > 110)]
print("\nwrist-internal hits NOT excluded by the D9 J6-sublimit: %d of %d"
      % (len(sublim), len(wrist_poses)))
for it, q, a, b, v in sublim[:15]:
    print("   pose %d q=%s  %s x %s %.0f mm3" % (it, q, a, b, v))
