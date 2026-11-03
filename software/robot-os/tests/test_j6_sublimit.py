"""D9 J6 conditional sublimit tests.

cradlefix/STATUS-cradlefix.md residual: with J5 < 0 the gripper servo
cable plug rolls into the J5 vendor case at |J6| > ~110 deg (vendor-pair
collision no printed part can fix). config.J6_SUBLIM_J5_NEG is a
firmware-side sublimit; J6 keeps its full +-180 range when J5 >= 0.
"""

import math

import pytest

from soma_arm import config
from soma_arm.kinematics import ArmKinematics, IKError, Pose

kin = ArmKinematics()
SUB = config.J6_SUBLIM_J5_NEG


def test_sublim_value():
    assert SUB == pytest.approx(math.radians(110))


def test_full_range_when_j5_nonneg():
    for q5 in (0.0, math.radians(30), math.radians(70)):
        assert kin.within_limits([0, 0, 0, 0, q5, math.radians(170)])
        assert kin.within_limits([0, 0, 0, 0, q5, -math.pi])


def test_sublim_when_j5_neg():
    q5 = math.radians(-30)
    assert not kin.within_limits([0, 0, 0, 0, q5, math.radians(170)])
    assert not kin.within_limits([0, 0, 0, 0, q5, -math.radians(170)])
    assert kin.within_limits([0, 0, 0, 0, q5, math.radians(109.9)])
    assert kin.within_limits([0, 0, 0, 0, q5, -math.radians(109.9)])
    # boundary: J5 = 0 exactly -> full range
    assert kin.within_limits([0, 0, 0, 0, 0.0, math.radians(170)])


def test_clamp_limits_sublim():
    q = kin.clamp_limits([0, 0, 0, 0, math.radians(-30), math.radians(170)])
    assert q[5] == pytest.approx(SUB)
    q = kin.clamp_limits([0, 0, 0, 0, math.radians(-30), -math.radians(170)])
    assert q[5] == pytest.approx(-SUB)
    # J5 >= 0 -> untouched
    q = kin.clamp_limits([0, 0, 0, 0, math.radians(30), math.radians(170)])
    assert q[5] == pytest.approx(math.radians(170))


def test_ik_refuses_plug_pose():
    """roll ~150 deg requested with J5 held negative -> IKError."""
    home = kin.fk([0, 0.2, -0.3, 0.1, 0, 0])
    with pytest.raises(IKError):
        kin.ik(Pose(home.x, home.y, home.z, pitch=home.pitch,
                    roll=math.radians(150)),
               q5=math.radians(-30))
    # same pose with J5 >= 0 solves fine
    sol = kin.ik(Pose(home.x, home.y, home.z, pitch=home.pitch,
                      roll=math.radians(150)),
                 q5=math.radians(30))
    assert sol.q[5] == pytest.approx(math.radians(150), abs=1e-6)
