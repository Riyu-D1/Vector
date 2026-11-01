# robot-os — Orange Pi software for SOMA v3

Pure-Python (3.9+) package `soma_arm`: kinematics, trajectory planning,
the framed link to the ESP32 base node, and a full dry-run simulator.
Only hard dependency is `numpy` (pytest for tests); serial I/O uses
POSIX termios — **no pyserial needed**.

## Layout

```
soma_arm/
  config.py      real geometry, limits, IDs, caps (UNVERIFIED flags inside)
  kinematics.py  exact FK chain (4x4) + analytic IK (x,y,z,pitch,roll)
  gravity.py     gravity-torque model + max_payload (80%-rated derate)
  planner.py     synchronized min-jerk quintic + per-waypoint torque gate
  can_proto.py   CAN codec — byte-identical to firmware/shared/can_proto.c
  feetech.py     Feetech STS packet codec — mirrors feetech_proto.c
  link.py        frame codec + termios serial + SimTransport (7 channels)
  sim.py         SimBaseNode — protocol-level base-node + MOTOR_EN model
  arm.py         high-level Arm API (move_joints/move_tcp/gripper/arm_motors)
  cli.py         `python -m soma_arm.cli ...`
tests/           pytest suite (57 tests — see docs/firmware-verification.md)
```

## Quick start (no hardware)

```bash
cd software/robot-os
PYTHONPATH=. python3 -m soma_arm.cli --sim demo
PYTHONPATH=. python3 -m soma_arm.cli --sim move-tcp 0.20 0.0 0.12 --pitch 0
PYTHONPATH=. python3 -m soma_arm.cli --sim move-joints 0 0.4 0.6 0 0 0.4
PYTHONPATH=. python3 -m soma_arm.cli --sim fk 0 0.4 0.6 0 0 0
PYTHONPATH=. python3 -m soma_arm.cli --sim sense
```

## Real hardware

```bash
PYTHONPATH=. python3 -m soma_arm.cli --port /dev/ttyUSB0 ping
PYTHONPATH=. python3 -m soma_arm.cli --port /dev/ttyUSB0 move-tcp \
    0.20 0.0 0.12 --pitch 0 --speed 0.3
```

## Geometry (real numbers from sim/CAD — see config.py)

Home-pose joint positions (mm): J1 (0,0,80.8) z; J2 (-20,0,143.5) y;
J3 (-20,0,270.2) y; J4 (96.4,0,216.2) y; J5 (134,0,240.4) z;
J6 (153.2,0,216.2) x; TCP (228.2,0,216.2). `BASE_Z` = 80.8 mm.
Effective link lengths: upper 126.7 mm, forearm ≈128.3 mm, wrist
assembly 131.8 mm. Positive J2/J3/J4 joint angles tip the tool
**down** — `Pose.pitch` (tool elevation) = −(q2+q3+q4).

Joint ranges: J1 ±180°, J2 −120..+70°, J3 −180..+30°, J4 ±70°,
J5 ±70°, J6 ±180°. IK solves (x, y, z, pitch, roll) with both elbow
branches and yaw-mirror candidates; limit-checked.

## Joint→bus map

| Joint | Actuator | Bus | Node/ID |
|---|---|---|---|
| J1 yaw | STS3250 | Feetech bus A 1 Mbaud | id 1 |
| J2 shoulder | Tarot 4008 330KV + 40:1 cycloidal, B-G431B-ESC1 | CAN 1 Mbps | node 2 |
| J3 elbow | Tarot 4008 330KV + 40:1 cycloidal, B-G431B-ESC1 | CAN | node 3 |
| J4 wrist pitch | STS3215-12V | Feetech bus A | id 4 |
| J5 wrist roll | STS3215-12V | Feetech bus A | id 5 |
| J6 wrist | STS3215-12V | Feetech bus A | id 6 |
| GRIP jaw | STS3215-12V | Feetech bus A | id 7 |

Motor power goes through relay K1 (`MOTOR_EN`) — `arm-motors` first,
then `enable`; any estop/watchdog/fault drops the rail and needs an
explicit re-arm (`docs/host-protocol.md`).

## Tests

```bash
cd software/robot-os && python3 -m pytest
```

57 tests incl. a byte-exact cross-check of the Python codecs against the
compiled C codecs, the real `motor_en.c` safety machine via ctypes, and
the gravity/payload-derate model against the FEA numbers (needs any C
compiler, skips cleanly without).
