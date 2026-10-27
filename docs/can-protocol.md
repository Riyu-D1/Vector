# SOMA v3 CAN protocol — J1–J3 cycloidal joints

CAN 2.0B classical, **1 Mbit/s**, 11-bit standard IDs.

Layout follows the Berkeley Humanoid Lite Recoil-Motor-Controller-BESC
firmware (MIT licence) — CANopen-style:

```
CAN ID = (function_code << 7) | node_id        function: 4 bits, node: 7 bits
```

Node IDs: J1 = 1, J2 = 2, J3 = 3. Payloads little-endian; all floats fp32.
Units are at the **output shaft** (post 15:1 gearbox): rad, rad/s, N·m, A, °C.

Joint limits come from `cad/arm/arm_params.py` via the generated
`firmware/shared/arm_params_gen.h` — the same numbers the host uses.
The base node pushes them to each driver as `POS_LIMIT_LO/HI` at boot;
drivers also clamp RPDO2 targets to their stored limits. Defaults
(host frame, output shaft): J1 ±170°, J2 −35..+70°, J3 ±90°. The
table/case guard (J3 ≤ 45 − 2·J2 in the CAD frame, i.e. q3 ≥ −45 − 2·q2
host-side) is enforced one level up in the base node, not in the
drivers — see `firmware/base-node/src/main.cpp` `arm_clamp_q`.

## Frame table

| Dir | CAN ID | Name | Payload | Meaning |
|---|---|---|---|---|
| M→S | `0x000` | NMT | `u8 cmd, u8 node` | mode control; node 0 = broadcast |
| S→M | `0x080+n` | EMCY | `u16 code, u8 reg` | fault/event report |
| M→S | `0x200+n` | RPDO1 | any ≤8B | presence ping — echoed back |
| S→M | `0x180+n` | TPDO1 | echo | ping reply |
| M→S | `0x300+n` | RPDO2 | `f32 pos, f32 vel` | position command + velocity FF |
| S→M | `0x280+n` | TPDO2 | `f32 pos, f32 vel` | state feedback (50 Hz) |
| M→S | `0x400+n` | RPDO3 | `f32 tau` | torque cmd/ffwd (torque mode) |
| S→M | `0x380+n` | TPDO3 | `f32 iq` | measured q-axis current (50 Hz) |
| M→S | `0x600+n` | RSDO | see below | parameter write/read request |
| S→M | `0x580+n` | TSDO | `u8 data[4]` | read response |

## NMT (byte0 = command, byte1 = target node, 0 = all)

| cmd | name | effect |
|---|---|---|
| `0x00` | DISABLE | torque off, coast |
| `0x01` | ENABLE | clear estop, enter position mode |
| `0x02` | CALIBRATE | run encoder-offset calibration (rotor must be free) |
| `0x7F` | ESTOP | latch: immediate torque-off until explicit ENABLE |

The base node's J9 pin estop and host-link watchdog both issue
`NMT ESTOP` to node 0.

## SDO

Request on `0x600+n` (8 bytes):

| byte | content |
|---|---|
| 0 | `0x20` = download/write, `0x40` = upload/read |
| 1–2 | parameter address, u16 LE |
| 3 | unused |
| 4–7 | value (writes only) |

Read response on `0x580+n`: 4 data bytes (no echo of the address — the
requester correlates). Writes get no response.

### Parameter addresses

| Addr | Name | Type | Access | Notes |
|---|---|---|---|---|
| 0x01 | CURRENT_LIMIT_A | f32 | rw | phase q-axis cap (J1 3 A, J2/J3 5 A) |
| 0x02 | POLE_PAIRS | u32 | ro | 5010 = 7 pp (UNVERIFIED — count magnets) |
| 0x03 | GEAR_RATIO | f32 | rw | 15.0 |
| 0x04 | ENCODER_OFFSET | f32 | ro | electrical zero from calibration |
| 0x05 | CAN_NODE_ID | u32 | rw | persist with SAVE_FLASH |
| 0x06 | KP | f32 | rw | angle P gain |
| 0x07 | KD | f32 | rw | damping gain |
| 0x08/0x09 | POS_LIMIT_LO/HI | f32 | rw | rad, output shaft |
| 0x0A | TEMPERATURE_C | f32 | ro | 0 until wired (TODO) |
| 0x0B | BUS_VOLTAGE_V | f32 | ro | VBUS divider, gain 10.4 |
| 0x0C | CALIBRATE | u32 | wo | write 1 = run calibration |
| 0x0D | ZERO_HERE | u32 | wo | write 1 = zero output position |
| 0x0E | FW_VERSION | u32 | ro | |
| 0x0F | STATUS | u32 | ro | b0 armed, b1 estop, b2 calibrated, b3 fault |
| 0x10 | SAVE_FLASH | u32 | wo | write 0x53515645 = persist params |
| 0x11 | VELOCITY_RADS | f32 | ro | measured output velocity |
| 0x12 | IQ_MEAS_A | f32 | ro | measured q-axis current |

## Timing budget (1 Mbps)

100 Hz RPDO2×3 + 50 Hz (TPDO2+TPDO3)×3 ≈ 600 frames/s × ~110 bit ≈
**6.6 % bus load** — plenty of headroom for SDO traffic.
