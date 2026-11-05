"""toolchg/mjcf_tc/build_tc.py - MuJoCo model for the D10 dock scene,
adapted from final2/build_mjcf_f2.py (same loaders, same body chain).

Scene contents:
  arm      - arm2b/cad3/cyclo4/wrist2 set with the D10 swap: grip body =
             tc_master only (arm carries the bare master plate when
             docking); no finger joints (the tool carries its own).
  tool     - free body, geoms = tool_grip + tc_vendor_g + tc_gear +
             tc_rack/fingers, posed in the rack slot by a world weld.
  pen      - second free body parked in another slot.
  tc_rack  - static worldbody geoms.

Coupling is modelled KINEMATICALLY like the f2 scene (all contype=0):
an equality weld tool<->world holds the tool in its slot; at lock it
swaps to a weld tool<->grip (relpose = the measured -48 deg lock
relationship, inv(G_lock)@dock_pose from tc_collision).  One world weld
per slot so undock can re-anchor at any slot.

Run: ~/Vector-wt/sim/.venv-mj/bin/python toolchg/mjcf_tc/build_tc.py
Meshes dumped to toolchg/mjcf_tc/meshes/ (scratch, not committed).
"""
import math
import os
import sys
import trimesh
from trimesh.transformations import rotation_matrix as rotmat, translation_matrix as tmat

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MESHDIR = os.path.join(HERE, "meshes")
os.makedirs(MESHDIR, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "cad", "arm2"))
sys.path.insert(0, os.path.join(ROOT, "software", "robot-os"))
import ap2 as P
from soma_arm import toolchange as TC

A2B, C3, CYC = (os.path.join(ROOT, d) for d in ("cad/arm2b/out", "cad3/out", "cyclo4/out"))
WR = os.path.join(ROOT, "wrist2", "out")
TCOUT = os.path.join(ROOT, "toolchg", "out")
DROP = {"vendor_act_j2", "vendor_act_j3", "vendor_actout_j2", "vendor_actout_j3",
        "vendor_sts3215_j4", "vendor_6803_j2", "vendor_6803_j3",
        "back_spacer_j2", "back_spacer_j3", "flange_j2", "flange_j3",
        "j4_cradle", "link4", "link5", "grip_frame",
        "vendor_sts3215_j5", "vendor_sts3215_j6", "vendor_sts3215_g",
        "vendor_rack_u", "vendor_rack_d", "vendor_gear_grip",
        "finger_u", "finger_d"}
WR_SKIP = {"w_grip_frame", "vendor_sts3215_g", "vendor_gear_grip",
           "vendor_rack_u", "vendor_rack_d", "finger_u", "finger_d",
           "vendor_sts3215_j4"}
CYC_UP = {"housing", "pin_ring", "front_ring", "vendor_ringpins", "vendor_motor",
          "mag_puck", "vendor_magnet", "vendor_as5600", "vendor_6808",
          "disc1", "disc2", "hub", "vendor_6702a", "vendor_6702b"}
CYC_OUT = {"carrier", "out_flange", "vendor_dowels", "vendor_outpins", "vendor_685"}
J2P, J3P = P.J2_XZ, P.J3_XZ
M_J2 = rotmat(math.radians(P.POSE_J2), (0, 1, 0), (J2P[0], 0, J2P[1]))
M_J3 = rotmat(math.radians(P.POSE_J3), (0, 1, 0), (J3P[0], 0, J3P[1]))
RX90 = rotmat(math.radians(90.0), (1, 0, 0))
def place(jxz):
    return tmat((jxz[0], P.ACT_BACK_Y, jxz[1])) @ RX90
M2_UP, M2_OUT = M_J2 @ place(J2P), place(J2P)
M3_UP, M3_OUT = M_J2 @ place(J3P), M_J2 @ M_J3 @ place(J3P)
FO = M_J2 @ M_J3
REPOSE = {"back_spacer_j2": M_J2, "back_spacer_j3": M_J2,
          "vendor_spring_j2": M_J2, "vendor_spring_j3": M_J2,
          "flange_j3": FO, "vendor_sts3250_j4": FO}

MESH = {}
for d, drop in ((A2B, DROP), (C3, set()), (WR, WR_SKIP)):
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

TC_TOOL = ["tool_grip", "tc_vendor_g", "tc_gear", "tc_rack_u", "tc_rack_d",
           "tc_finger_u", "tc_finger_d"]
for n in TC_TOOL + ["tc_master", "tc_rack", "tool_pen"]:
    m = trimesh.load_mesh(os.path.join(TCOUT, n + ".stl"), force="mesh")
    m.merge_vertices()
    MESH[n] = m

for n, m in MESH.items():
    m.export(os.path.join(MESHDIR, n + ".stl"))
print("meshes:", len(MESH))

# ---------------- joints ----------------
J1 = ("J1", (0.0, 0.0, 0.0808), (0, 0, 1), -3.14, 3.14, 0.98, 10.0)
J2 = ("J2", (-0.020, 0.0, 0.1435), (0, 1, 0), -2.0944, 1.2217, 3.5, 80.0)
J3 = ("J3", (-0.020, 0.0, 0.2702), (0, 1, 0), -3.1416, 0.5236, 2.25, 50.0)
J4 = ("J4", (0.0964, 0.0, 0.2162), (0, 1, 0), -1.2217, 1.2217, 0.98, 15.0)
J5 = ("J5", (0.1270, 0.0, 0.2238), (0, 0, 1), -1.2217, 1.2217, 0.98, 15.0)
J6 = ("J6", (0.1494, 0.0, 0.1992), (1, 0, 0), -3.14, 3.14, 0.98, 8.0)

CY2_OUT = ["cy2_" + n for n in sorted(CYC_OUT)]
CY2_UP = ["cy2_" + n for n in sorted(CYC_UP)]
CY3_OUT = ["cy3_" + n for n in sorted(CYC_OUT)]
CY3_UP = ["cy3_" + n for n in sorted(CYC_UP)]
BODIES = [
    ("base", None, ["base_plate", "base_link", "j1_cradle",
                    "vendor_sts3250_j1", "base_reinf"]),
    ("upper_base", J1, ["yaw_limit", "link1", "front_spacer_j2", "flange_j2"] + CY2_OUT),
    ("upper", J2, ["upper_out", "upper_back", "back_spacer_j2", "back_spacer_j3",
                    "vendor_spring_j2", "vendor_spring_j3"] + CY2_UP + CY3_UP),
    ("fore", J3, ["front_spacer_j3", "flange_j3", "dogleg_l", "dogleg_r",
                   "fore_l2", "fore_r2", "w_j4_cradle", "vendor_sts3250_j4"] + CY3_OUT),
    ("wrist4", J4, ["w_link4", "vendor_sts3215_j5"]),
    ("wrist5", J5, ["w_link5", "vendor_sts3215_j6"]),
    ("grip", J6, ["tc_master"]),
]

MASS = {"vendor_sts3250_j1": 0.075, "vendor_sts3250_j4": 0.0745,
        "vendor_sts3215_j5": 0.055, "vendor_sts3215_j6": 0.055,
        "tc_vendor_g": 0.055, "tc_gear": 0.008,
        "cy2_vendor_motor": 0.085, "cy3_vendor_motor": 0.085}
RHO = 1.27e-3
INFILL = 0.6

def part_mass(name):
    if name in MASS:
        return MASS[name]
    m = MESH[name]
    return m.volume * RHO * INFILL / 1000.0

def f(v):
    return " ".join("%.4f" % x for x in v)

def dock_pos_m(slot):
    """world position (m) of a tool body frame seated in `slot`."""
    dx, dy, dz = TC.dock_origin_x() - 96.4, TC.slot_y(slot), 127.0 - 216.2
    return (dx / 1000.0, dy / 1000.0, dz / 1000.0)

# weld relpose grip<->tool: measured inv(G_lock) @ D = rot_x(-48) about
# the J6 line (0,0,0.1992) in home coords - see tc_collision.R_OFF
REL_POS = (0.0, -0.148034, 0.065909)
REL_QUAT = (math.cos(math.radians(24.0)), -math.sin(math.radians(24.0)), 0.0, 0.0)

parts = [(n, b) for b, _, ns in BODIES for n in ns]
xml = []
xml.append('<mujoco model="soma_arm_tc">')
xml.append('  <compiler meshdir="meshes" angle="radian"/>')
xml.append('  <option gravity="0 0 -9.81"/>')
xml.append('  <default><joint damping="0.2" armature="0.01"/><geom contype="0" conaffinity="0"/></default>')
xml.append('  <asset>')
for n, _ in parts:
    xml.append('    <mesh name="%s" file="%s.stl" scale="0.001 0.001 0.001"/>' % (n, n))
for n in TC_TOOL + ["tool_pen", "tc_rack"]:
    xml.append('    <mesh name="%s" file="%s.stl" scale="0.001 0.001 0.001"/>' % (n, n))
xml.append('  </asset>')
xml.append('  <worldbody>')

def emit(idx, depth):
    name, j, ns = BODIES[idx]
    pad = "  " * depth
    xml.append('%s<body name="%s" pos="0 0 0">' % (pad, name))
    if j is not None:
        xml.append('%s  <joint name="%s" type="hinge" pos="%s" axis="%s" range="%.4f %.4f"/>' % (
            pad, j[0], f(j[1]), f(j[2]), j[3], j[4]))
    for n in ns:
        xml.append('%s  <geom name="g_%s" type="mesh" mesh="%s" mass="%.4f"/>' % (
            pad, n, n, part_mass(n)))
    if name == "grip":
        xml.append('%s  <site name="tcp" pos="0.2338 0 0.1992"/>' % pad)
        xml.append('%s  <site name="mst" pos="0.1651 0 0.1992"/>' % pad)  # master face a68.7
    if idx + 1 < len(BODIES):
        emit(idx + 1, depth + 1)
    xml.append('%s</body>' % pad)

emit(0, 1)
# static rack geoms straight into worldbody (world-frame STL)
for n in ("tc_rack",):
    xml.append('    <geom name="g_%s" type="mesh" mesh="%s" mass="%.4f"/>' % (
        n, n, MESH[n].volume * RHO / 1000.0))
# tool + pen free bodies, initially seated in slots 2 and 0
for nm, geoms, slot in (("tool", TC_TOOL, 2), ("pen", ["tool_pen"], 0)):
    p = dock_pos_m(slot)
    xml.append('    <body name="%s" pos="%s">' % (nm, f(p)))
    xml.append('      <freejoint name="%s_free"/>' % nm)
    for n in geoms:
        xml.append('      <geom name="g_%s" type="mesh" mesh="%s" mass="%.4f"/>' % (
            n, n, part_mass(n)))
    xml.append('      <site name="%s_ref" pos="%.4f %.4f %.4f"/>' % (
        nm, 0.0964 + 0.069, 0.0, 0.2162 - 0.017))   # socket mouth centre
    xml.append('    </body>')
xml.append('  </worldbody>')

# weld equalities: world anchors per slot + grip weld (lock)
xml.append('  <equality>')
for nm in ("tool", "pen"):
    for k in range(TC.TC_N_SLOTS):
        p = dock_pos_m(k)
        xml.append('    <weld name="w_%s_world_%d" body1="world" body2="%s" '
                   'relpose="%s 1 0 0 0" torquescale="500"/>' % (
                       nm, k, nm, f(p)))
    xml.append('    <weld name="w_%s_grip" body1="grip" body2="%s" '
               'relpose="%s %s" torquescale="500" active="false"/>' % (
                   nm, nm, f(REL_POS), f(REL_QUAT)))
xml.append('  </equality>')

xml.append('  <actuator>')
for _, j, _ in [b for b in BODIES if b[1] is not None]:
    xml.append('    <position name="%s" joint="%s" kp="%.1f" ctrlrange="%.4f %.4f" forcerange="-%.2f %.2f"/>' % (
        j[0], j[0], j[6], j[3], j[4], j[5], j[5]))
xml.append('  </actuator>')
xml.append('</mujoco>')

with open(os.path.join(HERE, "arm_tc.xml"), "w") as fh:
    fh.write("\n".join(xml) + "\n")

scene = """<mujoco model="soma_arm_tc_scene">
  <compiler meshdir="meshes" angle="radian"/>
  <include file="arm_tc.xml"/>
  <worldbody>
    <light directional="true" pos="1 -1 2.5" dir="-0.4 0.4 -1" diffuse="0.8 0.8 0.8"/>
    <geom name="floor" type="plane" pos="0 0 -0.001" size="2 2 0.05" contype="0" conaffinity="0" rgba="0.85 0.85 0.85 1"/>
  </worldbody>
</mujoco>
"""
with open(os.path.join(HERE, "scene_tc.xml"), "w") as fh:
    fh.write(scene)
print("WROTE arm_tc.xml + scene_tc.xml")
for b, _, ns in BODIES:
    print("%-11s %.3f kg : %s" % (b, sum(part_mass(n) for n in ns), ", ".join(ns)))
print("%-11s %.3f kg : %s" % ("tool", sum(part_mass(n) for n in TC_TOOL),
                              ", ".join(TC_TOOL)))
