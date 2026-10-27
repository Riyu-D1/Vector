"""Python mirror of firmware/shared/can_proto.h — SOMA v3 CAN protocol.

CANopen-flavoured (Berkeley Humanoid Lite Recoil-BESC style):
  11-bit ID = (function_code << 7) | node_id, payloads fp32 LE.
Kept byte-identical to the C codec; tests cross-check the compiled C
library when a host C compiler is available.
"""

import struct
from enum import IntEnum, IntFlag


class FC(IntEnum):
    NMT = 0x0
    EMCY = 0x1
    TPDO1 = 0x3
    RPDO1 = 0x4
    TPDO2 = 0x5
    RPDO2 = 0x6
    TPDO3 = 0x7
    RPDO3 = 0x8
    TSDO = 0xB
    RSDO = 0xC


class NMT(IntEnum):
    DISABLE = 0x00
    ENABLE = 0x01
    CALIBRATE = 0x02
    ESTOP = 0x7F


class SDO(IntEnum):
    CURRENT_LIMIT_A = 0x0001
    POLE_PAIRS = 0x0002
    GEAR_RATIO = 0x0003
    ENCODER_OFFSET = 0x0004
    CAN_NODE_ID = 0x0005
    KP = 0x0006
    KD = 0x0007
    POS_LIMIT_LO = 0x0008
    POS_LIMIT_HI = 0x0009
    TEMPERATURE_C = 0x000A
    BUS_VOLTAGE_V = 0x000B
    CALIBRATE = 0x000C
    ZERO_HERE = 0x000D
    FW_VERSION = 0x000E
    STATUS = 0x000F
    SAVE_FLASH = 0x0010
    VELOCITY_RADS = 0x0011
    IQ_MEAS_A = 0x0012


class Status(IntFlag):
    ENABLED = 0x1
    ESTOP = 0x2
    CALIBRATED = 0x4
    FAULT = 0x8


SDO_CMD_DOWNLOAD = 0x20
SDO_CMD_UPLOAD = 0x40


def can_id(fc, node):
    return ((int(fc) & 0xF) << 7) | (node & 0x7F)


def id_fc(frame_id):
    return (frame_id >> 7) & 0xF


def id_node(frame_id):
    return frame_id & 0x7F


# ------------------------------------------------------------ encoders
# Each returns (can_id, payload bytes). DLC = len(payload).

def enc_nmt(cmd, target_node):
    return 0x000, bytes([int(cmd), target_node])


def enc_rpdo1_ping(node, token=0):
    return can_id(FC.RPDO1, node), struct.pack("<I", token)


def enc_rpdo2_cmd(node, pos_rad, vel_rads):
    return can_id(FC.RPDO2, node), struct.pack("<ff", pos_rad, vel_rads)


def enc_rpdo3_torque(node, torque_nm):
    return can_id(FC.RPDO3, node), struct.pack("<f", torque_nm)


def enc_rsdo_write_f32(node, addr, value):
    return can_id(FC.RSDO, node), (
        bytes([SDO_CMD_DOWNLOAD]) + struct.pack("<H", int(addr))
        + b"\x00" + struct.pack("<f", value))


def enc_rsdo_write_u32(node, addr, value):
    return can_id(FC.RSDO, node), (
        bytes([SDO_CMD_DOWNLOAD]) + struct.pack("<H", int(addr))
        + b"\x00" + struct.pack("<I", value))


def enc_rsdo_read(node, addr):
    return can_id(FC.RSDO, node), (
        bytes([SDO_CMD_UPLOAD]) + struct.pack("<H", int(addr))
        + b"\x00" * 5)


# ------------------------------------------------------------ decoders

def dec_nmt(data):
    if len(data) < 2:
        raise ValueError("NMT needs 2 bytes")
    return data[0], data[1]


def dec_pdo2(data):
    if len(data) < 8:
        raise ValueError("PDO2 needs 8 bytes")
    return struct.unpack("<ff", data[:8])


def dec_pdo3(data):
    if len(data) < 4:
        raise ValueError("PDO3 needs 4 bytes")
    return struct.unpack("<f", data[:4])[0]


def dec_tsdo_resp(data):
    if len(data) < 4:
        raise ValueError("TSDO resp needs 4 bytes")
    return data[:4]


def dec_emcy(data):
    if len(data) < 3:
        raise ValueError("EMCY needs 3 bytes")
    return struct.unpack("<H", data[:2])[0], data[2]


def parse_feedback(frame_id, data):
    """Decode any drive->master frame into a dict."""
    fc = id_fc(frame_id)
    node = id_node(frame_id)
    if fc == FC.TPDO2:
        pos, vel = dec_pdo2(data)
        return {"node": node, "kind": "state", "pos": pos, "vel": vel}
    if fc == FC.TPDO3:
        return {"node": node, "kind": "iq", "iq": dec_pdo3(data)}
    if fc == FC.TSDO:
        return {"node": node, "kind": "sdo", "val4": dec_tsdo_resp(data)}
    if fc == FC.TPDO1:
        return {"node": node, "kind": "echo", "data": bytes(data)}
    if fc == FC.EMCY:
        code, reg = dec_emcy(data)
        return {"node": node, "kind": "emcy", "code": code, "reg": reg}
    return {"node": node, "kind": "unknown", "fc": fc, "data": bytes(data)}
