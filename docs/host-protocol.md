# SOMA v3 host link — Orange Pi ↔ ESP32-S3 base node

Binary framed protocol on the DevKit USB-UART console, **115200 8N1**.

```
0xAA 0x55 | seq u8 | type u8 | len u8 | payload[len] | crc16 LE
```

CRC16-CCITT/FALSE (poly 0x1021, init 0xFFFF) over `seq..payload`.
Max payload 200 B. fp32 little-endian. Joint order always J1..J6;
positions in radians at the output shaft (J6 = gripper servo shaft,
±90° envelope — the jaw maps 1:1 onto it).

Command envelope (clamped by `arm_clamp_q` on `SET_JOINT_POS`, and by
the jog integrator): J1 ±170°, J2 −35..+70°, J3 ±90°, J4 ±95°,
J5 ±160°, J6 ±90° — generated from `cad/arm/arm_params.py`. On top of
the per-joint ranges the table/case guard applies: q3 ≥ −45 − 2·q2
(degrees); violating commands get q3 raised onto the boundary.

**Watchdog**: every valid frame counts as a heartbeat. If no frame
arrives for 500 ms, the base node latches ESTOP (CAN NMT-ESTOP broadcast
+ servo torque-off). Stream `SET_JOINT_POS` at 20–50 Hz or send
`HEARTBEAT` at ≥ 5 Hz.

## Host → base node

| type | name | payload |
|---|---|---|
| 0x01 | SET_JOINT_POS | 6×f32 rad — stream during trajectories |
| 0x02 | SET_JOINT_VEL | 6×f32 rad/s (jog) |
| 0x03 | SET_TORQUE | 3×f32 Nm feedforward (J1–J3) |
| 0x05 | SET_CURRENT_LIM | u8 joint(1–3) + f32 A |
| 0x06 | SET_MODE | u8 joint(0=all CAN) + u8 nmt_cmd |
| 0x07 | ESTOP | — (immediate, latched) |
| 0x08 | CLEAR_ESTOP | — |
| 0x10 | GET_STATE | — (request one STATE) |
| 0x12 | HEARTBEAT | u32 counter |
| 0x13 | PING | — → PONG |
| 0x16 | READ_PARAM | u8 bus(0=CAN SDO,1=Feetech) + u8 node + u16 addr |
| 0x18 | SET_SERVO_REG | u8 id + u8 addr + u8 len + data |

## Base node → host

| type | name | payload |
|---|---|---|
| 0x11 | STATE | 18×f32 (pos, vel, tau — 6 each) + u8 flags + u8 can_ok_mask |
| 0x14 | PONG | u32 fw_version + u8 flags |
| 0x17 | PARAM | u8 bus + u8 node + u16 addr + 4B value |
| 0x1E | EVENT | u8 code + u8 arg |
| 0x7F | NACK | u8 offending type + u8 err |

`STATE` flags: b0 estop, b1 watchdog tripped, b2 armed, b3 CAN online.
`can_ok_mask`: bits 0–2 = J1–J3 heard from within 250 ms.

EVENT codes: 0x01 estop asserted, 0x02 estop cleared, 0x03 watchdog
trip, 0x04 CAN fault, 0x05 boot.

STATE streams automatically at 25 Hz once the node is up; `GET_STATE`
forces an extra sample.
