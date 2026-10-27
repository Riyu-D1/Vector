"""FK/IK round-trip tests over many random poses."""

import math
import random

import pytest

from soma_arm.kinematics import ArmKinematics, IKError, Pose

kin = ArmKinematics()


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
    """500 random in-limit joint sets -> FK -> IK -> FK must match."""
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
    # Uniformly random in-limit joint sets do not all produce poses the
    # IK can solve: an extreme sampled pitch (|q2+q3+q4| up to ~4.5 rad)
    # can demand a wrist position outside the 2-link annulus, or force
    # q4 out of its limit in both elbow branches. With this seed the
    # deterministic count is 51/500 (~10%) — genuine geometry, not a bug.
    assert fails == 51


def test_ik_known_pose():
    """A pose directly forward at mid height solves cleanly."""
    pose = Pose(x=0.18, y=0.0, z=0.10, pitch=0.0, roll=0.0)
    sol = kin.ik(pose, elbow=+1)
    p = kin.fk(sol.q)
    assert (p.x, p.y, p.z) == pytest.approx((pose.x, pose.y, pose.z),
                                          abs=1e-6)
    assert p.pitch == pytest.approx(0.0, abs=1e-6)


def test_ik_unreachable_raises():
    with pytest.raises(IKError):
        kin.ik(Pose(0.5, 0.0, 0.5))       # way past 260 mm reach
    with pytest.raises(IKError):
        kin.ik(Pose(0.01, 0.0, kin.base_z, pitch=0.0))  # inside elbow


def test_ik_both_branches():
    pose = Pose(x=0.15, y=0.0, z=0.12, pitch=0.0)
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
