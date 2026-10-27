"""Feetech STS packet codec tests — checksums, known vectors, loopback,
and a byte-exact cross-check against the compiled C codec.
"""

import ctypes
import os
import random
import shutil
import subprocess

import pytest

from soma_arm import feetech as ft
from conftest import SHARED_C_DIR


def test_checksum_known_vectors():
    """Hand-verified packets (Feetech protocol reference)."""
    # PING id 1 -> FF FF 01 02 01 FB
    assert ft.build_ping(1) == bytes.fromhex("FFFF0102 01FB".replace(" ", ""))
    # WRITE id 4 addr 42 data [0x00,0x08] -> FF FF 04 05 03 2A 00 08 C1
    pkt = ft.build_write_u16(4, 42, 2048)
    assert pkt == bytes([0xFF, 0xFF, 0x04, 0x05, 0x03, 0x2A, 0x00, 0x08,
                          0xC1])
    # READ id 6 addr 56 len 2 -> FF FF 06 04 02 38 02 B9
    pkt = ft.build_read(6, 56, 2)
    assert pkt == bytes([0xFF, 0xFF, 0x06, 0x04, 0x02, 0x38, 0x02, 0xB9])


def test_goal_packet_layout():
    pkt = ft.build_goal(4, 2048, 1000)
    assert pkt[:6] == bytes([0xFF, 0xFF, 0x04, 0x09, 0x03, 42])
    d = ft.parse_response  # cannot parse cmd as response; inspect raw
    body = pkt[6:-1]
    assert body[:2] == bytes([0x00, 0x08])       # pos L,H
    assert body[4:6] == bytes([0xE8, 0x03])      # speed 1000 L,H


def test_rad_counts_conversion():
    assert ft.rad_to_counts(0.0) == 2048
    assert ft.rad_to_counts(3.14159265) == 4095   # clamps at 4095
    assert ft.counts_to_rad(2048) == pytest.approx(0.0, abs=1e-3)
    assert ft.counts_to_rad(0) == pytest.approx(-3.14159265, abs=1e-3)


def test_parse_response():
    # synthetic response: id 4, err 0, params [pos L,H]
    resp = bytes([0xFF, 0xFF, 0x04, 0x04, 0x00, 0x00, 0x08, 0xEF])
    r = ft.parse_response(resp)
    assert r["id"] == 4 and r["err"] == 0
    assert ft.parse_present_pos(r["params"]) == 0x800


def test_parse_rejects():
    with pytest.raises(ft.ParseError):
        ft.parse_response(b"\xFF\xFF\x01")
    with pytest.raises(ft.ParseError):
        ft.parse_response(bytes([0xFF, 0xFE, 1, 2, 1, 0xFB]))  # bad hdr
    # corrupt checksum
    resp = bytearray([0xFF, 0xFF, 0x04, 0x04, 0x00, 0x00, 0x08, 0xBC])
    resp[-1] ^= 0xFF
    with pytest.raises(ft.ParseError):
        ft.parse_response(bytes(resp))


def test_signed_fields():
    assert ft.parse_present_speed(bytes([0x10, 0x80])) == -16
    assert ft.parse_present_speed(bytes([0x10, 0x00])) == 16
    assert ft.parse_present_load(bytes([0x00, 0x04])) == -0
    assert ft.parse_present_load(bytes([0x64, 0x04])) == -100


# ------------------------------------------------------- C cross-check
def _build_c_lib(tmpdir):
    cc = shutil.which("cc") or shutil.which("clang") or shutil.which("gcc")
    if cc is None:
        pytest.skip("no C compiler for C-codec cross-check")
    lib = os.path.join(str(tmpdir), "libftproto.so")
    src = os.path.join(SHARED_C_DIR, "feetech_proto.c")
    subprocess.run([cc, "-shared", "-fPIC", "-O2", "-o", lib, src],
                   check=True)
    return ctypes.CDLL(lib)


@pytest.fixture(scope="session")
def ftlib(tmp_path_factory):
    td = tmp_path_factory.mktemp("ftlib")
    return _build_c_lib(td)


def test_c_matches_python_packets(ftlib):
    rng = random.Random(3)
    for _ in range(100):
        sid = rng.randrange(1, 254)
        # ping
        out = (ctypes.c_uint8 * 32)()
        n = ftlib.ft_build_ping(out, sid)
        assert bytes(out[:n]) == ft.build_ping(sid)
        # read
        addr, nb = rng.randrange(70), rng.randrange(1, 9)
        n = ftlib.ft_build_read(out, sid, addr, nb)
        assert bytes(out[:n]) == ft.build_read(sid, addr, nb)
        # write u16
        addr = rng.choice([42, 46, 48, 33])
        v = rng.randrange(0, 4096)
        n = ftlib.ft_build_write_u16(out, sid, addr, v)
        assert bytes(out[:n]) == ft.build_write_u16(sid, addr, v)
        # goal
        pos, spd = rng.randrange(4096), rng.randrange(4096)
        n = ftlib.ft_build_goal(out, sid, pos, spd)
        assert bytes(out[:n]) == ft.build_goal(sid, pos, spd)


def test_c_checksum_matches(ftlib):
    rng = random.Random(5)
    for _ in range(200):
        sid = rng.randrange(1, 254)
        nparams = rng.randrange(0, 9)
        params = bytes(rng.randrange(256) for _ in range(nparams))
        ln = nparams + 2
        inst = rng.choice([1, 2, 3, 4, 5, 0x82, 0x83])
        cck = ftlib.ft_checksum(sid, ln, inst,
                                (ctypes.c_uint8 * max(1, len(params)))(
                                    *params) if params else None)
        pck = ft.checksum(sid, ln, inst, params)
        assert cck == pck
