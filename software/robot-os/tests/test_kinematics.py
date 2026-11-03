"""FK/IK round-trip tests over many random poses."""

import math
import random

import pytest

from soma_arm.kinematics import ArmKinematics, IKError, Pose

kin = ArmKinematics()


def test_fk_zero_pose():
    """q=0 -> the folded "L" pose: TCP (0.2338, 0, 0.1992) m, pitch 0."""
    p = kin.fk([0] * 6)
    assert p.x == pytest.approx(0.2338, abs=1e-9)
    assert p.y == pytest.approx(0.0, abs=1e-9)
    assert p.z == pytest.approx(0.1992, abs=1e-9)
    assert p.pitch == pytest.approx(0.0)
    assert p.roll == pytest.approx(0.0)


def test_fk_shoulder_down():
    """q2=+90deg tips everything past the shoulder down (tip-down conv)."""
    p = kin.fk([0, math.pi / 2, 0, 0, 0, 0])
    # J2 at (-20,143.5)mm; arm folds forward then the wrist hangs down:
    # TCP ~ (35.7, -110.3) mm in the (x,z) plane
    assert p.x == pytest.approx(0.0357, abs=2e-3)
    assert p.z == pytest.approx(-0.1103, abs=2e-3)
    assert p.pitch == pytest.approx(-math.pi / 2, abs=1e-9)


def test_yaw_rotation():
    """yaw 90deg swings the folded pose onto +Y."""
    p = kin.fk([math.pi / 2, 0, 0, 0, 0, 0])
    assert p.y == pytest.approx(0.2338, abs=1e-9)
    assert p.x == pytest.approx(0.0, abs=1e-9)
    assert p.z == pytest.approx(0.1992, abs=1e-9)


def test_ik_fk_roundtrip_random():
    """500 random in-limit joint sets -> FK -> IK -> FK must match.

    The closed-form IK solves the J1+J2/J3/J4 planar chain with the J5
    wrist yaw fixed at 0 (J5 is not pose-observable in (x,y,z,pitch)),
    so samples are drawn with q[4]=0 — the IK's working set."""
    rng = random.Random(20261027)
    fails = 0
    for _ in range(500):
        q = kin.random_reachable_q(rng)
        q[4] = 0.0
        pose = kin.fk(q)
        try:
            sol = kin.ik(pose, q_seed=q)
        except IKError:
            fails += 1
            continue
        p2 = kin.fk(sol.q)
        assert p2.x == pytest.approx(pose.x, abs=1e-4)
        assert p2.y == pytest.approx(pose.y, abs=1e-4)
        assert p2.z == pytest.approx(pose.z, abs=1e-4)
        # pitch is defined mod 2*pi (sum of three pitch joints)
        dpitch = (p2.pitch - pose.pitch + math.pi) % (2 * math.pi) - math.pi
        assert dpitch == pytest.approx(0.0, abs=1e-4)
    assert fails == 0


def test_ik_known_pose():
    """A mid-workspace pose solves cleanly."""
    pose = Pose(x=0.17288817636892745, y=0.0, z=0.19484759331746138,
                pitch=0.0, roll=0.0)
    sol = kin.ik(pose, elbow=+1)
    p = kin.fk(sol.q)
    assert (p.x, p.y, p.z) == pytest.approx((pose.x, pose.y, pose.z),
                                          abs=1e-6)
    assert p.pitch == pytest.approx(0.0, abs=1e-6)


def test_ik_home_pose():
    """The home TCP (0.2338,0,0.1992) solves to (near) q=0."""
    sol = kin.ik(Pose(0.2338, 0.0, 0.1992, pitch=0.0))
    assert sol.q[1] == pytest.approx(0.0, abs=1e-2)
    assert sol.q[2] == pytest.approx(0.0, abs=1e-2)
    assert sol.q[3] == pytest.approx(0.0, abs=1e-2)


def test_ik_unreachable_raises():
    with pytest.raises(IKError):
        kin.ik(Pose(0.5, 0.0, 0.5))       # way past ~0.37 m reach
    with pytest.raises(IKError):
        # J4 anchor lands on top of the J2 axis -> inside the dead zone
        kin.ik(Pose(0.1118, 0.0, 0.1435, pitch=0.0))


def test_ik_both_branches():
    """Near the outer/top of the workspace both elbow branches are
    within limits and produce different J3 values."""
    pose = Pose(x=0.29, y=0.0, z=0.34, pitch=0.2)
    sol_up = kin.ik(pose, elbow=+1)
    sol_dn = kin.ik(pose, elbow=-1)
    assert sol_up.q[2] != pytest.approx(sol_dn.q[2])
    for s in (sol_up, sol_dn):
        p = kin.fk(s.q)
        assert (p.x, p.y, p.z) == pytest.approx(
            (pose.x, pose.y, pose.z), abs=1e-6)


def test_ik_mirror_yaw():
    """TCP close to the J1 axis with the tool pointing back across it:
    the mirror yaw candidate must rescue the solve."""
    q = [-2.18, 0.586, -2.443, -0.763, 0.0, -2.98]
    pose = kin.fk(q)
    sol = kin.ik(pose, q_seed=q)
    p2 = kin.fk(sol.q)
    assert (p2.x, p2.y, p2.z) == pytest.approx(
        (pose.x, pose.y, pose.z), abs=1e-4)


def test_limits_enforced():
    q = kin.clamp_limits([9, -9, 9, -9, 9, -9])
    assert kin.within_limits(q)
    assert not kin.within_limits([9] * 6)
