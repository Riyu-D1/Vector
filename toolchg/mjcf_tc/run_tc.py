"""toolchg/mjcf_tc/run_tc.py - headless MuJoCo run of the D10 dock
sequence on the kinematic scene (position actuators, weld toggles for
the tool handoff; contact is disabled like the f2 scene - latch physics
is covered by the C1-C5 CAD checks, this proves the joint trajectory).

Script (from the stage): approach, insert, roll to lock, release the
tool from the rack, lift, retreat - then return it to another slot and
pick the second tool (pen).

Run: ~/Vector-wt/sim/.venv-mj/bin/python toolchg/mjcf_tc/run_tc.py
"""
import math
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "software", "robot-os"))
from soma_arm import toolchange as TC
import mujoco

m = mujoco.MjModel.from_xml_path(os.path.join(HERE, "scene_tc.xml"))
d = mujoco.MjData(m)
print("nbody", m.nbody, "njnt", m.njnt, "nu", m.nu, "neq", m.neq)

ok = True
def res(tag, good, msg):
    global ok
    ok &= bool(good)
    print("%-7s %-66s %s" % (tag, msg, "PASS" if good else "FAIL"))

# ---- ids ----
def jid(n):
    return mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, n)
def eid(n):
    return mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_EQUALITY, n)
def bid(n):
    return mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, n)
def sid(n):
    return mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, n)

QA = {n: m.jnt_qposadr[jid(n)] for n in ("J1", "J2", "J3", "J4", "J5", "J6",
                                         "tool_free", "pen_free")}
EQ = {n: eid(n) for n in
      ["w_tool_grip", "w_pen_grip"] +
      ["w_tool_world_%d" % k for k in range(4)] +
      ["w_pen_world_%d" % k for k in range(4)]}
TOOL_B, PEN_B = bid("tool"), bid("pen")
MST, TREF, PREF = sid("mst"), sid("tool_ref"), sid("pen_ref")
WELD_SET = {"w_tool_grip", "w_pen_grip"}

def dock_pos_m(slot):
    dx, dy, dz = TC.dock_origin_x() - 96.4, TC.slot_y(slot), 127.0 - 216.2
    return np.array([dx / 1000.0, dy / 1000.0, dz / 1000.0])

def body_pose(b):
    return d.xpos[b].copy(), d.xquat[b].copy()

def pose_err(b, slot):
    p, qq = body_pose(b)
    dp = np.linalg.norm(p - dock_pos_m(slot))
    dq = abs(qq[0])                      # identity quat w==1
    return dp, dq

def set_eq(name, on):
    d.eq_active[EQ[name]] = 1 if on else 0

def drive(q, steps=700):
    for i, jn in enumerate(("J1", "J2", "J3", "J4", "J5", "J6")):
        d.ctrl[i] = q[i]
    for _ in range(steps):
        mujoco.mj_step(m, d)

def q_arm():
    return np.array([d.qpos[QA["J%d" % i]] for i in range(1, 7)])

def finite():
    return bool(np.all(np.isfinite(d.qpos)))

# ---- initial state: tool in slot 2, pen in slot 0, arm near approach --
mujoco.mj_resetData(m, d)
d.qpos[QA["tool_free"]:QA["tool_free"] + 7] = \
    [*dock_pos_m(2), 1, 0, 0, 0]
d.qpos[QA["pen_free"]:QA["pen_free"] + 7] = \
    [*dock_pos_m(0), 1, 0, 0, 0]
set_eq("w_tool_world_2", True)
set_eq("w_pen_world_0", True)
for n in WELD_SET:
    set_eq(n, False)
for k in (0, 1, 3):
    set_eq("w_tool_world_%d" % k, False)
for k in (1, 2, 3):
    set_eq("w_pen_world_%d" % k, False)
mujoco.mj_forward(m, d)
print("init tool pose err (slot2): %.1f mm  pen (slot0): %.1f mm"
      % (1000 * pose_err(TOOL_B, 2)[0], 1000 * pose_err(PEN_B, 0)[0]))

def run_leg(wps, stop_at=None):
    """drive through waypoints; returns when stop_at name reached."""
    for n, q, v, a in wps:
        drive(q)
        err = float(np.max(np.abs(q_arm() - np.asarray(q))))
        print("   wp %-9s q_arm %s  err %.3f rad" %
              (n, np.round(np.degrees(q_arm()), 1).tolist(), err))
        if n == stop_at:
            break
    return q_arm()

# =================== 1) dock slot 2: pick the grip tool ================
print("== DOCK slot 2 (grip tool) ==")
wps = TC.plan_dock(2)
run_leg(wps, stop_at="seat")
# seat check: master-face site vs socket-mouth site gap
gap = float(np.linalg.norm(d.site_xpos[MST] - d.site_xpos[TREF]) * 1000.0)
res("SEAT", gap < 3.0,
    "master-face to socket-mouth gap %.2f mm at seat (want < 3)" % gap)
run_leg(wps, stop_at="lock")
dp, dq = pose_err(TOOL_B, 2)
res("SEATED", dp < 0.002 and abs(1 - dq) < 0.02,
    "tool still seated after lock twist: %.1f mm, quat w %.3f" % (1000 * dp, dq))
set_eq("w_tool_grip", True)
set_eq("w_tool_world_2", False)
print("   weld tool<->grip ON, tool<->world_2 OFF (locked)")
p0 = d.xpos[TOOL_B].copy()
run_leg(wps, stop_at="clear")
dp, dq = pose_err(TOOL_B, 2)
lifted = float(d.xpos[TOOL_B][2] - p0[2]) * 1000.0
res("LIFT", 30.0 < lifted < 42.0 and finite(),
    "tool lifted %.1f mm with the arm (want ~35)" % lifted)

# retreat to a safe hover pose above the rack
q_hover = np.array(wps[-1][1]); 
drive(q_hover, 300)

# =================== 2) undock slot 3: put the grip tool back ==========
print("== UNDOCK slot 3 (return grip tool) ==")
wps = TC.plan_undock(3)
run_leg(wps, stop_at="seat")
# seated: tool pose should be at slot 3 dock pose within tol
dp, dq = pose_err(TOOL_B, 3)
set_eq("w_tool_world_3", True)
set_eq("w_tool_grip", False)
print("   weld tool<->world_3 ON, tool<->grip OFF (released)")
run_leg(wps, stop_at="retreat")
dp, dq = pose_err(TOOL_B, 3)
res("PARKED", dp < 0.003 and finite(),
    "tool parked in slot 3: pose err %.1f mm, quat w %.3f" % (1000 * dp, dq))
mst_gap = float(np.linalg.norm(d.site_xpos[MST] - d.site_xpos[TREF]) * 1000.0)
res("CLEAR", mst_gap > 8.0,
    "master retreated %.1f mm from the socket mouth" % mst_gap)

# =================== 3) dock slot 0: pick the pen ======================
print("== DOCK slot 0 (pen) ==")
wps = TC.plan_dock(0)
run_leg(wps, stop_at="seat")
gap = float(np.linalg.norm(d.site_xpos[MST] - d.site_xpos[PREF]) * 1000.0)
res("SEAT", gap < 3.0,
    "master-face to pen socket gap %.2f mm at seat" % gap)
run_leg(wps, stop_at="lock")
set_eq("w_pen_grip", True)
set_eq("w_pen_world_0", False)
print("   weld pen<->grip ON, pen<->world_0 OFF (locked)")
p0 = d.xpos[PEN_B].copy()
run_leg(wps, stop_at="clear")
lifted = float(d.xpos[PEN_B][2] - p0[2]) * 1000.0
res("LIFT", 30.0 < lifted < 42.0 and finite(),
    "pen lifted %.1f mm with the arm" % lifted)

# =================== summary ===========================================
fin = finite() and np.all(np.isfinite(d.xpos))
res("FINAL", fin, "all qpos/xpos finite at end: %s" % fin)
print("final arm q", np.round(np.degrees(q_arm()), 1).tolist())
print("tool at slot3 pose err %.1f mm, pen lifted+carried %.1f mm"
      % (1000 * pose_err(TOOL_B, 3)[0], lifted))
print("CHECKS", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
