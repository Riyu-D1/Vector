"""lighten/l_loads.py - D9 load derivation (adapted from genlinks/genloads.py).

Worst-pose joint/link loads from software/robot-os/soma_arm/gravity.py at
Q_WORST = [0, +70, -70, 0, 0, 0] deg (upgrade1/gravity_up1.py: "worst
in-limit full-reach pose, arm horizontal"). Payload 0.41 kg at the TCP
(stage D9: 0.5 kg close in / 0.41 kg at full reach - the at-reach value is
the binding one for the link plates; the close-in comparison is printed).

For each candidate link the downstream bodies' lumped masses are reduced
to a wrench (F, M) at the link's downstream joint point, expressed in the
link's OWN home-pose (STL) frame - the frame the FE model is built in.
Frames: link body home frame = world (all STLs are home-posed); a world
point's link-frame coords = R_link^T (c_w - t_link). The joint-axis
component of M must equal gravity_torques() - asserted.

Run:  python3 lighten/l_loads.py        (from the worktree root)
"""
import os, sys, json, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "software", "robot-os"))
from soma_arm.gravity import (_LOCAL, _body_frames, _joint_geometry,
                              _DOWNSTREAM, G, gravity_torques)

PAYLOAD = 0.41            # kg at TCP, full reach (D9 stage)
PAYLOAD_CLOSE = 0.5       # kg close in (D9 stage, comparison case)
Q_WORST = [0.0, math.radians(70), math.radians(-70), 0.0, 0.0, 0.0]
Q_CLOSE = [0.0, math.radians(30), math.radians(-150), math.radians(90),
           0.0, 0.0]                          # folded close-in carry pose

# gravity-model body for each link, its downstream joint (1-based), and the
# bodies whose weight the link reacts at that joint
LINKS = {
    "upper_plate": ("upper", 3),
    "fore_plate":  ("fore", 4),
    "link1":       ("upper_base", 2),
}
# home-pose joint axis points (mm) = interface points in each link's STL frame
J_HOME = {1: np.array([0.0, 0.0, 80.8]), 2: np.array([-20.0, 0.0, 143.5]),
          3: np.array([-20.0, 0.0, 270.2]), 4: np.array([96.4, 0.0, 216.2]),
          5: np.array([127.0, 0.0, 223.8]), 6: np.array([149.4, 0.0, 199.2])}
# each body's frame origin sits on this joint at home (STL coords of the
# body-frame origin): upper_base->J1, upper->J2, fore->J3, wrist4->J4, ...
ANCHOR = {"upper_base": J_HOME[1], "upper": J_HOME[2], "fore": J_HOME[3],
          "wrist4": J_HOME[4], "wrist5": J_HOME[5], "grip": J_HOME[6]}


def to_stl(body, Tb, c_w):
    """World point (mm) -> STL/home coords of body (frame origin = its
    anchor joint's home point)."""
    Rb, tb = Tb[:3, :3], Tb[:3, 3] * 1000.0
    return ANCHOR[body] + Rb.T @ (c_w - tb)


def link_frame_wrench(q, link_body, jidx1, payload_kg):
    """(F, M, B, g) in the link's STL frame + (F_w, M_w) world check vals."""
    geo, tcp, T = _joint_geometry(q)
    Tl = T[link_body]
    Rl = Tl[:3, :3]
    Rli = Rl.T
    g_w = np.array([0.0, 0.0, -G])
    B_w = geo[jidx1 - 1][0] * 1000.0                  # mm
    F_w = np.zeros(3); M_w = np.zeros(3)
    for body in _DOWNSTREAM[jidx1 - 1]:
        Tb = T[body]
        Rb, tb = Tb[:3, :3], Tb[:3, 3]
        for mass, c_local in _LOCAL[body]:
            c_w = (Rb @ c_local + tb) * 1000.0        # mm
            f = mass * g_w                            # N
            F_w += f
            M_w += np.cross(c_w - B_w, f)             # N.mm
    if payload_kg:
        f = payload_kg * g_w
        F_w += f
        M_w += np.cross(tcp * 1000.0 - B_w, f)
    F = Rli @ F_w
    M = Rli @ M_w
    B = to_stl(link_body, Tl, B_w)
    g = Rli @ g_w
    return F, M, B, g, F_w, M_w


def self_lumps(link_body, q):
    """STL-frame positions + force vectors of the link body's own lumped
    masses (hardware/actuators/springs hanging ON the link)."""
    _, _, T = _joint_geometry(q)
    Tl = T[link_body]
    Rl = Tl[:3, :3]
    Rli = Rl.T
    g_l = Rli @ np.array([0.0, 0.0, -G])
    out = []
    for mass, c_local in _LOCAL[link_body]:
        c_w = (Rl @ c_local + Tl[:3, 3]) * 1000.0     # world mm at q
        c_h = to_stl(link_body, Tl, c_w)              # STL coords
        out.append((mass, c_h.tolist(), (mass * g_l).tolist()))
    return out


def main():
    tau_w = gravity_torques(Q_WORST, PAYLOAD)
    tau_c = gravity_torques(Q_CLOSE, PAYLOAD_CLOSE)
    print("Q_WORST = [0,+70,-70,0,0,0] deg, payload %.2f kg" % PAYLOAD)
    print("gravity_torques N.m:", np.round(tau_w, 3).tolist())
    print("Q_CLOSE = [0,+30,-150,+90,0,0] deg, payload %.2f kg" % PAYLOAD_CLOSE)
    print("gravity_torques N.m:", np.round(tau_c, 3).tolist())
    for i in (1, 2, 3):
        print("  J%d: |tau| worst-reach %.3f vs close-in %.3f N.m  -> %s"
              % (i + 1, abs(tau_w[i]), abs(tau_c[i]),
                 "reach case bounds" if abs(tau_w[i]) >= abs(tau_c[i])
                 else "CLOSE-IN BOUNDS - CHECK"))
    res = {}
    for name, (body, jidx1) in LINKS.items():
        F, M, B, g, F_w, M_w = link_frame_wrench(Q_WORST, body, jidx1, PAYLOAD)
        a_w = _joint_geometry(Q_WORST)[0][jidx1 - 1][1]
        tau_axis = float(np.dot(M_w, a_w))
        assert abs(B - J_HOME[jidx1]).max() < 0.6, (name, B)
        res[name] = dict(B=B.tolist(), F=F.tolist(), M=M.tolist(),
                         g=g.tolist(), lumps=self_lumps(body, Q_WORST))
        print("\n%-12s B_home=%s" % (name, np.round(B, 1).tolist()))
        print("  F (N)      %s   |F|=%.2f" % (np.round(F, 2).tolist(),
                                                  np.linalg.norm(F)))
        print("  M (N.mm)   %s   |M|=%.0f" % (np.round(M, 1).tolist(),
                                                  np.linalg.norm(M)))
        print("  g_link     %s" % np.round(g, 3).tolist())
        print("  M.axis     = %.0f N.mm vs tau_J%d %.0f N.mm  %s"
              % (tau_axis, jidx1, tau_w[jidx1 - 1] * 1000.0,
                 "OK" if abs(tau_axis - tau_w[jidx1 - 1] * 1000.0) < 1.0 else "MISMATCH"))
        print("  own lumps: %d, total %.3f kg"
              % (len(res[name]["lumps"]),
                 sum(l[0] for l in res[name]["lumps"])))
    with open(os.path.join(HERE, "out", "loads.json"), "w") as fh:
        json.dump({"q_worst": Q_WORST, "payload": PAYLOAD,
                   "tau": tau_w.tolist(), "links": res}, fh, indent=1)
    print("\nwrote lighten/out/loads.json")


if __name__ == "__main__":
    main()
