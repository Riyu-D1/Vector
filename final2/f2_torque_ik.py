"""final2/f2_torque_ik.py - F2 Task 3b + Task 4:
  IK reachability over the workspace (D6 chain vs the D5 scalar-l3
  back-projection, same limits -> unreachable/singular delta), and
  static torque per joint over the collision-sim pose set at 0.5 / 0.25 kg
  payload vs stage caps (J2 3.0, J3 2.0, J4 STS3250 1.12 derated,
  J5 STS3215 0.70 derated); max safe payload vs forward reach (+ plot).
Run: python3 final2/f2_torque_ik.py   (anaconda python3; writes
  final2/payload_vs_reach.png)
"""
import math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "software", "robot-os"))
from soma_arm import config
from soma_arm.kinematics import ArmKinematics, Pose, IKError
from soma_arm.gravity import gravity_torques, max_payload

KIN = ArmKinematics()
LIM = list(zip(config.JOINT_MIN, config.JOINT_MAX))
CAPS = {1: 3.0, 2: 2.0, 3: 1.12, 4: 0.70}          # stage caps N.m (J2,J3,J4,J5)
CAP_NAMES = {1: "J2", 2: "J3", 3: "J4", 4: "J5"}

# ================= IK reachability grid =================
print("== IK reachability: workspace grid, D6 vs D5-model ==")
KIN_D5 = ArmKinematics()
KIN_D5.w3a = 0.1318      # D5 scalar-l3 back-projection (h offset absent)
KIN_D5.w3z = 0.0
solved_d6 = solved_d5 = 0
only_d5, only_d6, both_fail = [], [], []
pitch_set = (-0.6, 0.0, 0.6)
for a in np.arange(0.05, 0.43, 0.02):          # radial dist in the arm plane
    for z in np.arange(-0.02, 0.46, 0.02):
        for yaw in (0.0, math.pi / 2):          # cover y != 0 via y=a cases
            x, y = (a, 0.0) if yaw == 0.0 else (0.0, a)
            for pit in pitch_set:
                p = Pose(x, y, z, pit, 0.0)
                r6 = r5 = False
                try:
                    KIN.ik(p); r6 = True; solved_d6 += 1
                except IKError:
                    pass
                try:
                    KIN_D5.ik(p); r5 = True; solved_d5 += 1
                except IKError:
                    pass
                if r5 and not r6:
                    only_d5.append((x, y, z, pit))
                elif r6 and not r5:
                    only_d6.append((x, y, z, pit))
                elif not r5 and not r6:
                    both_fail.append((x, y, z, pit))
tot = solved_d6 + len(only_d5) + len(both_fail)
print("grid %d targets: D6 solved %d, D5-model solved %d" % (tot, solved_d6, solved_d5))
print("solved by D5-model but NOT D6 (regressions): %d" % len(only_d5))
for t in only_d5[:20]:
    print("   regression (x %.2f y %.2f z %.2f pitch %.1f)" % t)
print("solved by D6 but not D5-model (gained): %d" % len(only_d6))
if only_d6:
    xs = [t[0] + t[1] for t in only_d6]
    print("   gained region radial dist %.2f..%.2f" % (min(xs), max(xs)))
# singularity check: smallest margin to annulus edge among solved
print("both models agree unreachable (outside annulus / limit-bound): %d" % len(both_fail))

# ================= static torque over the pose sweep =================
print("== torque per joint over sweep + MC + named poses (N.m) ==")
STEP = math.radians(2.5)
poses = []
for j in range(6):
    lo, hi = LIM[j]
    t = lo
    while t <= hi - 1e-9:
        q = [0.0] * 6; q[j] = t
        poses.append(q)
        t += STEP
    q = [0.0] * 6; q[j] = hi
    poses.append(q)
g2 = np.arange(LIM[1][0], LIM[1][1] + 1e-9, math.radians(5))
g3 = np.arange(LIM[2][0], LIM[2][1] + 1e-9, math.radians(5))
fx = fz = fmin = None
fxv, fzv, fminv = -1e9, -1e9, 1e9
for q2 in g2:
    for q3 in g3:
        q4 = -(q2 + q3)
        if not (LIM[3][0] <= q4 <= LIM[3][1]):
            continue
        tcp = KIN.fk_matrix([0, q2, q3, q4, 0, 0])[:3, 3]
        if tcp[0] > fxv: fxv, fx = tcp[0], [0, q2, q3, q4, 0, 0]
        if tcp[2] > fzv: fzv, fz = tcp[2], [0, q2, q3, q4, 0, 0]
        if tcp[2] < fminv: fminv, fmin = tcp[2], [0, q2, q3, q4, 0, 0]
NAMED = {"home": [0]*6,
         "stow": [0, math.radians(70), math.radians(-160), math.radians(70), 0, 0],
         "reach-forward": fx, "reach-up": fz, "reach-down": fmin,
         "wrist-fully-flexed": [0, math.radians(45), math.radians(-45),
                                math.radians(70), math.radians(70), 0]}
poses += list(NAMED.values())
for q2 in LIM[1]:
    for q3 in LIM[2]:
        for q4 in LIM[3]:
            poses.append([0, q2, q3, q4, 0, 0])
rng = np.random.default_rng(20261103)
poses += [[rng.uniform(lo, hi) for lo, hi in LIM] for _ in range(2200)]
print("%d poses" % len(poses))

worst = {pl: {i: (0.0, None) for i in range(6)} for pl in (0.5, 0.25)}
for q in poses:
    for pl in (0.5, 0.25):
        tau = gravity_torques(q, pl)
        for i in range(6):
            if abs(tau[i]) > worst[pl][i][0]:
                worst[pl][i] = (abs(tau[i]), list(q))
print("%-6s %-10s %-12s %-12s %s" % ("joint", "cap N.m", "max 0.5 kg", "max 0.25 kg", "verdict"))
for i in (1, 2, 3, 4):
    cap = CAPS[i]
    t5, q5 = worst[0.5][i]
    t2, q2 = worst[0.25][i]
    verdict = "PASS" if t5 <= cap else "FAIL %.0f%% over" % (100 * (t5 - cap) / cap)
    print("%-6s %-10.2f %-12.3f %-12.3f %s" % (CAP_NAMES[i], cap, t5, t2, verdict))
    print("   worst-pose deg:", np.round(np.degrees(q5), 1).tolist())
for i in (0, 5):
    print("%-6s %-10s %-12.3f %-12.3f (no stage cap; rated 0.98/0.80=%.2f)"
          % (config.JOINT_NAMES[i], "-", worst[0.5][i][0], worst[0.25][i][0], 0.98 * 0.8))

# ================= max payload vs forward reach =================
print("== max safe payload vs forward reach (level tool, stage caps) ==")
def payload_bound(q):
    tau0 = gravity_torques(q, 0.0)
    bounds = []
    for i in range(6):
        if i not in CAPS:
            continue
        # k = d tau / d payload (N.m per kg at TCP)
        k = gravity_torques(q, 1.0)[i] - tau0[i]
        if abs(k) < 1e-9:
            continue
        b = (CAPS[i] - tau0[i] * math.copysign(1.0, k)) / abs(k)
        bounds.append((max(0.0, b), i))
    return min(bounds) if bounds else (math.inf, -1)

rows = []
q2v = np.arange(LIM[1][0], LIM[1][1] + 1e-9, math.radians(2.5))
q3v = np.arange(LIM[2][0], LIM[2][1] + 1e-9, math.radians(2.5))
for q2 in q2v:
    for q3 in q3v:
        q4 = -(q2 + q3)
        if not (LIM[3][0] <= q4 <= LIM[3][1]):
            continue
        q = [0, q2, q3, q4, 0, 0]
        tcp = KIN.fk_matrix(q)[:3, 3]
        rows.append((float(tcp[0]), float(tcp[2]), q))
rows.sort()
seen = {}
for x, z, q in rows:
    b, ji = payload_bound(q)
    key = round(x, 2)
    if key not in seen or b > seen[key][0]:
        seen[key] = (b, ji, q, z)
print("%-10s %-12s %-10s %s" % ("reach x m", "max kg", "limit jt", "pose deg (q2,q3,q4)"))
table = []
for key in sorted(seen):
    b, ji, q, z = seen[key]
    table.append((key, z, b, CAP_NAMES.get(ji, "-"), q))
    print("%-10.2f %-12.3f %-10s %s" % (key, b, CAP_NAMES.get(ji, "-"),
                                       np.round(np.degrees([q[1], q[2], q[3]]), 0).tolist()))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
xs = [t[0] for t in table]
ys = [t[2] for t in table]
plt.figure(figsize=(7, 4))
plt.plot(xs, ys, "o-", ms=3)
for x, z, b, jn, q in table:
    if jn == "J2":
        plt.annotate(jn, (x, b), fontsize=6, alpha=0.6)
plt.axhline(0.5, ls="--", c="grey", lw=0.8)
plt.axhline(0.25, ls=":", c="grey", lw=0.8)
plt.xlabel("forward reach x (m, level tool)")
plt.ylabel("max payload (kg, stage caps)")
plt.title("F2: max safe TCP payload vs reach (J2 cap 3.0 / J3 2.0 / J4 1.12 / J5 0.70)")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(HERE, "payload_vs_reach.png"), dpi=140)
print("WROTE final2/payload_vs_reach.png")
