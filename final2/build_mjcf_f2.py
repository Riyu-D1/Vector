"""final2/build_mjcf_f2.py - MuJoCo model of the MERGED arm (arm-final2):
sim/build_mjcf.py adapted to the F2 assembly composition -
  arm2b 'fix' split at link1 kept; cyclo4 modules replace vendor_act*;
  cad3 D2 overrides (back_spacer, flange_j3, springs, sts3250_j4);
  wrist2/out K-KEEL wrist replaces j4_cradle/link4/link5/grip_frame.
Joint centres updated for D6 (J5 fin, J6 keel, TCP (0.2338,0,0.1992)).
Run: ~/Vector-wt/sim/.venv-mj/bin/python final2/build_mjcf_f2.py
Meshes are dumped to final2/mjcf/meshes/ (scratch, not committed).
"""
import math
import os
import sys
import trimesh
from trimesh.transformations import rotation_matrix as rotmat, translation_matrix as tmat

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MESHDIR = os.path.join(HERE, "mjcf", "meshes")
os.makedirs(MESHDIR, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "cad", "arm2"))
import ap2 as P

A2B, C3, CYC = (os.path.join(ROOT, d) for d in ("cad/arm2b/out", "cad3/out", "cyclo4/out"))
WR = os.path.join(ROOT, "wrist2", "out")
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

for n, m in MESH.items():
    m.export(os.path.join(MESHDIR, n + ".stl"))
print("meshes:", len(MESH))

# ---------------- joints: (name, pos m, axis, lo, hi, forcerange, kp) ----------------
J1 = ("J1", (0.0, 0.0, 0.0808), (0, 0, 1), -3.14, 3.14, 0.98, 10.0)
J2 = ("J2", (-0.020, 0.0, 0.1435), (0, 1, 0), -2.0944, 1.2217, 3.5, 80.0)
J3 = ("J3", (-0.020, 0.0, 0.2702), (0, 1, 0), -3.1416, 0.5236, 2.25, 50.0)
J4 = ("J4", (0.0964, 0.0, 0.2162), (0, 1, 0), -1.2217, 1.2217, 0.98, 15.0)
J5 = ("J5", (0.1270, 0.0, 0.2238), (0, 0, 1), -1.2217, 1.2217, 0.98, 15.0)   # D6 fin
J6 = ("J6", (0.1494, 0.0, 0.1992), (1, 0, 0), -3.14, 3.14, 0.98, 8.0)       # D6 keel
FU = ("finger_u", (0.1306, 0.0, 0.1992), (0, 1, 0), 0.0, 0.0125, 5.0, 50.0)
FD = ("finger_d", (0.1306, 0.0, 0.1992), (0, -1, 0), 0.0, 0.0125, 5.0, 50.0)

CY2_OUT = ["cy2_" + n for n in sorted(CYC_OUT)]
CY2_UP = ["cy2_" + n for n in sorted(CYC_UP)]
CY3_OUT = ["cy3_" + n for n in sorted(CYC_OUT)]
CY3_UP = ["cy3_" + n for n in sorted(CYC_UP)]
BODIES = [
    ("base", None, ["base_plate", "base_link", "j1_cradle", "vendor_sts3250_j1", "base_reinf"]),
    ("upper_base", J1, ["yaw_limit", "link1", "front_spacer_j2", "flange_j2"] + CY2_OUT),
    ("upper", J2, ["upper_out", "upper_back", "back_spacer_j2", "back_spacer_j3",
                    "vendor_spring_j2", "vendor_spring_j3"] + CY2_UP + CY3_UP),
    ("fore", J3, ["front_spacer_j3", "flange_j3", "dogleg_l", "dogleg_r",
                   "fore_l2", "fore_r2", "w_j4_cradle", "vendor_sts3250_j4"] + CY3_OUT),
    ("wrist4", J4, ["w_link4", "vendor_sts3215_j5"]),
    ("wrist5", J5, ["w_link5", "vendor_sts3215_j6"]),
    ("grip", J6, ["w_grip_frame", "vendor_sts3215_g", "vendor_gear_grip",
                  "vendor_rack_u", "vendor_rack_d"]),
    ("finger_u", FU, ["finger_u"]),
    ("finger_d", FD, ["finger_d"]),
]

MASS = {"vendor_sts3250_j1": 0.075, "vendor_sts3250_j4": 0.0745,
        "vendor_sts3215_j5": 0.055, "vendor_sts3215_j6": 0.055,
        "vendor_sts3215_g": 0.055,
        "vendor_gear_grip": 0.008, "vendor_rack_u": 0.012, "vendor_rack_d": 0.012,
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

parts = [(n, b) for b, _, ns in BODIES for n in ns]
assert len(parts) == 72, len(parts)
xml = []
xml.append('<mujoco model="soma_arm_f2">')
xml.append('  <compiler meshdir="meshes" angle="radian"/>')
xml.append('  <option gravity="0 0 -9.81"/>')
xml.append('  <default><joint damping="0.2" armature="0.01"/><geom contype="0" conaffinity="0"/></default>')
xml.append('  <asset>')
for n, _ in parts:
    xml.append('    <mesh name="%s" file="%s.stl" scale="0.001 0.001 0.001"/>' % (n, n))
xml.append('  </asset>')
xml.append('  <worldbody>')

def emit(idx, depth):
    name, j, ns = BODIES[idx]
    pad = "  " * depth
    xml.append('%s<body name="%s" pos="0 0 0">' % (pad, name))
    if j is not None:
        xml.append('%s  <joint name="%s" type="%s" pos="%s" axis="%s" range="%.4f %.4f"/>' % (
            pad, j[0], "slide" if name.startswith("finger") else "hinge", f(j[1]), f(j[2]), j[3], j[4]))
    for n in ns:
        xml.append('%s  <geom name="g_%s" type="mesh" mesh="%s" mass="%.4f"/>' % (pad, n, n, part_mass(n)))
    if name == "grip":
        xml.append('%s  <site name="tcp" pos="0.2338 0 0.1992"/>' % pad)   # J4 + (137.4,-17) D6
    kids = [i for i, (_, jj, _) in enumerate(BODIES) if idx == parent(i)]
    if name == "grip":
        for i, (bn, _, _) in enumerate(BODIES):
            if bn in ("finger_u", "finger_d"):
                emit(i, depth + 1)
    elif idx + 1 < len(BODIES) and BODIES[idx + 1][1] is not None and not BODIES[idx + 1][0].startswith("finger"):
        emit(idx + 1, depth + 1)
    xml.append('%s</body>' % pad)

def parent(i):
    order = {"upper_base": 0, "upper": 1, "fore": 2, "wrist4": 3, "wrist5": 4, "grip": 5,
             "finger_u": 5, "finger_d": 5}
    return order.get(BODIES[i][0], -1)

emit(0, 1)
xml.append('  </worldbody>')
xml.append('  <equality><joint joint1="finger_d" joint2="finger_u" polycoef="0 1 0 0 0"/></equality>')
xml.append('  <actuator>')
for _, j, _ in [b for b in BODIES if b[1] is not None]:
    if j[0] == "finger_d":
        continue
    xml.append('    <position name="%s" joint="%s" kp="%.1f" ctrlrange="%.4f %.4f" forcerange="-%.2f %.2f"/>' % (
        j[0], j[0], j[6], j[3], j[4], j[5], j[5]))
xml.append('  </actuator>')
xml.append('  <keyframe><key name="home" qpos="0 0 0 0 0 0 0 0" ctrl="0 0 0 0 0 0 0"/></keyframe>')
xml.append('</mujoco>')

arm = "\n".join(xml) + "\n"
with open(os.path.join(HERE, "mjcf", "arm.xml"), "w") as fh:
    fh.write(arm)

scene = """<mujoco model="soma_arm_f2_scene">
  <compiler meshdir="meshes" angle="radian"/>
  <include file="arm.xml"/>
  <worldbody>
    <light directional="true" pos="1 -1 2.5" dir="-0.4 0.4 -1" diffuse="0.8 0.8 0.8"/>
    <geom name="floor" type="plane" pos="0 0 -0.001" size="2 2 0.05" contype="0" conaffinity="0" rgba="0.85 0.85 0.85 1"/>
  </worldbody>
</mujoco>
"""
with open(os.path.join(HERE, "mjcf", "scene.xml"), "w") as fh:
    fh.write(scene)
print("WROTE arm.xml + scene.xml")
for b, _, ns in BODIES:
    print("%-11s %.3f kg : %s" % (b, sum(part_mass(n) for n in ns), ", ".join(ns)))
