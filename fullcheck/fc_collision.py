"""fullcheck/fc_collision.py - whole-arm collision + clearance check, R9 wrist.

Same method as final2/f2_collision.py (posed manifold solids, boolean
volume, PoE body transforms checked against robot-os FK) but loads the
R9 wrist from refine/out (posed w_*.stl + wrist_pin) instead of
wrist2/out, and adds a designed-fit table + exact minimum-distance
probes on the tightest pairs.

Two configs:
  --grip   (default) direct R9 gripper: w_grip_frame + racks/gear/fingers
  --tc     tool-changer: tc_master + fix_tool_grip + tc grip parts
           (requires toolchg/out STLs - build_toolchg.py)

Run:  $PY fullcheck/fc_collision.py [--tc]
"""
import math, os, sys
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
from soma_arm.kinematics import ArmKinematics

A2B, C3, CYC = (os.path.join(ROOT, d) for d in ("cad/arm2b/out", "cad3/out", "cyclo4/out"))
WR = os.path.join(ROOT, "refine", "out")
TC_OUT = os.path.join(ROOT, "toolchg", "out")
TC = "--tc" in sys.argv

# arm2b drop list identical to f2 (drops its own wrist + vendor wrist parts)
DROP = {"vendor_act_j2", "vendor_act_j3", "vendor_actout_j2", "vendor_actout_j3",
        "vendor_sts3215_j4", "vendor_6803_j2", "vendor_6803_j3",
        "back_spacer_j2", "back_spacer_j3", "flange_j2", "flange_j3",
        "j4_cradle", "link4", "link5", "grip_frame",
        "vendor_sts3215_j5", "vendor_sts3215_j6", "vendor_sts3215_g",
        "vendor_rack_u", "vendor_rack_d", "vendor_gear_grip",
        "finger_u", "finger_d"}
# R9 wrist part set (posed world-frame STLs in refine/out); wrist_pin is
# present in both end-effector configs (it is the J4 journal pin).
WR_PARTS = ["w_j4_cradle", "w_link4", "w_link5", "wrist_pin",
            "vendor_sts3215_j5", "vendor_sts3215_j6"]
TC_PARTS = ["tc_master", "fix_tool_grip_posed", "tc_vendor_g", "tc_gear",
            "tc_rack_u", "tc_rack_d", "tc_finger_u", "tc_finger_d"]
if TC:
    WR_PARTS += TC_PARTS
else:
    WR_PARTS += ["w_grip_frame", "vendor_sts3215_g",
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
for d, drop in ((A2B, DROP), (C3, set())):
    for f in sorted(os.listdir(d)):
        if f.endswith(".stl") and f[:-4] not in drop:
            m = trimesh.load_mesh(os.path.join(d, f), force="mesh")
            if f[:-4] in REPOSE:
                m.apply_transform(REPOSE[f[:-4]])
            m.merge_vertices()
            MESH[f[:-4]] = m
wrd = TC_OUT if TC else WR
for n in WR_PARTS:
    p = os.path.join(wrd, n + ".stl")
    if not os.path.exists(p):
        p = os.path.join(WR, n + ".stl")
    m = trimesh.load_mesh(p, force="mesh"); m.merge_vertices()
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
if TC:
    _add("grip", ["tc_master", "fix_tool_grip_posed", "tc_vendor_g", "tc_gear",
                  "tc_rack_u", "tc_rack_d", "tc_finger_u", "tc_finger_d"])
else:
    _add("grip", ["w_grip_frame", "vendor_sts3215_g", "vendor_gear_grip",
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
if not TC:
    _plug("grip", 66.8, 79.0, -39.0, -28.0, "plug_g")
missing = [n for n in MESH if n not in BODY]
assert not missing, missing
BIDX = {"ground": 0, "j1": 1, "upper": 2, "fore": 3, "wrist4": 4, "wrist5": 5, "grip": 6}

def man(m):
    return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                               tri_verts=np.asarray(m.faces, np.uint32)))
M = {n: man(m) for n, m in MESH.items()}
NAMES = sorted(M)

DECLARED = {}
for cy in ("cy2", "cy3"):
    DECLARED[frozenset((cy + "_carrier", cy + "_vendor_outpins"))] = \
        "cyclo outpins engage the carrier"
    DECLARED[frozenset((cy + "_disc1", cy + "_vendor_outpins"))] = \
        "cyclo drive: outpins in disc1 holes (precesses)"
    DECLARED[frozenset((cy + "_disc2", cy + "_vendor_outpins"))] = \
        "cyclo drive: outpins in disc2 holes (precesses)"
DECLARED[frozenset(("flange_j2", "vendor_spring_j2"))] = "spring seat"
DECLARED[frozenset(("flange_j3", "vendor_spring_j3"))] = "spring seat"
if not TC:
    DECLARED[frozenset(("vendor_gear_grip", "vendor_rack_u"))] = "gear/rack mesh"
    DECLARED[frozenset(("vendor_gear_grip", "vendor_rack_d"))] = "gear/rack mesh"
    DECLARED[frozenset(("wrist_pin", "w_j4_cradle"))] = "pin in cradle bore (designed fit)"
    DECLARED[frozenset(("wrist_pin", "w_link4"))] = "journal pin in boss bore (designed fit)"
    DECLARED[frozenset(("wrist_pin", "fore_r2"))] = "pin tail vs fore_r2 (check overlap)"
else:
    DECLARED[frozenset(("tc_gear", "tc_rack_u"))] = "gear/rack mesh"
    DECLARED[frozenset(("tc_gear", "tc_rack_d"))] = "gear/rack mesh"
    DECLARED[frozenset(("tc_master", "tool_grip"))] = "tool docked to master (designed fit)"
for px, own in (("plug_j5", "wrist4"), ("plug_j6", "wrist5"), ("plug_g", "grip")):
    if px not in MESH:
        continue
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
KIN = ArmKinematics()
_t = KIN.fk_matrix([0, 0, 0, 0, 0, 0])
if not TC:
    assert abs(MESH["finger_u"].bounds[1][0] - 233.8) < 0.5
    assert abs(_t[0, 3] * 1000 - 233.8) < 0.5 and abs(_t[2, 3] * 1000 - 199.2) < 0.5

def _tcp_point(q):
    TCP_HOME = np.array([233.8, 0.0, 199.2, 1.0])
    mesh_tcp = body_mats(q)[6] @ TCP_HOME
    fk_tcp = KIN.fk_matrix(q)[:3, 3] * 1000.0
    return float(np.linalg.norm(mesh_tcp[:3] - fk_tcp))

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
    if grip_t:
        Rg = mats[6][:3, :3]
        du = Rg @ np.array([0.0, 1.0, 0.0])
        grp = {"finger_u": ("finger_u", 1), "finger_d": ("finger_d", -1),
               "vendor_rack_u": ("vendor_rack_u", 1), "vendor_rack_d": ("vendor_rack_d", -1),
               "vendor_gear_grip": "gear"} if not TC else \
              {"finger_u": ("tc_finger_u", 1), "finger_d": ("tc_finger_d", -1),
               "vendor_rack_u": ("tc_rack_u", 1), "vendor_rack_d": ("tc_rack_d", -1),
               "vendor_gear_grip": "gear"}
        for k, v in grp.items():
            if v == "gear":
                continue
            nm, sgn = v
            out[nm] = out[nm].translate((sgn * grip_t * du).tolist())
        gear_name = "vendor_gear_grip" if not TC else "tc_gear"
        c_h = np.append(np.asarray(MESH[gear_name].bounds).mean(axis=0), 1.0)
        c_w = (mats[6] @ c_h)[:3]
        R = rotmat(math.radians(grip_t / 12.5 * 90.0), Rg @ np.array([1.0, 0.0, 0.0]), c_w)
        out[gear_name] = out[gear_name].transform(np.asarray(R[:3], np.float64))
    return out

for _q in ([0.5, 0.3, -0.7, 0.4, -0.5, 0.2], [0, 1.22, -0.09, -1.13, 0, 0],
           [-1.0, -0.8, 0.5, 0.6, 0.7, -1.2]):
    assert _tcp_point(_q) < 1.0, (_q, _tcp_point(_q))

def pair_ok(a, b):
    return not skip(a, b) and BODY[a] != BODY[b]
PAIRS_ALL = [(a, b) for i, a in enumerate(NAMES) for b in NAMES[i + 1:] if pair_ok(a, b)]
PAIRS_HOME = [(a, b) for i, a in enumerate(NAMES) for b in NAMES[i + 1:] if not skip(a, b)]
GRIP_GROUP = {"finger_u": "U", "vendor_rack_u": "U",
              "finger_d": "D", "vendor_rack_d": "D", "vendor_gear_grip": "G"} if not TC else \
             {"tc_finger_u": "U", "tc_rack_u": "U",
              "tc_finger_d": "D", "tc_rack_d": "D", "tc_gear": "G"}
PAIRS_GRIP = PAIRS_ALL + [
    (a, b) for i, a in enumerate(NAMES) for b in NAMES[i + 1:]
    if BODY[a] == BODY[b] == "grip" and not skip(a, b)
    and GRIP_GROUP.get(a) != GRIP_GROUP.get(b)]

def sweep_pairs(k):
    return [(a, b) for a, b in PAIRS_ALL
            if (BIDX[BODY[a]] >= k) != (BIDX[BODY[b]] >= k)]

def colliding(pm, pairs):
    hits, decl = [], []
    mn = math.inf
    bb = {n: pm[n].bounding_box() for n in NAMES}
    for a, b in pairs:
        ba, bb2 = bb[a], bb[b]
        if ba[0] > bb2[3] or bb2[0] > ba[3] or \
           ba[1] > bb2[4] or bb2[1] > ba[4] or \
           ba[2] > bb2[5] or bb2[2] > ba[5]:
            g = max(ba[0] - bb2[3], bb2[0] - ba[3],
                    ba[1] - bb2[4], bb2[1] - ba[4],
                    ba[2] - bb2[5], bb2[2] - ba[5])
            if g < mn:
                mn = g
            continue
        v = (pm[a] ^ pm[b]).volume()
        if v > 0.5:
            if frozenset((a, b)) in DECLARED:
                decl.append((a, b, v))
            else:
                hits.append((a, b, v))
        else:
            mn = min(mn, 0.0)
    return hits, decl, mn

def minz(pm):
    return min(pm[n].bounding_box()[2] for n in NAMES)

ok = True
def res(tag, good, msg):
    global ok
    ok &= bool(good)
    print("%-6s %-72s %s" % (tag, msg, "PASS" if good else "FAIL"), flush=True)

STEP = math.radians(2.5)
LIM = [(config.JOINT_MIN[i], config.JOINT_MAX[i]) for i in range(6)]
REPORT = {}

pm0 = posed([0.0] * 6, 0.0)
h0, d0, _ = colliding(pm0, PAIRS_HOME)
print("home-pose intersecting pairs: %d declared, %d undeclared" % (len(d0), len(h0)))
for a, b, v in d0:
    print("   DECLARED %s x %s %.1f mm3  (%s)" % (a, b, v, DECLARED[frozenset((a, b))]))
for a, b, v in h0:
    print("   UNDECLARED %s x %s %.1f mm3" % (a, b, v))
res("HOME", not h0, "home pose clear of undeclared intersections")

print("== per-joint sweeps (step 2.5 deg, others 0, grip closed) ==")
for j in range(6):
    lo, hi = LIM[j]
    rows = []
    pk = sweep_pairs(j + 1)
    t = lo
    while t <= hi - 1e-9:
        q = [0.0] * 6
        q[j] = t
        pm = posed(q)
        hits, decl, gap = colliding(pm, pk)
        rows.append((math.degrees(t), hits, decl, gap, minz(pm)))
        t += STEP
    q = [0.0] * 6
    q[j] = hi
    pm = posed(q)
    hits, decl, gap = colliding(pm, pk)
    rows.append((math.degrees(hi), hits, decl, gap, minz(pm)))
    coll = [(a_, h) for a_, h, d, g, z in rows if h]
    gap = min(g for a_, h, d, g, z in rows)
    zmin = min(z for a_, h, d, g, z in rows)
    REPORT["J%d" % (j + 1)] = (coll, gap, zmin)
    txt = "J%d swept %+.0f..%+.0f: min bbox gap %.1f mm, min z %.1f mm" % (
        j + 1, math.degrees(lo), math.degrees(hi), gap, zmin)
    if coll:
        seen = []
        for a_, hh in coll:
            for a, b, v in hh:
                seen.append("%+.1fdeg %s x %s %.0fmm3" % (a_, a, b, v))
        txt += "  COLLISIONS: " + "; ".join(seen[:12])
    res("SWEEP", not coll and zmin > -0.05, txt)

rows = []
for t in np.linspace(0.0, 12.5, 26):
    pm = posed([0.0] * 6, t)
    hits, decl, gap = colliding(pm, PAIRS_GRIP)
    rows.append((2 * t, hits, gap, minz(pm)))
coll = [(a_, h) for a_, h, g, z in rows if h]
gap = min(g for a_, h, g, z in rows)
REPORT["grip"] = (coll, gap, min(z for a_, h, g, z in rows))
res("SWEEP", not coll, "gripper 0..25 mm: min bbox gap %.1f mm%s"
    % (gap, "  COLLISIONS " + str(coll[:8]) if coll else ""))

print("== named + corner poses ==")
def fk_tcp(q):
    return KIN.fk_matrix(q)[:3, 3] * 1000.0
g2 = np.arange(LIM[1][0], LIM[1][1] + 1e-9, math.radians(5))
g3 = np.arange(LIM[2][0], LIM[2][1] + 1e-9, math.radians(5))
fx, fz, fmin = (-1e9, None), (-1e9, None), (1e9, None)
for q2 in g2:
    for q3 in g3:
        q4 = -(q2 + q3)
        if not (LIM[3][0] <= q4 <= LIM[3][1]):
            continue
        tcp = fk_tcp([0, q2, q3, q4, 0, 0])
        if tcp[0] > fx[0]:
            fx = (tcp[0], [0, q2, q3, q4, 0, 0])
        if tcp[2] > fz[0]:
            fz = (tcp[2], [0, q2, q3, q4, 0, 0])
        if tcp[2] < fmin[0]:
            fmin = (tcp[2], [0, q2, q3, q4, 0, 0])
NAMED = {
    "home": [0, 0, 0, 0, 0, 0],
    "stow": [0, math.radians(70), math.radians(-160), math.radians(70), 0, 0],
    "reach-forward": fx[1],
    "reach-up": fz[1],
    "reach-down": fmin[1],
    "wrist-fully-flexed": [0, math.radians(45), math.radians(-45),
                           math.radians(70), math.radians(70), 0],
}
for nm, q in NAMED.items():
    tcp = fk_tcp(q)
    pm = posed(q)
    hits, decl, gap = colliding(pm, PAIRS_ALL)
    z = minz(pm)
    pm2 = posed(q, 12.5)
    hits2, _, _ = colliding(pm2, PAIRS_ALL)
    allh = hits + hits2
    res("POSE", not allh and z > -0.05,
        "%-19s q=%s tcp=(%.0f,%.0f,%.0f) z_min %.1f %s"
        % (nm, np.round(np.degrees(q), 1).tolist(), tcp[0], tcp[1], tcp[2], z,
           ("COLLISIONS " + str(allh)) if allh else "clean"))
for q2 in LIM[1]:
    for q3 in LIM[2]:
        for q4 in LIM[3]:
            q = [0, q2, q3, q4, 0, 0]
            pm = posed(q)
            hits, decl, gap = colliding(pm, PAIRS_ALL)
            z = minz(pm)
            tag = "J2%+.0f J3%+.0f J4%+.0f" % tuple(np.degrees([q2, q3, q4]))
            res("CORNER", not hits and z > -0.05,
                "%s min z %.1f %s" % (tag, z, ("COLLISIONS " + str(hits)) if hits else "clean"))

print("== Monte-Carlo 1200 poses (uniform in limits, grip 0..25 mm) ==")
rng = np.random.default_rng(20261103)
mc_hits = []
mc_gap = math.inf
mc_z = math.inf
DECL_RANGE = {}
for it in range(1200):
    q = [rng.uniform(lo, hi) for lo, hi in LIM]
    gt = rng.uniform(0.0, 12.5)
    pm = posed(q, gt)
    hits, decl, gap = colliding(pm, PAIRS_ALL)
    z = minz(pm)
    mc_gap = min(mc_gap, gap)
    mc_z = min(mc_z, z)
    for a, b, v in hits:
        mc_hits.append((it, np.round(np.degrees(q), 1).tolist(), round(gt, 1), a, b, round(v, 1)))
    for a, b, v in decl:
        k = (a, b)
        lo_, hi_ = DECL_RANGE.get(k, (v, v))
        DECL_RANGE[k] = (min(lo_, v), max(hi_, v))
res("MC", not mc_hits and mc_z > -0.05,
    "1200 poses: min bbox gap %.1f, min z %.1f, undeclared collisions %d"
    % (mc_gap, mc_z, len(mc_hits)))
for h in mc_hits[:40]:
    print("   MC pose %d q=%s grip %.1f: %s x %s %.0f mm3" % h)

# ================= exact min-distance probes on tight pairs =================
# Designed-fit pairs have their own clearance spec (journal 0.20, gear
# mesh etc.) - probe them at home and report the measured gap.
print("== exact minimum-distance probes (surface+vertex sampling, mm) ==")
from trimesh.proximity import closest_point

def mesh_min_dist(ma, mb):
    """min surface distance estimate: verts+surface samples of a -> b."""
    pa = np.vstack([ma.vertices, ma.sample(3000)])
    _, d, _ = closest_point(mb, pa)
    return float(d.min())

PROBE = [("w_link4", "w_j4_cradle", "yoke plate / journal vs cradle - design 0.2 rad, 0.5 face"),
         ("wrist_pin", "w_link4", "d3 journal in boss bore - design 0.20 rad"),
         ("wrist_pin", "w_j4_cradle", "pin in cradle bore - designed fit"),
         ("w_link4", "fore_r2", "l4 vs fore_r2"),
         ("w_link5", "w_link4", "l5 vs l4 home"),
         ("vendor_sts3215_j5", "w_link4", "j5 case in cradle"),
         ("vendor_sts3215_j6", "w_link5", "j6 case in l5")]
if not TC:
    PROBE += [("w_grip_frame", "w_link5", "gf horn plate vs l5 - design ~0.8"),
              ("w_grip_frame", "w_link4", "gf ribs vs l4 collar - design ~0.8"),
              ("vendor_gear_grip", "w_grip_frame", "gear vs cage bore"),
              ("plug_j5", "w_link5", "j5 cable plug vs l5"),
              ("plug_j6", "w_grip_frame", "j6 plug vs gf"),
              ("plug_g", "w_link5", "g plug vs l5")]
else:
    PROBE += [("tc_master", "w_link5", "master plate vs l5"),
              ("fix_tool_grip_posed", "w_link5", "tool cage vs l5"),
              ("fix_tool_grip_posed", "w_link4", "tool cage vs l4 collar")]
pm0 = posed([0.0] * 6)
def to_tm(mf):
    mm = mf.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mm.vert_properties[:, :3]),
                           faces=np.asarray(mm.tri_verts), process=False)
for a, b, note in PROBE:
    try:
        ma, mb = to_tm(pm0[a]), to_tm(pm0[b])
        d = min(mesh_min_dist(ma, mb), mesh_min_dist(mb, ma))
        print("   %-20s x %-20s %7.3f mm   %s" % (a, b, d, note))
    except Exception as e:
        print("   %-20s x %-20s  ERR %s" % (a, b, e))

print("== per-joint summary ==")
print("%-8s %-18s %-12s %-10s %s" % ("joint", "range swept", "min gap mm", "min z mm", "verdict"))
for k in ("J1", "J2", "J3", "J4", "J5", "J6", "grip"):
    coll, gap, zmin = REPORT[k]
    rngtxt = "0..25 mm" if k == "grip" else "%+.0f..%+.0f deg" % (
        math.degrees(LIM[int(k[1]) - 1][0]), math.degrees(LIM[int(k[1]) - 1][1]))
    print("%-8s %-18s %-12.1f %-10.1f %s" % (k, rngtxt, gap, zmin, "FAIL" if coll else "PASS"))
print("CHECKS", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
