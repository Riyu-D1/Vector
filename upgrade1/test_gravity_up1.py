"""Tests for the D1 upgrade gravity model (upgrade1/gravity_up1.py).

New numbers asserted here were produced by running the upgraded model
itself (STS3250 at J4 + J2 balance spring k=0.45 N·m/rad engaged for
q2>0). Baseline cross-checks reuse the published worst-pose numbers
(0.391 kg J2-limited / J4 bound 0.487 kg).

Run:  cd <repo root> && python3 -m pytest upgrade1/test_gravity_up1.py -q
"""

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "software", "robot-os")
    ),
)

import gravity_up1 as gup
from soma_arm import config

Q_WORST = gup.Q_WORST   # [0, +70, -70, 0, 0, 0] deg — worst in-limit reach


def test_j4_rated_is_sts3250_real_spec():
    """STS3250 datasheet rated torque 16 kg.cm @12 V = 1.569 N·m."""
    assert gup.RATED_TORQUE_NM_UP1[3] == pytest.approx(1.569, abs=1e-3)
    # all other joints unchanged vs product config
    for i in (0, 1, 2, 4, 5):
        assert gup.RATED_TORQUE_NM_UP1[i] == config.RATED_TORQUE_NM[i]


def test_j4_servo_mass_swapped():
    """The J4 servo lump on 'fore' is now 74.5 g (was 55 g)."""
    fore = [m for b, m, _ in gup.PARTS if b == "fore"]
    assert any(m == pytest.approx(0.0745) for m in fore)
    assert not any(m == pytest.approx(0.055) for m in fore)


def test_spring_curve():
    """Zero assist for q2<=0, linear 0.55 N·m/rad above engagement."""
    assert gup.j2_spring_torque(-1.0) == 0.0
    assert gup.j2_spring_torque(0.0) == 0.0
    assert gup.j2_spring_torque(math.radians(70)) == pytest.approx(
        0.55 * math.radians(70))
    assert gup.j2_spring_torque(math.radians(70)) == pytest.approx(
        0.672, abs=0.005)


def test_worst_pose_payload_table():
    """Real output of gravity_up1.py — torques and % of rated."""
    expected = {
        0.0:  [0.000, 0.764, 0.561, 0.154, 0.000, 0.000],
        0.25: [0.000, 1.664, 1.170, 0.478, 0.000, 0.000],
        0.5:  [0.000, 2.565, 1.778, 0.801, 0.000, 0.000],
    }
    for p, want in expected.items():
        tau = gup.gravity_torques(Q_WORST, p)
        for i, w in enumerate(want):
            assert tau[i] == pytest.approx(w, abs=0.005), (p, i, tau[i])


def test_0p5kg_every_joint_within_80pct_rated():
    tau = gup.gravity_torques(Q_WORST, 0.5)
    for i in range(6):
        assert abs(tau[i]) <= 0.8 * gup.RATED_TORQUE_NM_UP1[i] + 1e-9


def test_max_payload_meets_0p5kg_target():
    m, limiting, bounds = gup.max_payload(Q_WORST)
    assert m >= 0.5
    assert m == pytest.approx(0.509, abs=0.005)
    assert limiting == 2                    # J3 is now the limiter
    assert bounds[1] == pytest.approx(0.565, abs=0.005)   # J2 headroom
    assert bounds[3] == pytest.approx(0.851, abs=0.005)   # J4 headroom


def test_baseline_still_reproducible_with_spring_off():
    """spring=False on the upgraded file leaves only the +19.5 g J4 servo
    delta; J2 bound returns to ~baseline (0.391 -> ~0.385)."""
    tau = gup.gravity_torques(Q_WORST, 0.5, spring=False)
    assert tau[1] == pytest.approx(3.238, abs=0.01)   # was 3.194 + servo


def test_spring_disabled_at_folded_poses():
    """q2<=0 poses must get no assist (spring disengaged one-way)."""
    q_fold = [0.0, math.radians(-60), math.radians(20), 0.0, 0.0, 0.0]
    on = gup.gravity_torques(q_fold, 0.3, spring=True)
    off = gup.gravity_torques(q_fold, 0.3, spring=False)
    assert on[1] == pytest.approx(off[1])


def test_utilisation_reported_vs_rated():
    """0.5 kg: J2 73.3 %, J3 79.0 %, J4 51.0 % of rated (real output)."""
    tau = gup.gravity_torques(Q_WORST, 0.5)
    util = [abs(t) / r * 100 for t, r in zip(tau, gup.RATED_TORQUE_NM_UP1)]
    assert util[1] == pytest.approx(73.3, abs=0.3)
    assert util[2] == pytest.approx(79.0, abs=0.3)
    assert util[3] == pytest.approx(51.0, abs=0.3)


def test_worst_over_q3q4_at_j2_limit_stays_derated():
    """Across all in-limit (q3,q4) at the q2=+70 limit, net J2 must stay
    under the 2.8 N·m derated allowance at 0.5 kg."""
    import numpy as np
    q2 = math.radians(70)
    worst = max(
        gup.gravity_torques([0.0, q2, q3, -(q2 + q3), 0.0, 0.0], 0.5)[1]
        for q3 in np.linspace(config.JOINT_MIN[2], config.JOINT_MAX[2], 60)
        if config.JOINT_MIN[3] <= -(q2 + q3) <= config.JOINT_MAX[3])
    assert worst == pytest.approx(2.674, abs=0.01)
    assert worst <= 0.8 * gup.RATED_TORQUE_NM_UP1[1]
