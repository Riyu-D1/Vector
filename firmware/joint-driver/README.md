# joint-driver — B-G431B-ESC1 firmware for J2/J3 cycloidal actuators

One ST B-G431B-ESC1 per joint — **J2 (shoulder, node 2) and J3
(elbow, node 3) only**; J1 is an STS3250 servo on Feetech bus A.
Tarot TL2955 **4008 330KV** motor + **40:1** printed cycloidal +
**AS5600 on the motor shaft** (single-turn → output = motor/40, and
the output angle is unknown at boot → homing is required).
SimpleFOC implementation of the Berkeley Recoil-BESC protocol shape
(MIT-licensed reference: github.com/T-K-233/Recoil-Motor-Controller-BESC).

## Hardware hookup (per actuator)

| Signal | Where | Notes |
|---|---|---|
| Motor phases U/V/W | ESC1 motor pads | any order — calibration fixes direction |
| AS5600 SCL/SDA | J8 sensor pads → PB6/PB7 | **UNVERIFIED** J8 pin order — check UM2516 before soldering; the alternative I2C1 pair PB7(SDA)/PB8(SCL) is also on J8 |
| CAN | J1 port | onboard transceiver — twisted pair to the carrier's TJA1051T/3 |
| 120 Ω term | PC14 = `CAN_TERM` | `CAN_TERM_LAST true` on the LAST node only |
| 12 V | J5/J6 power pads | switched `+12V_MOT` rail (J18/J20 on carrier) |
| ESC logic feed | — | **UNVERIFIED**: if logic is fed from +12V_MOT the drive can't
heartbeat while the rail is off and the arm can never arm — see
`docs/can-protocol.md` power caveat |

Soldering the small J1 CAN pads is fragile (Berkeley docs warn about
this too) — use thin wire, flux, and strain-relief the cable.

## Per-node configuration

Edit the top of `joint_driver.ino` before flashing each board:

| Joint | `DEVICE_CAN_ID` | `CAN_TERM_LAST` | current cap |
|---|---|---|---|
| J2 shoulder | 2 | false | 5.0 A [U] |
| J3 elbow | 3 | true (last on bus) | 5.0 A [U] |

`POLE_PAIRS` = 7 assumes the 4008 is a 12N14P motor — **UNVERIFIED**:
count rotor magnets (14 → 7 pp) or read the vendor datasheet; wrong
pole pairs = wrong commutation and no torque.

`KT_MOTOR` = 0.0289 N·m/A (4008 330 KV: 60/(2π·330)) — for the
phase-current ↔ torque mapping; **UNVERIFIED** estimate.

`GEAR_EFF` = 0.7 for the 40:1 printed cycloidal — **UNVERIFIED**
guess; output torque = motor torque × 40 × eff.

`HOME_*` (stop offset rad, homing current, crawl speed) — all
**UNVERIFIED**; measure the hard-stop angle per joint on the bench.

## Flashing

The ESC1's daughterboard has a built-in ST-LINK over USB-C:

- **PlatformIO (what CI/this repo uses)**: `pio run -t upload`.
  `platformio.ini` pins stm32duino core **2.12.0** — core 3.x broke
  SimpleFOC (`enableTimerClock` signature change); see
  `docs/firmware-verification.md`.
- **Arduino IDE**: stm32duino core **≤ 2.12.x** (same reason), board
  *"Discovery B-G431B-ESC1"*, SimpleFOC 2.4.x, set `DEVICE_CAN_ID`,
  Upload via ST-LINK.

Build verified — `docs/firmware-verification.md` (RAM 14.4 %,
flash 38.8 %).

## First-time bring-up per joint (bench, before installing)

1. Flash with the right `DEVICE_CAN_ID`.
2. Wire CAN to the base node (both ends terminated). **Logic power
   from an unswitched supply** — the relay rail is off until the
   drive has heartbeated (see the caveat above).
3. Rotor free: `NMT CALIBRATE` — SimpleFOC measures encoder
   direction + electrical zero; stored to flash (persisted).
4. `NMT HOME` — joint creeps into the hard stop at the homing
   current, detects stall, sets output zero at stop + offset;
   STATUS b4 (homed) sets. Required **every boot** — the AS5600 is
   single-turn and can't see which of the 40 motor turns it's on.
5. `NMT ENABLE` (refused before calibrated+homed) → position hold;
   send RPDO2 targets at 20–100 Hz in **output radians**.

See `docs/can-protocol.md` for the frame table and `docs/bringup.md`
for the full arm checklist.

## Behaviour notes

- Commands and feedback are in **output-shaft radians** — the
  firmware tracks multi-turn motor angle internally (the encoder
  alone can't) and divides by `GEAR_RATIO`.
- Torque commands (RPDO3) act only in torque mode; in position mode
  a non-zero RPDO3 is ignored (by design — keeps the position loop
  clean).
- Command watchdog: if RPDO2 stops for >300 ms the joint holds its
  current angle (never silent torque-off under load).
- NMT ESTOP or a base-node MOTOR_EN drop → torque off immediately;
  re-enable needs an explicit NMT ENABLE (and on a rail drop, the
  host must re-arm `MOTOR_EN` first anyway).
- `SDO SAVE_FLASH` (write 0x53515645) persists node id, encoder
  offset/direction, calibration flag, current limit, gains, position
  limits and homing params.
- Bus-off: `bus_can_recover()` re-inits FDCAN1 automatically.
