"""Gravity-torque model + payload derating tests.

Cross-checked against fea_arm3/input/parts_AB.json analytic moments:
in the AB pose (q=[0, +90deg, -90deg, 0, 0, 0], TCP horizontal reach)
the model must reproduce J2=3.286, J3=1.759, J4=0.801 Nm at 0.5 kg.
"""

import math

import pytest

from soma_arm import config
from soma_arm.gravity import gravity_torques, max_payload, torque_ok
from soma_arm.kinematics import ArmKinematics, Pose
from soma_arm.planner import TrajectoryPlanner, PlanError

# FEA "AB" full-reach pose: J2 +90, J3 -90 (over-travel past the J2
# +70 limit — kept because the FEA case is defined that way).
Q_AB = [0.0, math.pi / 2, -math.pi / 2, 0.0, 0.0, 0.0]


def test_ab_pose_matches_fea_analytic():
    """D6 wrist2 mass model at 0.5 kg payload (was parts_AB.json
    3.286/1.759/0.801 — J4 grew with the +5.6 mm TCP offset)."""
    tau = gravity_torques(Q_AB, payload_kg=0.5)
    assert tau[1] == pytest.approx(3.2486, abs=0.02)   # J2
    assert tau[2] == pytest.approx(1.7560, abs=0.02)   # J3
    assert tau[3] == pytest.approx(0.8280, abs=0.02)   # J4


def test_links_only_torque():
    tau = gravity_torques(Q_AB, payload_kg=0.0)
    # whole arm stretched out horizontally: J2 carries the arm
    assert 1.2 < tau[1] < 2.0
    assert 0.0 < tau[3] < 0.3     # wrist links alone are light


def test_j4_payload_limit_at_full_reach():
    """The required derating result: at full reach the J4 servo (0.98 Nm
    rated, 80% derate -> 0.784 Nm) caps payload below 0.5 kg. The
    overall bound is even tighter — J2 only has a 1.03x rated margin
    under its own links (FEA case A) so it caps ~0.37 kg."""
    m, limiting, bounds = max_payload(Q_AB)
    assert m < 0.5
    assert m == pytest.approx(0.380, abs=0.02)
    assert limiting == 1                       # J2 at full reach
    assert bounds[3] < 0.5                     # J4: the required check
    assert bounds[3] == pytest.approx(0.467, abs=0.02)


def test_max_payload_home_pose():
    """At the folded home pose J4 (weakest joint, 0.98 Nm rated) is the
    limiter — its bound is still below the nominal 0.5 kg payload."""
    m, limiting, bounds = max_payload([0] * 6)
    assert limiting == 3
    assert m < 0.5


def test_torque_ok_thresholds():
    ok, wi, ratio = torque_ok(Q_AB, payload_kg=0.5)
    assert not ok                    # J2 at 1.17x derated; J4 at 1.02x
    assert wi == 1
    ok2, _, _ = torque_ok(Q_AB, payload_kg=0.3)
    assert ok2


def test_planner_refuses_overloaded_move():
    """move_joints -> planner refuses a move ending at full reach with
    an over-limit payload."""
    arm_kin = ArmKinematics()
    sol = arm_kin.ik(Pose(0.2338, 0.0, 0.1992, 0.0))
    planner = TrajectoryPlanner()
    q_reach = Q_AB            # direct joint vector (over-travel pose)
    with pytest.raises(PlanError):
        planner.plan(sol.q, q_reach, payload_kg=0.6)


def test_planner_allows_light_move():
    planner = TrajectoryPlanner()
    T, pts = planner.plan([0] * 6, [0.2, -0.3, 0.4, 0, 0, 0],
                          payload_kg=0.2)
    assert T > 0 and pts[-1][0] == T


def test_gravity_torques_six_joints():
    tau = gravity_torques([0] * 6)
    assert tau.shape == (6,)
    # J1 axis is vertical — gravity can't load it
    assert abs(tau[0]) < 1e-3
