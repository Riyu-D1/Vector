"""Forward and inverse kinematics for the SOMA v3 6-DOF arm.

Frames: base frame at the J1 axis on the turntable plane, +Z up.
The chain is:

    T = Rz(q1) Tz(BASE_Z) [Ry(-q2) Tx(L1)] [Ry(-q3) Tx(L2)]
                           [Ry(-q4) Tx(L3)] Rx(q5)

Pitch angles (J2..J4) are elevations from horizontal — positive tips the
link up. With all q = 0 the arm points straight along +X (260 mm reach,
tool axis +X). J5 is roll about the tool axis, J6 is the gripper jaw and
does not affect the TCP pose.
"""

import math
from dataclasses import dataclass

import numpy as np

from . import config


@dataclass
class Pose:
    """TCP pose: position (m) + tool pitch (elevation, rad) + roll (rad)."""
    x: float
    y: float
    z: float
    pitch: float = 0.0
    roll: float = 0.0


@dataclass
class IKSolution:
    q: list               # joint angles J1..J6 (J6 passed through)
    branch: int           # elbow branch: +1/-1


def _rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])


def _ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1]])


def _rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]])


def _tx(d):
    return np.array([[1, 0, 0, d], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])


def _tz(d):
    return np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, d], [0, 0, 0, 1]])


class IKError(ValueError):
    pass


class ArmKinematics:
    def __init__(self, l1=config.L1, l2=config.L2, l3=config.L3,
                 base_z=config.BASE_Z,
                 joint_min=None, joint_max=None):
        self.l1, self.l2, self.l3 = l1, l2, l3
        self.base_z = base_z
        self.jmin = list(joint_min if joint_min is not None
                         else config.JOINT_MIN)
        self.jmax = list(joint_max if joint_max is not None
                         else config.JOINT_MAX)

    # ------------------------------------------------------------ FK
    def fk_matrix(self, q):
        """Full 4x4 homogeneous TCP transform. q = 6 joint angles (rad)."""
        q1, q2, q3, q4, q5, _ = q
        t = _rz(q1) @ _tz(self.base_z)
        t = t @ _ry(-q2) @ _tx(self.l1)
        t = t @ _ry(-q3) @ _tx(self.l2)
        t = t @ _ry(-q4) @ _tx(self.l3)
        t = t @ _rx(q5)
        return t

    def fk(self, q):
        """FK -> Pose. Tool pitch = q2+q3+q4 (elevation of tool axis),
        roll = q5."""
        t = self.fk_matrix(q)
        pitch = q[1] + q[2] + q[3]
        return Pose(x=float(t[0, 3]), y=float(t[1, 3]), z=float(t[2, 3]),
                    pitch=pitch, roll=q[4])

    # ------------------------------------------------------------ IK
    def ik(self, pose, elbow=+1, q_seed=None, q6=0.0, check_limits=True):
        """Analytic IK for a target Pose (x, y, z, pitch, roll).

        elbow = +1 picks the branch with the larger q3, -1 the other;
        q_seed (optional) picks whichever of the two branches is closer.
        Returns IKSolution with joint angles J1..J6 (J6 = q6).
        Raises IKError if unreachable or all branches violate limits.
        """
        r = math.hypot(pose.x, pose.y)
        q1_fwd = math.atan2(pose.y, pose.x) if r > 1e-9 else (
            q_seed[0] if q_seed else 0.0)

        # Two yaw hypotheses: the tip normally lies at +r in the arm
        # plane (q1 toward the tip), but with the shoulder able to pitch
        # to +70 deg the wrist can fold *behind* the J2 axis, putting the
        # tip at -r in the arm plane (q1 off by pi).  Try both; limits +
        # guard filter the results.
        sols = []
        zw = (pose.z - self.base_z) - self.l3 * math.sin(pose.pitch)
        for q1, sgn in ((q1_fwd, +1.0),
                        (self._norm(q1_fwd + math.pi), -1.0)):
            # wrist (J4 axis) in the arm plane: tip projected back by L3
            rw = sgn * r - self.l3 * math.cos(pose.pitch)

            d2 = rw * rw + zw * zw
            cos_q3 = (d2 - self.l1 ** 2 - self.l2 ** 2) / \
                (2 * self.l1 * self.l2)
            if cos_q3 > 1.000001 or cos_q3 < -1.000001:
                continue
            cos_q3 = max(-1.0, min(1.0, cos_q3))
            ang = math.acos(cos_q3)

            for q3rel in (ang, -ang):
                q2 = math.atan2(zw, rw) - math.atan2(
                    self.l2 * math.sin(q3rel),
                    self.l1 + self.l2 * math.cos(q3rel))
                q4 = pose.pitch - q2 - q3rel
                # normalise into [-pi, pi]
                sols.append([self._norm(q1), self._norm(q2),
                             self._norm(q3rel), self._norm(q4),
                             self._norm(pose.roll), q6])
        if not sols:
            raise IKError(
                f"unreachable: wrist past L1+L2="
                f"{(self.l1+self.l2)*1000:.0f} mm or inside elbow")

        def ok(c):
            if not check_limits:
                return True
            return (all(self.jmin[i] - 1e-6 <= c[i] <= self.jmax[i] + 1e-6
                        for i in range(6))
                    and self.within_guard(c))

        valid = [c for c in sols if ok(c)]
        if not valid:
            raise IKError("unreachable: both elbow branches violate "
                          "joint limits or geometry")
        if q_seed is not None:
            pick = min(valid, key=lambda c: sum(
                (c[i] - q_seed[i]) ** 2 for i in range(5)))
            return IKSolution(q=pick,
                              branch=+1 if pick is sols[0] else -1)
        pick = valid[0] if elbow >= 0 else valid[-1]
        return IKSolution(q=pick, branch=+1 if pick is sols[0] else -1)

    @staticmethod
    def _norm(a):
        while a > math.pi:
            a -= 2 * math.pi
        while a < -math.pi:
            a += 2 * math.pi
        return a

    # --------------------------------------------------------- helpers
    def guard_q3_min(self, q2):
        """Table/case guard: minimum legal q3 for a given q2 (rad)."""
        return config.guard_q3_min(q2)

    def within_guard(self, q):
        """True while (q2, q3) keeps the wrist above the table/lid."""
        return config.within_guard(q)

    def clamp_limits(self, q):
        """Clamp into per-joint limits, then onto the guard boundary."""
        c = [max(self.jmin[i], min(self.jmax[i], q[i])) for i in range(6)]
        return config.guard_clamp(c)

    def within_limits(self, q):
        return (all(self.jmin[i] <= q[i] <= self.jmax[i] for i in range(6))
                and self.within_guard(q))

    def random_reachable_q(self, rng):
        """Sample a random in-limit, guard-valid pose useful for tests."""
        while True:
            q = [rng.uniform(self.jmin[i], self.jmax[i]) for i in range(6)]
            if self.within_guard(q):
                return q

    def workspace_r_max(self):
        return self.l1 + self.l2 + self.l3
