# STATUS — Stream C: firmware & software (branch arm-firmware)

Deadline 31 Oct 2026. Updated every push.

## Done

- [x] **CAN protocol spec** — `docs/can-protocol.md`. CANopen-style
      (Berkeley Recoil-BESC compatible shape, MIT): fc<<7|node ID,
      RPDO2 pos+vel cmd, TPDO2/TPDO3 feedback @50 Hz, RSDO/TSDO params,
      NMT incl. broadcast ESTOP. 1 Mbps, ~6.6 % bus load.
- [x] **Host link spec** — `docs/host-protocol.md`. 0xAA55-framed, CRC16,
      115200 on the DevKit USB-UART port. Watchdog 500 ms → estop.
- [x] **Shared C codecs** — `firmware/shared/` (can_proto, feetech_proto,
      link_proto). Compiled on-host with `-Wall -Wextra -Werror` and
      pass a full encode/decode round-trip harness.
- [x] **ESP32-S3 base-node firmware** — `firmware/base-node/`
      (PlatformIO/Arduino). TWAI @1 Mbps on J15 (IO2 TX / IO1 RX),
      Feetech bus A @1 Mbps (IO17 TX / IO11 RX), host link, estop pin +
      watchdog, CAN bus-off recovery. **UNBUILT** — no PlatformIO
      toolchain on this machine; syntax-checked against Arduino stubs.
- [x] **B-G431B-ESC1 joint driver** — `firmware/joint-driver/`
      (SimpleFOC + STM32duino HAL FDCAN). Position/velocity/torque modes,
      AS5600 on PB6/PB7, calibration + flash params, current caps,
      CAN_TERM handling. **UNBUILT** — no STM32 toolchain.
- [x] **Orange Pi robot-os** — `software/robot-os/soma_arm`. FK/IK
      (analytic, both elbow branches), min-jerk planner w/ joint+speed
      limits, termios serial (no pyserial), CLI, SimBaseNode dry-run sim.
- [x] **Tests** — `software/robot-os/tests/`. 38 passed:
      500-pose FK/IK round-trip, CAN loopback incl. ctypes cross-check vs
      compiled C codec, Feetech checksums/vectors, link frames, sim
      estop latch. Real output in `docs/firmware-verification.md`.
- [x] **docs/bringup.md** — staged power-up checklist + safety.
- [x] **Real GPIO confirmed** — from pcb/gen_pcb.py: CAN = IO2/IO1 on J15
      (pins 3/4; 3V3 on pin 5), bus A = IO17/IO11, bus B = IO15/IO12,
      ESTOP = IO38, wrist UART = IO39/40. See firmware/base-node/README.md.

## In progress

- [ ] docs/firmware-verification.md — being finalized this push.

## Blocked / waiting

- Nothing blocking. PCB is final; no toolchain installs attempted
  (disk-tight policy) — both firmwares ship as code + build READMEs.

## UNVERIFIED items (must check before/while assembling)

| Item | Where | Note |
|---|---|---|
| 5010 pole pairs = 7 | joint_driver.ino | count rotor magnets (14) or vendor datasheet |
| 5010 Kt = 0.0265 Nm/A | joint_driver.ino | 60/(2π·360KV) estimate — torque cmds only |
| BASE_Z = 70 mm | config.py | shoulder axis height — take from Stream B CAD |
| Joint limits ±150–180° | config.py, config.h | placeholders until Stream B ROM numbers |
| Feetech 1 Mbps | spec+config.h | factory default, not proven on this wiring — fallback 500 k |
| AS5600 on J8 PB6/PB7 | joint_driver.ino, README | check UM2516 J8 pin order; alt PB7/PB8 |
| SN65HVD230 120 Ω jumper | base-node README | module-dependent; else solder 120 Ω |
| Iq→Nm scale | can-proto TPDO3 | reports phase current A, not output Nm |
| STS3215 current units | feetech_proto.h | ~6.5 mA/LSB assumed — check datasheet |

## Extra parts needed (beyond carrier BOM)

- SN65HVD230 CAN transceiver module (3.3 V) — ~$1–3, on J15.
- CAN twisted pair + JST pigtails to the three ESC1 J1 ports.
- 3× ST B-G431B-ESC1 + 3× 5010 motor + AS5600 boards + magnets
  (Stream A/B actuator BOM).
- 120 Ω axial resistors ×2 for CAN ends (if modules/boards lack them).
