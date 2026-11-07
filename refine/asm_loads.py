"""refine/asm_loads.py - R3 assembled load-path + payload-limit verification.

One authoritative static model run over the joint-limit pose space so the
previous claims can be reconciled explicitly:

  claim A (REFINE-LOG/wrist7_checks): 1-D horizontal model, J2 3.29 N.m
      @ 0.5 kg -> FAIL vs the 3.0 disc cap.
  claim B (final/SUMMARY + F2 sweep, product gravity = stale D5 masses,
      no spring): 0.5 kg close-in / ~0.41 kg workspace-wide, ~0.46 kg at
      0.36 m level reach; J2 cap binds.
  claim C (upgrade1 model, D6 masses + STS3250 J4 + J2 spring):
      max_payload 0.501 kg at Q_WORST.

Model used here: upgrade1/gravity_up1.py PARTS verbatim (the newest mass
set: STS3250 74.5 g at J4, D6 wrist centroids). Springs: J2 one-way
k=0.55 N.m/rad as designed (cad3/BOM_delta: Springmasters 471671 at J2
AND J3; the J3 spring's assist direction/range is NOT modelled -
unsprung J3 is the conservative convention, same as cad3/fea).

Caps (final/SUMMARY + config.TORQUE_CAP_NM + F2 stage caps):
  J2 3.0 N.m (printed-disc design envelope; cyclo4 SF-2 bound 3.65)
  J3 2.0 N.m (cyclo4 SF-2 bound 3.64)
  J4 1.12 N.m (STS3250 rated 1.569 / 1.4, F2 convention)
  J5/J6 0.70 N.m (STS3215 rated 0.98 / 1.4)

Target SF 2 lives INSIDE the caps: disc contact SF>=2 holds up to
3.65/3.64 N.m (cyclo4 bisection); servo "cap" is already derated /1.4.

Run: python3 refine/asm_loads.py
"""
import math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "software", "robot-os"))
sys.path.insert(0, os.path.join(ROOT, "upgrade1"))
from soma_arm import config
from soma_arm.kinematics import ArmKinematics
import gravity_up1 as G1

KIN = ArmKinematics()
LIM = list(zip(config.JOINT_MIN, config.JOINT_MAX))
CAPS = {1: 3.0, 2: 2.0, 3: 1.12, 4: 0.70, 5: 0.70}
CAP_NM = {1: "J2", 2: "J3", 3: "J4", 4: "J5", 5: "J6"}
STRUCT = {1: 3.65, 2: 3.64}          # cyclo4 SF=2 bisection bounds

def _spr(q2):
    return G1.j2_spring_torque(q2)

def tau_pair(q, spring):
    """(t0, t1) = torques at payload 0 and 1 kg in ONE FK pass each."""
    t0 = G1.gravity_torques(q, 0.0, spring=False)
    t1 = G1.gravity_torques(q, 1.0, spring=False)
    if spring:
        s = _spr(q[1])
        t0[1] -= s; t1[1] -= s
    return t0, t1

def tau(q, pl, spring):
    t = G1.gravity_torques(q, pl, spring=False)
    if spring:
        t[1] -= _spr(q[1])
    return t

def bound_for_pose(q, spring, tp=None):
    """payload bound (kg) at pose q = min over capped joints.
    tp = (t0,t1) precomputed torques at 0/1 kg."""
    t0, t1 = tp if tp is not None else tau_pair(q, spring)
    b = []
    for i, cap in CAPS.items():
        k = t1[i] - t0[i]
        if abs(k) < 1e-9:
            continue
        b.append((max(0.0, (cap - t0[i] * math.copysign(1.0, k)) / abs(k)), i))
    return min(b)

PAY = (0.25, 0.38, 0.5)

# ---------------- pose sets ----------------
Q_WORST = [0.0, math.radians(70), math.radians(-70), 0.0, 0.0, 0.0]
Q_CLOSE = [0.0, math.radians(30), math.radians(-150), math.radians(90),
           0.0, 0.0]
Q_AB = [0.0, math.radians(90), math.radians(-90), 0.0, 0.0, 0.0]
NAMED = {"Q_WORST(+70/-70)": Q_WORST, "Q_CLOSE(+30/-150/+90)": Q_CLOSE,
         "AB-level(+90/-90)": Q_AB, "home": [0.0] * 6,
         "stow": [0, math.radians(70), math.radians(-160),
                  math.radians(70), 0, 0]}

# full pitch sweep (q2,q3,q4 grid; J5/J6=0) + MC over all joints
grid = []
for q2 in np.arange(LIM[1][0], LIM[1][1] + 1e-9, math.radians(6)):
    for q3 in np.arange(LIM[2][0], LIM[2][1] + 1e-9, math.radians(6)):
        for q4 in np.arange(LIM[3][0], LIM[3][1] + 1e-9, math.radians(6)):
            grid.append([0.0, q2, q3, q4, 0.0, 0.0])
rng = np.random.default_rng(20261107)
mc = [[rng.uniform(lo, hi) for lo, hi in LIM] for _ in range(2000)]
poses = grid + mc + list(NAMED.values())
print("pose set: %d grid + %d MC + %d named = %d"
      % (len(grid), len(mc), len(NAMED), len(poses)), flush=True)

# ---------------- 1. worst |tau| per joint at the three payloads ----------------
# one FK pass pair per (pose, spring); payload is linear in m -> reuse.
for spring in (False, True):
    print("\n===== spring %s =====" % ("ON (J2, k=0.55, q2>0)" if spring
                                        else "OFF"), flush=True)
    worst = {pl: {i: (0.0, None) for i in range(6)} for pl in PAY}
    bmin, qmin, jmin = 1e9, None, -1
    for q in poses:
        t0, t1 = tau_pair(q, spring)
        for pl in PAY:
            t = t0 + pl * (t1 - t0)
            for i in range(6):
                if abs(t[i]) > worst[pl][i][0]:
                    worst[pl][i] = (abs(t[i]), q)
        b, ji = bound_for_pose(q, spring, (t0, t1))
        if b < bmin:
            bmin, qmin, jmin = b, q, ji
    for pl in PAY:
        row = "payload %.2f kg: " % pl
        for i in (1, 2, 3, 4, 5):
            w, q = worst[pl][i]
            verdict = "OK" if w <= CAPS[i] else "OVER"
            row += " J%d %.2f(%s)" % (i + 1, w, verdict)
        print(row, flush=True)
    for i in (1, 2, 3, 4, 5):
        w, q = worst[0.5][i]
        if w > 0.01:
            print("    J%d worst(0.5kg) %.3f N.m at q deg %s" %
                  (i + 1, w, np.round(np.degrees(q), 0).tolist()),
                  flush=True)
    print("    workspace-wide bound %.3f kg (lim %s) at %s"
          % (bmin, CAP_NM.get(jmin, "-"),
             np.round(np.degrees(qmin), 0).tolist()), flush=True)

# ---------------- 2. named-pose torque + payload bound tables ----------------
print("\n===== named poses (spring ON | OFF) =====")
print("%-22s %8s %s" % ("pose", "payload", "J2 J3 J4 N.m -> bound"))
for nm, q in NAMED.items():
    for spring in (True, False):
        for pl in (0.5,):
            t0, t1 = tau_pair(q, spring)
            t = t0 + pl * (t1 - t0)
            b, ji = bound_for_pose(q, spring, (t0, t1))
            print("%-22s spr=%d p=%.2f | J2 %.3f J3 %.3f J4 %.3f J5 %.3f"
                  " | bound %.3f kg (J%d)"
                  % (nm, spring, pl, t[1], t[2], t[3], t[4], b, ji + 1),
                  flush=True)

# ---------------- 3. payload vs level-tool reach (claim B reproduction) ----
print("\n===== max payload vs forward reach, level tool (spring OFF | ON) =====")
for spring in (False, True):
    rows = []
    for q2 in np.arange(LIM[1][0], LIM[1][1] + 1e-9, math.radians(2.5)):
        for q3 in np.arange(LIM[2][0], LIM[2][1] + 1e-9, math.radians(2.5)):
            q4 = -(q2 + q3)
            if not (LIM[3][0] <= q4 <= LIM[3][1]):
                continue
            q = [0.0, q2, q3, q4, 0.0, 0.0]
            tcp = KIN.fk_matrix(q)[:3, 3]
            rows.append((float(tcp[0]), float(tcp[2]), q))
    rows.sort()
    seen = {}
    for x, z, q in rows:
        b, ji = bound_for_pose(q, spring)
        key = round(x, 2)
        if key not in seen or b > seen[key][0]:
            seen[key] = (b, ji, q, z)
    print("spring %s:" % ("ON" if spring else "OFF"))
    print("%-10s %-9s %-6s %s" % ("reach x m", "max kg", "lim jt",
                                  "pose deg (q2,q3,q4)"))
    for key in sorted(seen):
        if key < 0.05:
            continue
        b, ji, q, z = seen[key]
        print("%-10.2f %-9.3f %-6s %s"
              % (key, b, CAP_NM.get(ji, "-"),
                 np.round(np.degrees([q[1], q[2], q[3]]), 0).tolist()),
              flush=True)

# ---------------- 5. wrist-local wrenches for the FEA decks ---------------
# TCP wrench seen by the wrist parts at full horizontal reach (tool forward):
# payload force at TCP + carried mass on the g-servo pocket.
print("\n===== wrist local load cases (arm horizontal, tool forward) =====")
J4X = 0.0
for pl in (0.25, 0.38, 0.5):
    Fz = -9.81 * pl
    Mb = Fz * (137.4 - 66.0)              # w_grip_frame plate at a~66
    Mb5 = Fz * (137.4 - 30.6)             # w_link5 plate at a~30.6
    Mb4 = Fz * (137.4 - 0.0)              # w_link4 about J4 axis a=0
    print("payload %.2f kg: Fz %.2f N -> M_b(gf plate) %.0f | "
          "M_b(l5 plate) %.0f | M_J4-axis %.0f N.mm"
          % (pl, Fz, Mb, Mb5, Mb4))
print("carried (unsuspended) mass on w_grip_frame cage: "
      "g-servo 55 g + gear 8 g + racks 24 g + fingers ~24 g ~ 0.11 kg -> "
      "1.08 N near (95,0,-40)")
print("w_link4/5 carried mass: j5+j6+g servos + cages ~0.19 kg at a~60 -> "
      "+~110 N.mm on the J5 plate, +~60 N.mm on the J4 plate")
