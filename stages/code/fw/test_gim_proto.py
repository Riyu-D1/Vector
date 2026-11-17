"""tests/test_gim_proto.py - GIM codec: Python vectors + C codec cross-check (ctypes)."""
import ctypes
import os
import subprocess

import pytest

from conftest import SHARED_C_DIR
from soma_arm import gim_proto as g

ENC = [
    (g.enc_position(3.14, 500), "95c3f54840f40100"),
    (g.enc_speed(30.0, 100), "940000f041640000"),
    (g.enc_current(-0.5, 20), "93000000bf140000"),
    (g.enc_cfg_write(g.CFG_CAN_ID, 2), "8300120002000000"),
    (g.enc_simple(g.START), "9100000000000000"),
]


@pytest.mark.parametrize("frame,hexs", ENC)
def test_encode(frame, hexs):
    assert frame.hex() == hexs


def test_decode_scalars():
    assert g.dec_pos(0x7FFF) == pytest.approx(-0.0001907377737, abs=1e-9)
    assert g.dec_pos(0xC000) == pytest.approx(6.250286106660564, abs=1e-9)
    assert g.dec_speed(0x7FF) == pytest.approx(-0.015873015873, abs=1e-9)
    assert g.dec_speed(0xC00) == pytest.approx(32.52380952380952, abs=1e-9)
    assert g.dec_torque(0x7FF, 3.46) == pytest.approx(-0.19010989011, abs=1e-9)
    assert g.dec_torque(0xA00, 3.46) == pytest.approx(194.86263736263732, abs=1e-6)


def test_decode_reply():
    r = g.dec_reply(bytes.fromhex("95002800C0C00A00"), 3.46)
    assert r["cmd"] == 0x95 and r["temp"] == 0x28
    assert r["pos"] == pytest.approx(6.250286, abs=1e-5)
    assert r["vel"] == pytest.approx(32.5238, abs=1e-4)
    assert r["torque"] == pytest.approx(194.8626, abs=1e-3)


@pytest.fixture(scope="module")
def clib(tmp_path_factory):
    so = tmp_path_factory.mktemp("gim") / "libgim.so"
    src = os.path.join(SHARED_C_DIR, "gim_proto.c")
    subprocess.check_call(["cc", "-shared", "-fPIC", "-O1", "-o", str(so), src])
    lib = ctypes.CDLL(str(so))
    lib.gim_enc_position.argtypes = [ctypes.c_char_p, ctypes.c_float, ctypes.c_uint32]
    lib.gim_enc_speed.argtypes = [ctypes.c_char_p, ctypes.c_float, ctypes.c_uint32]
    lib.gim_enc_current.argtypes = [ctypes.c_char_p, ctypes.c_float, ctypes.c_uint16]
    lib.gim_enc_cfg_write.argtypes = [ctypes.c_char_p, ctypes.c_uint8, ctypes.c_uint32]
    lib.gim_enc_simple.argtypes = [ctypes.c_char_p, ctypes.c_uint8]
    lib.gim_dec_reply.argtypes = [ctypes.c_char_p, ctypes.c_uint8, ctypes.c_float,
                                  ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_float),
                                  ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
                                  ctypes.POINTER(ctypes.c_uint8)]
    return lib


def _c(fn, *args):
    buf = ctypes.create_string_buffer(8)
    assert fn(buf, *args) == 8
    return buf.raw


def test_c_matches_python(clib):
    assert _c(clib.gim_enc_position, 3.14, 500).hex() == "95c3f54840f40100"
    assert _c(clib.gim_enc_speed, 30.0, 100).hex() == "940000f041640000"
    assert _c(clib.gim_enc_current, -0.5, 20).hex() == "93000000bf140000"
    assert _c(clib.gim_enc_cfg_write, 0x12, 2).hex() == "8300120002000000"
    assert _c(clib.gim_enc_simple, 0x92).hex() == "9200000000000000"


def test_c_decode(clib):
    cmd, temp = ctypes.c_uint8(), ctypes.c_uint8()
    pos, vel, tq = ctypes.c_float(), ctypes.c_float(), ctypes.c_float()
    rc = clib.gim_dec_reply(bytes.fromhex("95002800C0C00A00"), 8, 3.46, ctypes.byref(cmd),
                            ctypes.byref(pos), ctypes.byref(vel), ctypes.byref(tq), ctypes.byref(temp))
    assert rc == 0 and cmd.value == 0x95 and temp.value == 0x28
    assert pos.value == pytest.approx(6.250286, abs=1e-4)
    assert vel.value == pytest.approx(32.5238, abs=1e-3)
    assert tq.value == pytest.approx(194.8626, abs=1e-2)
