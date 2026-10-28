"""sim/build_mjcf.py - writes sim/arm.xml and sim/scene.xml (MuJoCo model of arm-2-done).
Run: ~/Knoll/mini/.venv/bin/python sim/build_mjcf.py
Meshes are the build_arm2b.py STLs (home/L pose, world mm); bodies keep pos=0 and each
joint pos is the joint centre in metres.  Joint centres/axes from ap2.py, arm2_checks.py
and arm2b_checks.py; masses = printed vol x 1.27 g/cm3 x 0.6 + servo masses."""
import os
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
MESHES = os.path.join(HERE, "meshes")

# ---------------- joints: (name, pos m, axis, lo rad, hi rad, forcerange, kp) ----------------
J1 = ("J1", (0.0, 0.0, 0.0808), (0, 0, 1), -3.14, 3.14, 0.98, 10.0)          # yaw, horn centre (0,0) z 80.8
J2 = ("J2", (-0.020, 0.0, 0.1435), (0, 1, 0), -2.0944, 1.2217, 3.5, 80.0)   # -120..+70 deg
J3 = ("J3", (-0.020, 0.0, 0.2702), (0, 1, 0), -3.1416, 0.5236, 2.25, 50.0)  # -180..+30 deg
J4 = ("J4", (0.0964, 0.0, 0.2162), (0, 1, 0), -1.2217, 1.2217, 0.98, 15.0)  # +-70 deg
J5 = ("J5", (0.1340, 0.0, 0.2404), (0, 0, 1), -1.2217, 1.2217, 0.98, 15.0)  # +-70 deg, along h -> +Z home
J6 = ("J6", (0.1532, 0.0, 0.2162), (1, 0, 0), -3.14, 3.14, 0.98, 8.0)       # roll along tool axis a -> +X home
FU = ("finger_u", (0.1250, 0.0, 0.2162), (0, 1, 0), 0.0, 0.0125, 5.0, 50.0)
FD = ("finger_d", (0.1250, 0.0, 0.2162), (0, -1, 0), 0.0, 0.0125, 5.0, 50.0)

# ---------------- bodies in chain order: (name, joint or None, part names) ----------------
BODIES = [
    ("base", None, ["base_plate", "base_link", "j1_cradle", "vendor_sts3250_j1", "base_reinf"]),
    ("upper_base", J1, ["yaw_limit", "link1", "front_spacer_j2", "flange_j2", "vendor_actout_j2"]),
    ("upper", J2, ["vendor_act_j2", "back_spacer_j2", "vendor_6803_j2", "upper_out", "upper_back",
                    "vendor_act_j3", "back_spacer_j3", "vendor_6803_j3"]),
    ("fore", J3, ["front_spacer_j3", "flange_j3", "vendor_actout_j3", "dogleg_l", "dogleg_r",
                   "fore_l2", "fore_r2", "j4_cradle", "vendor_sts3215_j4"]),
    ("wrist4", J4, ["link4", "vendor_sts3215_j5"]),
    ("wrist5", J5, ["link5", "vendor_sts3215_j6"]),
    ("grip", J6, ["grip_frame", "vendor_sts3215_g", "vendor_gear_grip", "vendor_rack_u", "vendor_rack_d"]),
    ("finger_u", FU, ["finger_u"]),
    ("finger_d", FD, ["finger_d"]),
]

# vendor part masses kg [U where the CAD says U]; everything else: vol x 1.27 x 0.6
MASS = {"vendor_sts3250_j1": 0.075,
        "vendor_sts3215_j4": 0.055, "vendor_sts3215_j5": 0.055, "vendor_sts3215_j6": 0.055,
        "vendor_sts3215_g": 0.055,
        "vendor_act_j2": 0.300, "vendor_act_j3": 0.300,
        "vendor_gear_grip": 0.008, "vendor_rack_u": 0.012, "vendor_rack_d": 0.012,
        "vendor_6803_j2": 0.0075, "vendor_6803_j3": 0.0075}
RHO = 1.27e-3          # g/mm3 solid PETG
INFILL = 0.6

def part_mass(name):
    if name in MASS:
        return MASS[name]
    m = trimesh.load_mesh(os.path.join(MESHES, name + ".stl"), force="mesh")
    return m.volume * RHO * INFILL / 1000.0          # mm3 -> g -> kg

def f(v):
    return " ".join("%.4f" % x for x in v)

parts = [(n, b) for b, _, ns in BODIES for n in ns]
assert len(parts) == 38, len(parts)
xml = []
xml.append('<mujoco model="soma_arm">')
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
        xml.append('%s  <site name="tcp" pos="0.2282 0 0.2162"/>' % pad)   # J4 + 131.8 along a
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
        continue          # finger_d follows finger_u through the equality coupling
    xml.append('    <position name="%s" joint="%s" kp="%.1f" ctrlrange="%.4f %.4f" forcerange="-%.2f %.2f"/>' % (
        j[0], j[0], j[6], j[3], j[4], j[5], j[5]))
xml.append('  </actuator>')
xml.append('  <keyframe><key name="home" qpos="0 0 0 0 0 0 0 0" ctrl="0 0 0 0 0 0 0"/></keyframe>')
xml.append('</mujoco>')

arm = "\n".join(xml) + "\n"
with open(os.path.join(HERE, "arm.xml"), "w") as fh:
    fh.write(arm)

scene = """<mujoco model="soma_arm_scene">
  <compiler meshdir="meshes" angle="radian"/>
  <include file="arm.xml"/>
  <worldbody>
    <light directional="true" pos="1 -1 2.5" dir="-0.4 0.4 -1" diffuse="0.8 0.8 0.8"/>
    <geom name="floor" type="plane" pos="0 0 -0.001" size="2 2 0.05" contype="0" conaffinity="0" rgba="0.85 0.85 0.85 1"/>
  </worldbody>
</mujoco>
"""
with open(os.path.join(HERE, "scene.xml"), "w") as fh:
    fh.write(scene)
print("WROTE arm.xml + scene.xml")
for b, _, ns in BODIES:
    print("%-11s %.3f kg : %s" % (b, sum(part_mass(n) for n in ns), ", ".join(ns)))
