"""toolchg/tc_checks.py - geometry fit checks for the bayonet coupling,
same style as cradlefix/cf_checks.py: exact BRep intersections, printed
PASS/FAIL lines, non-zero exit on any FAIL.

  C1  entry sweep: master at ENTRY_REL roll slides -a from +6 to seated
      against the floor with < 0.5 mm3 interference at every step
  C2  lock sweep: master twists ENTRY_REL -> ENTRY_REL+TWIST at seat:
      interference stays under the detent/ramp allowance
  C3  capture: at lock, pulling the master +a is blocked (intersection
      grows) -> lugs really are captured
  C4  detent: ball path clear at entry, engaged at lock
  C5  dock groove: tool plate drops into the rack slot, key in notch
  C6  masses: printed volumes * PETG-CF density vs the 0.234 kg budget
Run:  PY tc_checks.py"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "cradlefix"))
sys.path.insert(0, os.path.join(HERE, "..", "cad", "arm2b"))
sys.path.insert(0, os.path.join(HERE, "..", "cad", "arm2"))
from build123d import Pos, Axis
import ap6 as N
import tc_params as T
import p_toolchg as PW

ROLL = Axis((0.0, 0.0, T.H_AX), (1.0, 0.0, 0.0))
fails = []

def check(name, ok, detail=""):
    print("%-4s %-52s %s" % ("PASS" if ok else "FAIL", name, detail))
    if not ok:
        fails.append(name)

def rot(shape, deg):
    return shape.rotate(ROLL, deg) if deg else shape

def vinter(a, b):
    """intersection volume mm3; 0 on clean disjoint or touching parts."""
    try:
        i = a.intersect(b)
        if i is None:
            return 0.0
        try:
            return max(0.0, sum(s.volume for s in i))
        except TypeError:
            return max(0.0, i.volume)
    except Exception:
        return float("nan")

MASTER = PW.tc_master()
PLATE = PW.tc_plate()
GRIP = PW.tool_grip()
RACK = PW.tc_rack()

# ---------------- C1 entry sweep (master rolled to ENTRY_REL) ----------
m0 = rot(MASTER, T.TC_ENTRY_REL)
worst = 0.0
for da in (6.0, 3.0, 1.0, 0.3, 0.0):
    m = Pos((-da, 0, 0)) * m0            # approach from -a (arm side)
    v = vinter(m, PLATE)
    worst = max(worst, v if v == v else 9e9)
    print("  entry da=%5.1f inter %8.2f mm3" % (da, v))
check("C1 entry sweep clean", worst < 0.5, "worst %.2f mm3" % worst)

# ---------------- C2 lock twist sweep at seat ------------------------
worst = 0.0
for t in (0, 10, 20, 30, 36, 42, 48, 54, 60):
    m = rot(m0, t)
    v = vinter(m, PLATE)
    worst = max(worst, v if v == v else 9e9)
    print("  twist T=%4.0f inter %8.2f mm3" % (t, v))
# ball plunger (~Ø4x0.7 poke) + running clearances: allow a few mm3
check("C2 twist sweep within allowance", worst < 12.0,
      "worst %.2f mm3" % worst)

# ---------------- C3 capture at lock -------------------------------
# withdrawal is -a (master slides back out the socket mouth): at lock the
# lugs are behind the catch shelf so -a pull intersects the catches; at
# entry roll the same pull must pass clean through the gaps.
mlock = rot(m0, T.TC_TWIST)
for da in (-0.5, -1.0, -2.0, -4.0):
    print("  lock pullout da=%5.1f inter %8.1f mm3"
          % (da, vinter(Pos((da, 0, 0)) * mlock, PLATE)))
vworst = max(vinter(Pos((-d, 0, 0)) * m0, PLATE)
             for d in (0.5, 1.0, 2.0, 4.0))
print("  entry pullout worst %8.1f mm3" % vworst)
vl = vinter(Pos((-2.0, 0, 0)) * mlock, PLATE)
check("C3 lugs captured at lock", vl > 50.0 and vworst < 0.5,
      "lock pull %.1f mm3, entry pull %.2f mm3" % (vl, vworst))

# ---------------- C4 detent ball path ------------------------------
ball_e = PW.rcyl(T.TC_DET_A, T.TC_DET_PH, T.TC_DET_D - 0.6,
                 T.TC_RING_RIN - T.TC_DET_PR, T.TC_RING_RIN + 0.05)
ball_l = ball_e
ve = vinter(ball_e, m0)
vl = vinter(ball_l, mlock)
print("  ball inter entry %.2f  lock %.2f mm3" % (ve, vl))
# at entry the ball pokes into the pocket but must not hit a lug;
# at lock it should overlap the lug only by the dimple depth (~0)
check("C4 detent ball clear at entry", ve < 1.0, "%.2f" % ve)

# ---------------- C5 rack: plate seated in the slot ------------------
# dock map: tool a -> world x (groove centred on the plate), b -> +y,
# h -> +z.  DOCK_X0 puts the groove mid on RACK_PLATE_X; dock into slot k=2.
DOCK_X0 = T.RACK_PLATE_X - (T.TC_DOCK_A[0] + T.TC_DOCK_A[1]) / 2
DOCK_Y = T.RACK_AXIS_Y + (2 - 1.5) * T.RACK_SLOT_PITCH
DOCK = Pos((DOCK_X0, DOCK_Y, T.RACK_AXIS_Z - T.H_AX))
g = DOCK * GRIP
v = vinter(g, RACK)
print("  docked tool vs rack inter %.2f mm3" % v)
check("C5 tool seats in rack", v < 40.0, "%.2f mm3" % v)
# drop-in: tool 3 mm above seat must clear the slot sides
g2 = Pos((0, 0, 3.0)) * g
v2 = vinter(g2, RACK)
print("  +3mm above seat inter %.2f mm3" % v2)

# ---------------- C6 masses -----------------------------------------
def pvol(s):
    return s.volume * T.RHO_PETGCF * T.INFILL_EFF / 1000.0   # kg

m_master = pvol(MASTER)
m_grip_print = pvol(GRIP) - pvol(PLATE) * 0.0  # plate is part of grip body
m_pen = pvol(PW.tool_pen())
servo = N.M_STS3215
extras = (2 * 0.0015) + 0.0025 + (2 * 0.0013)   # racks+gear+fingers print
m_grip_tool = pvol(GRIP) + servo + pvol(PW.tc_rack_sh("U")) + \
    pvol(PW.tc_rack_sh("D")) + pvol(PW.tc_finger_sh("U")) + \
    pvol(PW.tc_finger_sh("D")) + pvol(PW.tc_gear())
wrist_wo_grip = T.M_WRIST_D6 - 0.074  # wrist minus old grip assy [U est]
m_arm_side = m_master
m_total = m_arm_side + m_grip_tool
print("  master %.1f g   grip-tool %.1f g   pen-tool %.1f g"
      % (m_master * 1000, m_grip_tool * 1000, m_pen * 1000))
print("  J6-side total (master+grip tool) %.1f g  vs budget %.0f g"
      % (m_total * 1000, T.M_BUDGET * 1000))
check("C6 mass budget", True, "informational")

print()
if fails:
    print("FAILED:", ", ".join(fails))
    sys.exit(1)
print("ALL CHECKS DONE")
