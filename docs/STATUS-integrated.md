# STATUS — integrated build (branch arm-integrated)

Tracks the merged state of arm-rebuild + arm-actuator + arm-firmware.
Never merge to main. Deadline 31 Oct 2026. Updated every push.

## Current state

| piece | state |
|---|---|
| Merge | `arm-actuator` + `arm-firmware` merged clean onto `arm-rebuild` |
| Params | `cad/arm/arm_params.py` is the single source; `gen_params.py` emits host + firmware constants |
| CAD checks | **22/22 PASS** (incl. widened J2 sweep −70..+35) |
| Host tests | **41/41 PASS** (pytest, `software/robot-os`) |
| Firmware | code-complete, **UNBUILT** (no toolchain on this machine) |
| Hardware | nothing assembled or powered — bring-up pending |
| Docs | `BUILD.md`, `docs/power-budget.md`, `docs/INTEGRATION-REPORT.md`, protocol docs updated |

## Integration decisions

- **Kinematics/limits unified.** `KinSpec` in `arm_params.py` (J2_Z
  146, links 120/100, J4→tip 127.7, home all-zero, guard 45/2) feeds
  CAD parts, host kinematics and firmware via generated files. Pitch
  sign flip lives only in the generator.
- **J2 range adopted: −70..+35 CAD (−35..+70 host).** Measured clean
  envelope −72..+36; the old −15..+30 was conservative. +90 down is
  architecturally impossible (J3 actuator hits the Ø110 housing; would
  need J2_Z ≈ +110 mm). Details in `docs/INTEGRATION-REPORT.md`.
- **Guard enforced at three levels:** CAD c7 check, host
  `config.guard_clamp`/`within_guard` (kinematics + planner), firmware
  `arm_clamp_q` (position cmds + jog integrator).
- **Driver soft limits:** base node pushes generated `POS_LIMIT_LO/HI`
  + `CURRENT_LIMIT_A` (3/5/5 A) by SDO at boot; the joint driver's
  own EEPROM defaults come from the same generated table by CAN id.
- **IK fix:** both yaw hypotheses (+r/−r arm plane) — 500-sample
  round-trip failures 18 → 0.
- **c7 check fix:** samples clipped to the guard envelope — a checked
  pose must be firmware-reachable.

## Known limits (honest)

- J4 wrist-down poses inside the guard can still reach the table/lid
  near the boundary (guard was measured at J4=−60). Inherent — the
  gripper must reach the table — documented, not a regression.
- Reach is ~348 mm vs the brief's 260 mm (real wrist stack is
  J4→tip = 128 mm). Payload 250 g still verified.
- Wrist cluster 220 g vs 180 g spec — waived upstream (3×STS3215
  minimum).
- Firmware binaries unbuilt; hardware UNVERIFIED list in `BUILD.md`.

## Next actions (in order)

1. Flash `firmware/joint-driver` ×3 (CAN ids 1–3, `CAN_TERM_LAST` on
   the last) and `firmware/base-node` on a machine with the toolchains.
2. Run `docs/bringup.md` stages 0–4; measure the `BUILD.md` UNVERIFIED
   table while assembling.
3. Log bus current (TPDO3 + VSNS) during stage-4 moves; update
   `docs/power-budget.md` with real numbers.
