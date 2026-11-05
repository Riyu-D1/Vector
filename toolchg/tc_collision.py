"""toolchg/tc_collision.py - D10 posed-mesh collision sim (f2_collision.py
pattern, same loaders/machinery; new files only).

Part set = final2 grip set replaced by the D10 toolchanger:
  grip body  = tc_master + tool_grip (socket plate + shifted gripper) +
               tc_vendor_g + tc_gear + tc_rack_u/d + tc_finger_u/d +
               shifted plug proxy (plug_g_tc at a+TC_SH)
  ground    += tc_rack (world frame) + docked tool copies per rack slot

Checks:
  A) J4/J5/J6 envelope sweeps of the new end (J6 sublimit honoured when
     J5 < 0), named/corner poses, Monte-Carlo - vs the unchanged arm.
  B) dock path per rack slot: approach -> insert -> lock-roll -> lift,
     interpolated; arm vs rack + docked tools; the master x docked-tool
     engagement volume is measured and declared (it is the designed
     capture), as is the tool x rack groove seat.

Run: $PY toolchg/tc_collision.py
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
from soma_arm import toolchange as TC
from soma_arm.kinematics import ArmKinematics
import tc_params as T

A2B, C3, CYC = (os.path.join(ROOT, d) for d in ("cad/arm2b/out", "cad3/out", "cyclo4/out"))
WR = os.path.join(ROOT, "wrist2", "out")
TCOUT = os.path.join(HERE, "out")

# ---- part loading: final2 set minus the replaced grip set ----
DROP = {"vendor_act_j2", "vendor_act_j3", "vendor_actout_j2", "vendor_actout_j3",
        "vendor_sts3215_j4", "vendor_6803_j2", "vendor_6803_j3",
        "back_spacer_j2", "back_spacer_j3", "flange_j2", "flange_j3",
        "j4_cradle", "link4", "link5", "grip_frame",
        "vendor_sts3215_j5", "vendor_sts3215_j6", "vendor_sts3215_g",
        "vendor_rack_u", "vendor_rack_d", "vendor_gear_grip",
        "finger_u", "finger_d"}
# D10: the wrist2 grip set is replaced by toolchg parts
WR_DROP = {"w_grip_frame", "vendor_sts3215_g", "vendor_gear_grip",
           "vendor_rack_u", "vendor_rack_d", "finger_u", "finger_d",
           "vendor_sts3215_j4"}
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
for d, drop in ((A2B, DROP), (C3, set()), (WR, WR_DROP)):
    for f in sorted(os.listdir(d)):
        if f.endswith(".stl") and f[:-4] not in drop:
            m = trimesh.load_mesh(os.path.join(d, f), force="mesh")
            if f[:-4] in REPOSE:
                m.apply_transform(REPOSE[f[:-4]])
            m.merge_vertices()
            MESH[f[:-4]] = m
for f in sorted(os.listdir(CYC)):
    if not f.endswith(".stl"):
        continue
    n = f[:-4]
    m = trimesh.load_mesh(os.path.join(CYC, f), force="mesh"); m.merge_vertices()
    up = n in CYC_UP
    a = m.copy(); a.apply_transform(M2_UP if up else M2_OUT); MESH["cy2_" + n] = a
    b = m.copy(); b.apply_transform(M3_UP if up else M3_OUT); MESH["cy3_" + n] = b

# D10 toolchanger parts (home-posed like wrist2) -----------------------
TC_TOOL = ["tool_grip", "tc_vendor_g", "tc_gear", "tc_rack_u", "tc_rack_d",
           "tc_finger_u", "tc_finger_d"]
TC_ARM = ["tc_master"]
for f in sorted(os.listdir(TCOUT)):
    if not f.endswith(".stl"):
        continue
    n = f[:-4]
    if n == "tc_rack" or n in TC_TOOL or n in TC_ARM:
        m = trimesh.load_mesh(os.path.join(TCOUT, f), force="mesh")
        m.merge_vertices()
        MESH[n] = m

# dock transforms: home coords -> slot k (pure translation; axes map
# +a->+x, +b->+y, +h->+z in both poses)
def dock_tmat(slot):
    return tmat((TC.dock_origin_x() - 96.4,
                 TC.slot_y(slot),
                 127.0 - 216.2))

DOCK_SLOT = 2                       # slot the engaged tool lives in
PEN_SLOT = 0                        # a second tool parked in the rack
for n in TC_TOOL:
    m = MESH[n].copy()
    m.apply_transform(dock_tmat(DOCK_SLOT))
    MESH["tdock_" + n] = m
m = trimesh.load_mesh(os.path.join(TCOUT, "tool_pen.stl"), force="mesh")
m.merge_vertices()
m.apply_transform(dock_tmat(PEN_SLOT))
MESH["tdock_pen"] = m

# ---- kinematic bodies ----
BODY = {}
def _add(body, names):
    for n in names:
        BODY[n] = body
_add("ground", ["base_plate", "base_link", "j1_cradle", "vendor_sts3250_j1",
                "base_reinf", "tc_rack", "tdock_pen"] +
                ["tdock_" + n for n in TC_TOOL])
_add("j1",     ["yaw_limit", "link1", "front_spacer_j2", "flange_j2"])
_add("upper",  ["upper_out", "upper_back", "back_spacer_j2", "back_spacer_j3",
                "vendor_spring_j2", "vendor_spring_j3"])
_add("fore",   ["front_spacer_j3", "flange_j3", "dogleg_l", "dogleg_r",
                "fore_l2", "fore_r2", "vendor_sts3250_j4", "w_j4_cradle"])
_add("wrist4", ["w_link4", "vendor_sts3215_j5"])
_add("wrist5", ["w_link5", "vendor_sts3215_j6"])
_add("grip",   ["tc_master"] + TC_TOOL + ["plug_g_tc"])
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
_plug("grip",   66.8 + T.TC_SH, 79.0 + T.TC_SH, -39.0, -28.0, "plug_g_tc")

missing = [n for n in MESH if n not in BODY]
assert not missing, missing
BIDX = {"ground": 0, "j1": 1, "upper": 2, "fore": 3, "wrist4": 4, "wrist5": 5, "grip": 6}

def man(m):
    return m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                               tri_verts=np.asarray(m.faces, np.uint32)))
M = {n: man(m) for n, m in MESH.items()}
NAMES = sorted(M)

# ---- declared pairs ----
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
DECLARED[frozenset(("tc_gear", "tc_rack_u"))] = "gear/rack mesh"
DECLARED[frozenset(("tc_gear", "tc_rack_d"))] = "gear/rack mesh"
for px, own in (("plug_j5", "wrist4"), ("plug_j6", "wrist5"), ("plug_g_tc", "grip")):
    for q in NAMES:
        if BODY[q] == own:
            DECLARED[frozenset((px, q))] = "plug proxy inside own servo/case zone"
# inherited product clearance (verified on the STOCK wrist2 part set,
# same poses): J4 cradle grazes link5 / J4 vendor case at combined
# J4/J5 bends ~3-35 mm3.  Pre-existing, unchanged by D10.
DECLARED[frozenset(("w_j4_cradle", "w_link5"))] = \
    "inherited: product cradle/link5 graze at J4/J5 corners"
DECLARED[frozenset(("vendor_sts3250_j4", "w_link5"))] = \
    "inherited: J4 vendor case vs link5 at extreme corners"

# D10 designed engagement: master in the docked socket + tool in the rack
DECLARED[frozenset(("tc_master", "tdock_tool_grip"))] = \
    "bayonet lugs under catches + spigot in socket (measured per step)"
# (master vs the tool's internal parts - servo, gear, racks, fingers -
# is NOT declared: any such overlap is a real seat fault.)
for n in TC_TOOL:
    DECLARED[frozenset(("tdock_" + n, "tc_rack"))] = "tool groove seated in slot"
DECLARED[frozenset(("tdock_pen", "tc_rack"))] = "tool groove seated in slot"

# bounded declarations: absorbed only while the measured overlap stays
# under the designed seat volume - a larger value is a real collision.
DECL_MAX = {}
for n in TC_TOOL:
    DECL_MAX[frozenset((n, "tc_rack"))] = 12.0   # C5 seat is 8.4 mm3

def skip(a, b):
    if a.startswith("vendor_") and b.startswith("vendor_"):
        act = lambda n: "act" in n or "sts32" in n
        return not (act(a) and act(b))
    return False

# ---- pose machinery (identical to f2) ----
AXES_HOME = [((0.0, 0.0, 80.8), (0.0, 0.0, 1.0)),
             ((-20.0, 0.0, 143.5), (0.0, 1.0, 0.0)),
             ((-20.0, 0.0, 270.2), (0.0, 1.0, 0.0)),
             ((96.4, 0.0, 216.2), (0.0, 1.0, 0.0)),
             ((127.0, 0.0, 223.8), (0.0, 0.0, 1.0)),
             ((149.4, 0.0, 199.2), (1.0, 0.0, 0.0))]
KIN = ArmKinematics()

def body_mats(q):
    Tm = np.eye(4)
    mats = [np.eye(4)]
    for k in range(6):
        Tm = Tm @ rotmat(q[k], np.array(AXES_HOME[k][1]), np.array(AXES_HOME[k][0]))
        mats.append(Tm.copy())
    return mats

GRIP_SLIDE = {"tc_finger_u": 1, "tc_finger_d": -1,
              "tc_rack_u": 1, "tc_rack_d": -1,
              "tdock_tc_finger_u": 1, "tdock_tc_finger_d": -1,
              "tdock_tc_rack_u": 1, "tdock_tc_rack_d": -1}

# physical lock relationship (measured): the carried tool is upright
# only when the master sits at LOCK roll +48 deg - i.e. the tool meshes
# (drawn upright) get a -48 deg pre-rotation about the J6 axis line.
R_OFF = rotmat(math.radians(-TC.LOCK_Q6), (1.0, 0.0, 0.0), (0.0, 0.0, 199.2))
TOOL_SET = TC_TOOL + ["plug_g_tc"]

def posed(q, grip_t=0.0, arm_empty=False):
    """{name: Manifold} at pose q (rad).
    arm_empty: arm carries only tc_master - the tool parts stay home in
               the rack, represented by their tdock_* ground copies.
    Otherwise: arm carries the gripper tool; tool parts get R_OFF so the
               pose matches the real -48 deg lock relationship.
    tdock_* copies are ground (already world-transformed at load).
    """
    mats = body_mats(q)
    out = {}
    for n in NAMES:
        if arm_empty and n in TOOL_SET:
            continue
        b = BIDX[BODY[n]]
        Tm = mats[b]
        if b == 6 and n in TOOL_SET:
            Tm = Tm @ R_OFF
        out[n] = M[n].transform(np.asarray(Tm[:3, :], np.float64))
    if grip_t:
        Rg = (mats[6] @ R_OFF)[:3, :3]
        du = Rg @ np.array([0.0, 1.0, 0.0])
        for n, sgn in GRIP_SLIDE.items():
            if n in out and not n.startswith("tdock_"):
                out[n] = out[n].translate((sgn * grip_t * du).tolist())
        c_h = np.append(np.asarray(MESH["tc_gear"].bounds).mean(axis=0), 1.0)
        c_w = ((mats[6] @ R_OFF) @ c_h)[:3]
        R = rotmat(math.radians(grip_t / 12.5 * 90.0),
                   Rg @ np.array([1.0, 0.0, 0.0]), c_w)
        if "tc_gear" in out:
            out["tc_gear"] = out["tc_gear"].transform(np.asarray(R[:3], np.float64))
    return out

def pair_ok(a, b):
    return not skip(a, b) and BODY[a] != BODY[b]

def colliding(pm, pairs):
    hits, decl = [], []
    mn = math.inf
    bb = {n: pm[n].bounding_box() for n in pm}
    for a, b in pairs:
        if a not in pm or b not in pm:
            continue
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
            fs = frozenset((a, b))
            if fs in DECLARED:
                decl.append((a, b, v))
            elif fs in DECL_MAX and v <= DECL_MAX[fs]:
                decl.append((a, b, v))
            else:
                hits.append((a, b, v))
        else:
            mn = min(mn, 0.0)
    return hits, decl, mn

def minz(pm):
    return min(pm[n].bounding_box()[2] for n in NAMES if n in pm)

ok = True
def res(tag, good, msg):
    global ok
    ok &= bool(good)
    print("%-6s %-72s %s" % (tag, msg, "PASS" if good else "FAIL"), flush=True)

LIM = [(config.JOINT_MIN[i], config.JOINT_MAX[i]) for i in range(6)]

# pair lists computed lazily per posed dict (tdock_* members swap bodies)
RACKZONE = {"tc_rack", "tdock_pen"} | {"tdock_" + n for n in TC_TOOL}
def pairs_for(pm):
    prs = []
    ks = sorted(pm)
    for i, a in enumerate(ks):
        for b in ks[i + 1:]:
            if pair_ok(a, b):
                prs.append((a, b))
    return prs

def split_rz(hits):
    """(arm-internal hits, rack-zone hits): the rack/docked tools are not
    part of the arm envelope - an arm pose can always be driven into the
    rack, which is an operational constraint, not a design defect."""
    rz = [(a, b, v) for a, b, v in hits
          if a in RACKZONE or b in RACKZONE]
    arm = [(a, b, v) for a, b, v in hits
           if a not in RACKZONE and b not in RACKZONE]
    return arm, rz

STEP = math.radians(2.5)
REPORT = {}

# ---- A) envelope sweeps, arm carrying the gripper tool ----
print("== A) J4/J5/J6 sweeps, gripper tool mounted (step 2.5 deg) ==")
for j in (3, 4, 5):
    lo, hi = LIM[j]
    rows = []
    t = lo
    while t <= hi - 1e-9:
        q = [0.0] * 6
        q[j] = t
        pm = posed(q)
        hits, decl, gap = colliding(pm, pairs_for(pm))
        rows.append((math.degrees(t), hits, gap, minz(pm)))
        t += STEP
    for t in (hi,):
        q = [0.0] * 6
        q[j] = t
        pm = posed(q)
        hits, decl, gap = colliding(pm, pairs_for(pm))
        rows.append((math.degrees(t), hits, gap, minz(pm)))
    coll, rzcoll = [], []
    for a_, h, g, z in rows:
        arm, rz = split_rz(h)
        if arm:
            coll.append((a_, arm))
        if rz:
            rzcoll.append((a_, rz))
    gap = min(g for a_, h, g, z in rows)
    zmin = min(z for a_, h, g, z in rows)
    REPORT["J%d" % (j + 1)] = (coll, gap, zmin)
    txt = "J%d swept %+.0f..%+.0f: min bbox gap %.1f, min z %.1f" % (
        j + 1, math.degrees(lo), math.degrees(hi), gap, zmin)
    if coll:
        seen = []
        for a_, hh in coll:
            for a, b, v in hh:
                seen.append("%+.1fdeg %s x %s %.0fmm3" % (a_, a, b, v))
        txt += "  ARM COLLISIONS: " + "; ".join(seen[:10])
    if rzcoll:
        txt += "  (rack-zone hits at %d poses - informational)" % len(rzcoll)
    res("SWEEP", not coll and zmin > -0.05, txt)

# J6 sweep across J5 grid incl. sublimit region
print("== J6 x J5 grid (sublimit applied when J5 < 0) ==")
worst, rz_n = [], 0
for q5 in np.linspace(LIM[4][0], LIM[4][1], 9):
    lo6, hi6 = LIM[5]
    if q5 < 0:
        lo6, hi6 = max(lo6, -config.J6_SUBLIM_J5_NEG), min(hi6, config.J6_SUBLIM_J5_NEG)
    for q6 in np.linspace(lo6, hi6, 25):
        q = [0, 0, 0, 0, q5, q6]
        pm = posed(q)
        hits, decl, gap = colliding(pm, pairs_for(pm))
        arm, rz = split_rz(hits)
        rz_n += len(rz)
        if arm:
            worst.append((round(math.degrees(q5), 1), round(math.degrees(q6), 1), arm))
res("GRID", not worst,
    "J6 x J5 grid: %d arm collisions, %d rack-zone hits (informational)"
    % (len(worst), rz_n))
for w in worst[:10]:
    print("   q5=%+.1f q6=%+.1f %s" % (w[0], w[1], w[2]))

# named + corner poses
print("== named/corner poses ==")
def fk_tcp(q):
    return KIN.fk_matrix(q)[:3, 3] * 1000.0
NAMED = {
    "home": [0, 0, 0, 0, 0, 0],
    "stow": [0, math.radians(70), math.radians(-160), math.radians(70), 0, 0],
    "wrist-flex": [0, math.radians(45), math.radians(-45),
                   math.radians(70), math.radians(70), 0],
}
for nm, q in NAMED.items():
    pm = posed(q)
    hits, decl, gap = colliding(pm, pairs_for(pm))
    pm2 = posed(q, 12.5)
    hits2, _, _ = colliding(pm2, pairs_for(pm2))
    allh = hits + hits2
    arm, rz = split_rz(allh)
    res("POSE", not arm and minz(pm) > -0.05,
        "%-11s q=%s tcp=%s z_min %.1f %s%s"
        % (nm, np.round(np.degrees(q), 1).tolist(),
           np.round(fk_tcp(q), 0).tolist(), minz(pm),
           ("ARM COLLISIONS " + str(arm)) if arm else "clean",
           (" rack-zone " + str(rz)) if rz else ""))
for q4 in LIM[3]:
    for q5 in LIM[4]:
        lo6, hi6 = LIM[5]
        if q5 < 0:
            lo6 = max(lo6, -config.J6_SUBLIM_J5_NEG)
            hi6 = min(hi6, config.J6_SUBLIM_J5_NEG)
        for q6 in (lo6, hi6):
            q = [0, 0, 0, q4, q5, q6]
            pm = posed(q)
            hits, decl, gap = colliding(pm, pairs_for(pm))
            arm, rz = split_rz(hits)
            res("CORNER", not arm,
                "J4%+.0f J5%+.0f J6%+.0f %s%s"
                % (math.degrees(q4), math.degrees(q5), math.degrees(q6),
                   ("ARM COLLISIONS " + str(arm)) if arm else "clean",
                   (" rack-zone " + str(rz)) if rz else ""))

# Monte-Carlo over the wrist envelope
print("== Monte-Carlo 800 wrist poses (tool mounted) ==")
rng = np.random.default_rng(20261214)
mc_hits, mc_gap, mc_z, mc_rz = [], math.inf, math.inf, 0
for it in range(800):
    q = [0.0] * 6
    q[3] = rng.uniform(*LIM[3])
    q[4] = rng.uniform(*LIM[4])
    lo6 = LIM[5][0]
    hi6 = LIM[5][1] if q[4] >= 0 else config.J6_SUBLIM_J5_NEG
    if q[4] < 0:
        lo6 = max(lo6, -config.J6_SUBLIM_J5_NEG)
    q[5] = rng.uniform(lo6, hi6)
    gt = rng.uniform(0.0, 12.5)
    pm = posed(q, gt)
    hits, decl, gap = colliding(pm, pairs_for(pm))
    arm, rz = split_rz(hits)
    mc_rz += len(rz)
    mc_gap = min(mc_gap, gap)
    mc_z = min(mc_z, minz(pm))
    for a, b, v in arm:
        mc_hits.append((it, np.round(np.degrees(q), 1).tolist(), round(gt, 1),
                        a, b, round(v, 1)))
res("MC", not mc_hits and mc_z > -0.05,
    "800 poses: min bbox gap %.1f, min z %.1f, arm hits %d, rack-zone %d"
    % (mc_gap, mc_z, len(mc_hits), mc_rz))
for h in mc_hits[:20]:
    print("   MC pose %d q=%s grip %.1f: %s x %s %.0f mm3" % h)

# ---- B) dock + undock path per slot ----
print("== B) dock and undock paths (all slots) ==")
SUB = 16                                # substeps between waypoints
DOCKED = ["tdock_" + n for n in TC_TOOL]

def dock_carried(tag):
    """dock: tool stays in the rack until the lock twist completes."""
    return (tag.startswith("lock->lift") or tag.startswith("lift->")
            or tag == "clear")

def undock_carried(tag):
    """undock: tool rides the arm until seated; the unlock twist and the
    retreat happen with the tool held by the slot (arm_empty)."""
    return not (tag.startswith("seat->unlock") or tag.startswith("unlock")
                or tag.startswith("back") or tag == "retreat")

def run_path(slot, wps, carried_fn, label):
    seq = []
    for i in range(len(wps) - 1):
        n0, q0, _, _ = wps[i]
        n1, q1, _, _ = wps[i + 1]
        for s in range(SUB):
            qq = np.asarray(q0) + (np.asarray(q1) - np.asarray(q0)) * s / SUB
            seq.append((n0 + "->" + n1, qq))
    seq.append((wps[-1][0], np.asarray(wps[-1][1])))
    bad, engmax, gapmin = [], 0.0, math.inf
    for tag, qq in seq:
        carried = carried_fn(tag)
        pm = posed(qq, arm_empty=not carried)
        if carried:
            for n in DOCKED:
                del pm[n]                    # tool on the arm, not in rack
        hits, decl, gap = colliding(pm, pairs_for(pm))
        gapmin = min(gapmin, gap)
        for a, b, v in decl:
            if a == "tc_master" or b == "tc_master":
                engmax = max(engmax, v)
        for a, b, v in hits:
            bad.append((tag, np.round(np.degrees(qq), 1).tolist(), a, b,
                        round(v, 1)))
    res(label, not bad,
        "slot %d: min bbox gap %.1f, max master<->tool engagement %.0f mm3%s"
        % (slot, gapmin, engmax, ("  COLLISIONS " + str(bad[:6])) if bad else ""))

for slot in range(TC.TC_N_SLOTS):
    # relocate the docked grip tool to this slot; park the pen in the
    # ADJACENT slot - worst-case test for 46 mm pitch clearance
    for n in TC_TOOL:
        m = MESH[n].copy()
        m.apply_transform(dock_tmat(slot))
        M["tdock_" + n] = man(m)
    pen_slot = slot - 1 if slot > 0 else slot + 1
    m = trimesh.load_mesh(os.path.join(TCOUT, "tool_pen.stl"), force="mesh")
    m.merge_vertices()
    m.apply_transform(dock_tmat(pen_slot))
    M["tdock_pen"] = man(m)
    run_path(slot, TC.plan_dock(slot), dock_carried, "DOCK")
    run_path(slot, TC.plan_undock(slot), undock_carried, "UNDOCK")

print("CHECKS", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
