"""Robot configuration — SOMA v3 hybrid arm (carrier v1.3 hardware).

Real geometry from sim/STATUS-sim.md (home pose, all joints 0 = the
"L" folded pose, mm) with the D6 wrist2 redesign (wrist2/STATUS-wrist2.md):
  J1 (0,0,80.8) axis z | J2 (-20,0,143.5) y | J3 (-20,0,270.2) y
  J4 (96.4,0,216.2) y | J5 (127.0,0,223.8) z | J6 (149.4,0,199.2) x
  TCP home (233.8, 0, 199.2). Pitch joints: + angle = tip DOWN.
Anything marked UNVERIFIED could not be sourced yet and MUST be confirmed
before driving real hardware (see docs/STATUS-fw2.md).
"""

import math

# ---------------------------------------------------------------- geometry
# Rest-pose (q=0) translations between consecutive joint frames, metres.
# Frame chain (see kinematics.py):
#   T(0,0,BASE_Z) Rz(q1) T(D_J2) Ry(q2) T(U_J3) Ry(q3) T(F_J4) Ry(q4)
#   T(W_J5) Rz(q5) T(W_J6) Rx(q6) T(T_J6)
BASE_Z = 0.0808                     # J1 output plane height
D_J2 = (-0.020, 0.0, 0.0627)        # J1 -> J2  (J2 sits behind J1 axis)
U_J3 = (0.0, 0.0, 0.1267)           # J2 -> J3  (upper arm, vertical at 0)
F_J4 = (0.1164, 0.0, -0.0540)       # J3 -> J4  (forearm dogleg)
W_J5 = (0.0306, 0.0, 0.0076)        # J4 -> J5  (dorsal fin yaw, D6)
W_J6 = (0.0224, 0.0, -0.0246)       # J5 -> J6  (ventral keel roll, D6)
T_TCP = (0.0844, 0.0, 0.0)          # J6 -> TCP (on the J6 axis, D6)
# derived: J4 -> TCP vector at q=0 = (0.1374, 0, -0.017) m — the TCP line
# rides 17 mm below the J4 tool axis, so IK uses the 2D vector, not a scalar

L_UPPER = 0.1267                    # |U_J3|
L_FORE = (0.1164**2 + 0.0540**2) ** 0.5   # |F_J4| = 0.12833
F_REST_ANG = math.atan2(-0.0540, 0.1164)  # forearm rest droop = -24.90 deg
L_WRIST = (0.1374**2 + 0.0170**2) ** 0.5  # |W_J5+W_J6+T_TCP| at q=0 = 0.13845

# Pitch sign convention (sim): +q about +Y moves the tool tip DOWN.
# Pose.pitch = tool elevation (+up) = -(q2+q3+q4). Pose.roll = q6.

# ------------------------------------------------------------------ limits
# Mechanical joint limits (rad) — sim/STATUS-sim.md swept ranges.
JOINT_MIN = [
    -math.pi,               # J1 base yaw  ±180
    math.radians(-120),     # J2 shoulder  -120..+70
    -math.pi,               # J3 elbow     -180..+30
    math.radians(-70),      # J4 wrist pitch ±70
    math.radians(-70),      # J5 wrist yaw   ±70
    -math.pi,               # J6 gripper twist ±180
]
JOINT_MAX = [
    math.pi,
    math.radians(70),
    math.radians(30),
    math.radians(70),
    math.radians(70),
    math.pi,
]
GRIP_MIN = 0.0                        # jaw open (rad) — UNVERIFIED
GRIP_MAX = 1.4                        # jaw closed — calibrate on bench

# D9 conditional J6 sublimit (cradlefix/STATUS-cradlefix.md residual):
# with J5 < 0 the gripper servo cable-plug lump rolls up at |J6| > ~110 deg
# into the J5 vendor case rear-bottom edge — a vendor-pair collision that
# printed geometry cannot fix. Firmware-side sublimit; J6 keeps its full
# +-180 deg mechanical range whenever J5 >= 0.
J6_SUBLIM_J5_NEG = math.radians(110)

# Velocity limits (rad/s) — J2/J3 capped at the ESC's VEL_LIMIT_OUT
# (0.5 rad/s ~ 29 deg/s, slow/smooth for the printed cycloidal discs);
# the base node clamps jog velocity to the same bound.
JOINT_VEL_MAX = [1.5, 0.5, 0.5, 2.0, 2.5, 2.5]
JOINT_ACC_MAX = [4.0, 3.0, 3.0, 8.0, 8.0, 12.0]

# Rated joint torques (N·m) — stage W1 + fea_arm3; J1/J5/J6 [U].
RATED_TORQUE_NM = [0.98, 3.5, 2.25, 0.98, 0.98, 0.98]
TORQUE_DERATE = 0.80                  # planner refuses >80% of rated

# ------------------------------------------------------------- CAN (J2-J3)
CAN_NODE_IDS = {1: 2, 2: 3}           # joint index -> CAN node id
CAN_BITRATE = 1_000_000

# D4 printed-disc torque envelope (cyclo4/STATUS-cyc4.md): joint index
# -> max output torque the discs may see. The planner refuses waypoints
# above these caps AND the ESC clamps phase current to the same bound.
TORQUE_CAP_NM = {1: 3.0, 2: 2.0}      # J2, J3 (0-based joint index)
GEAR_RATIO = 40.0                     # cycloidal 40:1
GEAR_EFF = 0.7                        # UNVERIFIED
MOTOR_POLE_PAIRS = 7                  # 4008 assumed 12N14P (UNVERIFIED)
KT_MOTOR = 60.0 / (2.0 * math.pi * 330.0)   # ~0.0289 N·m/A, Tarot 4008
                                          # 330KV estimate (UNVERIFIED)
# Driver phase-current caps (A), CAN order [J2, J3]:
#   I_cap = T_cap / (KT_MOTOR * GEAR_RATIO * GEAR_EFF)
#   J2 3.0 N·m -> 3.71 A, J3 2.0 N·m -> 2.47 A
CURRENT_LIMIT_A = [TORQUE_CAP_NM[1] / (KT_MOTOR * GEAR_RATIO * GEAR_EFF),
                   TORQUE_CAP_NM[2] / (KT_MOTOR * GEAR_RATIO * GEAR_EFF)]

# ------------------------------------------------------ Feetech (bus A)
# channel index -> servo id: J1 STS3250, J4/J5/J6 STS3215, GRIP STS3215
SERVO_IDS = {0: 1, 3: 4, 4: 5, 5: 6, 6: 7}
SERVO_BAUD = 1_000_000                # factory default; UNVERIFIED on
                                      # this wiring — confirm on bench
SERVO_COUNTS_PER_RAD = 4096.0 / (2.0 * math.pi)
SERVO_CENTER = 2048

# --------------------------------------------------------------- host link
LINK_BAUD = 115200
LINK_TIMEOUT_S = 0.5
HEARTBEAT_PERIOD_S = 0.1
STREAM_DT_S = 0.02

JOINT_NAMES = ["J1", "J2", "J3", "J4", "J5", "J6"]
N_CHAN = 7                            # J1..J6 + GRIP on the wire
