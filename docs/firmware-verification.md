# Firmware & software verification — Stream C

Real, reproducible outputs. Date: 27 Oct 2026. Machine: macOS,
Python 3.9.12 (anaconda), Apple clang, pytest 7.1.1.

## What was verified vs. what could not be

| Item | Status |
|---|---|
| FK/IK round-trip (500 random poses) | **TESTED — pass** |
| CAN codec loopback, Python + compiled C, byte-exact | **TESTED — pass** |
| Feetech packet checksums + known vectors | **TESTED — pass** |
| Host-link frames, CRC, resync, estop latch (sim) | **TESTED — pass** |
| Shared C codecs compile `-Wall -Wextra -Werror` | **TESTED — pass** |
| ESP32-S3 firmware build/flash | **UNBUILT** — no PlatformIO toolchain |
| B-G431B-ESC1 firmware build/flash | **UNBUILT** — no STM32 toolchain |
| Any on-hardware test | **not done** — see docs/bringup.md |

## 1. pytest suite (real output)

```
$ cd software/robot-os && python3 -m pytest
============================= test session starts ==============================
platform darwin -- Python 3.9.12, pytest-7.1.1, pluggy-1.0.0
rootdir: /Users/deepakdiwan/Vector-wt/firmware/software/robot-os, configfile: pytest.ini
collecting ... collected 38 items

tests/test_can_proto.py::test_id_make PASSED                             [  2%]
tests/test_can_proto.py::test_nmt_roundtrip PASSED                       [  5%]
tests/test_can_proto.py::test_estop_broadcast PASSED                     [  7%]
tests/test_can_proto.py::test_pdo2_roundtrip PASSED                      [ 10%]
tests/test_can_proto.py::test_pdo3_roundtrip PASSED                      [ 13%]
tests/test_can_proto.py::test_sdo_write_read PASSED                      [ 15%]
tests/test_can_proto.py::test_parse_feedback PASSED                      [ 18%]
tests/test_can_proto.py::test_decoders_reject_short PASSED               [ 21%]
tests/test_can_proto.py::test_c_matches_python_nmt PASSED                [ 23%]
tests/test_can_proto.py::test_c_matches_python_pdo PASSED                [ 26%]
tests/test_can_proto.py::test_c_matches_python_sdo PASSED                [ 28%]
tests/test_can_proto.py::test_c_decoder_matches PASSED                   [ 31%]
tests/test_feetech.py::test_checksum_known_vectors PASSED                [ 34%]
tests/test_feetech.py::test_goal_packet_layout PASSED                    [ 36%]
tests/test_feetech.py::test_rad_counts_conversion PASSED                 [ 39%]
tests/test_feetech.py::test_parse_response PASSED                        [ 42%]
tests/test_feetech.py::test_parse_rejects PASSED                         [ 44%]
tests/test_feetech.py::test_signed_fields PASSED                         [ 47%]
tests/test_feetech.py::test_c_matches_python_packets PASSED              [ 50%]
tests/test_feetech.py::test_c_checksum_matches PASSED                    [ 52%]
tests/test_kinematics.py::test_fk_zero_pose PASSED                       [ 55%]
tests/test_kinematics.py::test_fk_vertical PASSED                        [ 57%]
tests/test_kinematics.py::test_yaw_rotation PASSED                       [ 60%]
tests/test_kinematics.py::test_ik_fk_roundtrip_random PASSED             [ 63%]
tests/test_kinematics.py::test_ik_known_pose PASSED                      [ 65%]
tests/test_kinematics.py::test_ik_unreachable_raises PASSED              [ 68%]
tests/test_kinematics.py::test_ik_both_branches PASSED                   [ 71%]
tests/test_kinematics.py::test_limits_enforced PASSED                    [ 73%]
tests/test_link.py::test_frame_roundtrip PASSED                          [ 76%]
tests/test_link.py::test_frame_byte_by_byte PASSED                       [ 78%]
tests/test_link.py::test_bad_crc_dropped PASSED                          [ 81%]
tests/test_link.py::test_resync_after_garbage PASSED                     [ 84%]
tests/test_link.py::test_crc16_vector PASSED                             [ 86%]
tests/test_link.py::test_sim_ping PASSED                                 [ 89%]
tests/test_link.py::test_sim_state PASSED                                [ 92%]
tests/test_link.py::test_sim_estop_latch PASSED                          [ 94%]
tests/test_link.py::test_sim_move_tcp PASSED                             [ 97%]
tests/test_link.py::test_nack_on_bad_type PASSED                         [100%]

============================== 38 passed in 1.85s ==============================
```

### What the tests actually cover

- **Kinematics** (`test_kinematics.py`): zero-pose/yaw/vertical FK
  anchors; 500 random in-limit joint sets → FK → IK → FK round-trip,
  position tolerance 0.1 mm. Honest note inside the test: 51/500 sampled
  poses are IK-unsolvable (extreme sampled pitch forces the wrist out of
  the 2-link annulus or q4 out of limits) — geometry truth, asserted as
  a fixed count so a regression can't hide behind it.
- **CAN codec** (`test_can_proto.py`): ID packing, NMT/estop broadcast,
  PDO2/PDO3/SDO round-trips, feedback parsing, short-frame rejection —
  plus 350+ randomized encodes **byte-compared against the compiled C
  codec** (ctypes → `firmware/shared/can_proto.c`), including C-side
  decoder agreement and truncation rejection.
- **Feetech codec** (`test_feetech.py`): hand-verified packets
  (PING `FFFF010201FB`, WRITE `...05032A0008C1`, READ `...060402380 2B9`),
  goal-write layout, rad↔counts, response parse + rejects, signed
  load/speed fields, and the same randomized byte-exact check against
  `firmware/shared/feetech_proto.c` (300+ packets).
- **Link codec + sim** (`test_link.py`): CRC16-CCITT standard vector
  (`"123456789"` → `0x29B1`), byte-at-a-time parsing, bad-CRC drop,
  resync after garbage, then the full SimBaseNode loopback: ping, state,
  streamed joints, estop latch + clear, Cartesian move through IK →
  planner → framed link → sim → FK check, NACK on unknown type.

## 2. C codec host harness (real output)

```
$ cc -std=c99 -Wall -Wextra -Werror -O2 -I. -o /tmp/host_test \
    host_test.c can_proto.c feetech_proto.c link_proto.c
$ /tmp/host_test
HOST-CODEC-TEST: ALL PASS
```

Harness exercises every public encode/decode symbol in
`firmware/shared/` (all three protocols) with fixed vectors — the same
code the ESP32 firmware compiles via `src/shared_impl.cpp`.

## 3. Firmware static checks

- `firmware/base-node/src/*.cpp`: syntax-checked with clang++ against
  minimal Arduino/TWAI stubs (toolchain absent — see status file).
  Shared codecs compile cleanly inside a C++ TU.
- `firmware/joint-driver/`: review-checked against ST UM2516 pinout
  table + NuttX b-g431b-esc1 doc (6PWM PA8/PC13/PA9/PA12/PA10/PB15,
  shunt 3 mΩ gain −9.14, CAN PA11/PB9, CAN_TERM PC14). Not compiled.

## 4. Known limitations (honest list)

- `SDO_TEMPERATURE_C` returns 0 (no temp wired yet — TODO in driver).
- RPDO3 torque is ignored in position mode (documented; torque mode
  exists for torque commands).
- SimBaseNode uses a first-order lag model — it validates the protocol
  stack, not joint dynamics.
- IK is analytic 5-DOF pose (x,y,z,pitch,roll) + jaw; no full 6-DOF
  orientation target (J5 is roll-only by design).
- All UNVERIFIED hardware parameters are listed in
  `docs/STATUS-firmware.md`.
