# SOMA arm — final integration summary (arm-final2 / F2)

**What it is.** A 6-joint + gripper desktop robot arm, ~0.48× scale of the
reBot reference: J1 base yaw on a Feetech STS3250, J2 shoulder and J3 elbow
on 40:1 **printed cycloidal actuators** (PETG-CF discs, Tarot TL2955 4008
330KV + B-G431B-ESC1 + AS5600), J4 pitch on STS3250 and the **D6 K-KEEL
wrist** — J5 yaw on a dorsal-fin STS3215, J6 roll on a keel-mounted
STS3215, slim rail-frame parallel gripper on a 4th STS3215
(`wrist2/out` replaces the arm2b wrist; −43% printed wrist mass vs arm2b).
Coaxial one-way torsion balance springs at J2 and J3 (Springmasters 471671).
ESP32-S3 base node on CAN at 1 Mbps. Home "L" pose, J2→TCP reach ≈ 380 mm.

## Final limits (the safety contract — D4/F1/F2)

| Item | Value | Basis |
|---|---|---|
| Payload (rated) | **0.5 kg close-in / ~0.41 kg workspace-wide** — the J2 printed-disc cap binds first at full extension; 0.68–0.72 kg best-case under 0.27 m reach, ~0.46 kg at 0.36 m (level tool) | `gravity.max_payload` + F2 2774-pose sweep |
| J2 output torque cap | **3.0 N·m → 3.71 A phase** | `T = I × Kt(0.0289 [U]) × 40 × η(0.7 [U])` |
| J3 output torque cap | **2.0 N·m → 2.47 A phase** | same formula |
| Enforcement | ESC hard-clamps `CURRENT_LIMIT_A` (SDO + EEPROM clamped); base node pushes caps at boot; planner refuses over-cap waypoints | `joint_driver.ino`, `config.h`, `planner.py` |
| Output velocity cap | **0.5 rad/s** (20 rad/s motor ≈ 29 °/s) | `JOINT_VEL_LIMIT_OUT_RADS` |
| Soft stop | MOTOR_EN drop / E-stop / heartbeat loss ramps phase current to 0 over **75 ms**; 24 V relay cut stays independent | `ESTOP_RAMP_MS`, `start_softstop()` |
| Disc envelope | lobe SF ≥ 2 at cap (J2 2.21, J3 2.56 nominal @ design torque); ~10 of 41 pins share | cyclo4 |
| Cycloidal spec | NP=41, R=23.5, RP=1.5, E=0.42, CLR_TOOTH **0.01**, disc 4.25 mm, CLR_OUT 0.12 | D4 |

## Cost (GBP, BOM_FINAL_GBP.csv recomputed)

- **Verified + resolved lines: £674.07** — includes 3× STS3250 @ £136.15
  (Amazon UK B0FLJ6289C, in stock, rechecked 2 Nov 2026).
- **All-in including [U] estimates: £825.16.**

## Still [U] — bench-verify before/while running (see BUILD_GUIDE §checklist)

Pole pairs (7 assumed, 12N14P), Kt (0.0289), gear efficiency (0.7),
phase-current sensing, spring rate k≈0.55 N·m/rad, backlash, relay K1
cut, CAN 1 Mbps margin (fall back 500 kbps), AS5600 J8 pin order,
homing stop offsets. The **0.01 mm flank clearance** is below normal FDM
tolerance — print the coupon first (`final/out/coupon.stl`), pick the
station that measures closest to 0.01 mm real clearance, selective-fit
the 41 dowels, then print the 4 discs.

## Order blockers

Nothing blocking purchase — no buys were made (per stage rules). The
eBay STS3250 alternative stays as backup; Amazon UK is the decided
source (see `final/BOM_FINAL.md`).

## Run the simulation demo

```sh
cd software/robot-os
python3 -m pytest -q                      # 66 tests
python3 -m soma_arm.cli --sim demo        # TCP demo sweep, speed_scale 0.4
python3 -m soma_arm.cli --sim fk 0 0.4 0.6 0 0 0
python3 -m soma_arm.cli --sim sense       # joint state incl. motor_en flags
```

## Flash firmware

```sh
cd firmware/joint-driver
# edit joint_driver.ino top: DEVICE_CAN_ID 2 (J2) or 3 (J3); TQ_CAP_NM follows automatically
pio run -t upload                         # ST-LINK over USB-C, per node

cd firmware/base-node
pio run -t upload                         # ESP32-S3, UART-labeled USB port
```

## Artifacts

- `final/out/assembly.stl` (10.6 MB), `assembly.step.gz` → `gunzip` for
  the full-assembly STEP (34.1 MB; gzipped to stay under the 30 MB repo
  budget). Composed from arm2b posed parts + cad3 D2 overrides +
  2× cyclo4 actuator modules + the `wrist2/out` D6 wrist/gripper set
  replacing the arm2b wrist; cad3 parts were exported unposed and are
  re-posed here — see `export_assembly.py`.
- `final/out/coupon.stl` / `coupon.step.gz` — 4-station clearance coupon
  (0.00/0.05/0.10/0.15 mm), ~20 min print.
- `final/renders/{iso,front,side}.png` + `closeup_wrist.png` — Blender
  workbench renders of the home-pose assembly, verified visually
  (cyclo modules, K-KEEL wrist, gripper all seated; no floating parts).
- `PRINT_LIST.md`, `BOM_FINAL.md`, `BOM_FINAL_GBP.csv`, `BUILD_GUIDE.md`.
- `final2/STATUS-final2.md` — F2 merge + whole-arm validation report
  (collision, MuJoCo, IK, torque tables).
