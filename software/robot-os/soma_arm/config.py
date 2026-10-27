"""Robot configuration — SOMA v3 hybrid arm.

Anything marked UNVERIFIED could not be sourced yet and MUST be confirmed
before driving real hardware (see docs/STATUS-firmware.md).
"""

import math

# ---------------------------------------------------------------- geometry
# Link lengths from ARM_HYBRID_V3.md (verified spec):
L1 = 0.120          # shoulder -> elbow, m
L2 = 0.100          # elbow -> wrist (J4 axis), m
L3 = 0.040          # wrist -> tool point, m

# Height of the J2 (shoulder) axis above the base/J1 mounting plane.
# UNVERIFIED — comes from Stream B CAD (base + J1 actuator stack height).
# Placeholder consistent with a ~60 mm OD x ~70 mm actuator on a turntable.
BASE_Z = 0.070

# Zero convention: q = 0 -> arm fully extended horizontally along +X,
# tool pointing forward (+X), roll 0. Joint pitch angles are elevation
# from horizontal (positive = tip up).

# ------------------------------------------------------------------ limits
# Mechanical joint limits (rad). UNVERIFIED until Stream B publishes
# interference/ROM numbers; current values are conservative placeholders.
JOINT_MIN = [
    math.radians(-170),   # J1 base yaw
    math.radians(-150),   # J2 shoulder
    math.radians(-150),   # J3 elbow
    math.radians(-150),   # J4 wrist pitch
    math.radians(-180),   # J5 wrist roll
    0.0,                  # J6 gripper jaw (0 = open)
]
JOINT_MAX = [
    math.radians(170),
    math.radians(150),
    math.radians(150),
    math.radians(150),
    math.radians(180),
    1.4,                  # ~80 deg jaw travel
]

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
