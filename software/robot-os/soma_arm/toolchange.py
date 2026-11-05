"""soma_arm/toolchange.py - D10 automounter dock-sequence planner.

Computes the joint-space waypoint list for docking or undocking a tool
on the D10 bayonet coupling.  Pure kinematics - no hardware access, so
it is unit-testable; Arm.on_move_complete()/servo feedback is taken as
injected values by verify_latch().

Sequence (dock = pick a tool out of the rack):

    approach  -> master slides -a..+a to the socket mouth (entry roll)
    insert    -> straight +a to the seat
    lock      -> J6 +TWIST (60 deg): lugs under catches, ball clicks
    lift      -> straight +z out of the rack slot
    (drop-off is the mirror: lower -> unlock -> retreat)

All moves are speed/torque capped (slow dock profile); the J6 moves
respect the D9 conditional sublimit while q5 < 0.
"""

import math
import numpy as np

from . import config
from .kinematics import ArmKinematics, Pose, IKError

# ---- coupling geometry (mirrors toolchg/tc_params.py, mm/deg) ----
TC_PLATE_X = 145.0          # rack fork plate centre, world x mm
TC_AXIS_Y = -80.0           # slot-array centre, world y mm
TC_AXIS_Z = 110.0           # tool axis height, world z mm
TC_PITCH = 46.0             # slot pitch along y
TC_N_SLOTS = 4
TC_GROOVE_MID = 74.75       # tool-a of the dock groove centre
TC_FACE = 69.0              # tool-a of the socket face
TC_J6O = 53.0               # tool-a of the J6-out origin at seat
                            # (J6 joint sits at a 53.0; horn face a 62.7
                            # = J6o + 9.7)
TCP_OFFSET = 68.7           # arm TCP sits this far +a of the master face
                            # (A_TCP 137.4 - master face a 68.7)

ENTRY_Q6 = -12.0            # deg J6: lugs centred in the socket gaps
TWIST = 60.0                # deg +a roll entry -> locked
LOCK_Q6 = ENTRY_Q6 + TWIST  # +48 deg

APPROACH_D = 12.0           # mm stand-off before the socket face
LIFT_D = 35.0               # mm +z to clear the slot/fork

# dock-profile caps (fraction of the planner defaults; conservative)
DOCK_VEL = np.array([0.8, 0.25, 0.25, 1.0, 1.0, 1.0])       # rad/s
DOCK_ACC = np.array([2.0, 1.5, 1.5, 4.0, 4.0, 6.0])         # rad/s2
TWIST_VEL = 0.6                                           # rad/s J6 roll


def slot_y(k):
    """world y (mm) of rack slot k (0..3)."""
    return TC_AXIS_Y + (k - 1.5) * TC_PITCH


def dock_origin_x():
    return TC_PLATE_X - TC_GROOVE_MID


def _solve_dock(q5v, x_axis, y, z, kin):
    """damped least-squares solve: J6-out origin at (x_axis, y, z) mm
    with the grip-frame x axis parallel to world +x.  5 constraints on
    joints 1..5; returns q5 rad array or None."""
    from .kinematics import _rx, _rz, _ry, _t

    def frame(q):
        t = _t(0.0, 0.0, config.BASE_Z) @ _rz(q[0])
        t = t @ _t(*config.D_J2) @ _ry(q[1])
        t = t @ _t(*config.U_J3) @ _ry(q[2])
        t = t @ _t(*config.F_J4) @ _ry(q[3])
        t = t @ _t(*config.W_J5) @ _rz(q[4])
        t = t @ _t(*config.W_J6)
        return t

    P = np.array([x_axis, y, z], dtype=float)
    q = np.asarray(q5v, dtype=float)
    for it in range(60):
        t = frame(q)
        p = t[:3, 3] * 1000.0
        d = t[:3, :3] @ np.array([1.0, 0.0, 0.0])
        e_pos = (p - P) / 1000.0                     # m
        e_dir = np.cross(d, np.array([1.0, 0.0, 0.0]))
        e = np.concatenate([e_pos, e_dir])           # 6-vector
        if np.linalg.norm(e) < 1e-8:
            break
        # numeric jacobian on joints 1..5 (roll doesn't move pos/dir)
        J = np.zeros((6, 5))
        dq = 1e-6
        for j in range(5):
            qq = q.copy(); qq[j] += dq
            t2 = frame(qq)
            p2 = t2[:3, 3] * 1000.0
            d2 = t2[:3, :3] @ np.array([1.0, 0.0, 0.0])
            J[:, j] = np.concatenate(
                [(p2 - p) / dq / 1000.0,
                 (np.cross(d2, np.array([1.0, 0.0, 0.0])) - e_dir) / dq])
        dq_step = np.linalg.lstsq(J.T @ J + 1e-6 * np.eye(5),
                                  -J.T @ e, rcond=None)[0]
        q[:5] += np.clip(dq_step, -0.2, 0.2)
    else:
        return None
    t = frame(q)
    p = t[:3, 3] * 1000.0
    d = t[:3, :3] @ np.array([1.0, 0.0, 0.0])
    if np.linalg.norm(p - P) > 0.5 or \
            np.linalg.norm(np.cross(d, np.array([1.0, 0.0, 0.0]))) > 1e-3:
        return None
    return q


def dock_q(slot, standoff=0.0, lift=0.0, roll=ENTRY_Q6, q_seed=None,
           kin=None):
    """Joint vector putting the master `standoff` mm behind its seated
    position along the tool axis (+ = short of the socket) and `lift` mm
    above the slot.  roll in deg.  Returns np.array q or raises IKError.
    """
    kin = kin or ArmKinematics()
    y = slot_y(slot)
    x_axis = dock_origin_x() + TC_J6O - standoff
    z = TC_AXIS_Z + lift
    seed = np.array(q_seed if q_seed is not None else
                    [-0.3, 0.5, 0.2, -0.7, 0.3], dtype=float)[:5].copy()
    q5 = _solve_dock(seed, x_axis, y, z, kin)
    if q5 is None:
        raise IKError("dock pose unreachable: slot %d standoff %.1f lift %.1f"
                      % (slot, standoff, lift))
    q = np.concatenate([q5, [math.radians(roll)]])
    if not kin.within_limits(q):
        raise IKError("dock roll out of limits: slot %d" % slot)
    return q


def plan_dock(slot, q_seed=None, kin=None):
    """Dock a tool from rack `slot`: returns list of (name, q, vel, acc)
    waypoint tuples - joint-space targets, capped speeds/accelerations.
    Translational legs are split into ~8 mm steps: linear joint-space
    interpolation between far-apart waypoints does NOT hold the tool
    axis straight, and the socket/slot fits are tight - intermediate
    solved poses keep the extraction near-vertical (tc_collision found
    slot-wall grinding with single-segment moves).
    """
    kin = kin or ArmKinematics()
    q_app = dock_q(slot, standoff=APPROACH_D, roll=ENTRY_Q6,
                   q_seed=q_seed, kin=kin)
    wps = [("approach", q_app, DOCK_VEL, DOCK_ACC)]
    q_prev = q_app
    for sd in (6.0, 2.0, 0.0):
        q_prev = dock_q(slot, standoff=sd, roll=ENTRY_Q6,
                        q_seed=q_prev, kin=kin)
        name = "seat" if sd == 0.0 else "insert"
        wps.append((name, q_prev, DOCK_VEL * 0.5, DOCK_ACC * 0.5))
    q_lock = q_prev.copy()
    q_lock[5] = math.radians(LOCK_Q6)
    if not kin.within_limits(q_lock):
        raise IKError("lock roll violates limits at slot %d" % slot)
    wps.append(("lock", q_lock, np.array([0, 0, 0, 0, 0, TWIST_VEL]),
                np.array([0, 0, 0, 0, 0, 6.0])))
    for lift in (8.0, 16.0, 24.0, LIFT_D):
        q_lock = dock_q(slot, standoff=0.0, lift=lift, roll=LOCK_Q6,
                        q_seed=q_lock, kin=kin)
        name = "clear" if lift == LIFT_D else "lift"
        wps.append((name, q_lock, DOCK_VEL * 0.5, DOCK_ACC * 0.5))
    return wps


def plan_undock(slot, q_seed=None, kin=None):
    """Return the currently-held tool to rack `slot` (mirror of
    plan_dock, same densified translation legs)."""
    kin = kin or ArmKinematics()
    q = dock_q(slot, standoff=0.0, lift=LIFT_D, roll=LOCK_Q6,
               q_seed=q_seed, kin=kin)
    wps = [("above", q, DOCK_VEL, DOCK_ACC)]
    for lift in (24.0, 16.0, 8.0, 0.0):
        q = dock_q(slot, standoff=0.0, lift=lift, roll=LOCK_Q6,
                   q_seed=q, kin=kin)
        name = "seat" if lift == 0.0 else "drop"
        wps.append((name, q, DOCK_VEL * 0.5, DOCK_ACC * 0.5))
    q_un = q.copy()
    q_un[5] = math.radians(ENTRY_Q6)
    wps.append(("unlock", q_un, np.array([0, 0, 0, 0, 0, TWIST_VEL]),
                np.array([0, 0, 0, 0, 0, 6.0])))
    for sd in (2.0, 6.0, APPROACH_D):
        q_un = dock_q(slot, standoff=sd, roll=ENTRY_Q6,
                      q_seed=q_un, kin=kin)
        name = "retreat" if sd == APPROACH_D else "back"
        wps.append((name, q_un, DOCK_VEL * 0.5, DOCK_ACC * 0.5))
    return wps


# ---------- verification via servo feedback ----------
def verify_latch(q_target_deg, q_read_deg, load_read, tol_deg=2.5):
    """After the lock twist: the servo position must reach the lock roll
    and show the detent's torque signature.  Returns (ok, detail).  Pure
    function so it is unit-testable; feed arm.read_servo() values.
    """
    err = q_read_deg - q_target_deg
    if abs(err) > tol_deg:
        return False, ("latch miss: q6 %.1f vs target %.1f (err %.1f)"
                       % (q_read_deg, q_target_deg, err))
    if load_read is not None and abs(load_read) < 5.0:
        return False, ("latch suspect: roll reached but load %.0f%% - "
                       "no detent contact felt" % load_read)
    return True, ("latch ok: q6 %.1f (err %.1f), load %s"
                  % (q_read_deg, err,
                     "n/a" if load_read is None else "%.0f%%" % load_read))


def j6_sublim_ok(q5_deg, q6_deg):
    """Respect the D9 conditional J6 sublimit: while J5 < 0, |J6| <= the
    configured sublimit.  The dock sequence never needs J5 < 0, but the
    helper is exercised in the tests and used by plan_dock callers that
    hand-modify waypoints."""
    if q5_deg < 0.0:
        return abs(q6_deg) <= math.degrees(config.J6_SUBLIM_J5_NEG) + 1e-6
    return True
