"""refine/pose_wrenches.py - map named/swept poses to the w_link5 (a,b,h)
load direction used by the R5 FEA direction bounds.

The wrist5 body rotation (relative to the AB pose where the W frame is
world-aligned) is R5w = rz(q1) ry(q2) ry(q3) ry(q4) rz(q5).  Gravity in
the W = (a,b,h) frame is g_w = R5w^T . (0,0,-1).  Components -> deck:
  -h (z<0) standard deck, +h _up, +-a _axp/_axn, +-b _lat.

Run: python3 pose_wrenches.py
"""
import math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "software", "robot-os"))
from soma_arm import config

LIM = list(zip(config.JOINT_MIN, config.JOINT_MAX))


def _rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def _ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1.0, 0], [-s, 0, c]])


def g_wrench(q):
    """gravity direction in the wrist5 (a,b,h) frame for pose q (rad)."""
    r = _rz(q[0]) @ _ry(q[1]) @ _ry(q[2]) @ _ry(q[3]) @ _rz(q[4])
    return r.T @ np.array([0.0, 0.0, -1.0])


NAMED = {
    "Q_WORST(+70/-70)":      [0, 70, -70, 0, 0, 0],
    "AB-level(+90/-90)":     [0, 90, -90, 0, 0, 0],
    "flop(-90/-114/+14)":    [0, -90, -114, 14, 0, 0],
    "Q_CLOSE(+30/-150/+90)": [0, 30, -150, 90, 0, 0],
    "reach0.36(+60/-83/+23)": [0, 60, -83, 23, 0, 0],
    "home":                  [0, 0, 0, 0, 0, 0],
    "stow(70/-160/+70)":     [0, 70, -160, 70, 0, 0],
    "rolled(-120/-180/+30/-70)": [0, -120, -180, 30, -70, 0],
}

print("== named poses: gravity in the w_link5 (a,b,h) frame ==")
print("%-28s %s" % ("pose", "(a,b,h) components"))
for nm, qd in NAMED.items():
    g = g_wrench([math.radians(x) for x in qd])
    print("%-28s (%+.2f, %+.2f, %+.2f)%s"
          % (nm, g[0], g[1], g[2],
             "   <- near-pure -h" if g[2] < -0.95 and abs(g[1]) < 0.2
             else ""))

# envelope extremes over the joint limits (grid incl. q5 roll)
print("\n== envelope extremes of each component (q1..q5 grid 12 deg, q6=0) ==")
ext = {"a": (0.0, None), "b": (0.0, None), "+h": (0.0, None),
       "-h": (0.0, None)}
st = math.radians(12)
for q1 in np.arange(LIM[0][0], LIM[0][1] + 1e-9, st):
    for q2 in np.arange(LIM[1][0], LIM[1][1] + 1e-9, st):
        for q3 in np.arange(LIM[2][0], LIM[2][1] + 1e-9, st):
            for q4 in np.arange(LIM[3][0], LIM[3][1] + 1e-9, st):
                for q5 in np.arange(LIM[4][0], LIM[4][1] + 1e-9, st):
                    g = g_wrench([q1, q2, q3, q4, q5, 0.0])
                    qd = [round(math.degrees(x)) for x in
                          (q1, q2, q3, q4, q5)]
                    if abs(g[0]) > abs(ext["a"][0]):
                        ext["a"] = (g[0], qd)
                    if abs(g[1]) > abs(ext["b"][0]):
                        ext["b"] = (g[1], qd)
                    if g[2] > ext["+h"][0]:
                        ext["+h"] = (g[2], qd)
                    if g[2] < ext["-h"][0]:
                        ext["-h"] = (g[2], qd)
for k, (v, qd) in ext.items():
    print("max |%s| comp %+.3f at q deg %s" % (k, v, qd))
print("""
FEA mapping:  -h -> standard deck (l5_scrann) | +h -> _up | +-a -> _axp/_axn
              +-b -> _lat | deck applies full-magnitude axis-pure wrench
              (envelope component <=1.0 by construction) -> conservative
              bound, not a pose-matched load.""")

# ===================== R6: pose-matched FORCE + MOMENT wrenches =====================
# The l5 deck loads the part with a single force at ref (113.7,0,-30) via a
# rigid-body patch on the J6 pocket floor.  Here the actual gravity wrench
# of the carried stack is built from the corrected mass model: the force is
# (m_stack + m_pay) * 9.81 * g-hat and the moment about the deck ref point
# is sum (r_i - r_ref) x (m_i * 9.81 * g-hat).  The residual between the
# true wrench and the deck's single-force model shows how faithful the
# idealisation is at each pose.

REF = np.array([113.7, 0.0, -30.0])     # deck ref point (W frame)
# carried stack: (mass kg, W-frame COM mm) - from mass_r5.py (AB - 223.1,0,89.5)
STACK = [
    ("j6 servo",  0.05500, (41.53,   0.00, -29.59)),
    ("gf",        0.01379, (98.52,  -0.03, -26.09)),
    ("g servo",   0.05500, (95.53,   0.00, -29.59)),
    ("gear",      0.00800, (119.70,  0.00, -17.00)),
    ("rack_u",    0.01200, (119.90, -12.99, -3.28)),
    ("rack_d",    0.01200, (119.90,  12.99, -30.72)),
    ("finger_u",  0.00097, (131.08,   3.00, -16.62)),
    ("finger_d",  0.00097, (131.08,  -3.00, -17.38)),
    ("tool_grip", 0.01939, (100.19, -0.01, -23.81)),
]
TCP = np.array([137.4, 0.0, -17.0])     # payload point (W frame, J6->TCP)


def wrench(q, pay):
    """pose-matched gravity wrench of stack + payload on the l5:
    returns (F N, M N.mm about REF, equiv application point mm)."""
    g = g_wrench(q)
    F = np.zeros(3)
    M = np.zeros(3)
    for _, m, com in STACK:
        f = np.asarray(com) - REF
        Fi = m * 9.81 * g
        F += Fi
        M += np.cross(f, Fi)
    Fi = pay * 9.81 * g
    F += Fi
    M += np.cross(TCP - REF, Fi)
    # equivalent application point: r_eq = ref + F x M / |F|^2
    r_eq = REF + np.cross(F, M) / (F @ F)
    return F, M, r_eq


print("\n== pose-matched wrenches at pay=0.50 kg (stack %.3f kg + payload) =="
      % sum(m for _, m, _ in STACK))
print("%-28s %-20s %-22s %s" % ("pose", "F (a,b,h) N", "M (a,b,h) N.mm",
                              "r_eq - ref"))
for nm, qd in NAMED.items():
    F, M, r_eq = wrench([math.radians(x) for x in qd], 0.50)
    print("%-28s (%+.2f,%+.2f,%+.2f)  (%+6.0f,%+6.0f,%+6.0f)  (%+.1f,%+.1f,%+.1f)"
          % (nm, F[0], F[1], F[2], M[0], M[1], M[2],
             r_eq[0] - REF[0], r_eq[1] - REF[1], r_eq[2] - REF[2]))
print("""
Reading: the deck applies F only (no moment) at the fixed REF; a faithful
wrench needs F applied at r_eq.  |r_eq - ref| is the application-point
error - the residual couple the deck misses.  The direction-matched entry
patches (pocket floor + bearing wall for lateral) approximate case bearing
better than the old floor-only patch.""")
