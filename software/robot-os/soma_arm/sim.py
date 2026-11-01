"""Simulated ESP32-S3 base node for dry-run testing without hardware.

Implements the host link protocol exactly (same frames, same CRC) plus a
tiny behavioural model: commanded positions are tracked with first-order
lag, J2/J3 CAN joints report simulated state, ESTOP latches, the
MOTOR_EN relay requires an explicit ARM_MOTOR command (phase 1 of the
two-phase arm — the sim's ESCs are always alive) and drops on
estop/watchdog. Use via link.SimTransport.
"""

import struct
import time

from . import link


class SimBaseNode:
    """Pure-software stand-in for firmware/base-node."""

    def __init__(self, q_home=None):
        self.q = list(q_home if q_home is not None
                      else [0.0] * 7)   # J1..J6 + GRIP
        self.q_target = list(self.q)
        self.estop = False
        self.armed = False
        self.motor_en = False       # relay K1 state; ARM_MOTOR closes it
        self.can_ok = 0x0C          # bits: CAN nodes 2,3 online
        self.fw_version = 0x000200
        self._parser = link.FrameParser()
        self._rx = bytearray()
        self._tx = bytearray()
        self._last_frame_t = time.monotonic()
        self._seq = 0
        self.events = []

    # ------------------------------------------------ transport iface
    def write(self, data):
        """Bytes from host -> sim. Returns bytes sim -> host."""
        self._rx.extend(data)
        out_len = len(self._tx)
        for (seq, ftype, payload) in self._parser.feed(data):
            self._last_frame_t = time.monotonic()
            self._handle(seq, ftype, payload)
        resp = bytes(self._tx[out_len:])
        return resp

    def read(self, n=512):
        out = bytes(self._tx[:n])
        del self._tx[:n]
        return out

    # ----------------------------------------------------------- model
    def step(self, dt):
        """Advance the joint model (call periodically)."""
        if self.estop or not self.armed:
            return
        tau = 0.08  # s, first-order lag to mimic real joints
        k = min(1.0, dt / tau)
        for i in range(7):
            self.q[i] += (self.q_target[i] - self.q[i]) * k

    def _emit(self, ftype, payload=b""):
        self._seq = (self._seq + 1) & 0xFF
        self._tx.extend(link.build_frame(self._seq, ftype, payload))

    def _state_payload(self):
        p = (struct.pack("<7f", *self.q)
             + struct.pack("<7f", *([0.0] * 7))
             + struct.pack("<7f", *([0.0] * 7)))
        flags = 0
        if self.estop:
            flags |= link.FLAG_ESTOP
        if self.armed:
            flags |= link.FLAG_ARMED
        if self.can_ok:
            flags |= link.FLAG_CAN_ONLINE
        if self.motor_en:
            flags |= link.FLAG_MOTOR_EN
        return p + bytes([flags, self.can_ok])

    def _drop_motor_en(self):
        self.motor_en = False
        self.armed = False
        self._emit(link.T.EVENT, bytes([link.EV_MOTOR_EN_OFF, 0]))

    def _handle(self, seq, ftype, p):
        if ftype == link.T.SET_JOINT_POS:
            if len(p) == 28:
                self.q_target = list(struct.unpack("<7f", p))
        elif ftype == link.T.SET_JOINT_VEL:
            if len(p) == 28:
                dq = struct.unpack("<7f", p)
                dt = 0.02
                self.q_target = [self.q_target[i] + dq[i] * dt
                                 for i in range(7)]
        elif ftype == link.T.ARM_MOTOR:
            # explicit re-arm (phase 1: closes K1 while estop is clear;
            # sim doesn't model the ESC boot window — drives are always
            # alive here)
            if not self.estop and not self.motor_en:
                self.motor_en = True
                self._emit(link.T.EVENT, bytes([link.EV_MOTOR_EN_ON, 0]))
        elif ftype == link.T.ESTOP:
            self.estop = True
            if self.motor_en:
                self._drop_motor_en()
            else:
                self.armed = False
            self._emit(link.T.EVENT, bytes([link.EV_ESTOP_ASSERTED, 0]))
        elif ftype == link.T.CLEAR_ESTOP:
            self.estop = False
            self._emit(link.T.EVENT, bytes([link.EV_ESTOP_CLEARED, 0]))
        elif ftype == link.T.SET_MODE:
            if len(p) >= 2 and p[1] == 1:
                self.armed = self.motor_en and not self.estop
            elif len(p) >= 2 and p[1] == 0:
                self.armed = False
        elif ftype == link.T.GET_STATE:
            self._emit(link.T.STATE, self._state_payload())
        elif ftype == link.T.PING:
            flags = ((0x04 if self.armed else 0x00)
                     | (0x01 if self.estop else 0x00)
                     | (0x10 if self.motor_en else 0x00))
            self._emit(link.T.PONG,
                       struct.pack("<I", self.fw_version)
                       + bytes([flags]))
        elif ftype == link.T.HEARTBEAT:
            pass                      # presence already noted
        elif ftype == link.T.READ_PARAM:
            self._emit(link.T.PARAM, bytes(p[:4]) + b"\x00" * 4)
        else:
            self._emit(link.T.NACK, bytes([int(ftype), 0x01]))
