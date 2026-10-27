"""CAN protocol codec tests — Python loopback plus a byte-exact
cross-check against the compiled C codec (firmware/shared/can_proto.c).
"""

import ctypes
import os
import random
import shutil
import struct
import subprocess

import pytest

from soma_arm import can_proto as cp
from conftest import SHARED_C_DIR


# ---------------------------------------------------------- C library
def _build_c_lib(tmpdir):
    cc = shutil.which("cc") or shutil.which("clang") or shutil.which("gcc")
    if cc is None:
        pytest.skip("no C compiler for C-codec cross-check")
    lib = os.path.join(str(tmpdir), "libcanproto.so")
    src = os.path.join(SHARED_C_DIR, "can_proto.c")
    subprocess.run(
        [cc, "-shared", "-fPIC", "-O2", "-o", lib, src],
        check=True)
    return ctypes.CDLL(lib)


@pytest.fixture(scope="session")
def clib(tmp_path_factory):
    td = tmp_path_factory.mktemp("clib")
    return _build_c_lib(td)


def _c_encode(lib, fn, *args):
    """Call a C encoder that writes into out[8] and returns dlc."""
    out = (ctypes.c_uint8 * 8)()
    n = getattr(lib, fn)(out, *args)
    return bytes(out[:n])


# ------------------------------------------------------- python loopback
def test_id_make():
    assert cp.can_id(cp.FC.RPDO2, 1) == 0x301
    assert cp.can_id(cp.FC.TPDO2, 3) == 0x283
    assert cp.can_id(cp.FC.RSDO, 2) == 0x602
    assert cp.can_id(cp.FC.TSDO, 2) == 0x582
    assert cp.id_node(0x301) == 1 and cp.id_fc(0x301) == cp.FC.RPDO2


def test_nmt_roundtrip():
    fid, data = cp.enc_nmt(cp.NMT.ENABLE, 0)
    assert fid == 0x000 and data == bytes([1, 0])
    cmd, node = cp.dec_nmt(data)
    assert cmd == cp.NMT.ENABLE and node == 0


def test_estop_broadcast():
    fid, data = cp.enc_nmt(cp.NMT.ESTOP, 0)
    assert fid == 0x000
    cmd, node = cp.dec_nmt(data)
    assert cmd == 0x7F and node == 0


def test_pdo2_roundtrip():
    fid, data = cp.enc_rpdo2_cmd(2, 1.25, -0.5)
    assert fid == 0x302
    pos, vel = cp.dec_pdo2(data)
    assert pos == pytest.approx(1.25) and vel == pytest.approx(-0.5)


def test_pdo3_roundtrip():
    fid, data = cp.enc_rpdo3_torque(3, 2.5)
    assert fid == 0x403
    assert cp.dec_pdo3(data) == pytest.approx(2.5)


def test_sdo_write_read():
    fid, data = cp.enc_rsdo_write_f32(1, cp.SDO.CURRENT_LIMIT_A, 5.0)
    assert fid == 0x601
    assert data[0] == cp.SDO_CMD_DOWNLOAD
    assert struct.unpack("<H", data[1:3])[0] == cp.SDO.CURRENT_LIMIT_A
    assert struct.unpack("<f", data[4:8])[0] == pytest.approx(5.0)

    fid, data = cp.enc_rsdo_read(1, cp.SDO.STATUS)
    assert data[0] == cp.SDO_CMD_UPLOAD
    assert struct.unpack("<H", data[1:3])[0] == cp.SDO.STATUS


def test_parse_feedback():
    fid = cp.can_id(cp.FC.TPDO2, 2)
    msg = cp.parse_feedback(fid, struct.pack("<ff", 0.5, -0.25))
    assert msg["kind"] == "state" and msg["node"] == 2
    assert msg["pos"] == pytest.approx(0.5)
    fid = cp.can_id(cp.FC.EMCY, 1)
    msg = cp.parse_feedback(fid, bytes([0x01, 0x00, 0x11]))
    assert msg["kind"] == "emcy" and msg["code"] == 1 and msg["reg"] == 0x11


def test_decoders_reject_short():
    with pytest.raises(ValueError):
        cp.dec_pdo2(b"\x00" * 7)
    with pytest.raises(ValueError):
        cp.dec_nmt(b"\x00")


# ------------------------------------------------- C cross-check vectors
def test_c_matches_python_nmt(clib):
    for cmd, node in [(0, 0), (1, 3), (0x7F, 0), (2, 1)]:
        c = _c_encode(clib, "enc_nmt", cmd, node)
        _, p = cp.enc_nmt(cmd, node)
        assert c == p, f"NMT cmd={cmd} node={node}: C={c.hex()} py={p.hex()}"


def test_c_matches_python_pdo(clib):
    rng = random.Random(7)
    for _ in range(200):
        pos, vel = rng.uniform(-3.2, 3.2), rng.uniform(-10, 10)
        c = _c_encode(clib, "enc_rpdo2_cmd", ctypes.c_float(pos),
                      ctypes.c_float(vel))
        _, p = cp.enc_rpdo2_cmd(1, pos, vel)
        assert c == p
        tq = rng.uniform(-8, 8)
        c = _c_encode(clib, "enc_rpdo3_torque", ctypes.c_float(tq))
        _, p = cp.enc_rpdo3_torque(1, tq)
        assert c == p


def test_c_matches_python_sdo(clib):
    rng = random.Random(11)
    for _ in range(50):
        addr = rng.randrange(0x20)
        v = rng.uniform(-100, 100)
        c = _c_encode(clib, "enc_rsdo_write_f32", addr,
                      ctypes.c_float(v))
        _, p = cp.enc_rsdo_write_f32(1, addr, v)
        # drop the node id from python side — enc_* returns (id,payload);
        # C side encodes payload only. Compare payloads.
        assert c == p
        u = rng.randrange(2 ** 32)
        c = _c_encode(clib, "enc_rsdo_write_u32", addr, u)
        _, p = cp.enc_rsdo_write_u32(1, addr, u)
        assert c == p
        c = _c_encode(clib, "enc_rsdo_read", addr)
        _, p = cp.enc_rsdo_read(1, addr)
        assert c == p


def test_c_decoder_matches(clib):
    """C decoder must agree with python decoder on the same bytes."""
    rng = random.Random(13)
    for _ in range(100):
        pos, vel = rng.uniform(-3, 3), rng.uniform(-5, 5)
        _, data = cp.enc_rpdo2_cmd(1, pos, vel)
        buf = (ctypes.c_uint8 * 8)(*data)
        p = ctypes.c_float(); v = ctypes.c_float()
        rc = clib.dec_pdo2(buf, 8, ctypes.byref(p), ctypes.byref(v))
        assert rc == 0
        assert p.value == pytest.approx(pos) and v.value == pytest.approx(vel)
        # and a truncated frame is rejected the same way
        assert clib.dec_pdo2(buf, 7, ctypes.byref(p), ctypes.byref(v)) == -1
        with pytest.raises(ValueError):
            cp.dec_pdo2(data[:7])
