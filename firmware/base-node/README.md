# base-node — ESP32-S3 brainstem firmware (carrier v1.3)

Runs on the ESP32-S3-DevKitC-1 socketed onto the `soma-carrier` PCB
**v1.3**. The carrier is final — every net below is already routed.

## What it does

- **MOTOR_EN safety chain**: IO40 → Q3 → relay K1 → `+12V_MOT`
  (J18/J20). Two-phase arm: phase 1 = explicit host `ARM_MOTOR`
  while host link alive + estop released + no bus-off (ESC
  heartbeats can't be a precondition — the drives are dead until
  K1 closes); phase 2 = every configured ESC must heartbeat inside
  the 1500 ms boot window else the rail drops `ESC_BOOT_TIMEOUT`.
  Once armed, any estop/watchdog/bus-off/ESC-fault/lost-heartbeat
  drops it instantly (NMT ESTOP broadcast + servo torque-off).
  Pure-C machine in `firmware/shared/motor_en.c`, host-tested via
  ctypes.
- **CAN master @ 1 Mbit/s** for J2/J3 cycloidal actuators
  (B-G431B-ESC1 running `firmware/joint-driver`, nodes 2 and 3),
  CANopen-style — see [docs/can-protocol.md](../../docs/can-protocol.md).
  Onboard **TJA1051T/3** transceiver — no module needed.
- **Feetech STS bus master @ 1 Mbaud** for J1 (STS3250, id 1),
  J4/J5/J6 (STS3215, ids 4–6) and gripper (id 7) on bus A —
  UNVERIFIED baud, see below.
- **Framed serial link** to the Orange Pi (`docs/host-protocol.md`),
  115200 8N1 on the DevKit's USB-UART port (UART0, IO43/IO44
  console), 7 channels (J1..J6, GRIP), 86-byte STATE.
- **Safety**: J9 ESTOP sense (IO38, NC loop — open = estop), J19 NC
  loop in the relay coil path (hardware cut regardless of firmware),
  500 ms host-link watchdog, CAN bus-off auto-recovery.

## Wiring (all on the carrier v1.3)

| Signal | ESP32 pin | Where | Notes |
|---|---|---|---|
| CAN TX | IO2 | TJA1051T/3 → CAN header | onboard transceiver |
| CAN RX | IO1 | TJA1051T/3 | |
| MOTOR_EN | IO40 | R11 → Q3 → K1 coil | high = +12V_MOT live |
| ESTOP sense | IO38 | J9 | NC loop report only |
| BUS A data | IO17 (TX) | J4/J5 | servo daisy-chain |
| BUS A echo | IO11 (RX) | via R1 | already wired on carrier |
| STAT LED | IO16 | D3 | already on carrier |

**Removed in v1.3 (do not use):** bus B (IO15/IO12), second I2C
(IO41/IO42), wrist UART (IO39/IO14). The pins exist on the module
footprint but route nowhere.

CAN bus far end: the LAST B-G431B-ESC1's termination (`CAN_TERM`,
PC14). The carrier end is handled by the TJA1051T/3 section.

Feetech bus A is a single TTL wire: ESP32 TX (IO17) drives it, RX
(IO11) hears it through R1 — the firmware discards its own echo.
Baud is the Feetech factory 1 Mbps — UNVERIFIED on this wiring; if
flaky, drop `FT_BAUD` in `src/config.h` to 500000 and re-flash
(servos must be re-bauded too).

## Build & flash

```
pio run                            # build (esp32-s3-devkitc-1)
pio run -t upload                  # flash (UART-labeled USB port)
pio device monitor                 # serial console @115200
```

Built and verified — see `docs/firmware-verification.md` for the
real output (RAM 6.0 %, flash 8.6 %).

## Boot sequence notes

- MOTOR_EN comes up LOW first thing — the rail is dead until a host
  proves itself.
- CAN init, Feetech init, SDO `CURRENT_LIMIT_A` (5 A) pushed to J2/J3,
  joints left DISABLED.
- HOST must `ARM_MOTOR` → K1 closes → every ESC must heartbeat inside
  1500 ms (`ESC_BOOT_TIMEOUT` drop otherwise) → `enable` (NMT ENABLE)
  → joints must have been calibrated + homed or the drives refuse
  (see `docs/bringup.md`).
- `STATE` telemetry streams at ~25 Hz automatically.

## Pin map (authoritative: pcb13 STATUS + gen_pcb.py)

Also present but **unconnected on v1.3**: IO15/IO12, IO41/IO42,
IO39/IO14. Other spares: IO8/IO18 = I2C1, IO7 = buzzer, IO10 = 12 V
divider ADC, IO4 = WS2812, IO21/47/48 = jog encoder (J13).
