# STATUS — Stage W1: firmware v2 for the CURRENT arm (branch arm-fw2)

Base: `arm-firmware` @e9271b5 (old firmware, never built). Worktree
`~/Vector-wt/fw2`. 3 h budget. Real compile/test output only.

## Step 1 — planned changes (written before editing)

Hardware deltas vs the old code (from pcb13/sim/fea STATUS files):

- Carrier v1.3: **MOTOR_EN = IO40** drives relay K1 → +12V_MOT on J18/J20
  (motors unpowered until firmware closes it; J19 NC e-stop loop can open
  the coil regardless). ESTOP sense stays IO38. **Removed from board:**
  bus B (IO15/12), I2C2 (IO41/42), wrist UART (IO39/40).
- J1 is now an **STS3250 servo on bus A** (was CAN cycloidal).
- J2/J3 keep B-G431B-ESC1 CAN drivers but motor is **Tarot TL2955 4008
  330KV** (was 5010 360KV), gearbox **40:1** (was 15:1), encoder on the
  motor shaft (single-turn → homing needed).
- J4/J5/J6 + **gripper** = STS3215 on bus A → bus A carries 5 servos,
  host link gains a 7th channel.
- Real geometry (sim/STATUS-sim.md): J1 (0,0,80.8) z; J2 (-20,0,143.5) y;
  J3 (-20,0,270.2) y; J4 (96.4,0,216.2) y; J5 (134,0,240.4) z;
  J6 (153.2,0,216.2) x. Ranges: J1 ±180°, J2 −120..+70, J3 −180..+30,
  J4 ±70, J5 ±70, J6 ±180 (rad in code).
- Rated torques (stage): J2 3.5, J3 2.25, J4/J5/J6 0.98 N·m; J1 STS3250
  treated as 0.98 [U]. FEA @0.5 kg full reach: J4 1.75 OVER (frd) /
  0.80 analytic (parts_AB.json moments field).

### File plan

- `firmware/shared/`: NEW `motor_en.h/.c` (pure-C MOTOR_EN state
  machine — compiled into the firmware AND into a host pytest via
  ctypes); `can_proto.h` + NMT_HOME cmd + home SDO addrs + STATUS bit;
  `link_proto.h` + LK_ARM_MOTOR cmd, MOTOR_EN flag/event, 7-joint
  comments.
- `firmware/base-node/`: `pins.h` v1.3 map (add IO40 MOTOR_EN, drop
  BUSB/I2C2/wrist); `config.h` 2 CAN nodes {2,3} + 5 servos {1,4,5,6,7}
  + 7-channel limits + gear 40 + fw 0.2.0; `arm_state.h` q[7]; `main.cpp`
  MOTOR_EN wiring, estop→rail cut, arm gating, bus-off/ESC-fault inputs;
  `can_bus` exposes bus-off; `feetech_bus` drop BusB, 5 servos;
  `host_link` 28 B pos/vel, 2-joint torque, ARM_MOTOR, 86 B STATE.
- `firmware/joint-driver/`: Tarot 4008 params (Kt 0.0289 [U], pp 7 [U],
  40:1, eff 0.7 [U], 5 A [U]), NMT_HOME homing-into-stop, torque gated
  on calibrated+homed, output-rad commands unchanged, new
  `platformio.ini` (disco_b_g431b_esc1, SimpleFOC).
- `software/robot-os/`: `config.py` real geometry+rated torques;
  `kinematics.py` exact FK chain (J1z,J2-4y,J5z,J6x + real offsets),
  planar IK q1..q4 (q5=0, roll→q6); NEW `gravity.py` (part-mass torque
  model + `max_payload` + 80 %-rated planner check); `link.py`/`sim.py`
  7 channels + ARM_MOTOR + MOTOR_EN flag; `arm.py`/`cli.py` updated;
  new tests (motor_en ctypes, gravity vs parts_AB.json numbers,
  derating <0.5 kg at full reach).
- `docs/`: bringup (relay bench test → one actuator no-load → homing →
  loaded), can-protocol (HOME + safety state), host-protocol (7 ch,
  ARM_MOTOR), READMEs, firmware-verification (real outputs).

## UNVERIFIED table (bench before powering)

| Item | Value used | Where | Note |
|---|---|---|---|
| 4008 pole pairs | 7 | joint_driver.ino | count rotor magnets (14→7 pp) |
| 4008 Kt | 0.0289 N·m/A | joint_driver.ino, config.py | 60/(2π·330 KV), phase current |
| Phase current cap | 5 A | config.h, joint_driver.ino | conservative until bench |
| Gear efficiency | 0.7 | joint_driver.ino, gravity.py | 40:1 cycloidal guess |
| Relay K1 pad map | coil 1/2, COM 3, NO 5 | pcb13 STATUS | check Songle SRD datasheet |
| AS5600 pins on J8 | PB6 SCL/PB7 SDA | joint_driver.ino | alt pair PB7/PB8 on J8 |
| CAN node IDs | J2=2, J3=3 | config.h, can_proto.h | kept old numbering |
| STS3215 current units | ~6.5 mA/LSB | feetech_proto.h | check datasheet |
| Servo bus 1 Mbps | 1 Mbaud | config.h, config.py | factory default, unproven wiring |
| J1 servo id | 1 (STS3250, STS proto) | config.h | set id on bench |
| Gripper servo id | 7 | config.h | jaw channel index 6 |
| Hard-stop offset per joint | pos_lo | joint_driver.ino | stop angle not in sim — measure |
| J1 rated torque | 0.98 N·m | config.py | STS3250 datasheet pending |

## Steps 2–4 — implemented

- **Base node**: pins.h = v1.3 map (CAN IO2/IO1, MOTOR_EN IO40,
  estop sense IO38, bus A IO17/IO11; bus B / I2C2 / wrist UART
  removed). New `firmware/shared/motor_en.c` = pure-C safety machine
  (boot-low; arm only on explicit host ARM_MOTOR while
  handshake+alive+estop-released+all-ESC-heartbeats+no-fault+no-bus-off;
  any violation → immediate drop, host must re-arm explicitly).
  main.cpp ticks it every loop; drop → NMT ESTOP broadcast + servo
  torque-off. host_link: 7 channels (J1..J6,GRIP), 86 B STATE,
  LK_ARM_MOTOR 0x19, LKF_MOTOR_EN flag, MOTOR_EN_ON/OFF events with
  medr_t reason. CAN nodes {2,3} pinged at 200 ms round-robin,
  alive window 400 ms. fw_version 0x000200.
- **Joint driver** (new platformio.ini, disco_b_g431b_esc1):
  Tarot 4008 330KV (Kt 0.0289 [U], pp 7 [U]), 40:1, eff 0.7 [U],
  5 A phase cap [U]. AS5600 on motor shaft → multi-turn tracking via
  SimpleFOC shaft angle; commands/feedback in output radians.
  NMT_HOME = low-iq hard-stop homing with stall detect → zero at
  stop + SDO_HOME_STOP_RAD. NMT_ENABLE refused before calibrated
  AND homed. Calibration offset/direction + homed params persist in
  EEPROM.
- **robot-os**: config.py real geometry + ranges + rated torques +
  vel/acc caps; kinematics.py exact 6-joint FK chain + limit-checked
  IK (dual yaw candidates + elbow branches, tip-down convention);
  NEW gravity.py (part-mass torques, calibrated to FEA AB-pose
  moments, 0.5 kg payload) + max_payload() at 80 %-rated;
  planner gates every waypoint through torque_ok; arm/link/sim/cli
  7-channel + arm_motors() + MOTOR_EN flag semantics.
- **FEA cross-check**: gravity model reproduces the AB-pose analytic
  moments (J2 3.29 / J3 1.76 / J4 0.80 N·m incl. 0.5 kg payload);
  at full reach J4's allowed payload < 0.5 kg, matching the stage
  requirement (J4 1.75 vs 0.98 rated = over). Note: the FEA AB pose
  uses J2=+90° which exceeds the sim-documented J2 max of +70° —
  recorded, not silently corrected.

## Step 5 — builds (real output in docs/firmware-verification.md)

- base-node `esp32-s3-devkitc-1`: **SUCCESS** — RAM 6.0 %
  (19752/327680 B), flash 8.6 % (285885/3342336 B).
- joint-driver `disco_b_g431b_esc1`: **SUCCESS** — RAM 14.4 %
  (4728/32768 B), flash 38.8 % (50840/131072 B).
- Build env notes: PlatformIO venv in worktree; registry lacks the
  platform-manifest framework (~4.20801.0) on darwin; core 3.x
  (4.30000.0) breaks SimpleFOC (`enableTimerClock` signature) →
  pinned stm32duino **2.12.0** + framework-cmsis-dsp +
  `askuric/Simple FOC @ ^2.4.0`. Two failed environment attempts
  before this combination — inside the 3-attempt limit.

## Step 6 — tests

`python3 -m pytest tests` → **57 passed** incl. test_motor_en.py
driving the exact `motor_en.c` via ctypes (boot low, all gate
conditions, each drop cause, explicit re-arm). Full output in
`docs/firmware-verification.md`.

## Step 7 — docs

Updated: `can-protocol.md` (J2/J3 nodes, 40:1, NMT_HOME, STATUS b4,
homing SDOs, MOTOR_EN safety section + ESC-logic power caveat),
`host-protocol.md` (7 ch, ARM_MOTOR 0x19, 86 B STATE, LKF_MOTOR_EN,
drop-reason events), `bringup.md` (staged: relay/e-stop multimeter
proof → CAN heartbeat precondition → no-load spin → homing →
loaded), `firmware-verification.md` (real outputs), READMEs
(base-node, joint-driver, robot-os). Superseded banners added to
v1.1-era docs (build-notes, pcb-verification, STATUS-firmware,
architecture, torque-analysis). UNVERIFIED table above kept current.

## Stage W2 — two-phase MOTOR_EN arm (fixes the W1 deadlock)

Problem: the B-G431B-ESC1s are powered from `+12V_MOT`, dead until
K1 closes — but the W1 machine required all-ESC-heartbeats BEFORE
closing K1, so the arm could never arm.

Fix implemented exactly per the stage file:

- `firmware/shared/motor_en.c/.h`: two-phase arm. Phase 1 (pre-arm)
  needs only host handshake + alive + explicit `ARM_MOTOR` + estop
  released + no bus-off → closes K1, starts `esc_boot_window_ms`
  (default 1500 ms; a real param — `ESC_BOOT_WINDOW_MS` in
  `config.h`). Phase 2: every configured ESC must heartbeat inside
  the window else immediate drop, reason
  `MEDR_ESC_BOOT_TIMEOUT` (6); a fresh explicit `ARM_MOTOR` retries.
  Once `MEP_ARMED` the old rule is unchanged: estop / host timeout /
  bus-off / ESC fault / heartbeat lost (400 ms) drops at once.
  Estop/host-timeout/bus-off/ESC-fault also drop during the window.
- `firmware/base-node`: `safety_tick` feeds `now` to the machine;
  `medr_str` + `LKE_CAN_FAULT` mapping cover reason 6; `arm_estop`
  resets `phase` with the other mirrored fields.
- `firmware/joint-driver/joint_driver.ino` boot path re-checked
  against vendored SimpleFOC 2.4.0: `initFOC()` ends with an
  unconditional `enable()` and `loopFOC()` early-returns on
  `!enabled` — so `motor.disable()` now runs at the end of `setup()`
  (no PWM before NMT_ENABLE, incl. right after relay close). Same
  stale-enable cleanups: `do_calibrate()` disables after `initFOC`;
  homing success now ends `MODE_DISABLED` instead of `MODE_POSITION`
  (that "hold" never actually ran — `move()` is gated on `armed` —
  it only left a frozen voltage on the phases). NMT_ENABLE still
  refuses before calibrated+homed; `homed` is not persisted.
- **Servo-rail answer (pcb13):** bus-A servos (J1 STS3250 id 1,
  J4/J5/J6/GRIP STS3215) are on J4/J5 pin 2 = `+12V`, the
  **unswitched** post-F1 rail — `+12V_MOT` nets only K1.5/J18/J20
  (pcb13 STATUS net table). Servos are live at board power-on and
  need no boot-window ping; only the CAN ESCs are windowed.

Tests (`python3 -m pytest tests` in `software/robot-os`,
Python 3.9.12 / pytest 7.1.1): **62 passed** — test_motor_en.py grew
to 14 ctypes cases on the real `motor_en.c`: pre-arm closes K1 with
zero heartbeats, boot-window expiry drops `ESC_BOOT_TIMEOUT`,
heartbeat inside the window arms, loss after armed drops
`ESC_LOST`, estop during the window drops `ESTOP`, the window is a
settable param, all phase-1 refusals, explicit re-arm required —
plus every W1 drop case re-checked through the armed phase.

Builds (`pio run`, `.venv-pio`, real output in
`docs/firmware-verification.md`):

- base-node `esp32-s3-devkitc-1`: **SUCCESS** — RAM 6.0 %
  (19760/327680 B), flash 8.6 % (285969/3342336 B).
- joint-driver `disco_b_g431b_esc1`: **SUCCESS** — RAM 14.4 %
  (4728/32768 B), flash 38.8 % (50896/131072 B).

Payload note: the FEA full-reach pose uses J2 = +90°, over the sim
max of +70°. `max_payload` at the real-limit pose
`q=[0, +70°, −70°, 0,0,0]` (still fully horizontal — the worst
gravity case): overall bound 0.391 kg (J2-limited); **J4 allowed
payload = 0.487 kg** — identical to the +90° pose because J4's
downstream lever arm is horizontal in both; the <0.5 kg derating
still holds at the real worst case.

Fallbacks used: none. Open questions: none — the ESC-logic-feed
[U] row was removed (resolved by design: the drives boot off
`+12V_MOT` inside the window).
