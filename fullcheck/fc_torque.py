"""fullcheck/fc_torque.py - whole-arm mass, COM and static torque audit.

Model: upgrade1/gravity_up1.py (part-mass table + J2 spring option)
patched by refine/mass_r9.py (measured R9 wrist solids + steel pin,
60%-solid PETG-CF convention). Stale pre-R9 fore entry dropped by
default (kept with --keepstale; effect reported both ways).

Caps vs ratings (from repo docs/config, no invented numbers):
  J1 STS3250  rated 1.569 N.m (16 kg.cm @12V, Feetech ds A/0)
  J2 cyclo    fw cap 3.0 N.m; struct bound 3.65 (cyclo4 SF2 bisection)
  J3 cyclo    fw cap 2.0 N.m; struct bound 3.64
  J4 STS3250  rated 1.569, working cap 1.12 (= /1.4 convention)
  J5/J6 STS3215 rated 0.98 [U], working cap 0.70 (= /1.4 convention)

Run: $PY fullcheck/fc_torque.py
"""
import math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "software", "robot-os"))
sys.path.insert(0, os.path.join(ROOT, "upgrade1"))
sys.path.insert(0, os.path.join(ROOT, "refine"))
from soma_arm import config
from soma_arm.kinematics import ArmKinematics
from soma_arm.kinematics import _t, _rx, _ry, _rz
import gravity_up1 as G1
import mass_r9
mass_r9.apply(G1)

STALE = ("fore", 0.02186139)
stale_hits = [p for p in G1.PARTS
              if p[0] == STALE[0] and abs(p[1] - STALE[1]) < 2e-5]
print("stale fore cradle entry %.5f kg in model: %s"
      % (STALE[1], bool(stale_hits)))
if stale_hits and "--keepstale" not in sys.argv:
    G1.PARTS = [p for p in G1.PARTS if p not in stale_hits]
    G1._LOCAL = G1._local_parts()
    print("  -> dropped (use --keepstale to bound the difference)")

KIN = ArmKinematics()
LIM = list(zip(config.JOINT_MIN, config.JOINT_MAX))
RATED = [1.569, 3.0, 2.0, 1.569, 0.98, 0.98]
CAPS  = [1.569, 3.0, 2.0, 1.12, 0.70, 0.70]
STRUCT = {1: 3.65, 2: 3.64}
PL = 0.25
G = 9.81
gvec = np.array([0.0, 0.0, -G])

BODIES = ["upper_base", "upper", "fore", "wrist4", "wrist5", "grip"]
DOWN = [("upper_base", "upper", "fore", "wrist4", "wrist5", "grip"),
        ("upper", "fore", "wrist4", "wrist5", "grip"),
        ("fore", "wrist4", "wrist5", "grip"),
        ("wrist4", "wrist5", "grip"), ("wrist5", "grip"), ("grip",)]
# per-body part arrays: (m_k, c_local_kx3)
PART = {}
for b in BODIES:
    ps = G1._LOCAL[b]
    PART[b] = (np.array([m for m, _ in ps]),
               np.array([c for _, c in ps]))
BODYM = {b: PART[b][0].sum() for b in BODIES}

def frames(q):
    T_ub = _t(0.0, 0.0, config.BASE_Z) @ _rz(q[0])
    T_up = T_ub @ _t(*config.D_J2) @ _ry(q[1])
    T_fore = T_up @ _t(*config.U_J3) @ _ry(q[2])
    T_w4 = T_fore @ _t(*config.F_J4) @ _ry(q[3])
    T_w5 = T_w4 @ _t(*config.W_J5) @ _rz(q[4])
    T_g = T_w5 @ _t(*config.W_J6) @ _rx(q[5])
    return {"upper_base": T_ub, "upper": T_up, "fore": T_fore,
            "wrist4": T_w4, "wrist5": T_w5, "grip": T_g}

AXES_LOCAL = [np.array([0., 0., 1.]), np.array([0., 1., 0.]),
              np.array([0., 1., 0.]), np.array([0., 1., 0.]),
              np.array([0., 0., 1.]), np.array([1., 0., 0.])]
AXIS_BODY = ["upper_base", "upper", "fore", "wrist4", "wrist5", "grip"]

def torques(q, payload):
    """static gravity torques J1..J6 at pose q (rad), payload at TCP."""
    T = frames(q)
    # world coms per body
    cw = {}
    for b in BODIES:
        O, R = T[b][:3, 3], T[b][:3, :3]
        cw[b] = O + PART[b][1] @ R.T          # (k,3) world centroids
    # joint points + world axes
    pts = KIN.joint_positions(q)
    a_pitch = T["upper_base"][:3, :3] @ np.array([0., 1., 0.])
    ax = [np.array([0., 0., 1.]), a_pitch, a_pitch, a_pitch,
          T["wrist4"][:3, :3] @ np.array([0., 0., 1.]),
          T["wrist5"][:3, :3] @ np.array([1., 0., 0.])]
    tcp = pts[6]
    t = np.zeros(6)
    for i in range(6):
        p_i, a_i = np.asarray(pts[i]), ax[i]
        s = 0.0
        for b in DOWN[i]:
            r = cw[b] - p_i
            s += float((PART[b][0] * (np.cross(r, gvec) @ a_i)).sum())
        if payload:
            s += payload * float(np.dot(np.cross(tcp - p_i, gvec), a_i))
        t[i] = s
    return t

# ---------- total mass + home COM ----------
m_arm = sum(BODYM.values())
T0 = frames([0.0] * 6)
com = np.zeros(3)
for b in BODIES:
    O, R = T0[b][:3, 3], T0[b][:3, :3]
    com += (PART[b][0] * (O + PART[b][1] @ R.T).T).sum(axis=1)
com /= m_arm
print("\ntotal modelled arm mass %.3f kg" % m_arm)
print("home COM (world m): (%.3f, %.3f, %.3f); radial from J1 axis %.1f mm"
      % (com[0], com[1], com[2], 1000 * math.hypot(com[0], com[1])))
wrist = sum(BODYM[b] for b in ("wrist4", "wrist5", "grip"))
print("wrist+gripper carried mass %.3f kg" % wrist)

# ---------- pose space ----------
grid = []
for q2 in np.arange(LIM[1][0], LIM[1][1] + 1e-9, math.radians(6)):
    for q3 in np.arange(LIM[2][0], LIM[2][1] + 1e-9, math.radians(6)):
        for q4 in np.arange(LIM[3][0], LIM[3][1] + 1e-9, math.radians(6)):
            grid.append([0.0, q2, q3, q4, 0.0, 0.0])
rng = np.random.default_rng(20261121)
mc = [[rng.uniform(lo, hi) for lo, hi in LIM] for _ in range(2000)]
NAMED = {"flop  J2-90/J3-114/J4+14": [0, -90, -114, 14, 0, 0],
         "reach J2+60/J3-83/J4+23": [0, 60, -83, 23, 0, 0],
         "AB J2+90/J3-90 (J2>lim)": [0, 90, -90, 0, 0, 0],
         "worst J2+70/J3-70": [0, 70, -70, 0, 0, 0],
         "stow J2+70/J3-160/J4+70": [0, 70, -160, 70, 0, 0]}
poses = grid + mc + [[math.radians(a) for a in q] for q in NAMED.values()]
print("\npose set: %d grid + %d MC + %d named" % (len(grid), len(mc), len(NAMED)))

worst = {i: (0.0, None) for i in range(6)}
wbound, qbound, jbound = 1e9, None, -1
wbound_st, = (1e9,)
qb_st, jb_st = None, -1
for q in poses:
    t0 = torques(q, 0.0)
    t1 = torques(q, 1.0)
    t = t0 + PL * (t1 - t0)
    for i in range(6):
        if abs(t[i]) > worst[i][0]:
            worst[i] = (abs(t[i]), list(q))
    for i, cap in enumerate(CAPS):
        k = t1[i] - t0[i]
        if abs(k) < 1e-9:
            continue
        b = max(0.0, (cap - t0[i] * math.copysign(1.0, k)) / abs(k))
        if b < wbound:
            wbound, qbound, jbound = b, list(q), i
        if i in STRUCT:
            bs = max(0.0, (STRUCT[i] - t0[i] * math.copysign(1.0, k)) / abs(k))
            if bs < wbound_st:
                wbound_st, qb_st, jb_st = bs, list(q), i

print("\n=== worst |tau| at %.2f kg over %d poses ===" % (PL, len(poses)))
print("%-4s %9s %9s %9s %9s   %s" % ("jt", "tau", "rated", "cap", "cap%", "pose deg"))
for i in range(6):
    w, q = worst[i]
    qs = np.round(np.degrees(q), 0).tolist() if q is not None else "n/a"
    print("J%-3d %9.3f %9.3f %9.3f %8.0f%%   %s"
          % (i + 1, w, RATED[i], CAPS[i], 100 * w / CAPS[i], qs))
print("workspace payload bound vs caps: %.3f kg (J%d) at %s"
      % (wbound, jbound + 1, np.round(np.degrees(qbound), 0).tolist()))
print("workspace payload bound vs cyclo struct (J2 3.65/J3 3.64): %.3f kg (J%d) at %s"
      % (wbound_st, jb_st + 1, np.round(np.degrees(qb_st), 0).tolist()))

print("\n=== named poses, tau at %.2f kg ===" % PL)
for nm, qd in NAMED.items():
    q = [math.radians(a) for a in qd]
    t = torques(q, PL)
    print("%-34s J1 %+.2f  J2 %+.2f  J3 %+.2f  J4 %+.2f  J5 %+.2f  J6 %+.2f"
          % (nm, *t[:6]))

print("\n=== J2 spring ON (k=0.55, q2>0) worst at %.2f kg ===" % PL)
w2, qw = 0.0, None
for q in poses:
    t = torques(q, PL)
    t[1] -= G1.j2_spring_torque(q[1])
    if abs(t[1]) > w2:
        w2, qw = abs(t[1]), q
print("J2 worst %.3f N.m at %s (cap 3.0)" % (w2, np.round(np.degrees(qw), 0).tolist()))
