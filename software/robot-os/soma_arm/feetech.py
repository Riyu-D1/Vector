"""Python mirror of firmware/shared/feetech_proto.h.

Feetech STS/SCS packet codec for J4-J6 STS3215 servos.
Packet: 0xFF 0xFF | id | len | inst | params... | checksum
  len   = params + 2 ;  cksum = ~(id + len + inst + params) & 0xFF
Response has the same shape with an error byte in the inst slot.
"""

from enum import IntEnum


class Inst(IntEnum):
    PING = 0x01
    READ = 0x02
    WRITE = 0x03
    REG_WRITE = 0x04
    ACTION = 0x05
    RESET = 0x06
    SYNC_READ = 0x82
    SYNC_WRITE = 0x83


class Reg(IntEnum):
    ID = 5
    MODE = 33
    TORQUE_EN = 40
    ACC = 41
    GOAL_POS = 42
    GOAL_SPEED = 46
    TORQUE_LIMIT = 48
    LOCK = 55
    PRESENT_POS = 56
    PRESENT_SPEED = 58
    PRESENT_LOAD = 60
    PRESENT_VOLT = 62
    PRESENT_TEMP = 63
    MOVING = 66
    PRESENT_CUR = 69


ID_BROADCAST = 0xFE


def checksum(servo_id, length, inst, params=b""):
    return (~((servo_id + length + inst + sum(params)) & 0xFFFF)) & 0xFF


def build(servo_id, inst, params=b""):
    length = len(params) + 2
    pkt = bytes([0xFF, 0xFF, servo_id & 0xFF, length, int(inst)]) + bytes(params)
    return pkt + bytes([checksum(servo_id & 0xFF, length, int(inst), params)])


def build_ping(servo_id):
    return build(servo_id, Inst.PING)


def build_read(servo_id, addr, nbytes):
    return build(servo_id, Inst.READ, bytes([addr, nbytes]))


def build_write(servo_id, addr, data):
    return build(servo_id, Inst.WRITE, bytes([addr]) + bytes(data))


def build_write_u8(servo_id, addr, value):
    return build_write(servo_id, addr, bytes([value & 0xFF]))


def build_write_u16(servo_id, addr, value):
    return build_write(servo_id, addr,
                       bytes([value & 0xFF, (value >> 8) & 0xFF]))


def build_goal(servo_id, pos_counts, speed_counts=0):
    """One WRITE covering 42-47: pos, run-time(0), speed."""
    d = bytes([pos_counts & 0xFF, (pos_counts >> 8) & 0xFF, 0, 0,
               speed_counts & 0xFF, (speed_counts >> 8) & 0xFF])
    return build_write(servo_id, Reg.GOAL_POS, d)


def rad_to_counts(rad):
    c = int(round(2048 + rad * (4096.0 / 6.283185307179586)))
    return max(0, min(4095, c))


def counts_to_rad(counts):
    return (counts - 2048) * (6.283185307179586 / 4096.0)


class ParseError(ValueError):
    pass


def parse_response(pkt):
    """Parse a servo response packet -> dict(id, err, params)."""
    if len(pkt) < 6:
        raise ParseError("packet too short")
    if pkt[0] != 0xFF or pkt[1] != 0xFF:
        raise ParseError("bad header")
    length = pkt[3]
    if length + 4 != len(pkt):
        raise ParseError("bad length field")
    cksum = checksum(pkt[2], pkt[3], pkt[4], pkt[5:-1])
    if cksum != pkt[-1]:
        raise ParseError(f"checksum mismatch: got 0x{pkt[-1]:02X}, "
                         f"want 0x{cksum:02X}")
    return {"id": pkt[2], "err": pkt[4], "params": bytes(pkt[5:-1])}


def parse_present_pos(params):
    return params[0] | (params[1] << 8)


def parse_present_speed(params):
    raw = params[0] | (params[1] << 8)
    sign = -1 if (raw & 0x8000) else 1
    return sign * (raw & 0x7FFF)


def parse_present_load(params):
    raw = params[0] | (params[1] << 8)
    sign = -1 if (raw & 0x0400) else 1
    return sign * (raw & 0x03FF)
