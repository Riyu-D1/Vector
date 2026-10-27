"""Host-link frame codec + simulated base node loopback tests."""

import struct

import pytest

from soma_arm import link
from soma_arm.arm import Arm
from soma_arm.sim import SimBaseNode


def test_frame_roundtrip():
    p = link.FrameParser()
    payload = struct.pack("<6f", *range(6))
    fr = link.build_frame(7, link.T.SET_JOINT_POS, payload)
    got = p.feed(fr)
    assert got == [(7, link.T.SET_JOINT_POS, payload)]


def test_frame_byte_by_byte():
    p = link.FrameParser()
    fr = link.build_frame(1, link.T.PING)
    got = []
    for b in fr:
        got += p.feed(bytes([b]))
    assert got == [(1, link.T.PING, b"")]


def test_bad_crc_dropped():
    p = link.FrameParser()
    fr = bytearray(link.build_frame(1, link.T.PING))
    fr[-1] ^= 0xFF
    assert p.feed(bytes(fr)) == []


def test_resync_after_garbage():
    p = link.FrameParser()
    fr = link.build_frame(9, link.T.PING)
    got = p.feed(b"\x00\x11\x22\xAA" + fr)     # stray AA then real frame
    assert got == [(9, link.T.PING, b"")]


def test_crc16_vector():
    # CRC16-CCITT/FALSE of "123456789" = 0x29B1
    assert link.crc16(b"123456789") == 0x29B1


# ------------------------------------------------------- sim loopback
def _sim_arm():
    node = SimBaseNode()
    return Arm(link.SimTransport(node)), node


def test_sim_ping():
    arm, _ = _sim_arm()
    r = arm.ping()
    assert r["fw"] == 0x000100


def test_sim_state():
    arm, node = _sim_arm()
    arm.enable()
    arm.stream_joints([0, 0.4, 0.6, 0, 0, 0.2])
    for _ in range(80):
        node.step(0.02)
    s = arm.sense()
    assert s["pos"][1] == pytest.approx(0.4, abs=0.05)
    assert s["flags"] & link.FLAG_ARMED


def test_sim_estop_latch():
    arm, node = _sim_arm()
    arm.enable()
    arm.estop()
    arm._pump()
    s = arm.sense()
    assert s["flags"] & link.FLAG_ESTOP
    assert not (s["flags"] & link.FLAG_ARMED)
    # commands are ignored while estopped
    arm.stream_joints([1.0] * 6)
    for _ in range(50):
        node.step(0.02)
    assert node.q[0] != pytest.approx(1.0, abs=0.1)
    arm.clear_estop()
    arm._pump()
    arm.enable()
    s = arm.sense()
    assert not (s["flags"] & link.FLAG_ESTOP)


def test_sim_move_tcp():
    from soma_arm.kinematics import Pose
    arm, node = _sim_arm()
    arm.enable()
    target = Pose(0.18, 0.0, 0.12, 0.0, 0.0)
    T = arm.move_tcp(target.x, target.y, target.z, realtime=False)
    assert T > 0
    for _ in range(80):
        node.step(0.02)
    p = arm.tcp_pose()
    # TCP tracked to within the sim's first-order lag after settle
    assert p.x == pytest.approx(target.x, abs=0.02)
    assert p.z == pytest.approx(target.z, abs=0.02)


def test_nack_on_bad_type():
    node = SimBaseNode()
    fr = link.build_frame(1, 0x66, b"\x00")
    node.write(fr)
    p = link.FrameParser()
    frames = p.feed(node.read())
    assert len(frames) == 1 and frames[0][1] == link.T.NACK
