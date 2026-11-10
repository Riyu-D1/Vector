"""fullcheck/fea/fc_loads.py - per-part joint wrenches for the bolted/pinned
per-part SF2 study (arm-fullfix Task 4).

Same mass model as fc_torque.py (gravity_up1 patched by mass_r9, stale fore
entry dropped), payload 0.25 kg.  For each part the downstream bodies'
lumped masses are reduced to a wrench (F, M) at the part's interface joint,
expressed in the part's own home/STL frame (the frame the FE mesh is in) -
the lighten/l_loads.py method.  Pose = the fc_torque worst for the
governing joint (see POSES).

Part -> (body whose frame the STL lives in, 1-based downstream joint, pose key)

Run:  python3 fullcheck/fea/fc_loads.py   ->  fullcheck/fea/loads.json
"""
import os, sys, json, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "software", "robot-os"))
sys.path.insert(0, os.path.join(ROOT, "upgrade1"))
sys.path.insert(0, os.path.join(ROOT, "refine"))
from soma_arm.kinematics import ArmKinematics, _t, _rx, _ry, _rz
from soma_arm import config
import gravity_up1 as G1
import mass_r9
mass_r9.apply(G1)

G1.PARTS = [p for p in G1.PARTS
            if not (p[0] == "fore" and abs(p[1] - 0.02186139) < 2e-5)]
G1._LOCAL = G1._local_parts()

G = 9.81
gvec = np.array([0.0, 0.0, -G])
PAYLOAD = 0.25
KIN = ArmKinematics()

BODIES = ["upper_base", "upper", "fore", "wrist4", "wrist5", "grip"]
DOWN = [("upper_base", "upper", "fore", "wrist4", "wrist5", "grip"),
        ("upper", "fore", "wrist4", "wrist5", "grip"),
        ("fore", "wrist4", "wrist5", "grip"),
        ("wrist4", "wrist5", "grip"), ("wrist5", "grip"), ("grip",)]
PART = {b: (np.array([m for m, _ in G1._LOCAL[b]]),
            np.array([c for _, c in G1._LOCAL[b]])) for b in BODIES}

def frames(q):
    T_ub = _t(0.0, 0.0, config.BASE_Z) @ _rz(q[0])
    T_up = T_ub @ _t(*config.D_J2) @ _ry(q[1])
    T_fore = T_up @ _t(*config.U_J3) @ _ry(q[2])
    T_w4 = T_fore @ _t(*config.F_J4) @ _ry(q[3])
    T_w5 = T_w4 @ _t(*config.W_J5) @ _rz(q[4])
    T_g = T_w5 @ _t(*config.W_J6) @ _rx(q[5])
    return {"upper_base": T_ub, "upper": T_up, "fore": T_fore,
            "wrist4": T_w4, "wrist5": T_w5, "grip": T_g}

# home-pose joint points (mm) - same as fc_collision/l_loads
J_HOME = {1: np.array([0.0, 0.0, 80.8]), 2: np.array([-20.0, 0.0, 143.5]),
          3: np.array([-20.0, 0.0, 270.2]), 4: np.array([96.4, 0.0, 216.2]),
          5: np.array([127.0, 0.0, 223.8]), 6: np.array([149.4, 0.0, 199.2])}
ANCHOR = {"upper_base": J_HOME[1], "upper": J_HOME[2], "fore": J_HOME[3],
          "wrist4": J_HOME[4], "wrist5": J_HOME[5], "grip": J_HOME[6]}
BODY_OF_FRAME = {"ground": None, "j1": "upper_base", "upper": "upper",
                 "fore": "fore"}

def to_stl(body, Tb, c_w):
    Rb, tb = Tb[:3, :3], Tb[:3, 3] * 1000.0
    return ANCHOR[body] + Rb.T @ (c_w - tb)

def wrench(q, body, jidx1, payload):
    """(F, M, B, g) of bodies downstream of joint jidx1, in the home frame
    of `body` (None -> world frame for ground parts)."""
    T = frames(q)
    pts = KIN.joint_positions(q)
    B_w = np.asarray(pts[jidx1 - 1])                     # metres
    F_w = np.zeros(3); M_w = np.zeros(3)
    for b in DOWN[jidx1 - 1]:
        Rb, tb = T[b][:3, :3], T[b][:3, 3]
        cw = (Rb @ PART[b][1].T).T + tb                  # (k,3) world m
        f = PART[b][0][:, None] * gvec[None, :]
        F_w += f.sum(axis=0)
        M_w += (np.cross(cw - B_w, f)).sum(axis=0)
    if payload:
        f = payload * gvec
        tcp = np.asarray(pts[6])
        F_w += f
        M_w += np.cross(tcp - B_w, f)
    if body is None:
        Rl = np.eye(3); Bl = B_w * 1000.0
    else:
        Rl = T[body][:3, :3]
        Bl = to_stl(body, T[body], B_w * 1000.0)
    return (Rl.T @ F_w, Rl.T @ M_w * 1000.0, Bl, Rl.T @ gvec,
            float(np.dot(M_w, np.array([0.0, 1.0, 0.0]))))

POSES = {
    "flop":  [0.0, -90.0, -114.0, 14.0, 0.0, 0.0],   # J2 worst 2.481
    "j3w":   [0.0, -120.0, -84.0, 14.0, 0.0, 0.0],   # J3 worst 1.258
    "j4w":   [0.0, -120.0, -90.0, 20.0, 0.0, 0.0],   # J4 worst 0.503
    "reach": [0.0,  60.0,  -83.0, 23.0, 0.0, 0.0],   # reach 2.31
}

# part -> (body frame, downstream joint, pose key)
SPEC = {
    "link1":           ("upper_base", 2, "flop"),
    "yaw_limit":       ("upper_base", 1, "flop"),
    "j1_cradle":       (None,         1, "flop"),
    "base_link":       (None,         1, "flop"),
    "base_reinf":      (None,         1, "flop"),
    "base_plate":      (None,         1, "flop"),
    "upper_out":       ("upper",      3, "j3w"),
    "upper_back":      ("upper",      3, "j3w"),
    "dogleg_l":        ("fore",       3, "j3w"),
    "dogleg_r":        ("fore",       3, "j3w"),
    "fore_l2":         ("fore",       4, "j4w"),
    "fore_r2":         ("fore",       4, "j4w"),
    "j4_cradle":       ("fore",       4, "j4w"),
    "cy2_housing":     ("upper",      2, "flop"),
    "cy3_housing":     ("upper",      3, "j3w"),
    "cy2_carrier":     ("upper_base", 2, "flop"),
    "cy3_carrier":     ("fore",       3, "j3w"),
    "cy2_out_flange":  ("upper_base", 2, "flop"),
    "cy3_out_flange":  ("fore",       3, "j3w"),
    "flange_j2":       ("upper_base", 2, "flop"),
    "flange_j3":       ("fore",       3, "j3w"),
    "front_spacer_j2": ("upper_base", 2, "flop"),
    "back_spacer_j2":  ("upper",      2, "flop"),
    "front_spacer_j3": ("fore",       3, "j3w"),
    "back_spacer_j3":  ("upper",      3, "j3w"),
}

def main():
    out = {}
    for name, (body, j, pk) in SPEC.items():
        q = [math.radians(a) for a in POSES[pk]]
        F, M, B, g, tau_w = wrench(q, body, j, PAYLOAD)
        out[name] = dict(body=body, joint=j, pose=POSES[pk], pose_key=pk,
                         F=F.tolist(), M=M.tolist(), B=B.tolist(),
                         g=g.tolist(), tau_axis=tau_w)
        print("%-16s J%d %-5s |F|=%6.2f N  |M|=%7.0f N.mm  M.jointaxis=%6.0f"
              % (name, j, pk, np.linalg.norm(F), np.linalg.norm(M), tau_w))
    with open(os.path.join(HERE, "loads.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print("wrote fullcheck/fea/loads.json")

if __name__ == "__main__":
    main()
