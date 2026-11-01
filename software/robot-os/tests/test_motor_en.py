"""MOTOR_EN safety state machine — host-testable via ctypes on the
same C source that the ESP32 base node compiles
(firmware/shared/motor_en.c). Two-phase arm (W2): pre-arm closes K1
WITHOUT ESC heartbeats (the drives sit on +12V_MOT, dead until the
relay closes); phase 2 requires every configured ESC heartbeat inside
esc_boot_window_ms else MEDR_ESC_BOOT_TIMEOUT; once armed, the
estop/watchdog/bus-off/fault/lost-heartbeat drops and the explicit
re-arm rule are unchanged.
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
        ("now_ms", ctypes.c_uint32),
    ]


class MotorEn(ctypes.Structure):
    _fields_ = [
        ("motor_en", ctypes.c_uint8),
        ("fault_latched", ctypes.c_uint8),
        ("drop_reason", ctypes.c_uint8),
        ("phase", ctypes.c_uint8),
        ("boot_start_ms", ctypes.c_uint32),
        ("esc_boot_window_ms", ctypes.c_uint32),
    ]


def _setup(clib):
    clib.motor_en_step.restype = ctypes.c_uint8
    st = MotorEn()
    clib.motor_en_init(ctypes.byref(st))
    return st


def _inp(now_ms=0, **kw):
    i = MotorEnIn(0, 0, 0, 0, 0, 0, 0, now_ms)
    for k, v in kw.items():
        setattr(i, k, v)
    return i


def _pre_arm(now_ms=0, **kw):
    """Phase-1 conditions + explicit arm command — NO ESC heartbeats
    (esc_all_alive defaults to 0: the drives are dead until K1 closes)."""
    base = dict(host_seen=1, host_alive=1, estop_released=1,
                arm_cmd=1)
    base.update(kw)
    return _inp(now_ms, **base)


def _all_ok(now_ms=0, **kw):
    """Everything satisfied incl. ESC heartbeats + explicit arm."""
    base = dict(host_seen=1, host_alive=1, estop_released=1,
                esc_all_alive=1, arm_cmd=1)
    base.update(kw)
    return _inp(now_ms, **base)


def _no_arm(now_ms=0, **kw):
    """Conditions holding (no fresh arm command)."""
    base = dict(host_seen=1, host_alive=1, estop_released=1,
                esc_all_alive=1)
    base.update(kw)
    return _inp(now_ms, **base)


# medr reasons (firmware/shared/motor_en.h)
MEDR_NONE, MEDR_ESTOP, MEDR_HOST_TIMEOUT, MEDR_CAN_BUS_OFF, \
    MEDR_ESC_FAULT, MEDR_ESC_LOST, MEDR_ESC_BOOT_TIMEOUT = 0, 1, 2, 3, 4, 5, 6

# mep phases
MEP_IDLE, MEP_BOOTING, MEP_ARMED = 0, 1, 2


def _arm_and_boot(clib, st, t0=0, t_esc=800):
    """Drive the machine through pre-arm -> armed: arm at t0, first
    ESC heartbeats at t_esc (inside the default 1500 ms window)."""
    clib.motor_en_step(ctypes.byref(st), ctypes.byref(_pre_arm(t0)))
    assert st.motor_en == 1 and st.phase == MEP_BOOTING
    for t in range(t0 + 100, t_esc, 100):
        clib.motor_en_step(
            ctypes.byref(st), ctypes.byref(_no_arm(t, esc_all_alive=0)))
    dropped = clib.motor_en_step(
        ctypes.byref(st), ctypes.byref(_no_arm(t_esc)))
    assert dropped == 0
    assert st.motor_en == 1 and st.phase == MEP_ARMED
    return t_esc


def test_boot_low(clib):
    st = _setup(clib)
    assert st.motor_en == 0
    assert st.phase == MEP_IDLE
    assert st.esc_boot_window_ms == 1500      # param default
    # even a long run with an arm command but no host -> stays low
    for t in range(10):
        clib.motor_en_step(ctypes.byref(st),
                           ctypes.byref(_inp(t, arm_cmd=1)))
    assert st.motor_en == 0


def test_prearm_closes_relay_without_esc(clib):
    """W2 fix: ESCs sit on +12V_MOT — dead until K1 closes, so the
    heartbeat can NOT be an arm precondition. Phase-1 arm with
    esc_all_alive=0 must still close the relay."""
    st = _setup(clib)
    dropped = clib.motor_en_step(ctypes.byref(st),
                               ctypes.byref(_pre_arm(0, esc_all_alive=0)))
    assert dropped == 0
    assert st.motor_en == 1
    assert st.phase == MEP_BOOTING
    assert st.boot_start_ms == 0
    # still no heartbeats, inside the window -> stays up (not ESC_LOST)
    for t in range(100, 1500, 100):
        dropped = clib.motor_en_step(
            ctypes.byref(st),
            ctypes.byref(_no_arm(t, esc_all_alive=0)))
        assert dropped == 0
        assert st.motor_en == 1
        assert st.phase == MEP_BOOTING


def test_esc_boot_timeout_drops(clib):
    """No heartbeat inside esc_boot_window_ms -> immediate drop with
    MEDR_ESC_BOOT_TIMEOUT; recovery needs a fresh explicit ARM."""
    st = _setup(clib)
    clib.motor_en_step(ctypes.byref(st), ctypes.byref(_pre_arm(1000)))
    assert st.motor_en == 1 and st.phase == MEP_BOOTING
    # last tick inside the window is fine
    dropped = clib.motor_en_step(
        ctypes.byref(st), ctypes.byref(_no_arm(1000 + 1500, esc_all_alive=0)))
    assert dropped == 0 and st.motor_en == 1
    # one tick past the window -> ESC_BOOT_TIMEOUT (not ESC_LOST)
    dropped = clib.motor_en_step(
        ctypes.byref(st), ctypes.byref(_no_arm(1000 + 1501, esc_all_alive=0)))
    assert dropped == 1
    assert st.motor_en == 0
    assert st.phase == MEP_IDLE
    assert st.drop_reason == MEDR_ESC_BOOT_TIMEOUT
    assert st.fault_latched == 1
    # heartbeats appearing now do NOT re-close the rail on their own
    for t in range(2600, 3000, 100):
        clib.motor_en_step(ctypes.byref(st), ctypes.byref(_no_arm(t)))
    assert st.motor_en == 0
    # fresh explicit arm -> back to BOOTING, fault cleared
    clib.motor_en_step(ctypes.byref(st), ctypes.byref(_pre_arm(3000)))
    assert st.motor_en == 1
    assert st.phase == MEP_BOOTING
    assert st.fault_latched == 0
    assert st.drop_reason == MEDR_NONE


def test_heartbeat_inside_window_arms(clib):
    """ESCs boot and heartbeat inside the window -> phase ARMED; the
    relay stays closed."""
    st = _setup(clib)
    clib.motor_en_step(ctypes.byref(st), ctypes.byref(_pre_arm(0)))
    assert st.motor_en == 1 and st.phase == MEP_BOOTING
    # heartbeats appear partway through the window
    dropped = clib.motor_en_step(
        ctypes.byref(st), ctypes.byref(_no_arm(800)))
    assert dropped == 0
    assert st.motor_en == 1
    assert st.phase == MEP_ARMED
    # stays on while conditions hold, without re-arm commands
    for t in range(900, 3000, 100):
        clib.motor_en_step(ctypes.byref(st), ctypes.byref(_no_arm(t)))
    assert st.motor_en == 1
    # well past the boot window now — a heartbeat loss is ESC_LOST
    dropped = clib.motor_en_step(
        ctypes.byref(st), ctypes.byref(_no_arm(3100, esc_all_alive=0)))
    assert dropped == 1
    assert st.drop_reason == MEDR_ESC_LOST
    assert st.phase == MEP_IDLE


def test_heartbeat_loss_after_armed_drops(clib):
    st = _setup(clib)
    t = _arm_and_boot(clib, st)
    dropped = clib.motor_en_step(
        ctypes.byref(st),
        ctypes.byref(_no_arm(t + 100, esc_all_alive=0)))
    assert dropped == 1
    assert st.motor_en == 0
    assert st.drop_reason == MEDR_ESC_LOST


def test_estop_during_window_drops(clib):
    """E-stop while still BOOTING drops the rail at once — we never
    wait for the window on a real safety input."""
    st = _setup(clib)
    clib.motor_en_step(ctypes.byref(st), ctypes.byref(_pre_arm(0)))
    assert st.motor_en == 1 and st.phase == MEP_BOOTING
    dropped = clib.motor_en_step(
        ctypes.byref(st),
        ctypes.byref(_no_arm(500, estop_released=0, esc_all_alive=0)))
    assert dropped == 1
    assert st.motor_en == 0
    assert st.drop_reason == MEDR_ESTOP


def test_boot_window_param(clib):
    """esc_boot_window_ms is a real param: shrink it and the timeout
    fires earlier."""
    st = _setup(clib)
    st.esc_boot_window_ms = 300
    clib.motor_en_step(ctypes.byref(st), ctypes.byref(_pre_arm(0)))
    dropped = clib.motor_en_step(
        ctypes.byref(st), ctypes.byref(_no_arm(301, esc_all_alive=0)))
    assert dropped == 1
    assert st.drop_reason == MEDR_ESC_BOOT_TIMEOUT


def test_arm_requires_host_and_estop(clib):
    st = _setup(clib)
    # missing host handshake -> arm refused
    clib.motor_en_step(ctypes.byref(st),
                       ctypes.byref(_pre_arm(0, host_seen=0)))
    assert st.motor_en == 0
    # host link dead -> refused
    clib.motor_en_step(ctypes.byref(st),
                       ctypes.byref(_pre_arm(0, host_alive=0)))
    assert st.motor_en == 0
    # estop held -> refused
    clib.motor_en_step(ctypes.byref(st),
                       ctypes.byref(_pre_arm(0, estop_released=0)))
    assert st.motor_en == 0
    # bus-off -> refused
    clib.motor_en_step(ctypes.byref(st),
                       ctypes.byref(_pre_arm(0, can_bus_off=1)))
    assert st.motor_en == 0
    # now pre-arm conditions good -> rises without heartbeats
    dropped = clib.motor_en_step(ctypes.byref(st),
                               ctypes.byref(_pre_arm(0)))
    assert dropped == 0
    assert st.motor_en == 1
    assert st.drop_reason == MEDR_NONE


def test_estop_drops(clib):
    st = _setup(clib)
    t = _arm_and_boot(clib, st)
    dropped = clib.motor_en_step(
        ctypes.byref(st), ctypes.byref(_no_arm(t + 1, estop_released=0)))
    assert dropped == 1 and st.motor_en == 0
    assert st.drop_reason == MEDR_ESTOP


def test_watchdog_drops(clib):
    """host_alive=0 (500 ms timeout) drops the relay."""
    st = _setup(clib)
    t = _arm_and_boot(clib, st)
    dropped = clib.motor_en_step(
        ctypes.byref(st), ctypes.byref(_no_arm(t + 1, host_alive=0)))
    assert dropped == 1 and st.motor_en == 0
    assert st.drop_reason == MEDR_HOST_TIMEOUT


def test_esc_fault_drops(clib):
    st = _setup(clib)
    t = _arm_and_boot(clib, st)
    dropped = clib.motor_en_step(
        ctypes.byref(st), ctypes.byref(_no_arm(t + 1, esc_fault=1)))
    assert dropped == 1 and st.drop_reason == MEDR_ESC_FAULT


def test_bus_off_drops(clib):
    st = _setup(clib)
    t = _arm_and_boot(clib, st)
    dropped = clib.motor_en_step(
        ctypes.byref(st),
        ctypes.byref(_no_arm(t + 1, esc_all_alive=0, can_bus_off=1)))
    assert dropped == 1 and st.drop_reason == MEDR_CAN_BUS_OFF


def test_rearm_requires_command(clib):
    """After a drop, restoring conditions does NOT re-enable; a fresh
    explicit arm_cmd is required (and re-runs the boot window)."""
    st = _setup(clib)
    t = _arm_and_boot(clib, st)
    # estop drop
    clib.motor_en_step(
        ctypes.byref(st), ctypes.byref(_no_arm(t + 1, estop_released=0)))
    assert st.motor_en == 0
    # conditions recover but no arm command -> stays off
    for i in range(5):
        dropped = clib.motor_en_step(
            ctypes.byref(st), ctypes.byref(_no_arm(t + 100 + i)))
        assert dropped == 0
        assert st.motor_en == 0
    # explicit re-arm -> rises again into BOOTING, fault cleared
    clib.motor_en_step(ctypes.byref(st),
                       ctypes.byref(_pre_arm(t + 200)))
    assert st.motor_en == 1
    assert st.phase == MEP_BOOTING
    assert st.fault_latched == 0


def test_arm_cmd_ignored_while_estopped(clib):
    st = _setup(clib)
    clib.motor_en_step(ctypes.byref(st),
                       ctypes.byref(_pre_arm(0, estop_released=0)))
    assert st.motor_en == 0
