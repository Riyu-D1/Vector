# SOMA arm — knuckle redesign V5 (brushless) — shared spec for Devin

Read this whole file once before any stage. Then do ONLY the stage file you were given
(`~/Vector/stages/SN_*.md`). Every number below is tagged:
- **[S]** SOURCED — from a vendor file (path given) or measured from a vendor STEP mesh by the tested helper code.
- **[D]** DESIGN — chosen by the designer and checked by the tested gate scripts (gate.py / cable.py / rom.py).
- **[U]** UNVERIFIED — best guess. Never "fix" a [U] value by inventing a new number; write it in STATUS instead.

## 0. Hard rules (read twice)
1. Git: use `/usr/bin/git` only. Branch `arm-knuckle` only. Never merge, rebase onto, or push to `main`. Never `--force`.
2. Work dir is the worktree `~/Vector-wt/knuckle` (made from `arm-integrated` @2eeda06). Never edit files in `~/Vector` (main checkout); it is read-only for you.
3. One commit per stage, message exactly as the stage file says, then `git tag stage-N-done` and `/usr/bin/git push origin arm-knuckle --tags`.
4. Disk: never commit `out/`, `renders/*.png` bigger than 1.5 MB, `*.stl`, `.venv`, `__pycache__`. Keep total new files under 30 MB. Delete scratch files.
5. Time box: a single problem gets at most 20 minutes OR 3 attempts. Then use the fallback that the stage file names, write what happened in `docs/STATUS-knuckle.md`, and continue.
6. Never invent a dimension. Every number you need is in `cad/knuckle/kp.py` (copied in S1). If a number is missing: stop that step, write `BLOCKED: <what>` in STATUS, continue with the next step.
7. The geometry code in `~/Vector/stages/code/` is TESTED. Copy it verbatim. Do not "improve", reformat, rename, or re-order it. Only change a value when a stage step tells you the exact old and new text.
8. Python for CAD: `PY=/Users/deepakdiwan/soma/.venv/bin/python` (build123d 0.13.0, trimesh, manifold3d). Python for tests: `python3` (anaconda, has pytest). Blender: `/usr/local/bin/blender` (4.5).
9. Do not launch other agents, do not install packages, do not send messages.
10. If a command prints something different from "Expected", re-run it once. If still different: follow the stage's "If not" line. Never edit the expected text to match.

## 1. Frames and layout
- G frame (world, mm): origin = centre of the drum recess floor on the existing case lid = case.py point (75, 88, 37.5) [S cad/lib/case.py: DRUM_CX, DRUM_CY = 75, 88; lid top 37.5]. +X = arm forward, +Z = up.
- Home pose = arm straight forward, horizontal; all joints 0.
- Joint axes (home): J1 = Z through (0,0); J2 = Y through (x 0, z 150); J3 = Y through (150, 150); J4 = Y through (280, 150) (wrist pitch); J5 = X through (y 0, z 150) (wrist roll); J6 = Y through (388.61, 162) (gripper jaw). [D]
- Zig-zag layout: J2 actuator sits in the turret knuckle (+Y side, y −24.2..35.6); upper arm is on −Y (y −25..−79.8); forearm comes back to +Y (y −24.2..29.8); tool centre point TCP = (438.61, 0, 150). [D]
- Link lengths: J2→J3 150, J3→J4 130, J4→TCP 158.61 [D]. Reach from J1 axis ≈ 439 mm.
- Joint limits (degrees, + = right-hand rule about the axis, for J2/J3/J4 + = tip down): J1 ±170, J2 −70..+35, J3 −135..+90, J4 ±95, J5 ±160, J6 −35..0 [D, checked by rom.py in S7].

## 2. Actuators (5-DOF + gripper) — user OK pending on "5 DOF"
| Joint | Part | Key numbers | Source |
|---|---|---|---|
| J1 base yaw | Steadywin GIM4305-10 | body Ø53, output face Z 51, back face Z 23.0, cap Ø40 to Z 18; output 3×M3 PCD27 @29/149/269°; back 6×M2.5 PCD47.5 @31°+60k | [S] cad/vendor/GIM4305-10.STEP + GIM4305-10-2D.pdf; Z 23.0 measured from mesh |
| J2 shoulder | Steadywin GIM4310-36 | body Ø55, output face y −25, raised ring Ø20..Ø28 to y −27.5, back face y 17.3, cap Ø40 to y 22.8; output 3×M3 PCD27 @2/122/242°, 3× Ø4 pins PCD24 @62/182/302°; back 6×M3 PCD48 @21°+60k | [S] cad/vendor/GIM4310-36.STEP + -2D.pdf; ring + back face measured from mesh; screw PCD vs ring [U] |
| J3 elbow | Steadywin GIM4310-10-GDS | body Ø53, output face y −24.2, back y −57.0, cap Ø40 to y −63.2; output 3×M3 PCD27 @29/149/269°; back 6×M2.5 PCD47.5 | [S] cad/vendor/GIM4310-10-GDS.stp + -2D.pdf |
| J4 wrist pitch | Feetech STS3215 (12 V variant) | body 45.2×24.7×35.7; horn Ø19.2, face 9.6 above origin; horn 4×M3 PCD14 | [S] cad/arm/reference/sts3215_servo.step, cad/vendor/sts3215.pdf; 12 V variant [U] |
| J5 wrist roll | STS3215 | same | same |
| J6 gripper | STS3215 | same | same |

- Torques [S datasheets in cad/vendor/*-2D.pdf as summarised in kp.py]: rated 1.0 / 7.38 / 2.05 N·m, peak 3.47 / 20.16 / 5.6 N·m (J1/J2/J3). STS3215 stall 2.94 N·m at 12 V [U].
- Estimated static holding at full reach with 200 g payload [D]: J2 ≈ 2.6 N·m (35 % rated), J3 ≈ 1.2 N·m (≈ 60 % rated), J4 ≈ 17 % stall. Gate: ≤ 70 % of rated.
- Masses [S]: 4305-10 150 g, 4310-10 227 g, 4310-36 310 g, STS3215 55 g.

## 3. Parameters
All numbers live in `cad/knuckle/kp.py` (copied from `~/Vector/stages/code/kp.py`). Highlights:
| Name | Value | Tag |
|---|---|---|
| WALL / MIN_WALL | 2.4 / 1.6 | [D] |
| CLR (rotating gap) / SLIP (servo pocket per side) / PRESS (plug oversize on Ø) / FACE_GAP | 0.3 / 0.15 / 0.05 / 0.8 | [D] |
| M3 clear / tap-fit / counterbore | 3.4 / 3.3 / Ø6.2×3.2 | [D] |
| M2.5 clear 2.9; M2 pilot 1.6 / clear 2.4; M4 4.4 / cb Ø8.4×4.2; M3 insert Ø4.6×6; magnet pocket Ø6.2×3.2 | | [D] |
| Base bearing | 6812 (60×78×10) at Z 64..74, seat Ø77.95 | [S ISO 15] / [D] |
| Drum | skirt Ø131.4 Z 0..10; drum Ø96/91.2 Z 0..74; J1 bulkhead Z 18.6..22.6 | [D] |
| Turret | hub Ø59.9 Z 51..56; hat Ø102 Z 80..87; column Ø58 (cy 4) Z 80..150; knuckle Ø76, y −24.2..33 | [D] |
| Upper arm | R 38 at J2, R 33 at J3, y −25..−74.8; cover y −74.8..−79.8 (magnets) | [D] |
| Forearm | cap Ø66 y −24.2..29.8; tube Ø54/49.2 to x 298.6 | [D] |
| Head (J4 output) | cup Ø50 y 30.6..38.6; pod x 316.4..366.65 | [D] |
| Gripper | body x 368.6..404.72, finger to x 448.61 | [D] |
| GIM CAN | 1 Mbit in old firmware; GIM default 500 kbit/s | [U] check GIM-protocol.pdf |
| GIM plug room behind cap | 8 mm | [U] |
| STS3215 plug zone | (−22..−11, −40.2..−28, ±9) servo frame | [U] |

## 4. Part list (all build123d primitives: Box via gbox/sbox, Cylinder via xcyl/ycyl/zcyl, extruded polygon via yprism; booleans + and −)
| STL stem | File (function) | Stage | Print orientation | Supports |
|---|---|---|---|---|
| drum | p_base.drum | S1 | skirt down | none |
| drum_cap | p_base.drum_cap | S1 | flat | none |
| turret | p_base.turret | S1 | hat down (flip Z) | tree, only knuckle underside + column void |
| kn_endcap | p_base.kn_endcap | S1 | disc down | none |
| upper_arm | p_upper.upper_arm | S2 | open side (−Y) up, +Y wall on bed | none |
| upper_cover | p_upper.upper_cover | S2 | flat | none |
| forearm | p_fore.forearm | S3 | +Y face (y 29.8) on bed | tree, tube bore + blister |
| fa_endcap | p_fore.fa_endcap | S3 | disc down | none |
| fa_elbow_cap | p_fore.fa_elbow_cap | S3 | flat | none |
| head | p_wrist.head | S4 | cup face (y 38.6) on bed | tree, pod pocket |
| cup_cap, pod_front | p_wrist | S4 | flat | none |
| gripper | p_grip.gripper | S4 | open side (y −18) up | none |
| grip_lid, jaw, jaw_cap | p_grip | S4 | flat / plate down | grip_lid: tree inside bump |
Vendor solids for checks only (never printed): vendor_J1..J3 (GIM STEP), vendor_J4..J6 (STS3215 STEP).
Every part's largest size is ≤ 240 mm (A1 bed 256) — checked by gate.py.

## 5. Fasteners (buy list) [D]
- J1 output→turret: 3× M3×5 socket head (hub counterbore). J1 back→drum bulkhead: 6× M2.5×6.
- J2 back→knuckle bulkhead: 6× M3×8 + washer. J2 output→upper arm: 3× M3×6 + 3 dowel pins Ø4 (vendor).
- J3 back→upper arm bulkhead: 6× M2.5×6. J3 output→forearm: 3× M3×6.
- Drum to case: 3× M4×12 into existing case posts. Drum cap: 4× M3×8 into M3 heat-set inserts.
- Servo horns (J4, J5, J6): 4× M3×6 each (from the part side, counterbored, hidden by caps).
- pod_front: 4× M2×6 self-tapping. grip_lid: 4× M2×6 self-tapping. (visible — flag to user)
- Magnets: 8× 6×3 mm disc (upper arm + cover). Bearing: 1× 6812-2RS.

## 6. Hidden-everything rules
- No cable is visible in any of the 6 renders. Cable routes (checked by cable.py): base notch → drum → J1 bulkhead slot → spigot slot → column → riser → knuckle cavity → tunnel → J2 groove (over the top) → upper arm → J3 notch → forearm groove → forearm tube → pass → J4 plug zone → channel → cup groove → P1/P2 → pod channel → pod_front hole → gripper groove → slot → J6 plug.
- Only exception allowed: ≈12 mm of cable at the gripper lid rear [U, flag to user].
- All horn screws sit under a press-fit cap (cup_cap, jaw_cap) or inside a closed part.
- No screw head outside except: 3× M4 under the drum skirt (hidden by the case), pod_front M2 ×4 and grip_lid M2 ×4 (flagged).

## 7. Verification tools (copied in S1, tested)
- `$PY build.py [names]` → writes `out/<name>.stl`, prints `<name>: bbox=(xmin, xmax, ymin, ymax, zmin, zmax) vol=<cm3>`.
- `$PY gate.py out/*.stl` → per-part `watertight / bbox / minwall`, `INTERF a x b`, `PRESS a x b ... ok`, last line `GATE PASS` or `GATE FAIL`.
- `$PY cable.py` → `CABLE PASS` / `CABLE FAIL`.
- `$PY rom.py [J2 ...]` → `ROM PASS` / `ROM FAIL` and the safe range per joint.
- `$PY selftest.py` → frame self-test (vendor bboxes).
- Blender: `/usr/local/bin/blender -b -P render_blend.py -- renders/<prefix> list.txt` (list lines: `out/x.stl r g b`) → prints `WROTE …` 6 times (frontiso, backiso, side, top, front, cutaway).
- Blender review: at least 3 iterations per stage that renders: render → open each PNG (Read tool) → write 1 line per view in STATUS (what you see, any visible cable/screw/gap) → if a problem is visible, fix only via the stage's fallback list → re-render.

## 8. Print rules (Bambu A1, PLA or PETG)
- 0.4 nozzle, 0.2 layer, 4 walls, 25 % gyroid, 5 top/bottom layers. Structural parts (turret, upper_arm, forearm, head, gripper): 6 walls, 40 %.
- Max part size 240 mm. Supports only where the part list says. Press caps: print, test-fit, sand if too tight.

## 9. Docs to write
- `cad/knuckle/BUILD.md` (S7): part list, print settings, fastener list, assembly order (base up), cable routing order, wiring table.
- `docs/STATUS-knuckle.md` (every stage, last step): append a section `## Stage N — <date>` with: gate lines (copy the PASS/FAIL lines), files changed, any [U] value hit, any fallback used, open questions for the user.

## 10. Reuse from arm-integrated (do not rewrite)
- `cad/lib/case.py` (case, posts, rear channel) — the drum sits in the existing drum recess.
- `cad/arm/reference/sts3215_servo.step`, `cad/arm/arm_params.py`, `cad/arm/gen_params.py` (single source → `software/robot-os/soma_arm/arm_geometry.py` and `firmware/shared/arm_params_gen.h`).
- `firmware/base-node` (ESP32 TWAI CAN) and `firmware/shared` codecs; `software/robot-os` tests (`41 passed` before S6).

## 11. Firmware (S6 only) — GIM CAN protocol replaces the custom ESC firmware
Source: `cad/vendor/GIM-protocol.pdf` [S]; frame layouts below are what the designer read from it; the test vectors were computed from these layouts.
- Bus: J15 wiring unchanged (CAN H/L + 24 V). Bit rate 500 kbit/s [U — check pdf; if it says 1 Mbit keep 1 Mbit].
- Frame: standard ID = motor CAN id (J1=1, J2=2, J3=3), DLC 8, unused bytes 0.
- Commands (byte 0): 0x91 start/enable, 0x92 stop/disable, 0x93 torque-ish current (f32 + u16 ms), 0x94 speed (f32 rad/s + u24 ms), 0x95 position (f32 rad + u24 ms), 0x97 e-stop, 0xB3 clear errors, 0x83 config write.
- Reply: b0 cmd echo, b1 error flags [U], b2 temperature, b3..4 position u16 LE, b5..7 speed u12 + torque u12. pos = u·25/65535 − 12.5 rad; speed = u·130/4095 − 65 rad/s; torque = ktg·(u·450/4095 − 225) N·m [U: ktg = output Kt 0.62/3.46/0.96]. Test vectors in code/fw/test_gim_proto.py are the spec.
- Driver mapping (keep the can_bus.h API): pdo2(node,pos,vel) → 0x95; pdo3 → no-op; sdo → no-op returning OK; enable → 0xB3 then 0x91; disable → 0x92; estop → 0x97 then 0x92; poll nodes in turn, wait ≤ 3 ms, attribute a reply to the last node sent to.

## 12. Common mistakes (Devin, check this list before every commit)
1. Running CAD with `python3` instead of `$PY` → `ModuleNotFoundError: build123d`.
2. Running pytest with `$PY` → `No module named pytest`. Use `python3 -m pytest -q` in `software/robot-os`.
3. Editing tested code "to make it cleaner". Don't.
4. Committing `out/` or STLs. `git status --short` must show only the stage's files.
5. Changing a number in kp.py to make a gate pass without the stage telling you. Write STATUS instead.
6. Forgetting `cd ~/Vector-wt/knuckle/cad/knuckle` before `$PY build.py` (paths are relative).
7. Using `git` instead of `/usr/bin/git`.
8. Pushing to main or merging. Only `origin arm-knuckle`.
9. Rendering at higher resolution (disk). Keep render_blend.py as is.
10. Treating a vendor (`vendor_*`) watertight=False as an error — it is expected.
