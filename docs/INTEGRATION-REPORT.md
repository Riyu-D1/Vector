# Integration report — SOMA ARM v3 (`arm-integrated`)

Merged: `arm-rebuild` + `arm-actuator` + `arm-firmware`. Both merges
were clean. Nothing was merged to `main`. Verified state below is real
test output; anything the checks could not prove is marked UNVERIFIED.

## Verdict

- **Ready to print:** yes. All 37 printed parts (2 case + 14 arm +
  3×7 actuator) are watertight, fit-checked and within a 220 mm bed.
  Print orientations: `cad/arm/export/print/` + actuator-verification
  §6. Full list: `BUILD.md`.
- **Ready to flash:** code-complete, **UNBUILT**. Both firmwares
  (ESP32-S3 base node, B-G431B-ESC1 joint driver) are written and
  host-side-tested where possible, but no toolchain exists on this
  machine — they have only been syntax-checked. Flash + bring-up per
  `docs/bringup.md` on a machine with PlatformIO/STM32duino.
- **Ready to build:** yes, against the UNVERIFIED table in `BUILD.md`
  (pole-pair count, J8 pin order, module terminators, etc.).
- **Ready to run:** not yet — hardware bring-up has never happened.

## What the integration changed

### Single source of truth for geometry/limits (Task 1)

`cad/arm/arm_params.py` now carries a `KinSpec` (`KIN`): J2 axis z=146,
links 120/100 mm, J4→tip 127.7 mm, home all-zeros, guard constants.
`parts.py` consumes `KIN` directly; `cad/arm/gen_params.py` (stdlib
only) emits:

- `software/robot-os/soma_arm/arm_geometry.py` — host constants
- `firmware/shared/arm_params_gen.h` — firmware constants (C and C++)

`config.py`, `kinematics.py`, `planner.py`, `sim.py`, base-node
`config.h`/`main.cpp`, and `joint_driver.ino` all consume the generated
values. The placeholder geometry (BASE_Z=70, L3=40, ±150° limits) is
gone everywhere.

Sign convention is handled once, in the generator: CAD pitch is
down-positive about +Y, host pitch is up-positive. Host limits are the
sign-flipped CAD ranges; the CAD guard `J3 ≤ 45 − 2·J2` becomes host
`q3 ≥ −45 − 2·q2`.

### Joint limits (adopted, verified by CAD mesh sweeps)

| joint | CAD frame | host frame |
|---|---|---|
| J1 | ±170° | ±170° |
| J2 | **−70..+35** (was −15..+30) | **−35..+70** |
| J3 | ±90° | ±90° |
| J4 | ±95° | ±95° |
| J5 | ±160° | ±160° |
| J6 | ±90° (servo shaft) | ±90° |

### J2 range decision (Task 2)

Target was ≥ −60..+90. Result: **−70..+35 CAD is the practical
maximum; +90 is architecturally impossible.**

- Exported-mesh sweeps (the real `checks.py` pipeline) measured clean
  travel to **−72°** (first hit −75 vs `turret_cap`) and **+36°**
  (first hit +37 vs `bearing_cap`/housing). Adopted −70..+35 for
  margin. The documented −15..+30 was conservative.
- At +90 the J3 actuator body and link chain fold into the Ø110 mm
  base housing / bearing-cap zone — the collision is the *actuator
  envelope*, not trimmable plastic.
- Raising the J2 axis was tried: J2_Z 146→166 mm only moved the down
  boundary +37→+40. Extrapolating the geometry, +90 needs J2_Z ≈
  +110 mm (≈256 mm axis) — an ~11 cm taller turret, rejected.
- Net: the −60 leg is met with margin; the +90 leg is documented
  impossible with this base/turret architecture. Home pose, reach
  (~348 mm) and torques all re-verified at the new range: 22/22.

### Guard verification and the c7 fix

- `checks.py` c7 sampled `j3=0` even where the guard forbids it
  (J2 ≥ 26 → `j3_max < 0`) — that was the only 21/22 failure after the
  range change. The check now samples inside the guard envelope plus
  its boundary. Result: **22/22**.
- Boundary sweep across the new J2 range (5° grid, J4=−60): every
  violation sits strictly above `J3 = 45 − 2·J2` with ≥20° margin —
  the guard line itself is sound over the widened range.
- **Documented limitation:** the guard was measured for the canonical
  wrist fold (J4=−60 CAD). With J4 pitched down (+60..+95 CAD), poses
  *inside* the guard can still put the gripper nose below the table
  plane — e.g. J2=+18, J3=+9, J4=+60 → nose z≈−65 mm — and one
  boundary corner (J2=−22, J3=+89, J4=+60) grazes the case lid
  (~180 mm³). This exposure predates the range change and is inherent:
  the gripper must reach the table to manipulate. Treat deep wrist-down
  folds near the table as an operator/planner concern, not a firmware
  guarantee. `UNVERIFIED` how the host planner should penalise them.

### Firmware now consumes the shared limits (Task 3)

- `firmware/shared/arm_params_gen.h` holds limits, home, guard
  constants and link geometry — generated, compiles as C and C++.
- Base node: `arm_clamp_q()` clamps all 6 joints then raises q3 onto
  the guard boundary (never moves q2). Applied on `SET_JOINT_POS`
  (`host_link.cpp`) and inside the jog integrator (`joint_update`),
  which also zeroes a q3 jog that would cross the boundary.
- At boot the base node pushes `CURRENT_LIMIT_A` (3/5/5 A) and
  `POS_LIMIT_LO/HI` from the generated table to each driver by SDO.
- Joint driver: EEPROM-default `pos_lo/pos_hi` come from the same
  table, indexed by its CAN id (J1=1…J3=3); RPDO2 targets are clamped
  to them. A driver flashed standalone (no base node) still gets the
  right limits.
- Protocol docs updated (`docs/can-protocol.md`, `host-protocol.md`):
  units unchanged (rad at the output shaft); the real envelope and
  where the guard lives are now written down. J6 documented as the
  servo shaft.

### IK yaw-hypothesis fix (found during integration)

`kinematics.ik()` assumed the tip lies at +r in the arm plane. With
J2 able to pitch to +70°, the wrist can fold *behind* the shoulder,
putting the tip at −r (yaw off by π). The solver now tries both yaw
hypotheses; 500-sample FK→IK→FK round-trip went 18 fails → **0**.

## Test results (real output)

- `cad/arm/checks.py`: **22/22 PASS** (watertight, servo fit,
  interference, ROM sweeps over the new ranges, table/lid under the
  guard, reach 348 mm, mass 2379 g, torques, bed size, fastener table,
  cable paths).
- `software/robot-os` pytest: **41 passed** (FK/IK round-trips, limits,
  guard, planner rejection, CAN codec ctypes cross-check, Feetech
  vectors, link frames, sim estop).
- `firmware/shared` codecs: C round-trip harness — passed earlier on
  `arm-firmware`; `arm_params_gen.h` compile-checked standalone.
- Firmware builds: **UNBUILT** — see above.

## Unbuilt / unverified

- No hardware exists yet; no motor has spun; nothing is calibrated.
- Firmware binary verification pending a toolchain.
- The J4-down table exposure above.
- Everything in `BUILD.md`'s UNVERIFIED table (mechanical fits on
  arrival, module pinouts, servo current draw).

## Files of record

- Params: `cad/arm/arm_params.py` (`KIN`, `JOINTS`), `gen_params.py`
- Generated: `soma_arm/arm_geometry.py`, `firmware/shared/arm_params_gen.h`
- Checks: `cad/arm/checks.py`, `docs/arm-verification.md`
- Build: `BUILD.md`, `docs/power-budget.md`, `docs/bringup.md`
