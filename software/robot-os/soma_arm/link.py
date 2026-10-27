"""Framed serial link to the ESP32-S3 base node.

Mirror of firmware/shared/link_proto.h:
  0xAA 0x55 | seq u8 | type u8 | len u8 | payload[len] | crc16 LE
CRC16-CCITT (poly 0x1021, init 0xFFFF) over seq..payload.

Transport: a POSIX termios serial port (no pyserial dependency — the
Orange Pi runs Linux), or SimLoopback for dry-run testing.
"""

import os
import struct
import termios
from enum import IntEnum


class T(IntEnum):
    # host -> base
    SET_JOINT_POS = 0x01
    SET_JOINT_VEL = 0x02
    SET_TORQUE = 0x03
    SET_CURRENT_LIM = 0x05
    SET_MODE = 0x06
    ESTOP = 0x07
    CLEAR_ESTOP = 0x08
    GET_STATE = 0x10
    HEARTBEAT = 0x12
    PING = 0x13
    READ_PARAM = 0x16
    SET_SERVO_REG = 0x18
    # base -> host
    STATE = 0x11
    PONG = 0x14
    PARAM = 0x17
    EVENT = 0x1E
    NACK = 0x7F


SYNC = b"\xAA\x55"
MAX_PAYLOAD = 200
FLAG_ESTOP = 0x01
FLAG_WATCHDOG = 0x02
FLAG_ARMED = 0x04
FLAG_CAN_ONLINE = 0x08

EV_ESTOP_ASSERTED = 0x01
EV_ESTOP_CLEARED = 0x02
EV_WD_TRIPPED = 0x03
EV_CAN_FAULT = 0x04
EV_BOOT = 0x05


def crc16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if (crc & 0x8000) \
                else (crc << 1) & 0xFFFF
    return crc


def build_frame(seq, ftype, payload=b""):
    if len(payload) > MAX_PAYLOAD:
        raise ValueError("payload too large")
    body = bytes([seq & 0xFF, int(ftype) & 0xFF, len(payload)]) + bytes(payload)
    return SYNC + body + struct.pack("<H", crc16(body))


class FrameParser:
    """Byte-stream parser mirroring link_parser_feed() in C."""

    def __init__(self):
        self._buf = bytearray()
        self._synced = False
        self._want = 0

    def feed(self, data):
        """Feed bytes; returns list of (seq, type, payload) frames."""
        out = []
        for byte in data:
            r = self._feed1(byte)
            if r is not None:
                out.append(r)
        return out

    def _feed1(self, byte):
        if not self._synced:
            if len(self._buf) == 0:
                if byte == SYNC[0]:
                    self._buf.append(byte)
            else:
                if byte == SYNC[1]:
                    self._buf.append(byte)
                    self._synced = True
                else:
                    self._buf.clear()
                    if byte == SYNC[0]:
                        self._buf.append(byte)
            return None
        self._buf.append(byte)
        if len(self._buf) == 5:
            if self._buf[4] > MAX_PAYLOAD:
                self._buf.clear()
                self._synced = False
                return None
            self._want = 5 + self._buf[4] + 2
        if self._want and len(self._buf) >= self._want:
            frame = bytes(self._buf)
            self._buf.clear()
            self._synced = False
            self._want = 0
            (got_crc,) = struct.unpack("<H", frame[-2:])
            if crc16(frame[2:-2]) != got_crc:
                return None
            return frame[2], frame[3], frame[5:-2]
        if len(self._buf) >= 5 + MAX_PAYLOAD + 2:
            self._buf.clear()
            self._synced = False
            self._want = 0
        return None


# ------------------------------------------------------------ payloads

def p_set_joint_pos(q):
    if len(q) != 6:
        raise ValueError("need 6 joints")
    return struct.pack("<6f", *q)


def p_set_joint_vel(dq):
    if len(dq) != 6:
        raise ValueError("need 6 joints")
    return struct.pack("<6f", *dq)


def p_set_torque(tau3):
    return struct.pack("<3f", *tau3)


def p_set_current_lim(joint, amps):
    return bytes([joint & 0xFF]) + struct.pack("<f", amps)


def p_set_mode(joint, nmt_cmd):
    return bytes([joint & 0xFF, nmt_cmd & 0xFF])


def p_read_param(bus, node, addr):
    return bytes([bus & 0xFF, node & 0xFF]) + struct.pack("<H", addr)


def p_set_servo_reg(servo_id, addr, data):
    return bytes([servo_id & 0xFF, addr & 0xFF, len(data)]) + bytes(data)


def parse_state(payload):
    """-> dict(pos[6], vel[6], tau[6], flags, can_ok_mask)"""
    if len(payload) < 74:
        raise ValueError(f"STATE payload too short: {len(payload)}")
    vals = struct.unpack("<18f", payload[:72])
    return {
        "pos": list(vals[0:6]),
        "vel": list(vals[6:12]),
        "tau": list(vals[12:18]),
        "flags": payload[72],
        "can_ok_mask": payload[73],
    }


# ------------------------------------------------------------ transport

class SerialTransport:
    """Minimal POSIX termios serial transport (Linux/macOS, no deps)."""

    BAUDS = {9600: 9600, 19200: 19200, 38400: 38400, 57600: 57600,
             115200: 115200, 230400: 230400, 460800: 460800,
             500000: 500000, 921600: 921600, 1000000: 1000000}

    def __init__(self, path, baud=115200, timeout=0.05):
        self.fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        attr = termios.tcgetattr(self.fd)
        baud_const = getattr(termios, "B%d" % baud, None)
        if baud_const is None:
            os.close(self.fd)
            raise ValueError(f"unsupported baud {baud}")
        attr[4] = baud_const          # ispeed
        attr[5] = baud_const          # ospeed
        attr[2] |= termios.CLOCAL | termios.CREAD   # c_cflag
        attr[2] &= ~termios.PARENB
        attr[2] &= ~termios.CSTOPB
        attr[2] &= ~termios.CSIZE
        attr[2] |= termios.CS8
        attr[0] = 0                    # raw iflag
        attr[1] = 0                    # raw oflag
        attr[3] = 0                    # raw lflag
        attr[6][termios.VMIN] = 0
        attr[6][termios.VTIME] = int(timeout * 10)
        termios.tcsetattr(self.fd, termios.TCSANOW, attr)
        termios.tcflush(self.fd, termios.TCIOFLUSH)

    def write(self, data):
        os.write(self.fd, data)

    def read(self, n=512):
        try:
            return os.read(self.fd, n)
        except BlockingIOError:
            return b""

    def close(self):
        os.close(self.fd)


class SimTransport:
    """Loopback transport wired to a sim.SimBaseNode instance."""

    def __init__(self, base_node):
        self.node = base_node
        self._rx = bytearray()

    def write(self, data):
        self._rx.extend(self.node.write(bytes(data)))

    def read(self, n=512):
        out = bytes(self._rx[:n])
        del self._rx[:n]
        return out

    def close(self):
        pass
