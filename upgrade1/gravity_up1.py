"""UPGRADE1 design-study copy of soma_arm/gravity.py — NOT product code.

Chosen D1 changes (see DESIGN_CHANGES.md / STATUS-up1.md):
  1. J4 servo STS3215 -> Feetech STS3250 (ST-3250-C001). Same case
     envelope (45.22x24.72x35 mm vs 45.2x24.7x35 mm), same 25T spline,
     same 12V TTL bus. Real specs: rated 16 kg.cm = 1.569 N.m @12V,
     stall 50 kg.cm, mass 74.5 g (was 55 g -> +19.5 g, carried on the
     "fore" body = servo stator side bolted to the forearm).
     Source: Feetech datasheet rev A/0 2024-01-16 (feetech.cn).
  2. J2 coaxial torsion balance spring, one-way engagement at q2 >= 0:
     tau_s = K_SPRING * max(0, q2 - ENGAGE_RAD) opposing tip-down
     gravity torque. K_SPRING = 0.55 N.m/rad -> ~0.67 N.m assist at the
     +70 deg limit pose; worst-over-(q3,q4) net J2 = 2.67 N.m vs the
     2.8 N.m derated allowance (tolerates ~-15% rate error; a 0.45
     N.m/rad spring leaves only 0.004 N.m margin -> rejected).
     Spring class: stock stainless torsion spring wire ~2.0-2.2 mm /
     OD ~22-27 mm / ~5 active coils (Springmasters UK, e.g. part
     471671/471672); achieved rate [U] - shim on bench.

Everything else is verbatim from software/robot-os/soma_arm/gravity.py.
"""

import os
import sys

# allow running as a plain script from the repo-root upgrade1/ dir
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "software", "robot-os")
    ),
)

import math
import numpy as np

from soma_arm import config
from soma_arm.kinematics import _t, _rx, _ry, _rz, ArmKinematics

G = 9.81

# --- D1 delta 1: STS3250 rated torque (real datasheet value) ---------------
# index:            J1     J2    J3     J4      J5     J6
RATED_TORQUE_NM_UP1 = [0.98, 3.5, 2.25, 1.569, 0.98, 0.98]
#                                     ^^^^ 16 kg.cm = 1.569 N.m (was 0.98)

# --- D1 delta 2: J2 gravity-balance torsion spring -------------------------
J2_SPRING_K = 0.55          # N.m/rad, target rate (see header)
J2_SPRING_ENGAGE_RAD = 0.0  # spring picks up the arm only for q2 > 0


def j2_spring_torque(q2):
    """Assist torque (N.m) the balance spring applies against tip-down."""
    return J2_SPRING_K * max(0.0, q2 - J2_SPRING_ENGAGE_RAD)


# (body, mass kg, centroid mm) — centroids in the AB pose, verbatim from
# parts_AB.json. Bodies: upper_base (J1 out/J2 stator), upper (J2 out),
# fore (J3 out), wrist4, wrist5, grip (J6 out incl. fingers).
PARTS = [
    ("upper_base", 0.01000438, (   0.1765,   0.0036,  86.1185)),
    ("upper_base", 0.03243059, (  -8.0028,   0.0000, 113.7798)),
    ("upper_base", 0.00214011, ( -20.0000, -33.6250, 143.5000)),
    ("upper_base", 0.00391325, ( -19.9999,  32.1802, 143.5001)),
    ("upper_base", 0.00075387, ( -20.0000, -31.3664, 143.5000)),
    ("upper",      0.30000000, ( -20.0000,  -3.8000, 143.5000)),
    ("upper",      0.00720973, ( -20.0000,  25.6814, 143.5000)),
    ("upper",      0.00750000, ( -20.0000,  27.8000, 143.5000)),
    ("upper",      0.01443861, (  43.3500, -29.4136, 143.5000)),
    ("upper",      0.02101408, (  43.3500,  30.0846, 143.5000)),
    ("upper",      0.30000000, ( 106.7000,  -3.8000, 143.5000)),
    ("upper",      0.00720973, ( 106.7000,  25.6814, 143.5000)),
    ("upper",      0.00750000, ( 106.7000,  27.8000, 143.5000)),
    ("fore",       0.00269543, ( 106.7000, -34.1250, 143.5000)),
    ("fore",       0.00456931, ( 106.7000,  32.6738, 143.5001)),
    ("fore",       0.00075387, ( 106.7000, -31.3664, 143.5000)),
    ("fore",       0.01476488, ( 122.1943, -39.0023, 116.6632)),
    ("fore",       0.01476488, ( 122.1943,  39.0023, 116.6632)),
    ("fore",       0.01822479, ( 176.5844, -34.6000,  88.2569)),
    ("fore",       0.01811543, ( 176.7825,  34.6000,  88.2658)),
    ("fore",       0.02186139, ( 202.3020,   7.8644,  89.4179)),
    ("fore",       0.07450000, ( 210.3985,  -4.5658,  89.5000)),  # was 0.055
    ("wrist4",     0.02266971, ( 255.4230,  -7.3274, 121.5595)),
    ("wrist4",     0.05500000, ( 260.7000,  12.7015, 126.1442)),
    ("wrist5",     0.00853289, ( 262.8755,   0.0000,  90.5865)),
    ("wrist5",     0.05500000, ( 264.0658,   0.0000,  76.7985)),
    ("grip",       0.01591721, ( 320.2830,   0.0000,  85.8303)),
    ("grip",       0.05500000, ( 312.0658,   0.0000,  76.7985)),
    ("grip",       0.00800000, ( 337.2000,   0.0000,  89.5000)),
    ("grip",       0.01200000, ( 337.4000, -12.9788, 102.5571)),
    ("grip",       0.01200000, ( 337.4000,  12.9788,  76.4428)),
    ("grip",       0.00096585, ( 348.4791,   3.0000,  89.9452)),
    ("grip",       0.00096585, ( 348.4791,  -3.0000,  89.0548)),
]

# body frame origins in the AB pose (mm): the joint axis each body hangs
# off. upper_base hangs off J1 (yaw only) — its parts only feed J1 torque.
_ORIGIN_AB_MM = {
    "upper_base": (0.0, 0.0, 80.8),
    "upper":      (-20.0, 0.0, 143.5),
    "fore":       (106.7, 0.0, 143.5),
    "wrist4":     (223.1, 0.0, 89.5),
    "wrist5":     (260.7, 0.0, 113.7),
    "grip":       (279.9, 0.0, 89.5),
}

# in the AB pose the upper body is pitched +90 deg about J2; un-rotate
# part centroids into the body's rest frame. All other bodies are at
# zero accumulated pitch in AB.
_AB_ROT = {"upper": -math.pi / 2.0}     # applied as Ry(angle)


def _local_parts():
    out = {b: [] for b in _ORIGIN_AB_MM}
    for body, mass, cmm in PARTS:
        ox, oy, oz = _ORIGIN_AB_MM[body]
        v = np.array([(cmm[0] - ox) / 1000.0,
                      (cmm[1] - oy) / 1000.0,
                      (cmm[2] - oz) / 1000.0])
        if body in _AB_ROT:
            v = _ry(_AB_ROT[body])[:3, :3] @ v
        out[body].append((mass, v))
    return out


_LOCAL = _local_parts()

# which bodies are downstream of each joint
_DOWNSTREAM = [
    ("upper_base", "upper", "fore", "wrist4", "wrist5", "grip"),  # J1
    ("upper", "fore", "wrist4", "wrist5", "grip"),                # J2
    ("fore", "wrist4", "wrist5", "grip"),                         # J3
    ("wrist4", "wrist5", "grip"),                                 # J4
    ("wrist5", "grip"),                                           # J5
    ("grip",),                                                    # J6
]


def _body_frames(q):
    """World transform (origin, R) of each moving body at joint pose q.
    Same chain as ArmKinematics.fk_matrix."""
    T_ub = _t(0.0, 0.0, config.BASE_Z) @ _rz(q[0])
    T_up = T_ub @ _t(*config.D_J2) @ _ry(q[1])
    T_fore = T_up @ _t(*config.U_J3) @ _ry(q[2])
    T_w4 = T_fore @ _t(*config.F_J4) @ _ry(q[3])
    T_w5 = T_w4 @ _t(*config.W_J5) @ _rz(q[4])
    T_g = T_w5 @ _t(*config.W_J6) @ _rx(q[5])
    return {
        "upper_base": T_ub, "upper": T_up, "fore": T_fore,
        "wrist4": T_w4, "wrist5": T_w5, "grip": T_g,
    }


_KIN = ArmKinematics()


def _joint_geometry(q):
    """Per-joint (axis point, unit axis) in world — matches sim axes."""
    T = _body_frames(q)
    pts = _KIN.joint_positions(q)
    R_ub = T["upper_base"][:3, :3]
    a_pitch = R_ub @ np.array([0.0, 1.0, 0.0])      # J2/J3/J4 share this
    geo = [
        (pts[0], np.array([0.0, 0.0, 1.0])),                        # J1
        (pts[1], a_pitch),                                          # J2
        (pts[2], a_pitch),                                          # J3
        (pts[3], a_pitch),                                          # J4
        (pts[4], T["wrist4"][:3, :3] @ np.array([0.0, 0.0, 1.0])),  # J5
        (pts[5], T["wrist5"][:3, :3] @ np.array([1.0, 0.0, 0.0])),  # J6
    ]
    tcp = pts[6]
    return geo, tcp, T


def gravity_torques(q, payload_kg=0.0, spring=True):
    """Static holding torques (N·m) at joints J1..J6 for pose q with
    payload_kg carried at the TCP. Sign: positive = gravity pulls the
    joint in +q direction (matches the sim pitch convention).

    D1: with spring=True (default) the J2 balance spring's assist
    torque is subtracted from the J2 gravity load."""
    if len(q) != 6:
        raise ValueError("q must have 6 elements")
    geo, tcp, T = _joint_geometry(q)
    gvec = np.array([0.0, 0.0, -G])
    tau = np.zeros(6)

    for i in range(6):
        p_i, a_i = geo[i]
        t = 0.0
        for body in _DOWNSTREAM[i]:
            Tb = T[body]
            O, R = Tb[:3, 3], Tb[:3, :3]
            for mass, c_local in _LOCAL[body]:
                c = O + R @ c_local
                t += mass * float(np.dot(np.cross(c - p_i, gvec), a_i))
        if payload_kg:
            t += payload_kg * float(
                np.dot(np.cross(tcp - p_i, gvec), a_i))
        tau[i] = t
    if spring:
        tau[1] -= j2_spring_torque(q[1])
    return tau


def max_payload(q, derate=None):
    """Largest TCP payload (kg) such that every joint's static gravity
    torque stays within `derate` * rated. Returns
    (payload_kg, limiting_joint_index, per_joint_bounds_kg).
    A joint that already exceeds its derated torque on links alone
    yields a bound of 0 (or negative headroom, reported as 0).

    D1: uses RATED_TORQUE_NM_UP1 (J4 = STS3250 rated 1.569 N·m) and the
    J2 spring is included via gravity_torques."""
    if derate is None:
        derate = config.TORQUE_DERATE
    geo, tcp, T = _joint_geometry(q)
    gvec = np.array([0.0, 0.0, -G])
    tau_links = gravity_torques(q, 0.0)

    bounds = []
    for i in range(6):
        allowed = derate * RATED_TORQUE_NM_UP1[i]
        p_i, a_i = geo[i]
        k = float(np.dot(np.cross(tcp - p_i, gvec), a_i))   # Nm per kg
        if abs(k) < 1e-9:
            bounds.append(math.inf)         # payload can't load joint
            continue
        # |tau_links + m*k| <= allowed  ->  upper bound on m
        b = (allowed - tau_links[i] * math.copysign(1.0, k)) / abs(k)
        bounds.append(max(0.0, b))

    limiting = int(min(range(6), key=lambda i: bounds[i]))
    return (float(min(bounds)), limiting, bounds)


def torque_ok(q, payload_kg=0.0, derate=None):
    """(ok, worst_joint, worst_ratio) — worst_ratio = max |tau|/rated."""
    if derate is None:
        derate = config.TORQUE_DERATE
    tau = gravity_torques(q, payload_kg)
    worst, wi = 0.0, 0
    for i in range(6):
        lim = derate * RATED_TORQUE_NM_UP1[i]
        ratio = abs(tau[i]) / lim if lim > 0 else 0.0
        if ratio > worst:
            worst, wi = ratio, i
    return (worst <= 1.0, wi, worst)


# worst in-limit full-reach pose (J2 +70 deg, arm horizontal)
Q_WORST = [0.0, math.radians(70), math.radians(-70), 0.0, 0.0, 0.0]


if __name__ == "__main__":
    print("gravity_up1 — D1 upgrade model @ worst pose "
          "q=[0,+70,-70,0,0,0] deg")
    print("rated N.m:", RATED_TORQUE_NM_UP1)
    for p in (0.0, 0.25, 0.5):
        tau = gravity_torques(Q_WORST, p)
        row = []
        for i in range(6):
            util = abs(tau[i]) / RATED_TORQUE_NM_UP1[i] * 100.0
            row.append(f"J{i+1} {tau[i]:+.3f} ({util:.1f}%)")
        print(f"payload {p:>4.2f} kg: " + "  ".join(row))
    m, wi, bounds = max_payload(Q_WORST)
    print(f"max_payload = {m:.4f} kg, limiting = J{wi+1}")
    print("bounds kg:", ["inf" if b == math.inf else f"{b:.4f}"
                          for b in bounds])
