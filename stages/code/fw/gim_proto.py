"""soma_arm/gim_proto.py - Steadywin GIM CAN codec (mirror of firmware/shared/gim_proto.c)."""
import struct

CFG_WRITE, START, STOP, CURRENT, SPEED, POSITION, ESTOP, CLEAR_ERR = (
    0x83, 0x91, 0x92, 0x93, 0x94, 0x95, 0x97, 0xB3)
CFG_CAN_ID = 0x12


def enc_simple(cmd):
    return bytes([cmd]) + bytes(7)


def enc_position(rad, ms):
    return bytes([POSITION]) + struct.pack("<f", rad) + int(ms).to_bytes(3, "little")


def enc_speed(rad_s, ms):
    return bytes([SPEED]) + struct.pack("<f", rad_s) + int(ms).to_bytes(3, "little")


def enc_current(amps, ms):
    return bytes([CURRENT]) + struct.pack("<f", amps) + int(ms).to_bytes(2, "little") + bytes(1)


def enc_cfg_write(param, value):
    return bytes([CFG_WRITE, 0, param, 0]) + int(value).to_bytes(4, "little")


def dec_pos(u):
    return u * 25.0 / 65535.0 - 12.5


def dec_speed(u):
    return u * 130.0 / 4095.0 - 65.0


def dec_torque(u, ktg):
    return ktg * (u * 450.0 / 4095.0 - 225.0)


def dec_reply(b, ktg):
    """-> dict(cmd, temp, pos, vel, torque)"""
    if len(b) < 8:
        raise ValueError("short frame")
    up = b[3] | (b[4] << 8)
    us = (b[5] << 4) | (b[6] >> 4)
    ut = ((b[6] & 0x0F) << 8) | b[7]
    return {"cmd": b[0], "temp": b[2], "pos": dec_pos(up), "vel": dec_speed(us),
            "torque": dec_torque(ut, ktg)}
