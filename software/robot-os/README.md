# robot-os — Orange Pi software for SOMA v3

Pure-Python (3.9+) package `soma_arm`: kinematics, trajectory planning,
the framed link to the ESP32 base node, and a full dry-run simulator.
Only hard dependency is `numpy` (pytest for tests); serial I/O uses
POSIX termios — **no pyserial needed**.

## Layout

```
soma_arm/
  config.py      geometry, limits, IDs, caps (UNVERIFIED flags inside)
  kinematics.py  FK (4x4) + analytic IK (x,y,z,pitch,roll), 2 branches
  planner.py     synchronized min-jerk quintic, joint vel/acc caps
  can_proto.py   CAN codec — byte-identical to firmware/shared/can_proto.c
  feetech.py     Feetech STS packet codec — mirrors feetech_proto.c
  link.py        frame codec + termios serial + SimTransport
  sim.py         SimBaseNode — full protocol-level base-node simulator
  arm.py         high-level Arm API (move_joints/move_tcp/gripper/sense)
  cli.py         `python -m soma_arm.cli ...`
tests/           pytest suite (38 tests — see docs/firmware-verification.md)
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

## Geometry (must match Stream B CAD)

L1 = 120 mm (shoulder→elbow), L2 = 100 mm (elbow→wrist), L3 = 40 mm
(wrist→tool), `BASE_Z` = 70 mm **UNVERIFIED** (shoulder axis height over
the turntable plane — set from CAD when Stream B lands). Zero pose = arm
extended along +X. Pitch angles are elevations from horizontal.

IK solves (x, y, z, pitch, roll): q1 = atan2(y,x), wrist centre backed
off by L3, 2-link planar solve for q2/q3, q4 = pitch − q2 − q3, q5 = roll.
Both elbow branches are produced; seed-based branch pick in `Arm.move_tcp`.

## Joint→bus map

| Joint | Actuator | Bus | Node/ID |
|---|---|---|---|
| J1 yaw | 5010 + cycloidal | CAN 1 Mbps | node 1 |
| J2 shoulder | 5010 + cycloidal | CAN | node 2 |
| J3 elbow | 5010 + cycloidal | CAN | node 3 |
| J4 wrist pitch | STS3215-12V | Feetech bus A | id 4 |
| J5 wrist roll | STS3215-12V | Feetech bus A | id 5 |
| J6 gripper | STS3215-12V | Feetech bus A | id 6 |

## Tests

```bash
cd software/robot-os && python3 -m pytest
```

38 tests incl. a byte-exact cross-check of the Python codecs against the
compiled C codecs (needs any C compiler, skips cleanly without).
