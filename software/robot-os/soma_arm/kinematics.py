"""Forward and inverse kinematics — real v3 geometry.

Base frame at the J1 axis on the ground plane, +Z up. Chain (metres):

    T = Tz(BASE_Z) Rz(q1) T(D_J2) Ry(q2) T(U_J3) Ry(q3) T(F_J4) Ry(q4)
        T(W_J5) Rz(q5) T(W_J6) Rx(q6) T(T_TCP)

from sim/STATUS-sim.md joint axes. Pitch joints (J2..J4) rotate about
+Y with +q = tool tip DOWN, so Pose.pitch (tool elevation, +up) is
-(q2+q3+q4). J5 is wrist yaw (+Z local), J6 wrist roll (+X local):
Pose.roll = q6. At q=0 the arm is the "L" pose: TCP (0.2282, 0, 0.2162).
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
    q: list               # joint angles J1..J6
    branch: int           # elbow branch: +1/-1


def _rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0],
                     [0, 0, 0, 1]])


def _ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0],
                     [0, 0, 0, 1]])


def _rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0],
                     [0, 0, 0, 1]])


def _t(x, y, z):
    return np.array([[1, 0, 0, x], [0, 1, 0, y], [0, 0, 1, z],
                     [0, 0, 0, 1]])


class IKError(ValueError):
    pass


class ArmKinematics:
    def __init__(self, joint_min=None, joint_max=None):
        self.jmin = list(joint_min if joint_min is not None
                         else config.JOINT_MIN)
        self.jmax = list(joint_max if joint_max is not None
                         else config.JOINT_MAX)
        self.base_z = config.BASE_Z
        # link lengths used by tests + workspace helpers
        self.l1 = config.L_UPPER
        self.l2 = config.L_FORE
        self.l3 = config.L_WRIST
        self.reach_xy0 = config.D_J2[0]   # J2 radial offset (-0.02)

    # ------------------------------------------------------------ FK
    def fk_matrix(self, q):
        """Full 4x4 homogeneous TCP transform. q = 6 joint angles (rad)."""
        t = _t(0.0, 0.0, self.base_z) @ _rz(q[0])
        t = t @ _t(*config.D_J2) @ _ry(q[1])
        t = t @ _t(*config.U_J3) @ _ry(q[2])
        t = t @ _t(*config.F_J4) @ _ry(q[3])
        t = t @ _t(*config.W_J5) @ _rz(q[4])
        t = t @ _t(*config.W_J6) @ _rx(q[5])
        t = t @ _t(*config.T_TCP)
        return t

    def fk(self, q):
        """FK -> Pose. pitch = -(q2+q3+q4) (tool elevation), roll = q6."""
        t = self.fk_matrix(q)
        return Pose(x=float(t[0, 3]), y=float(t[1, 3]),
                    z=float(t[2, 3]),
                    pitch=-(q[1] + q[2] + q[3]), roll=q[5])

    def joint_positions(self, q):
        """World positions of J1..J6 axes + TCP (metres, list of np vec3)."""
        pts = []
        t = _t(0.0, 0.0, self.base_z)
        pts.append(t[:3, 3].copy())                          # J1
        t = t @ _rz(q[0])
        pts.append((t @ _t(*config.D_J2))[:3, 3])            # J2
        t = t @ _t(*config.D_J2) @ _ry(q[1])
        pts.append((t @ _t(*config.U_J3))[:3, 3])            # J3
        t = t @ _t(*config.U_J3) @ _ry(q[2])
        pts.append((t @ _t(*config.F_J4))[:3, 3])            # J4
        t = t @ _t(*config.F_J4) @ _ry(q[3])
        pts.append((t @ _t(*config.W_J5))[:3, 3])            # J5
        t = t @ _t(*config.W_J5) @ _rz(q[4])
        pts.append((t @ _t(*config.W_J6))[:3, 3])            # J6
        t = t @ _t(*config.W_J6) @ _rx(q[5])
        pts.append((t @ _t(*config.T_TCP))[:3, 3])           # TCP
        return pts

    # ------------------------------------------------------------ IK
    def ik(self, pose, elbow=+1, q_seed=None, q5=0.0,
           check_limits=True):
        """Analytic IK for a target Pose (x, y, z, pitch, roll).

        Solves J1 yaw + the J2/J3/J4 planar chain (J5 wrist yaw is not
        pose-observable -> q5 kept at the given value, J6 = pose.roll).
        elbow = +1 picks one bend sign, -1 the mirror; q_seed picks the
        branch closest to the seed. Raises IKError if unreachable or all
        branches violate limits.
        """
        r = math.hypot(pose.x, pose.y)
        q1_guess = math.atan2(pose.y, pose.x) if r > 1e-9 else (
            q_seed[0] if q_seed else 0.0)

        # tool elevation is defined mod 2pi — normalize before using it
        # to project the J4 anchor back from the TCP
        pitch = self._norm(pose.pitch)

        sols = []
        # Two yaw candidates: the TCP's own bearing, and the mirror yaw
        # 180 deg off (tool pointing back across the axis — happens when
        # the TCP sits close to J1). Try both, collect all candidates.
        for q1 in (q1_guess, self._norm(q1_guess + math.pi)):
            out = self._solve_planar(q1, pitch, pose, q5)
            if out is not None:
                sols.extend(out)

        if not sols:
            raise IKError(
                "unreachable: J4 anchor outside the 2-link annulus for "
                "both yaw candidates")

        def ok(c):
            if not check_limits:
                return True
            return all(self.jmin[i] - 1e-6 <= c[i] <= self.jmax[i] + 1e-6
                       for i in range(6))

        valid = [c for c in sols if ok(c)]
        if not valid:
            raise IKError("unreachable: all elbow/yaw branches violate "
                          "joint limits")
        if q_seed is not None:
            pick = min(valid, key=lambda c: sum(
                (c[i] - q_seed[i]) ** 2 for i in range(6)))
            return IKSolution(q=pick,
                              branch=+1 if pick is sols[0] else -1)
        pick = valid[0] if elbow >= 0 else valid[-1]
        return IKSolution(q=pick, branch=+1 if pick is sols[0] else -1)

    def _solve_planar(self, q1, pitch, pose, q5):
        """All geometric planar solutions (both bends) for one arm-plane
        yaw. Returns ([cand,...], (a4,z4,D)) or None if the J4 anchor is
        outside the annulus."""
        a_tcp = pose.x * math.cos(q1) + pose.y * math.sin(q1)
        a4 = a_tcp - self.l3 * math.cos(pitch)
        z4 = pose.z - self.l3 * math.sin(pitch)

        j2a = self.reach_xy0
        j2z = self.base_z + config.D_J2[2]
        da, dz = a4 - j2a, z4 - j2z
        d = math.hypot(da, dz)
        if d > self.l1 + self.l2 + 1e-9 or \
                d < abs(self.l1 - self.l2) - 1e-9:
            return None
        cos_beta = (self.l1**2 + self.l2**2 - d*d) / (2*self.l1*self.l2)
        cos_beta = max(-1.0, min(1.0, cos_beta))
        beta = math.acos(cos_beta)

        sols = []
        for e in (+1, -1):
            b = e * (math.pi - beta)              # bend angle at J3 axis
            psi1 = math.atan2(dz, da) - math.atan2(
                self.l2 * math.sin(b),
                self.l1 + self.l2 * math.cos(b))
            psi2 = psi1 + b                        # forearm direction
            # link1 rest dir = +90 deg, +q2 tips DOWN; forearm rest dir
            # = F_REST_ANG; tool elevation = -(q2+q3+q4)
            q2 = math.pi / 2.0 - psi1
            q3 = config.F_REST_ANG - psi2 - q2
            q4 = -pitch - q2 - q3
            sols.append([self._norm(q1), self._norm(q2),
                         self._norm(q3), self._norm(q4),
                         self._norm(q5), self._norm(pose.roll)])
        return sols

    @staticmethod
    def _norm(a):
        while a > math.pi:
            a -= 2 * math.pi
        while a < -math.pi:
            a += 2 * math.pi
        return a

    # --------------------------------------------------------- helpers
    def clamp_limits(self, q):
        return [max(self.jmin[i], min(self.jmax[i], q[i]))
                for i in range(6)]

    def within_limits(self, q):
        return all(self.jmin[i] <= q[i] <= self.jmax[i]
                   for i in range(6))

    def random_reachable_q(self, rng):
        """Sample a random in-limit joint vector (for tests)."""
        return [rng.uniform(self.jmin[i], self.jmax[i])
                for i in range(6)]

    def workspace_r_max(self):
        return self.l1 + self.l2 + self.l3


# ------------------------------------------------------------ module fns
def forward_kinematics(q):
    return ArmKinematics().fk(q)


def inverse_kinematics(pose, branch=1):
    return ArmKinematics().ik(pose, elbow=branch).q
