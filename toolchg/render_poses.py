"""toolchg/render_poses.py - generate posed STL variants + concept-sheet
mockups + Blender list files for the D10 renders.

Mesh loading/repose/body map is copied verbatim from tc_collision.py so
the renders show exactly the geometry the collision sim verified.

Outputs (scratch, not committed):  toolchg/renders/scratch/*.stl
List files (committed):            toolchg/renders/lists_*.txt

Scenes:
  asm      - wrist + gripper tool at the home pose
  rack     - rack, grip tool docked at slot 2, pen at slot 1, arm posed
             at the slot-2 lock waypoint
  arm      - full arm at home pose, tool mounted
  concept  - the three candidate couplings side by side

Run: $PY toolchg/render_poses.py   then blender -b -P render_blend.py
"""
import math, os, sys
import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix as rotmat, translation_matrix as tmat

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "cad", "arm2"))
sys.path.insert(0, os.path.join(ROOT, "software", "robot-os"))
sys.path.insert(0, HERE)
import ap2 as P
from soma_arm import toolchange as TC
import tc_params as T

A2B, C3, CYC = (os.path.join(ROOT, d) for d in ("cad/arm2b/out", "cad3/out", "cyclo4/out"))
WR = os.path.join(ROOT, "wrist2", "out")
TCOUT = os.path.join(HERE, "out")
SCR = os.path.join(HERE, "renders", "scratch")
os.makedirs(SCR, exist_ok=True)

# ---- verbatim loader from tc_collision.py ----------------------------
DROP = {"vendor_act_j2", "vendor_act_j3", "vendor_actout_j2", "vendor_actout_j3",
        "vendor_sts3215_j4", "vendor_6803_j2", "vendor_6803_j3",
        "back_spacer_j2", "back_spacer_j3", "flange_j2", "flange_j3",
        "j4_cradle", "link4", "link5", "grip_frame",
        "vendor_sts3215_j5", "vendor_sts3215_j6", "vendor_sts3215_g",
        "vendor_rack_u", "vendor_rack_d", "vendor_gear_grip",
        "finger_u", "finger_d"}
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
SRC = {}
for d, drop in ((A2B, DROP), (C3, set()), (WR, WR_DROP)):
    for f in sorted(os.listdir(d)):
        if f.endswith(".stl") and f[:-4] not in drop:
            m = trimesh.load_mesh(os.path.join(d, f), force="mesh")
            if f[:-4] in REPOSE:
                m.apply_transform(REPOSE[f[:-4]])
            m.merge_vertices()
            MESH[f[:-4]] = m
            SRC[f[:-4]] = d
for f in sorted(os.listdir(CYC)):
    if not f.endswith(".stl"):
        continue
    n = f[:-4]
    m = trimesh.load_mesh(os.path.join(CYC, f), force="mesh"); m.merge_vertices()
    up = n in CYC_UP
    a = m.copy(); a.apply_transform(M2_UP if up else M2_OUT)
    MESH["cy2_" + n] = a; SRC["cy2_" + n] = CYC
    b = m.copy(); b.apply_transform(M3_UP if up else M3_OUT)
    MESH["cy3_" + n] = b; SRC["cy3_" + n] = CYC

TC_TOOL = ["tool_grip", "tc_vendor_g", "tc_gear", "tc_rack_u", "tc_rack_d",
           "tc_finger_u", "tc_finger_d"]
for f in sorted(os.listdir(TCOUT)):
    if not f.endswith(".stl"):
        continue
    n = f[:-4]
    if n == "tc_rack" or n in TC_TOOL or n == "tc_master":
        m = trimesh.load_mesh(os.path.join(TCOUT, f), force="mesh")
        m.merge_vertices()
        MESH[n] = m; SRC[n] = TCOUT

def dock_tmat(slot):
    return tmat((TC.dock_origin_x() - 96.4, TC.slot_y(slot), 127.0 - 216.2))
for n in TC_TOOL:
    m = MESH[n].copy(); m.apply_transform(dock_tmat(2))
    MESH["tdock_" + n] = m; SRC["tdock_" + n] = None
m = trimesh.load_mesh(os.path.join(TCOUT, "tool_pen.stl"), force="mesh")
m.merge_vertices(); m.apply_transform(dock_tmat(1))
MESH["tdock_pen"] = m; SRC["tdock_pen"] = None

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
    BODY["cy2_" + n] = "upper"
    BODY["cy3_" + n] = "fore"
for n in CYC_UP:
    BODY["cy2_" + n] = "j1"
    BODY["cy3_" + n] = "upper"
# -----------------------------------------------------------------------

AXES_HOME = [((0.0, 0.0, 80.8), (0.0, 0.0, 1.0)),
             ((-20.0, 0.0, 143.5), (0.0, 1.0, 0.0)),
             ((-20.0, 0.0, 270.2), (0.0, 1.0, 0.0)),
             ((96.4, 0.0, 216.2), (0.0, 1.0, 0.0)),
             ((127.0, 0.0, 223.8), (0.0, 0.0, 1.0)),
             ((149.4, 0.0, 199.2), (1.0, 0.0, 0.0))]
BIDX = {"ground": 0, "j1": 1, "upper": 2, "fore": 3, "wrist4": 4,
        "wrist5": 5, "grip": 6}
R_OFF = rotmat(math.radians(-TC.LOCK_Q6), (1.0, 0.0, 0.0), (0.0, 0.0, 199.2))
TOOL_SET = TC_TOOL + ["plug_g_tc"]

def body_mats(q):
    Tm = np.eye(4)
    mats = [np.eye(4)]
    for k in range(6):
        Tm = Tm @ rotmat(q[k], np.array(AXES_HOME[k][1]), np.array(AXES_HOME[k][0]))
        mats.append(Tm.copy())
    return mats

def save(m, n):
    p = os.path.join(SCR, n + ".stl")
    m.export(p)
    return p

# colours (match wrist2 lists: printed dark, servo orange, mech grey)
PRINTED = "0.30 0.31 0.36"; ORANGE = "0.78 0.38 0.12"; MECH = "0.55 0.56 0.60"
ACCENT = "0.16 0.50 0.72"; RACK_C = "0.62 0.64 0.68"

def colour(n):
    if n == "tc_master" or n.startswith("con_"):
        return ACCENT
    if "sts32" in n or "sts3250" in n:
        return ORANGE
    if n in ("tc_gear", "tc_rack_u", "tc_rack_d", "vendor_gear_grip",
             "vendor_rack_u", "vendor_rack_d", "vendor_spring_j2",
             "vendor_spring_j3", "vendor_6803_j2", "vendor_6803_j3",
             "vendor_685", "vendor_6702a", "vendor_6702b", "vendor_6808",
             "vendor_motor", "vendor_magnet", "vendor_ringpins",
             "vendor_outpins", "vendor_dowels", "vendor_as5600",
             "mag_puck", "vendor_6702a"):
        return MECH
    return PRINTED

def poselist(names, q, tag):
    """pose `names` at joint vector q -> [(scratch path, colour)]"""
    mats = body_mats(q)
    out = []
    for n in names:
        m = MESH[n].copy()
        Tm = mats[BIDX[BODY[n]]]
        if BIDX[BODY[n]] == 6 and n in TOOL_SET:
            Tm = Tm @ R_OFF
        m.apply_transform(Tm)
        out.append((save(m, "%s_%s" % (tag, n)), colour(n)))
    return out

ARM_NAMES = [n for n in MESH if BODY.get(n) not in (None, "ground")
             and not n.startswith("tdock_")]
GND_NAMES = [n for n in MESH if BODY.get(n) == "ground"]
ARM_REST = [n for n in ARM_NAMES if BODY[n] != "grip"]
Q0 = [0.0] * 6

lists = {"asm": [], "rack": [], "arm": [], "concept": []}
def add(scene, path, rgb):
    lists[scene].append("%s %s" % (path, rgb))

# ---------------- asm: wrist + tool at home ----------------------------
ASM_NAMES = [n for n in ARM_NAMES if BODY[n] in ("fore", "wrist4",
                                               "wrist5", "grip")
             and n not in ("front_spacer_j3", "flange_j3",
                           "dogleg_l", "dogleg_r")]
for p, c in poselist(ASM_NAMES, Q0, "asm"):
    add("asm", p, c)

# ---------------- rack scene -------------------------------------------
add("rack", os.path.join(TCOUT, "tc_rack.stl"), RACK_C)
for n in ("tdock_pen",) + tuple("tdock_" + t for t in TC_TOOL):
    add("rack", save(MESH[n], n),
        "0.85 0.62 0.18" if n == "tdock_pen" else colour(n[6:]))
q_lock = dict((n, q) for n, q, v, a in TC.plan_dock(2))["lock"]
EMPTY = [n for n in ARM_NAMES if n not in TOOL_SET]
for p, c in poselist(EMPTY, q_lock, "dock"):
    add("rack", p, c)

# rack close-up: tools seated, no arm
lists["rackonly"] = []
add("rackonly", os.path.join(TCOUT, "tc_rack.stl"), RACK_C)
for n in ("tdock_pen",) + tuple("tdock_" + t for t in TC_TOOL):
    add("rackonly", save(MESH[n], "ro_" + n),
        "0.85 0.62 0.18" if n == "tdock_pen" else colour(n[6:]))

# ---------------- full arm iso at home ---------------------------------
for n in GND_NAMES:
    if n == "tc_rack" or n.startswith("tdock_"):
        continue
    add("arm", os.path.join(SRC[n], n + ".stl"), colour(n))
for p, c in poselist(ARM_NAMES, Q0, "home"):
    add("arm", p, c)
add("arm", os.path.join(TCOUT, "tc_rack.stl"), RACK_C)
add("arm", save(MESH["tdock_pen"], "d_tool_pen"), "0.85 0.62 0.18")

# ---------------- concept sheet mockups --------------------------------
from build123d import (Pos, Rot, Cylinder, Cone, Box, Sphere, Axis,
                       export_stl)

def cylz(r, h, x, y, z):
    return Pos((x, y, z)) * Cylinder(radius=r, height=h)

X0 = 80.0
# (a) bayonet twist-lock (chosen): plate+spigot+lugs, socket ring above,
#     detent ball beside the spigot
xa = X0
parts = [cylz(20, 6, xa, 0, 3), cylz(13, 14, xa, 0, 13)]
for ph in (70, 190, 310):
    lug = Pos((14.5, 0, 20)) * Rot(Axis.Y, 90) * \
        Cylinder(radius=4.2, height=6)
    parts.append(Pos((xa, 0, 0)) * Rot(Axis.Z, ph) * lug)
parts.append(Pos((xa + 20, 0, 13)) * Sphere(radius=2.5))
ring = Pos((xa, 0, 34)) * (Cylinder(radius=20, height=4) -
                           Pos((0, 0, 0)) * Cylinder(radius=18.2,
                                                     height=4.4))
s = parts[0]
for p in parts[1:]:
    s = s + p
s = s + ring
export_stl(s, os.path.join(SCR, "con_bayonet.stl"))
add("concept", os.path.join(SCR, "con_bayonet.stl"), ACCENT)

# (b) kinematic V-mount + spring latch: V plate, balls mid-air, top
#     plate + latch tab above
xb = X0 + 110
s = cylz(20, 5, xb, 0, 2.5)
for ph in (0, 120, 240):
    a = math.radians(ph)
    s = s - Pos((xb + 15 * math.cos(a), 15 * math.sin(a), 5.5)) * \
        Cone(bottom_radius=5.0, top_radius=1.6, height=3.0)
s2 = cylz(20, 5, xb, 0, 33)
for ph in (0, 120, 240):
    a = math.radians(ph)
    s = s + Pos((xb + 15 * math.cos(a), 15 * math.sin(a), 13.5)) * \
        Sphere(radius=3.5)
s2 = s2 + Pos((xb + 26, 0, 28)) * Box(8, 6, 10)
export_stl(s + s2, os.path.join(SCR, "con_kinematic.stl"))
add("concept", os.path.join(SCR, "con_kinematic.stl"), "0.40 0.65 0.35")

# (c) magnetic kinematic + pogo pins: magnet pucks on lower plate,
#     pogo pins hanging under the upper plate
xc = X0 + 220
s = cylz(20, 5, xc, 0, 2.5)
for ph in (0, 120, 240):
    a = math.radians(ph)
    s = s + cylz(4.0, 3.0, xc + 14 * math.cos(a), 14 * math.sin(a), 6.5)
s2 = cylz(20, 5, xc, 0, 34)
for ph in (30, 150, 210, 270, 330):
    a = math.radians(ph)
    s2 = s2 + cylz(0.9, 10.0, xc + 10 * math.cos(a), 10 * math.sin(a), 26)
export_stl(s + s2, os.path.join(SCR, "con_magnetic.stl"))
add("concept", os.path.join(SCR, "con_magnetic.stl"), "0.72 0.30 0.42")

# ---------------- write list files -------------------------------------
for name, rows in lists.items():
    with open(os.path.join(HERE, "renders", "lists_%s.txt" % name), "w") as fh:
        fh.write("\n".join(rows) + "\n")
    print("lists_%s.txt: %d parts" % (name, len(rows)))
print("scratch STLs in", SCR)
