"""D10 toolchange planner tests (new file - no existing files touched).

Verifies the dock/undock waypoint sequences against forward kinematics:
approach stand-off, seated insert, J6 roll to latch, lift out, and the
mirror for return-to-rack.  All poses must keep the tool axis parallel
to world +x and respect joint limits incl. the D9 J6 sublimit.
"""

import math

import numpy as np
import pytest

from soma_arm import config, toolchange as TC
from soma_arm.kinematics import ArmKinematics, IKError, _rz, _ry, _t

kin = ArmKinematics()


def grip_frame(q):
    """J6-out frame (world, metres) - same chain as kinematics.w6."""
    t = _t(0.0, 0.0, config.BASE_Z) @ _rz(q[0])
    t = t @ _t(*config.D_J2) @ _ry(q[1])
    t = t @ _t(*config.U_J3) @ _ry(q[2])
    t = t @ _t(*config.F_J4) @ _ry(q[3])
    t = t @ _t(*config.W_J5) @ _rz(q[4])
    t = t @ _t(*config.W_J6)
    return t


def j6o(q):
    return grip_frame(q)[:3, 3] * 1000.0


def tdir(q):
    return grip_frame(q)[:3, :3] @ np.array([1.0, 0.0, 0.0])


@pytest.mark.parametrize("slot", range(TC.TC_N_SLOTS))
def test_dock_waypoints_pose(slot):
    x_seat = TC.dock_origin_x() + TC.TC_J6O
    y = TC.slot_y(slot)
    wps = dict((n, q) for n, q, v, a in TC.plan_dock(slot))
    # approach: master 12 mm behind seat, entry roll, axis parallel +x
    np.testing.assert_allclose(j6o(wps["approach"]),
                               [x_seat - TC.APPROACH_D, y, TC.TC_AXIS_Z],
                               atol=0.5)
    np.testing.assert_allclose(tdir(wps["approach"]), [1, 0, 0], atol=1e-3)
    assert math.degrees(wps["approach"][5]) == pytest.approx(TC.ENTRY_Q6)
    # insert steps stay under 8 mm apart so the socket slide stays axial
    ins = [q for n, q, v, a in TC.plan_dock(slot) if n == "insert"]
    prev = wps["approach"]
    for q in ins + [wps["seat"]]:
        assert np.linalg.norm(j6o(q) - j6o(prev)) < 8.5
        prev = q
    # seat: master face on the socket floor
    np.testing.assert_allclose(j6o(wps["seat"]),
                               [x_seat, y, TC.TC_AXIS_Z], atol=0.5)
    # lock: same pose, rolled to the latch phase
    np.testing.assert_allclose(j6o(wps["lock"]),
                               [x_seat, y, TC.TC_AXIS_Z], atol=0.5)
    assert math.degrees(wps["lock"][5]) == pytest.approx(TC.LOCK_Q6)
    # clear: straight +z, still locked
    np.testing.assert_allclose(j6o(wps["clear"]),
                               [x_seat, y, TC.TC_AXIS_Z + TC.LIFT_D],
                               atol=0.5)
    assert math.degrees(wps["clear"][5]) == pytest.approx(TC.LOCK_Q6)
    for name, q, v, a in TC.plan_dock(slot):
        assert kin.within_limits(q), name
        np.testing.assert_allclose(tdir(q), [1, 0, 0], atol=1e-3, err_msg=name)


@pytest.mark.parametrize("slot", range(TC.TC_N_SLOTS))
def test_undock_waypoints_pose(slot):
    x_seat = TC.dock_origin_x() + TC.TC_J6O
    y = TC.slot_y(slot)
    wps = dict((n, q) for n, q, v, a in TC.plan_undock(slot))
    np.testing.assert_allclose(j6o(wps["above"]),
                               [x_seat, y, TC.TC_AXIS_Z + TC.LIFT_D],
                               atol=0.5)
    np.testing.assert_allclose(j6o(wps["seat"]),
                               [x_seat, y, TC.TC_AXIS_Z], atol=0.5)
    assert math.degrees(wps["seat"][5]) == pytest.approx(TC.LOCK_Q6)
    assert math.degrees(wps["unlock"][5]) == pytest.approx(TC.ENTRY_Q6)
    np.testing.assert_allclose(j6o(wps["retreat"]),
                               [x_seat - TC.APPROACH_D, y, TC.TC_AXIS_Z],
                               atol=0.5)
    for name, q, v, a in TC.plan_undock(slot):
        assert kin.within_limits(q), name


def test_undock_is_mirror_of_dock():
    d = dict((n, q) for n, q, v, a in TC.plan_dock(2))
    u = dict((n, q) for n, q, v, a in TC.plan_undock(2))
    # underdetermined solve may pick different J5 values - compare poses
    np.testing.assert_allclose(j6o(d["clear"]), j6o(u["above"]), atol=0.5)
    np.testing.assert_allclose(d["lock"][5], u["seat"][5])
    np.testing.assert_allclose(j6o(d["approach"]), j6o(u["retreat"]),
                               atol=0.5)


def test_speed_and_torque_profile():
    for slot in range(TC.TC_N_SLOTS):
        for name, q, v, a in TC.plan_dock(slot):
            assert np.all(np.asarray(v) <= np.array([0.8, 1.0, 1.0,
                                                     1.0, 1.0, 1.0]))
            assert np.all(np.asarray(a) <= np.array([2.0, 4.0, 4.0,
                                                     4.0, 4.0, 6.0]))
        # the pure-roll moves must not drive other joints
        wps = dict((n, q) for n, q, v, a in TC.plan_dock(slot))
        np.testing.assert_allclose(wps["seat"][:5], wps["lock"][:5],
                                   atol=1e-9)


def test_verify_latch():
    ok, _ = TC.verify_latch(48.0, 47.4, load_read=22.0)
    assert ok
    ok, msg = TC.verify_latch(48.0, 43.0, load_read=22.0)
    assert not ok and "miss" in msg
    ok, msg = TC.verify_latch(48.0, 48.0, load_read=0.0)
    assert not ok and "no detent" in msg
    ok, _ = TC.verify_latch(48.0, 48.0, load_read=None)
    assert ok                                   # no load telemetry ok


def test_j6_sublim_guard():
    SUB = math.degrees(config.J6_SUBLIM_J5_NEG)
    assert TC.j6_sublim_ok(q5_deg=30, q6_deg=170)
    assert not TC.j6_sublim_ok(q5_deg=-30, q6_deg=SUB + 1)
    assert TC.j6_sublim_ok(q5_deg=-30, q6_deg=SUB - 1)
    # dock poses never need J5 < 0 -> full J6 range available
    for slot in range(TC.TC_N_SLOTS):
        for name, q, v, a in TC.plan_dock(slot):
            assert math.degrees(q[4]) > -1e-6, name
            assert TC.j6_sublim_ok(math.degrees(q[4]),
                                   math.degrees(q[5]))


def test_unreachable_slot_raises():
    with pytest.raises(IKError):
        TC.dock_q(2, standoff=0.0, lift=400.0)   # 400 mm up: no reach
