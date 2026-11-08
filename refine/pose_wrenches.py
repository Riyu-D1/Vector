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
