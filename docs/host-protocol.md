# SOMA host link — Orange Pi ↔ ESP32-S3 base node

Binary framed protocol on the DevKit USB-UART console, **115200 8N1**.

```
0xAA 0x55 | seq u8 | type u8 | len u8 | payload[len] | crc16 LE
```

CRC16-CCITT/FALSE (poly 0x1021, init 0xFFFF) over `seq..payload`.
Max payload 200 B. fp32 little-endian. Channel order is always
**J1..J6, GRIP — 7 channels** (GRIP = gripper jaw servo, rad at the
output, 0 = open — calibrate on bench). Positions in radians at the
output shaft.

**Watchdog**: every valid frame counts as a heartbeat. If no frame
arrives for 500 ms the base node drops `MOTOR_EN` (relay K1 opens,
NMT ESTOP broadcast + servo torque-off) and latches estop. Stream
`SET_JOINT_POS` at 20–50 Hz or send `HEARTBEAT` at ≥ 5 Hz.

## Host → base node

| type | name | payload |
|---|---|---|
| 0x01 | SET_JOINT_POS | 7×f32 rad — stream during trajectories |
| 0x02 | SET_JOINT_VEL | 7×f32 rad/s (jog) |
| 0x03 | SET_TORQUE | 2×f32 N·m feedforward (J2, J3 — CAN joints only) |
| 0x05 | SET_CURRENT_LIM | u8 joint(2–3) + f32 A |
| 0x06 | SET_MODE | u8 joint(0=all CAN) + u8 nmt_cmd (incl. `0x03` HOME) |
| 0x07 | ESTOP | — (immediate, latched; drops MOTOR_EN) |
| 0x08 | CLEAR_ESTOP | — (clears the latch; does NOT re-arm motors) |
| 0x10 | GET_STATE | — (request one STATE) |
| 0x12 | HEARTBEAT | u32 counter |
| 0x13 | PING | — → PONG |
| 0x16 | READ_PARAM | u8 bus(0=CAN SDO,1=Feetech) + u8 node + u16 addr |
| 0x18 | SET_SERVO_REG | u8 id + u8 addr + u8 len + data |
| 0x19 | **ARM_MOTOR** | — explicit arm, phase 1: closes relay K1 iff
host handshake seen + host alive + estop released + no CAN bus-off
(ESC heartbeats are NOT required — the drives are dead until K1
closes). Phase 2 then needs every ESC heartbeat inside the 1500 ms
boot window, else the rail drops `ESC_BOOT_TIMEOUT`. Required after
every drop. |

## Base node → host

| type | name | payload |
|---|---|---|
| 0x11 | STATE | **86 B**: 7×f32 pos + 7×f32 vel + 7×f32 tau/load + u8 flags + u8 can_ok_mask |
| 0x14 | PONG | u32 fw_version + u8 flags |
| 0x17 | PARAM | u8 bus + u8 node + u16 addr + 4B value |
| 0x1E | EVENT | u8 code + u8 arg |
| 0x7F | NACK | u8 offending type + u8 err |

`STATE` flags: b0 `ESTOP`, b1 `WATCHDOG` tripped, b2 `ARMED`,
b3 `CAN_ONLINE`, b4 `MOTOR_EN` (relay K1 closed, +12V_MOT live).
`can_ok_mask`: bit0 = J2 (CAN node 2), bit1 = J3 (node 3), heard
within 400 ms.

EVENT codes: 0x01 estop asserted, 0x02 estop cleared, 0x03 watchdog
trip, 0x04 CAN fault (arg = drop reason), 0x05 boot,
0x06 MOTOR_EN on, 0x07 MOTOR_EN off (arg = drop reason:
1 estop, 2 host-timeout, 3 bus-off, 4 esc-fault, 5 esc-lost,
6 esc-boot-timeout).

STATE streams automatically at ~25 Hz once the node is up;
`GET_STATE` forces an extra sample.

## Safety summary

1. Boot: MOTOR_EN low — no motor power.
2. Host sends `ARM_MOTOR` → relay closes iff the phase-1 conditions
   hold (host handshake+alive, estop released, no bus-off — see
   `docs/can-protocol.md` safety section). EVENT 0x06 confirms.
3. Phase 2: every ESC must heartbeat within 1500 ms of K1 closing,
   else the rail drops `ESC_BOOT_TIMEOUT` (EVENT 0x07 arg=6) and a
   fresh `ARM_MOTOR` is needed to retry.
4. `SET_MODE ... ENABLE` then arms the drives (joints must be
   calibrated + homed; the ESC refuses otherwise, and powers up
   torque-disabled by design).
5. Any estop/watchdog/bus-off/ESC-fault/lost-heartbeat (400 ms) →
   MOTOR_EN drop + NMT ESTOP broadcast + servo torque-off + EVENT 0x07.
6. Recover: fix cause → `CLEAR_ESTOP` → `ARM_MOTOR` → `SET_MODE
   ENABLE`. The relay never re-closes on its own.
