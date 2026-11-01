"""Static gravity-torque model (point-mass) + payload derating.

Mass properties: fea_arm3/input/parts_AB.json per-part masses and
centroids, transcribed below. The json pose ("AB") is q=[0,+90,-90,0,0,0]
(arm horizontal); body-local centroids are recovered by un-rotating the
upper body by -90 deg about J2. Model reproduces the json's analytic
moments_nm (J2 3.286 / J3 1.759 / J4 0.801 Nm at 0.5 kg TCP payload).

max_payload() applies the 80%-of-rated derate per joint — at full reach
the J4 servo (rated 0.98 Nm) is the limiting joint.
"""

import math
import numpy as np

from . import config
from .kinematics import _t, _rx, _ry, _rz, ArmKinematics

G = 9.81

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
    ("fore",       0.05500000, ( 210.3985,  -4.5658,  89.5000)),
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


def gravity_torques(q, payload_kg=0.0):
    """Static holding torques (N·m) at joints J1..J6 for pose q with
    payload_kg carried at the TCP. Sign: positive = gravity pulls the
    joint in +q direction (matches the sim pitch convention)."""
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
    return tau


def max_payload(q, derate=None):
    """Largest TCP payload (kg) such that every joint's static gravity
    torque stays within `derate` * rated. Returns
    (payload_kg, limiting_joint_index, per_joint_bounds_kg).
    A joint that already exceeds its derated torque on links alone
    yields a bound of 0 (or negative headroom, reported as 0)."""
    if derate is None:
        derate = config.TORQUE_DERATE
    geo, tcp, T = _joint_geometry(q)
    gvec = np.array([0.0, 0.0, -G])
    tau_links = gravity_torques(q, 0.0)

    bounds = []
    for i in range(6):
        allowed = derate * config.RATED_TORQUE_NM[i]
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
        lim = derate * config.RATED_TORQUE_NM[i]
        ratio = abs(tau[i]) / lim if lim > 0 else 0.0
        if ratio > worst:
            worst, wi = ratio, i
    return (worst <= 1.0, wi, worst)
