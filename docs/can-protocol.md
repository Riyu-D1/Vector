# SOMA CAN protocol — J2/J3 cycloidal actuators

CAN 2.0B classical, **1 Mbit/s**, 11-bit standard IDs. Only J2
(shoulder) and J3 (elbow) are CAN nodes — J1 is an STS3250 servo and
J4–J6 + gripper are STS3215 servos, all on Feetech bus A.

Layout follows the Berkeley Humanoid Lite Recoil-Motor-Controller-BESC
firmware (MIT licence) — CANopen-style:

```
CAN ID = (function_code << 7) | node_id        function: 4 bits, node: 7 bits
```

Node IDs: **J2 = 2, J3 = 3** (UNVERIFIED — kept from the old layout;
flash each ESC before install). Payloads little-endian; floats fp32.
Units are at the **output shaft** (post 40:1 cycloidal gearbox):
rad, rad/s, N·m, A, °C.

## Frame table

| Dir | CAN ID | Name | Payload | Meaning |
|---|---|---|---|---|
| M→S | `0x000` | NMT | `u8 cmd, u8 node` | mode control; node 0 = broadcast |
| S→M | `0x080+n` | EMCY | `u16 code, u8 reg` | fault/event report |
| M→S | `0x200+n` | RPDO1 | `u32 token` | presence ping — echoed back (heartbeat) |
| S→M | `0x180+n` | TPDO1 | echo | ping reply (drives the ESC-alive logic) |
| M→S | `0x300+n` | RPDO2 | `f32 pos, f32 vel` | position command + velocity FF |
| S→M | `0x280+n` | TPDO2 | `f32 pos, f32 vel` | state feedback |
| M→S | `0x400+n` | RPDO3 | `f32 iq` | q-axis current / torque ffwd |
| S→M | `0x380+n` | TPDO3 | `f32 iq` | measured q-axis current |
| M→S | `0x600+n` | RSDO | see below | parameter write/read request |
| S→M | `0x580+n` | TSDO | `u8 data[4]` | read response |

## NMT (byte0 = command, byte1 = target node, 0 = all)

| cmd | name | effect |
|---|---|---|
| `0x00` | DISABLE | torque off, coast |
| `0x01` | ENABLE | position mode — **refused until calibrated + homed** |
| `0x02` | CALIBRATE | encoder-offset calibration (rotor must be free) |
| `0x03` | HOME | drive slowly into the mechanical hard stop at a low
current, detect stall, set output zero at stop + configured offset;
required every boot (AS5600 on the motor shaft is single-turn —
the output angle is otherwise unknown) |
| `0x7F` | ESTOP | latch: immediate torque-off until explicit ENABLE |

## Safety state (base node → MOTOR_EN → drives)

`MOTOR_EN` (IO40) closes relay K1 → `+12V_MOT` (J18/J20) feeds the
ESCs (power *and* logic — the drives are dead until K1 closes, so a
heartbeat precondition could never be satisfied; that was the W1
arm deadlock). The state machine is therefore a **two-phase arm**:

- **Phase 1 (pre-arm)** — `MOTOR_EN` LOW at boot; rises only on an
  explicit host `ARM_MOTOR` command while ALL of:
  - at least one valid host frame has been received (handshake);
  - a host frame arrived inside the 500 ms watchdog window;
  - the e-stop sense (IO38, NC loop) is released and no latched estop;
  - CAN not bus-off.

  Closing K1 starts the `ESC_BOOT_WINDOW_MS` timer (1500 ms, param
  in `config.h` / `motor_en.esc_boot_window_ms`).

- **Phase 2 (boot window)** — every configured ESC must answer a CAN
  ping (its first heartbeat) inside the window. Any ESC missing at
  window expiry drops `MOTOR_EN` immediately with reason
  `ESC_BOOT_TIMEOUT`; a fresh explicit `ARM_MOTOR` retries.
  All ESCs alive → phase `ARMED`.

- **Armed** — every configured ESC heartbeat must stay inside the
  400 ms alive window. Any estop, host watchdog timeout, CAN bus-off,
  ESC fault or lost heartbeat drops `MOTOR_EN` LOW immediately and the
  base node broadcasts `NMT ESTOP` (0x7F → node 0) plus servo
  torque-off. Estop/host-timeout/bus-off/ESC-fault also drop during
  the boot window — only the *lost-heartbeat* rule waits for armed.

The drop reason rides in the `MOTOR_EN_OFF` event arg
(`docs/host-protocol.md`, medr_t: 1 estop, 2 host-timeout,
3 bus-off, 4 esc-fault, 5 esc-lost, 6 esc-boot-timeout). Re-arm
always needs a fresh explicit `ARM_MOTOR`.

The physical NC e-stop loop on **J19** sits in the relay coil path —
opening it drops K1 regardless of firmware. The IO38 sense line lets
firmware see that and send the NMT stop so the drives don't coast
powered-down but enabled.

## SDO

Request on `0x600+n` (8 bytes):

| byte | content |
|---|---|
| 0 | `0x20` = download/write, `0x40` = upload/read |
| 1–2 | parameter address, u16 LE |
| 3 | unused |
| 4–7 | value (writes only) |

Read response on `0x580+n`: 4 data bytes (no echo of the address —
the requester correlates). Writes get no response.

### Parameter addresses

| Addr | Name | Type | Access | Notes |
|---|---|---|---|---|
| 0x01 | CURRENT_LIMIT_A | f32 | rw | phase q-axis cap; 5 A default [U] |
| 0x02 | POLE_PAIRS | u32 | rw | Tarot 4008 = 7 pp [U — count magnets] |
| 0x03 | GEAR_RATIO | f32 | rw | 40.0 |
| 0x04 | ENCODER_OFFSET | f32 | ro | electrical zero from calibration |
| 0x05 | CAN_NODE_ID | u32 | rw | persist with SAVE_FLASH |
| 0x06 | KP | f32 | rw | position-loop gain |
| 0x07 | KD | f32 | rw | damping gain |
| 0x08/0x09 | POS_LIMIT_LO/HI | f32 | rw | rad, output shaft (sim ranges) |
| 0x0A | TEMPERATURE_C | f32 | ro | 0 until wired (TODO) |
| 0x0B | BUS_VOLTAGE_V | f32 | ro | VBUS divider |
| 0x0C | CALIBRATE | u32 | wo | write 1 = run calibration |
| 0x0D | ZERO_HERE | u32 | wo | write 1 = zero output position |
| 0x0E | FW_VERSION | u32 | ro | |
| 0x0F | STATUS | u32 | ro | b0 enabled, b1 estop, b2 calibrated, b3 fault, **b4 homed** |
| 0x10 | SAVE_FLASH | u32 | wo | write 0x53515645 = persist params |
| 0x11 | VELOCITY_RADS | f32 | ro | measured output velocity |
| 0x12 | IQ_MEAS_A | f32 | ro | measured q-axis current |
| 0x13 | HOME_STOP_RAD | f32 | rw | output rad assigned to the hard stop [U — measure] |
| 0x14 | HOME_CURRENT_A | f32 | rw | iq used during homing (stall detect) [U] |
| 0x15 | HOME_SPEED_RADS | f32 | rw | homing crawl speed, output rad/s [U] |

## Timing budget (1 Mbps)

100 Hz RPDO2×2 + 50 Hz (TPDO2+TPDO3)×2 + 200 ms ping round-robin ≈
410 frames/s × ~110 bit ≈ **4.5 % bus load** — plenty of headroom for
SDO traffic.
