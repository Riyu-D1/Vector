"""D4 printed-disc torque-envelope wiring (stage F1).

The firmware caps J2/J3 output torque at 3.0 / 2.0 N·m via phase-current
limits I_cap = T_cap / (Kt * ratio * eta); the planner must refuse
waypoints whose static gravity torque exceeds the same caps.
"""
import math

import pytest

from soma_arm import config
from soma_arm.gravity import gravity_torques
from soma_arm.planner import TrajectoryPlanner, PlanError

# arm horizontal (the parts_AB.json validation pose), deg -> rad
Q_AB = [0.0, math.radians(90), math.radians(-90), 0.0, 0.0, 0.0]


def test_current_limits_match_torque_caps():
    # I = T / (Kt * 40 * 0.7): 3.0 Nm -> ~3.71 A, 2.0 Nm -> ~2.47 A
    denom = config.KT_MOTOR * config.GEAR_RATIO * config.GEAR_EFF
    assert config.CURRENT_LIMIT_A[0] == pytest.approx(3.0 / denom, abs=1e-6)
    assert config.CURRENT_LIMIT_A[1] == pytest.approx(2.0 / denom, abs=1e-6)
    assert config.CURRENT_LIMIT_A[0] == pytest.approx(3.71, abs=0.01)
    assert config.CURRENT_LIMIT_A[1] == pytest.approx(2.47, abs=0.01)
    # and the caps are never above the old 5 A firmware default
    assert all(a < 5.0 for a in config.CURRENT_LIMIT_A)


def test_joint_vel_caps_slow():
    # J2/J3 jog velocity cap matches the ESC VEL_LIMIT_OUT = 0.5 rad/s
    assert config.JOINT_VEL_MAX[1] == 0.5
    assert config.JOINT_VEL_MAX[2] == 0.5


def test_planner_refuses_waypoint_above_disc_cap():
    # 0.5 kg at the AB pose pulls 3.29 N·m at J2 — over the 3.0 cap
    tau = gravity_torques(Q_AB, 0.5)
    assert abs(tau[1]) > config.TORQUE_CAP_NM[1]
    with pytest.raises(PlanError, match="disc cap"):
        TrajectoryPlanner().check_torque(Q_AB, 0.5)


def test_planner_accepts_home_pose():
    TrajectoryPlanner().check_torque([0.0] * 6, 0.0)
