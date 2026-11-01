"""MOTOR_EN safety state machine — host-testable via ctypes on the
same C source that the ESP32 base node compiles
(firmware/shared/motor_en.c). Covers: boot low, e-stop drop, watchdog
drop, missing-ESC block, explicit re-arm requirement.
"""

import ctypes
import os
import shutil
import subprocess

import pytest

from conftest import SHARED_C_DIR


def _build_lib(tmpdir):
    cc = shutil.which("cc") or shutil.which("clang") or shutil.which("gcc")
    if cc is None:
        pytest.skip("no C compiler for motor_en cross-check")
    lib = os.path.join(str(tmpdir), "libmotoren.so")
    src = os.path.join(SHARED_C_DIR, "motor_en.c")
    subprocess.run(
        [cc, "-shared", "-fPIC", "-O2", "-o", lib, src],
        check=True)
    return ctypes.CDLL(lib)


@pytest.fixture(scope="session")
def clib(tmp_path_factory):
    td = tmp_path_factory.mktemp("clib_men")
    return _build_lib(td)


class MotorEnIn(ctypes.Structure):
    _fields_ = [
        ("host_seen", ctypes.c_uint8),
        ("host_alive", ctypes.c_uint8),
        ("estop_released", ctypes.c_uint8),
        ("esc_all_alive", ctypes.c_uint8),
        ("esc_fault", ctypes.c_uint8),
        ("can_bus_off", ctypes.c_uint8),
        ("arm_cmd", ctypes.c_uint8),
    ]


class MotorEn(ctypes.Structure):
    _fields_ = [
        ("motor_en", ctypes.c_uint8),
        ("fault_latched", ctypes.c_uint8),
        ("drop_reason", ctypes.c_uint8),
    ]


def _setup(clib):
    clib.motor_en_step.restype = ctypes.c_uint8
    st = MotorEn()
    clib.motor_en_init(ctypes.byref(st))
    return st


def _inp(**kw):
    i = MotorEnIn(0, 0, 0, 0, 0, 0, 0)
    for k, v in kw.items():
        setattr(i, k, v)
    return i


def _all_ok(**kw):
    """Every safety condition satisfied + explicit arm command."""
    base = dict(host_seen=1, host_alive=1, estop_released=1,
                esc_all_alive=1, arm_cmd=1)
    base.update(kw)
    return _inp(**base)


def _no_arm(**kw):
    """Conditions holding (no fresh arm command)."""
    base = dict(host_seen=1, host_alive=1, estop_released=1,
                esc_all_alive=1)
    base.update(kw)
    return _inp(**base)


# medr reasons (firmware/shared/motor_en.h)
MEDR_NONE, MEDR_ESTOP, MEDR_HOST_TIMEOUT, MEDR_CAN_BUS_OFF, \
    MEDR_ESC_FAULT, MEDR_ESC_LOST = 0, 1, 2, 3, 4, 5


def test_boot_low(clib):
    st = _setup(clib)
    assert st.motor_en == 0
    # even a long run with an arm command but no host -> stays low
    for _ in range(10):
        clib.motor_en_step(ctypes.byref(st),
                           ctypes.byref(_inp(arm_cmd=1)))
    assert st.motor_en == 0


def test_arm_requires_all_conditions(clib):
    st = _setup(clib)
    # missing ESC heartbeat -> arm refused
    clib.motor_en_step(ctypes.byref(st),
                       ctypes.byref(_all_ok(esc_all_alive=0)))
    assert st.motor_en == 0
    # now everything good -> rises
    dropped = clib.motor_en_step(ctypes.byref(st),
                               ctypes.byref(_all_ok()))
    assert dropped == 0
    assert st.motor_en == 1
    assert st.drop_reason == MEDR_NONE
    # stays on while conditions hold, without re-arm commands
    for _ in range(5):
        clib.motor_en_step(ctypes.byref(st), ctypes.byref(_no_arm()))
    assert st.motor_en == 1


def test_missing_esc_blocks(clib):
    st = _setup(clib)
    clib.motor_en_step(ctypes.byref(st),
                       ctypes.byref(_all_ok(esc_all_alive=0)))
    assert st.motor_en == 0
    clib.motor_en_step(ctypes.byref(st), ctypes.byref(_all_ok()))
    assert st.motor_en == 1
    dropped = clib.motor_en_step(
        ctypes.byref(st), ctypes.byref(_no_arm(esc_all_alive=0)))
    assert dropped == 1
    assert st.motor_en == 0
    assert st.drop_reason == MEDR_ESC_LOST


def test_estop_drops(clib):
    st = _setup(clib)
    clib.motor_en_step(ctypes.byref(st), ctypes.byref(_all_ok()))
    assert st.motor_en == 1
    dropped = clib.motor_en_step(
        ctypes.byref(st), ctypes.byref(_no_arm(estop_released=0)))
    assert dropped == 1 and st.motor_en == 0
    assert st.drop_reason == MEDR_ESTOP


def test_watchdog_drops(clib):
    """host_alive=0 (500 ms timeout) drops the relay."""
    st = _setup(clib)
    clib.motor_en_step(ctypes.byref(st), ctypes.byref(_all_ok()))
    assert st.motor_en == 1
    dropped = clib.motor_en_step(
        ctypes.byref(st), ctypes.byref(_no_arm(host_alive=0)))
    assert dropped == 1 and st.motor_en == 0
    assert st.drop_reason == MEDR_HOST_TIMEOUT


def test_esc_fault_drops(clib):
    st = _setup(clib)
    clib.motor_en_step(ctypes.byref(st), ctypes.byref(_all_ok()))
    dropped = clib.motor_en_step(
        ctypes.byref(st), ctypes.byref(_no_arm(esc_fault=1)))
    assert dropped == 1 and st.drop_reason == MEDR_ESC_FAULT


def test_bus_off_drops(clib):
    st = _setup(clib)
    clib.motor_en_step(ctypes.byref(st), ctypes.byref(_all_ok()))
    dropped = clib.motor_en_step(
        ctypes.byref(st),
        ctypes.byref(_no_arm(esc_all_alive=0, can_bus_off=1)))
    assert dropped == 1 and st.drop_reason == MEDR_CAN_BUS_OFF


def test_rearm_requires_command(clib):
    """After a drop, restoring conditions does NOT re-enable; a fresh
    explicit arm_cmd is required."""
    st = _setup(clib)
    clib.motor_en_step(ctypes.byref(st), ctypes.byref(_all_ok()))
    assert st.motor_en == 1
    # estop drop
    clib.motor_en_step(
        ctypes.byref(st), ctypes.byref(_no_arm(estop_released=0)))
    assert st.motor_en == 0
    # conditions recover but no arm command -> stays off
    for _ in range(5):
        dropped = clib.motor_en_step(ctypes.byref(st),
                                     ctypes.byref(_no_arm()))
        assert dropped == 0
        assert st.motor_en == 0
    # explicit re-arm -> rises again, fault cleared
    clib.motor_en_step(ctypes.byref(st), ctypes.byref(_all_ok()))
    assert st.motor_en == 1
    assert st.fault_latched == 0


def test_arm_cmd_ignored_while_estopped(clib):
    st = _setup(clib)
    clib.motor_en_step(ctypes.byref(st),
                       ctypes.byref(_all_ok(estop_released=0)))
    assert st.motor_en == 0
