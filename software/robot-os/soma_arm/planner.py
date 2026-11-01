"""Joint-space trajectory planner.

Synchronized minimum-jerk (quintic) profiles: zero endpoint velocity and
acceleration, joint limits enforced, per-joint velocity/acceleration caps
from config. Produces a list of (t, q[6]) setpoints at dt spacing for the
base node to stream.
"""

import math

from . import config
from . import gravity


def _minjerk(s):
    """Min-jerk blend 0..1 for normalized time s in [0,1]."""
    s = max(0.0, min(1.0, s))
    return s * s * s * (10.0 + s * (-15.0 + 6.0 * s))


class PlanError(ValueError):
    pass


class TrajectoryPlanner:
    def __init__(self, vel_max=None, acc_max=None, joint_min=None,
                 joint_max=None):
        self.vmax = list(vel_max or config.JOINT_VEL_MAX)
        self.amax = list(acc_max or config.JOINT_ACC_MAX)
        self.jmin = list(joint_min if joint_min is not None
                         else config.JOINT_MIN)
        self.jmax = list(joint_max if joint_max is not None
                         else config.JOINT_MAX)

    def check_in_limits(self, q):
        for i in range(6):
            if not (self.jmin[i] - 1e-9 <= q[i] <= self.jmax[i] + 1e-9):
                raise PlanError(
                    f"joint {i+1} target {q[i]:.4f} outside limits "
                    f"[{self.jmin[i]:.3f}, {self.jmax[i]:.3f}]")

    def move_time(self, q0, q1, speed_scale=1.0):
        """Min duration for a synchronized min-jerk move.

        Min-jerk peaks: v_peak = 1.875*D/T, a_peak = 5.774*D/T^2.
        """
        if not 0.05 <= speed_scale <= 1.0:
            raise PlanError("speed_scale must be in [0.05, 1.0]")
        t = 0.0
        for i in range(6):
            d = abs(q1[i] - q0[i])
            if d < 1e-12:
                continue
            tv = 1.875 * d / (self.vmax[i] * speed_scale)
            ta = math.sqrt(5.774 * d / (self.amax[i] * speed_scale))
            t = max(t, tv, ta)
        return max(t, 0.05)  # never a zero-length move

    def check_torque(self, q, payload_kg=0.0):
        """Raise PlanError if any joint's static gravity torque at q
        exceeds 80% of rated under payload_kg. Returns worst ratio."""
        ok, wi, ratio = gravity.torque_ok(q, payload_kg)
        if not ok:
            raise PlanError(
                f"joint {wi+1} gravity torque exceeds "
                f"{config.TORQUE_DERATE:.0%} of rated "
                f"(worst {ratio:.2f}x) with {payload_kg:.2f} kg payload "
                f"— refuse move or reduce payload")
        return ratio

    def plan(self, q0, q1, speed_scale=1.0, dt=config.STREAM_DT_S,
             payload_kg=0.0):
        """-> (T, [(t, q[6]), ...]) synchronized quintic move.

        Includes the endpoint at t=T exactly. Both q0 and q1 must be
        inside joint limits. If payload_kg > 0 every waypoint is also
        checked against the 80%-of-rated gravity-torque derate; the
        whole move is refused if any sample violates.
        """
        self.check_in_limits(q0)
        self.check_in_limits(q1)
        T = self.move_time(q0, q1, speed_scale)
        n = max(2, int(math.ceil(T / dt)) + 1)
        pts = []
        for k in range(n):
            t = min(T, k * dt)
            s = _minjerk(t / T)
            pts.append((t, [q0[i] + (q1[i] - q0[i]) * s for i in range(6)]))
        pts[-1] = (T, list(q1))
        for (_, q) in pts:
            self.check_torque(q, payload_kg)
        return T, pts

    def plan_via(self, q0, waypoints, speed_scale=1.0,
                 dt=config.STREAM_DT_S, payload_kg=0.0):
        """Multi-segment move through a list of joint targets."""
        traj = []
        t_off = 0.0
        q = list(q0)
        for qn in waypoints:
            T, pts = self.plan(q, qn, speed_scale, dt, payload_kg)
            for (t, p) in pts:
                traj.append((t + t_off, p))
            t_off += T
            q = list(qn)
        return t_off, traj
