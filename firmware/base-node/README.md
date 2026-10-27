# base-node — ESP32-S3 brainstem firmware (SOMA v3)

Runs on the ESP32-S3-DevKitC-1 socketed onto the `soma-carrier` PCB.
The carrier is final — every net below is already routed.

## What it does

- **CAN master @ 1 Mbit/s** for J1–J3 printed cycloidal actuators
  (B-G431B-ESC1 running `firmware/joint-driver`), CANopen-style protocol —
  see [docs/can-protocol.md](../../docs/can-protocol.md).
- **Feetech STS bus master @ 1 Mbaud** for J4 (wrist pitch, id 4),
  J5 (wrist roll, id 5), J6 (gripper, id 6) on bus A — UNVERIFIED baud,
  see below.
- **Framed serial link** to the Orange Pi (`docs/host-protocol.md`),
  115200 8N1 on the DevKit's USB-UART port (UART0, IO43/IO44 console).
- **Safety**: J9 ESTOP loop (NC to GND — open = estop), 500 ms host-link
  watchdog, CAN bus-off auto-recovery. Any estop source latches:
  CAN NMT-ESTOP broadcast + servo torque-off until `CLEAR_ESTOP`.

## Wiring (all on the carrier)

| Signal | ESP32 pin | Carrier port | Wire |
|---|---|---|---|
| CAN TX | IO2 (SP1) | J15 pin 3 | SN65HVD230 module CTX/D |
| CAN RX | IO1 (SP2) | J15 pin 4 | SN65HVD230 module CRX/R |
| 3V3 | — | J15 pin 5 | SN65HVD230 VCC |
| GND | — | J15 pin 2 | SN65HVD230 GND |
| (+5V) | — | J15 pin 1 | spare (module is 3V3) |
| BUS A data | IO17 (TX) | J4/J5 | servo daisy-chain data |
| BUS A echo | IO11 (RX) | via R1 | (already wired on carrier) |
| ESTOP | IO38 | J9 pin 1↔2 | NC e-stop loop to GND |
| STAT LED | IO16 | D3 | already on carrier |

SN65HVD230 CANH/CANL go to the actuator bus (twisted pair). The far end
is the LAST B-G431B-ESC1's J1 port; turn its 120 Ω termination ON
(`CAN_TERM_LAST true` in joint_driver.ino). The ESP32 end needs 120 Ω
across CANH-CANL too — most SN65HVD230 modules have a jumper/pad for it;
otherwise solder an axial 120 Ω at the module. UNVERIFIED: whether the
ordered module has the jumper.

Feetech bus A is a single TTL wire: ESP32 TX (IO17) drives it, RX (IO11)
hears it through R1 — the firmware discards its own echo. Baud is the
Feetech factory 1 Mbps; spec marks that UNVERIFIED on this wiring —
if the bus is flaky, drop `FT_BAUD` in `src/config.h` to 500000 and
re-flash (servos must then be re-bauded too — see STS docs).

## Build & flash

```
pip install platformio            # or use the VS Code extension
pio run                            # build
pio run -t upload                  # flash (UART-labeled USB port)
pio device monitor                 # serial console @115200
```

UNBUILT on the authoring machine (no PlatformIO toolchain installed —
per ARM_HYBRID_V3.md the code + this README are the deliverable). The
shared codecs in `../shared/` are verified on-host (`-Wall -Werror`
clean, round-trip tests in `software/robot-os/tests/`).

## Boot sequence notes

- On boot: CAN init, Feetech init, SDO `CURRENT_LIMIT_A` pushed to each
  joint (3 A J1 / 5 A J2,J3 — spec), joints left DISABLED.
- Arm with `SET_MODE enable` only after joints are calibrated + homed —
  see `docs/bringup.md`.
- `STATE` telemetry streams at 25 Hz automatically.

## Pin map (authoritative: pcb/gen_pcb.py)

Also used/spare: IO15/IO12 = bus B UART2 (spare, unused in v3),
IO8/IO18 = I2C1, IO41/IO42 = I2C2, IO39/IO40 = wrist-node UART (J10),
IO7 = buzzer, IO10 = 12 V divider ADC, IO4 = WS2812, IO21/47/48 = jog
encoder (J13).
