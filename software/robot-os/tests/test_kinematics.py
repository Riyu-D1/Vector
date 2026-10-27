"""FK/IK round-trip tests over many random poses.

Geometry + limits now come from cad/arm/arm_params.py via the generated
soma_arm/arm_geometry.py — these tests pin the real CAD numbers (J2 axis
z=146 mm, links 120/100 mm, J4->tip ~128 mm, tip reach ~348 mm, J2 host
range -35..+70 deg, table guard q3 >= -45 - 2*q2).
"""

import math
import random

import pytest

from soma_arm import config
from soma_arm.kinematics import ArmKinematics, IKError, Pose
from soma_arm.planner import PlanError, TrajectoryPlanner

kin = ArmKinematics()


def test_generated_params_match_cad():
    """The generated constants must equal the cad/arm verified numbers."""
    import soma_arm.arm_geometry as g
    assert g.BASE_Z == pytest.approx(0.146)          # J2_Z (parts.py)
    assert g.L1 == pytest.approx(0.120)
    assert g.L2 == pytest.approx(0.100)
    assert g.L3 == pytest.approx(0.1277)             # J4 -> tip (real wrist)
    assert config.JOINT_MIN[1] == pytest.approx(math.radians(-35.0))
    assert config.JOINT_MAX[1] == pytest.approx(math.radians(+70.0))
    assert config.JOINT_MIN[2] == pytest.approx(math.radians(-90.0))
    assert config.JOINT_MAX[4] == pytest.approx(math.radians(+160.0))


def test_home_pose_is_legal():
    """CAD home (all zeros) must be in limits + inside the guard."""
    assert kin.within_limits(config.HOME_Q)
    p = kin.fk(config.HOME_Q)
    assert p.x == pytest.approx(0.3477, abs=1e-3)    # ~348 mm tip reach
    assert p.z == pytest.approx(kin.base_z, abs=1e-9)


def test_fk_zero_pose():
    """q=0 -> arm horizontal along +X, full reach L1+L2+L3, z=BASE_Z."""
    p = kin.fk([0] * 6)
    assert p.x == pytest.approx(kin.l1 + kin.l2 + kin.l3, abs=1e-9)
    assert p.y == pytest.approx(0.0, abs=1e-9)
    assert p.z == pytest.approx(kin.base_z, abs=1e-9)
    assert p.pitch == pytest.approx(0.0)
    assert p.roll == pytest.approx(0.0)


def test_fk_vertical():
    """shoulder +90deg -> upper link straight up."""
    p = kin.fk([0, math.pi / 2, 0, 0, 0, 0])
    assert p.x == pytest.approx(0.0, abs=1e-9)
    assert p.z == pytest.approx(kin.base_z + kin.l1 + kin.l2 + kin.l3,
                                abs=1e-9)


def test_yaw_rotation():
    """yaw 90deg points the whole chain along +Y."""
    p = kin.fk([math.pi / 2, 0, 0, 0, 0, 0])
    assert p.y == pytest.approx(kin.l1 + kin.l2 + kin.l3, abs=1e-9)
    assert p.x == pytest.approx(0.0, abs=1e-9)


def test_ik_fk_roundtrip_random():
    """500 random in-limit guard-valid joint sets -> FK -> IK -> FK."""
    rng = random.Random(20261027)
    fails = 0
    for _ in range(500):
        q = kin.random_reachable_q(rng)
        pose = kin.fk(q)
        try:
            sol = kin.ik(pose, q_seed=q, q6=q[5])
        except IKError:
            fails += 1
            continue
        p2 = kin.fk(sol.q)
        assert p2.x == pytest.approx(pose.x, abs=1e-4)
        assert p2.y == pytest.approx(pose.y, abs=1e-4)
        assert p2.z == pytest.approx(pose.z, abs=1e-4)
        # pitch is defined mod 2*pi (sum of three pitch joints; the stored
        # joint angles are normalised, so the sum may differ by 2*pi)
        dpitch = (p2.pitch - pose.pitch + math.pi) % (2 * math.pi) - math.pi
        assert dpitch == pytest.approx(0.0, abs=1e-4)
        # the returned solution must satisfy the guard as well
        assert kin.within_limits(sol.q)
    # Uniformly random in-limit, guard-valid joint sets all produce
    # IK-solvable poses: the solver tries both yaw hypotheses (+r/-r in
    # the arm plane), so wrist-folded-behind-shoulder poses covered by
    # the widened J2 range also resolve. 0/500 failures expected.
    assert fails == 0


def test_ik_known_pose():
    """A reachable pose near full extension solves cleanly."""
    pose = Pose(x=0.33, y=0.0, z=0.11, pitch=0.0, roll=0.0)
    sol = kin.ik(pose, elbow=+1)
    p = kin.fk(sol.q)
    assert (p.x, p.y, p.z) == pytest.approx((pose.x, pose.y, pose.z),
                                          abs=1e-6)
    assert p.pitch == pytest.approx(0.0, abs=1e-6)


def test_ik_unreachable_raises():
    with pytest.raises(IKError):
        kin.ik(Pose(0.5, 0.0, 0.5))       # way past ~348 mm reach
    with pytest.raises(IKError):
        kin.ik(Pose(0.01, 0.0, kin.base_z, pitch=0.0))  # inside elbow


def test_ik_both_branches():
    pose = Pose(x=0.33, y=0.0, z=0.11, pitch=0.0)
    sol_up = kin.ik(pose, elbow=+1)
    sol_dn = kin.ik(pose, elbow=-1)
    assert sol_up.q[2] != pytest.approx(sol_dn.q[2])  # different elbows
    for s in (sol_up, sol_dn):
        p = kin.fk(s.q)
        assert (p.x, p.y, p.z) == pytest.approx(
            (pose.x, pose.y, pose.z), abs=1e-6)


def test_limits_enforced():
    q = kin.clamp_limits([9, -9, 9, -9, 9, -9])
    assert kin.within_limits(q)
    assert not kin.within_limits([9] * 6)
    # real CAD J2 range is asymmetric: host -35..+70 deg
    q = kin.clamp_limits([0, math.radians(90), 0.5, 0, 0, 0])
    assert q[1] == pytest.approx(math.radians(70.0))
    q = kin.clamp_limits([0, math.radians(-60), 0.5, 0, 0, 0])
    assert q[1] == pytest.approx(math.radians(-35.0))


def test_guard_enforced():
    """The table/case guard: q3 >= -45 - 2*q2 (host frame, deg).

    CAD equivalent: J3 <= 45 - 2*J2 (measured boundary, checks.py c7).
    """
    # q2 = -35 deg (shoulder fully down): q3 must be >= +25 deg
    q = [0, math.radians(-35), 0.0, 0, 0, 0]
    assert not kin.within_guard(q)
    c = kin.clamp_limits(q)
    assert c[2] == pytest.approx(math.radians(+25.0))
    assert kin.within_guard(c)
    assert c[1] == pytest.approx(math.radians(-35.0))  # q2 untouched
    # q2 = +15 (up): bound relaxes to q3 >= -75 deg
    assert kin.within_guard([0, math.radians(15),
                             math.radians(-75), 0, 0, 0])
    assert not kin.within_guard([0, math.radians(15),
                                 math.radians(-76), 0, 0, 0])
    # planner must refuse a violating target rather than silently clamp
    planner = TrajectoryPlanner()
    with pytest.raises(PlanError):
        planner.plan(config.HOME_Q,
                         [0, math.radians(-35), math.radians(-45),
                          0, 0, 0])
    # a boundary-respecting move plans fine
    T, pts = planner.plan(config.HOME_Q,
                          [0, math.radians(-20), math.radians(0),
                           0, 0, 0])
    assert T > 0 and kin.within_limits(pts[-1][1])
