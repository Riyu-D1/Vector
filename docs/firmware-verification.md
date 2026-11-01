# Firmware & software verification — Stage W1 (firmware v2)

Real, reproducible outputs from the `arm-fw2` worktree. Machine: macOS
arm64, Python 3.12.2, pytest 9.1.1, PlatformIO Core 6.1.x in a local
venv (`~/Vector-wt/fw2/.venv-pio`), packages in `~/.platformio`.
Nothing installed system-wide.

## What was verified vs. what could not be

| Item | Status |
|---|---|
| ESP32-S3 base-node firmware build (`esp32-s3-devkitc-1`) | **PASS — compiles + links** (below) |
| B-G431B-ESC1 joint-driver build (`disco_b_g431b_esc1`) | **PASS — compiles + links** (below) |
| MOTOR_EN safety state machine (exact C source via ctypes) | **TESTED — pass** (9 cases) |
| FK/IK round-trip under the real geometry + limits | **TESTED — pass** (0 fails/500) |
| Gravity model vs FEA `parts_AB.json` moments | **TESTED — pass** (matches AB-pose refs) |
| Payload derating (J4 collapses limit at full reach) | **TESTED — pass** (<0.5 kg there) |
| CAN/Feetech/link codecs, byte-exact C↔Python | **TESTED — pass** |
| Sim safety: arm→drop→explicit re-arm | **TESTED — pass** |
| Any on-hardware test (relay, homing, spin) | **NOT DONE — see `docs/bringup.md`** |

## 1. PlatformIO builds (real output)

### Base node — `firmware/base-node`

```
$ cd firmware/base-node && pio run
PLATFORM: Espressif 32 (6.5.0) > Espressif ESP32-S3-DevKitC-1
...
RAM:   [=         ]   6.0% (used 19752 bytes from 327680 bytes)
Flash: [=         ]   8.6% (used 285885 bytes from 3342336 bytes)
========================= [SUCCESS] Took 2.71 seconds =========================
```

### Joint driver — `firmware/joint-driver`

```
$ cd firmware/joint-driver && pio run
PLATFORM: ST STM32 (17.6.0) > ST B-G431B-ESC1 Discovery
HARDWARE: STM32G431CBU6 170MHz, 32KB RAM, 128KB Flash
PACKAGES:
 - framework-arduinoststm32 @ 4.21200.0 (2.12.0)
 - framework-cmsis @ 2.50900.0 (5.9.0)
 - toolchain-gccarmnoneeabi @ 1.120301.0 (12.3.1)
...
RAM:   [=         ]  14.4% (used 4728 bytes from 32768 bytes)
Flash: [====      ]  38.8% (used 50840 bytes from 131072 bytes)
Building .pio/build/disco_b_g431b_esc1/firmware.bin
========================= [SUCCESS] Took 42.59 seconds =========================
```

**Environment note (why `platform_packages` is pinned):** the
ststm32 platform manifest asks for `framework-arduinoststm32
~4.20801.0`, which the registry no longer serves on macOS — and the
one it does serve for stm32duino core 3.x (`4.30000.0`) changed the
signature of `enableTimerClock()` (`TIM_HandleTypeDef*` →
`TIM_TypeDef*`), which breaks SimpleFOC 2.3.x–2.4.x inside
`drivers/hardware_specific/stm32/stm32_mcu.cpp` (upstream master is
unfixed). `platformio.ini` therefore pins core **2.12.0**
(`4.21200.0`, newest pre-3.x) + `framework-cmsis-dsp`, with
`askuric/Simple FOC @ ^2.4.0`. First attempts against 4.30000.0 and
a git URL for the old core failed — this combination is the one that
builds.

## 2. Host test suite (real output)

```
$ cd software/robot-os && python3 -m pytest tests -x -q
============================= test session starts ==============================
platform darwin -- Python 3.12.2, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/deepakdiwan/Vector-wt/fw2/software/robot-os
configfile: pytest.ini
collected 57 items

tests/test_can_proto.py ............                                     [ 21%]
tests/test_feetech.py ........                                           [ 35%]
tests/test_gravity.py ........                                           [ 49%]
tests/test_kinematics.py ..........                                      [ 66%]
tests/test_link.py ..........                                            [ 84%]
tests/test_motor_en.py .........                                         [100%]

============================== 57 passed in 4.35s ==============================
```

### MOTOR_EN state machine — what's actually exercised

`tests/test_motor_en.py` compiles **`firmware/shared/motor_en.c` to a
shared library and drives it through ctypes** — the same bytes the
ESP32 links, not a Python reimplementation. Cases: boot-low, no-arm
without handshake, no-arm while e-stop held, no-arm without ESC
heartbeats, arm when all conditions hold, drop on lost heartbeat,
drop on e-stop, drop on watchdog, drop on ESC fault, drop on
bus-off, and explicit `ARM_MOTOR` required again after any drop.

## 3. Honest limitations

- **Nothing ran on hardware.** Compile + host-side tests only. The
  relay chain, homing, FOC commutation, servo bus at 1 Mbps, CAN
  heartbeat timing and the ESC power-path question are all
  UNVERIFIED — bench list is `docs/bringup.md` stage 0–2.
- `joint_driver.ino` built cleanly but SimpleFOC board support for
  B-G431B-ESC1 was only cross-checked against UM2516 docs; pin/timer
  assignment is UNVERIFIED until a scope sees PWM.
- `SDO_TEMPERATURE_C` returns 0 until a temp sensor is wired.
- SimBaseNode is a protocol model (lag + flags), not joint dynamics.
- IK is analytic for the 6-DOF chain with the current wrist
  convention — full-reach J4 torque collapses payload to <0.5 kg by
  design of the FEA numbers, not a solver artifact.
- All UNVERIFIED hardware parameters: `docs/STATUS-fw2.md` table.

## W2 — two-phase MOTOR_EN arm (real output)

Same environment (`~/Vector-wt/fw2/.venv-pio` — PlatformIO Core
6.1.18; tests on anaconda `python3` = Python 3.9.12, pytest 7.1.1).

### Base node — `firmware/base-node`

```
$ cd firmware/base-node && pio run
PLATFORM: Espressif 32 (6.5.0) > Espressif ESP32-S3-DevKitC-1
...
RAM:   [=         ]   6.0% (used 19760 bytes from 327680 bytes)
Flash: [=         ]   8.6% (used 285969 bytes from 3342336 bytes)
========================= [SUCCESS] Took 17.16 seconds =========================
```

### Joint driver — `firmware/joint-driver`

```
$ cd firmware/joint-driver && pio run
PLATFORM: ST STM32 (17.6.0) > ST B-G431B-ESC1 Discovery
HARDWARE: STM32G431CBU6 170MHz, 32KB RAM, 128KB Flash
PACKAGES:
 - framework-arduinoststm32 @ 4.21200.0 (2.12.0)
 - framework-cmsis-dsp @ 1.17.1
 - toolchain-gccarmnoneeabi @ 1.120301.0 (12.3.1)
...
RAM:   [=         ]  14.4% (used 4728 bytes from 32768 bytes)
Flash: [====      ]  38.8% (used 50896 bytes from 131072 bytes)
========================= [SUCCESS] Took 79.86 seconds =========================
```

### Host test suite

```
$ cd software/robot-os && python3 -m pytest tests -x -q
============================= test session starts ==============================
platform darwin -- Python 3.9.12, pytest-7.1.1, pluggy-1.0.0
rootdir: /Users/deepakdiwan/Vector-wt/fw2/software/robot-os
configfile: pytest.ini
collected 62 items

tests/test_can_proto.py ............                                     [ 19%]
tests/test_feetech.py ........                                           [ 32%]
tests/test_gravity.py ........                                           [ 45%]
tests/test_kinematics.py ..........                                      [ 61%]
tests/test_link.py ..........                                            [ 77%]
tests/test_motor_en.py ..............                                    [100%]

============================== 62 passed in 14.40s ==============================
```

`tests/test_motor_en.py` (14 cases, ctypes on the real
`firmware/shared/motor_en.c`): pre-arm closes K1 with **no** ESC
heartbeats (the W2 fix), boot-window expiry drops
`ESC_BOOT_TIMEOUT` (reason 6) with a fresh-ARM retry, heartbeat
inside the window reaches `MEP_ARMED`, heartbeat loss after armed
drops `ESC_LOST`, estop during the window drops `ESTOP`,
`esc_boot_window_ms` is a settable param, phase-1 refusals
(no host/dead link/estop/bus-off), explicit re-arm required — plus
every W1 drop case re-checked through the armed phase.
