"""Robot configuration — SOMA v3 hybrid arm.

Geometry, joint limits, home pose and the table/case guard come from
`soma_arm.arm_geometry`, which is GENERATED from the single source of
truth `cad/arm/arm_params.py` by `cad/arm/gen_params.py`.  Do not edit
the numbers here — change the CAD params and rerun the generator.

Anything marked UNVERIFIED could not be sourced yet and MUST be confirmed
before driving real hardware (see docs/STATUS-firmware.md).
"""

import math

from . import arm_geometry as _g

# ---------------------------------------------------------------- geometry
# Real CAD geometry (cad/arm/arm_params.py KIN): shoulder axis height and
# link lengths.  Note the wrist/gripper stack makes J4->tip ~128 mm, so
# the tip reach is ~348 mm, not the 260 mm in the v3 brief.
L1 = _g.L1            # shoulder -> elbow, m
L2 = _g.L2            # elbow -> wrist (J4 axis), m
L3 = _g.L3            # wrist -> gripper tip, m

# Height of the J2 (shoulder) axis above the base/J1 mounting plane.
BASE_Z = _g.BASE_Z    # 0.146 m — verified from cad/arm/parts.py J2_Z

# Zero convention: q = 0 -> arm fully extended horizontally along +X,
# tool pointing forward (+X), roll 0 — identical to the CAD build/home
# pose.  Joint pitch angles are elevation from horizontal (positive =
# tip up); the CAD frame uses the opposite sign on J2/J3/J4 (positive =
# down), the generator flips it.
HOME_Q = list(_g.HOME_Q)

# ------------------------------------------------------------------ limits
# Mechanical joint limits (rad) — from cad/arm/arm_params.py JOINTS via
# the generator (CAD frame: J1 +-170, J2 -70..+35, J3 +-90, J4 +-95,
# J5 +-160, J6 +-90; pitch joints flipped to elevation-positive here).
JOINT_MIN = list(_g.JOINT_MIN)
JOINT_MAX = list(_g.JOINT_MAX)

# Table/case guard (required behaviour — checks.py c7 measured the
# boundary): the wrist stays above the table/lid only while
#     q3 >= GUARD_Q3_A + GUARD_Q3_B * q2      (host frame, rad)
# i.e. CAD frame J3 <= 45 - 2*J2.  Enforced in kinematics/planner here
# and in the base node (arm_clamp_q) — see firmware/base-node/src/main.cpp.
GUARD_Q3_A = _g.GUARD_Q3_A
GUARD_Q3_B = _g.GUARD_Q3_B


def guard_q3_min(q2):
    """Lowest allowed q3 (rad) for a given q2 under the table guard."""
    return GUARD_Q3_A + GUARD_Q3_B * q2


def guard_clamp(q):
    """Clamp q3 up onto the guard boundary if (q2, q3) violates it.

    Only q3 is raised (elbow folds back up); q2 is left alone — moving
    the shoulder could swing the upper link into the base. Returns a new
    list.
    """
    q = list(q)
    lo = guard_q3_min(q[1])
    if q[2] < lo:
        q[2] = lo
    return q


def within_guard(q):
    return q[2] >= guard_q3_min(q[1]) - 1e-9


# Velocity limits (rad/s) — conservative defaults for a 250 g payload arm.
# J1-J3 limited by chosen driver current caps; J4-J6 by STS3215 speed.
JOINT_VEL_MAX = [1.5, 1.5, 1.5, 2.0, 2.5, 3.0]
JOINT_ACC_MAX = [4.0, 4.0, 4.0, 8.0, 8.0, 12.0]

# ------------------------------------------------------------- CAN (J1-J3)
CAN_NODE_IDS = {0: 1, 1: 2, 2: 3}          # joint index -> CAN node id
CAN_BITRATE = 1_000_000

# Driver phase-current caps (A). Spec: ~5 A phase max, lower for J1.
CURRENT_LIMIT_A = [3.0, 5.0, 5.0]          # J1, J2, J3  (UNVERIFIED pending
                                           # bench measurement — start here)
GEAR_RATIO = 15.0                          # cycloidal 15:1
MOTOR_POLE_PAIRS = 7                       # 5010 = 12N14P -> 7 pp (UNVERIFIED)

# ------------------------------------------------------ Feetech (J4-J6)
SERVO_IDS = {3: 4, 4: 5, 5: 6}             # joint index -> servo id
SERVO_BAUD = 1_000_000                     # Feetech factory default; the spec
                                           # flags 1 Mbps UNVERIFIED on this
                                           # bus wiring — confirm on bench
SERVO_COUNTS_PER_RAD = 4096.0 / (2.0 * math.pi)
SERVO_CENTER = 2048

# --------------------------------------------------------------- host link
LINK_BAUD = 115200                         # USB-UART console speed
LINK_TIMEOUT_S = 0.5                       # watchdog: no frame -> freeze
HEARTBEAT_PERIOD_S = 0.1
STREAM_DT_S = 0.02                         # trajectory point period (50 Hz)

JOINT_NAMES = ["J1", "J2", "J3", "J4", "J5", "J6"]
