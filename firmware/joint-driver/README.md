# joint-driver — B-G431B-ESC1 firmware for the printed cycloidal actuators

One ST B-G431B-ESC1 per joint (J1, J2, J3). 5010 motor + 15:1 printed
cycloidal + AS5600 encoder, per the Berkeley Humanoid Lite actuator
concept. SimpleFOC implementation of the Berkeley Recoil-BESC protocol
shape (MIT-licensed reference: github.com/T-K-233/Recoil-Motor-Controller-BESC).

## Hardware hookup (per actuator)

| Signal | Where | Notes |
|---|---|---|
| Motor phases U/V/W | ESC1 motor pads | any order — calibration fixes direction |
| AS5600 SCL/SDA | J8 sensor pads → PB6/PB7 | **UNVERIFIED** J8 pin order — check UM2516 before soldering; the alternative I2C1 pair PB7(SDA)/PB8(SCL) is also on J8 |
| CAN | J1 port | onboard transceiver — no extra hardware. CANH/CANL twisted pair between nodes and the ESP32's SN65HVD230 |
| 120 Ω term | PC14 = `CAN_TERM` | `CAN_TERM_LAST true` on the LAST node only |
| 12 V | J5/J6 power pads | from the fused carrier rail (6 A fuse) |

Soldering the small J1 CAN pads is fragile (Berkeley docs warn about
this too) — use thin wire, flux, and strain-relief the cable.

## Per-node configuration

Edit the top of `joint_driver.ino` before flashing each board:

| Joint | `DEVICE_CAN_ID` | `CAN_TERM_LAST` | current cap |
|---|---|---|---|
| J1 base yaw | 1 | false | 3.0 A (SDO-pushed) |
| J2 shoulder | 2 | false | 5.0 A |
| J3 elbow | 3 | true (if last on bus) | 5.0 A |

`POLE_PAIRS` = 7 assumes the 5010 is a 12N14P motor — **UNVERIFIED**:
count rotor magnets (14 → 7 pp) or read the vendor datasheet; wrong
pole pairs = wrong commutation and no torque.

`KT_MOTOR` = 0.0265 Nm/A (5010 360 KV estimate) — torque-command units
only; position/velocity control doesn't need it.

## Flashing

The ESC1's daughterboard has a built-in ST-LINK over USB-C:

- **Option A (Arduino IDE)**: install STM32duino core
  (https://github.com/stm32duino/BoardManagerFiles), board
  *"Discovery B-G431B-ESC1"*, install SimpleFOC from the library manager,
  open `joint_driver.ino`, set `DEVICE_CAN_ID`, Upload via ST-LINK.
- **Option B (PlatformIO)**: `board = disco_b_g431b_esc1`,
  `framework = arduino`, `lib_deps = simplefoc/Simple FOC @ ^2.3`,
  upload protocol `stlink`.

UNBUILT on the authoring machine (no STM32 toolchain). Board pin facts
are cross-checked against ST UM2516 and the NuttX b-g431b-esc1 board
documentation.

## First-time bring-up per joint (bench, before installing)

1. Flash with the right `DEVICE_CAN_ID`.
2. Wire CAN to the ESP32 base node (both ends terminated), power 12 V.
3. From robot-os or any CAN tool: `NMT CALIBRATE` to that node with the
   rotor free to spin — SimpleFOC measures encoder direction +
   electrical zero; firmware stores both to flash.
4. `SDO CURRENT_LIMIT_A` is re-pushed at every base-node boot.
5. `NMT ENABLE` → position hold; send RPDO2 targets at 20–100 Hz.

See `docs/can-protocol.md` for the frame table and `docs/bringup.md`
for the full arm checklist.

## Behaviour notes

- Torque commands (RPDO3) act only in torque mode; in position mode a
  non-zero RPDO3 is ignored (by design — keeps the position loop clean).
- Command watchdog: if RPDO2 stops for >300 ms the joint holds its
  current angle (never silent torque-off under load).
- `SDO SAVE_FLASH` (write 0x53515645) persists node id, encoder offset,
  current limit, gains and position limits.
- Bus-off: `bus_can_recover()` re-inits FDCAN1 automatically.
