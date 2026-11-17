# Stage A2b — reBot wrist J4–J6 (3× STS3215) + STS3215 gripper, on the A2a arm
> Before you start: you already read `~/Vector/ARM_KNUCKLE_V5.md`. Rules 0.1–0.10 apply, with these overrides for this stage only:
> (a) branch is `arm-arm2b` (made from tag `arm-2a-done` = `77bb073` on `arm-arm2`), worktree `~/Vector-wt/arm2b`; never commit, push or tag on `arm-arm2`, `arm-actuator2*` or `arm-knuckle`;
> (b) every number lives in `cad/arm2b/ap2b.py`; rule 0.6 applies to ap2b.py. The code is a tested bundle: you copy it (step 2) and run it. You type no geometry and edit no `.py` file;
> (c) status file is `docs/STATUS-arm2b.md` (new file).
> Work dir: `~/Vector-wt/arm2b/cad/arm2b`. Type first in every new shell: `export PY=/Users/deepakdiwan/soma/.venv/bin/python`.
> "Expected" = output must match (numbers ±0.05 unless stated). If not: re-run once, then do the "If not" line.
> Do NOT edit by hand: `cad/knuckle/*`, `cad/act2/*`, `cad/arm2/*`, `cad/arm2b/*.py`, `cad/arm2b/rebot_src/*`, any file in `~/Vector/stages/` (read only).

**Goal:** the wrist (J4 pitch, J5 yaw, J6 roll, each a Feetech STS3215) and an STS3215-driven rack-and-pinion gripper as printable parts (STEP + STL) on the A2a arm, passing `arm2b_checks.py` (reach, holes, gripper stroke, torque, ROM) and `gate.py` on the whole arm (watertight, bbox ≤ 240, minwall ≥ 1.60, no INTERF at the home pose), then renders, status, commit, tag `arm-2-done`, push.
**Why:** keep the reBot wrist layout and its exposed, minimal links, slim, at 0.48 span: J4→J5 37.6, J5→J6 19.2, J6→TCP 75.0 (J4→TCP 131.8, reach 374.9). The DM4310 wrist motors are too heavy for our printed J2/J3 actuators; 4× STS3215 (55 g) keep J2 at 2.36 N·m. The designer ran the whole bundle on this Mac (literal outputs below).
**Inputs (read only):** `~/Vector/stages/code/arm2b/` (tested bundle: `ap2b.py`, `p_arm2b.py`, `build_arm2b.py`, `arm2b_checks.py`, `NOTICE.md`, `BOM.md`, `rebot_src/` = 2 reBot STEP parts `02_Rack_U`, `02_Rack_D` re-exported unchanged in their assembly position from `reBot_B601_DM_v1.1_20260425.step`, reBot commit `13bebbf`, CERN-OHL-W-2.0), `cad/arm2/` (A2a, imported by the bundle), `~/Vector/stages/ref/rebot-adapt2.md`.

## 0. What the bundle does (for your understanding; all numbers are already in ap2b.py)
| Item | reBot (DM4310 wrist, metal) | A2b |
|---|---|---|
| Frame | — | parts drawn in a wrist frame W (a = tool direction, b = world Y, h = up at home, origin on the J4 axis), moved to the reBot rest frame, then posed like A2a `fo`. At home W = world moved to J4 (96.4, 0, 216.2) |
| Forearm J4 end | Ø38 DM4310 pilot in `03_Link3` | A2a `fore_l`/`fore_r` rebuilt as `fore_l2`/`fore_r2`: Ø38 plugged; `fore_r2` gets 4× Ø3.4 for `j4_cradle` |
| J4 (pitch, axis Y) | DM4310 | STS3215 in printed `j4_cradle` (pocket +0.15/side, 2.5 walls, 4× M3 from fore_r2), horn face at b −26.6 |
| J4→J5 | `02_Wrist_Bracket` + `Lower_Wrist_Link_L/R`, 78.3 | one printed `link4`: 4 mm horn plate (R14 end, 4× Ø3.4 PCD14 + Ø6.2 counterbores + Ø7 recess) + J5 servo pocket with a lightening window, **37.6** |
| J5 (yaw, vertical at home) | DM4310 | STS3215 on top, horn down at h 14.61, case end exposed past b 30 |
| J5→J6 | `03_Link5`, 40 | printed `link5`: 4 mm horn plate on the J5 horn + cheeks round the J6 servo, **19.2** to the J6 frame; J6 horn face at a 63.0 (so the J6 plug clears the J4 servo) |
| J6 (roll, tool axis) | DM4310 | STS3215, horn forward |
| Gripper | DM motor + MGN9 rail + m1 16T gear + 2 racks + 2 fingers | `grip_frame` (J6 horn plate, gripper STS3215 pocket, bracket, rack channels with lips), gripper STS3215 on the tool axis, m1 16T gear (Ø18 × 6) on its horn, reBot `02_Rack` cut to 36 mm, flat 4 mm fingers `finger_u`/`finger_d`, tips = TCP at J4 + **131.8**, stroke 25 (gap 2 → 27) |
| Not in A2b | — | covers, handle, camera, cable guides |

## 1. Steps (in this order)
1. Command: `cd ~/Vector-wt/arm2b && /usr/bin/git branch --show-current && /usr/bin/git log --oneline -1 && /usr/bin/git status --short`
   Expected: `arm-arm2b`, then `77bb073 A2a: reBot-DevArm J1-J3 around the printed actuator (0.48 span, flat 4 mm plates, STS3250 J1)`, then nothing (or only `?? cad/arm2/out/` / `?? cad/act2/out/`). If not: STOP, `BLOCKED: worktree`.
2. **Copy the bundle** (ONCE): `mkdir -p ~/Vector-wt/arm2b/cad/arm2b && cp -R ~/Vector/stages/code/arm2b/. ~/Vector-wt/arm2b/cad/arm2b/ && cd ~/Vector-wt/arm2b/cad/arm2b && ls && ls rebot_src/*.step | wc -l`
   Expected: `BOM.md NOTICE.md ap2b.py arm2b_checks.py build_arm2b.py p_arm2b.py rebot_src` and `2`.
   Then: `$PY -c "import ap2b as B; print(B.A_J5, B.A_J6, B.A_TCP, B.A6_FACE, B.AG_FACE, B.SERVOS['j4'][0], B.STS3215_RATED, B.ROM_MIN)"` → `37.6 56.8 131.8 63.0 111.0 (0.0, -17.0, 0.0) 0.98 {'J4': 140.0, 'J5': 140.0, 'J6': 360.0}`. If ImportError on `ap2` or `ap`: STOP, `BLOCKED: cad/arm2 or cad/act2 missing` (wrong base commit).
3. **Build** (about 20 s): `rm -rf out && $PY build_arm2b.py 2>&1 | grep -v Warning`
   Expected exactly these 39 lines, no Traceback:
   ```
base_plate           fix bbox 140.0 x 200.0 x 14.0  vol 385.5 cm3  wt True
base_link            fix bbox 92.0 x 92.0 x 63.7  vol 243.5 cm3  wt True
j1_cradle            fix bbox 57.5 x 57.5 x 54.5  vol 104.2 cm3  wt True
vendor_sts3250_j1    fix bbox 45.2 x 24.7 x 49.8  vol 42.9 cm3  wt True
base_reinf           fix bbox 92.0 x 92.0 x 7.0  vol 27.3 cm3  wt True
yaw_limit            fix bbox 77.0 x 77.0 x 7.1  vol 13.2 cm3  wt True
link1                fix bbox 83.8 x 77.3 x 84.1  vol 42.6 cm3  wt True
front_spacer_j2      fix bbox 34.8 x 4.0 x 34.8  vol 2.8 cm3  wt True
flange_j2            fix bbox 34.8 x 9.8 x 34.8  vol 5.2 cm3  wt True
vendor_actout_j2     fix bbox 44.0 x 2.9 x 44.0  vol 1.0 cm3  wt True
vendor_act_j2        up  bbox 57.0 x 54.4 x 57.0  vol 138.8 cm3  wt True
back_spacer_j2       up  bbox 57.0 x 4.7 x 57.0  vol 9.5 cm3  wt True
vendor_6803_j2       up  bbox 26.0 x 5.0 x 26.0  vol 1.5 cm3  wt True
upper_out            up  bbox 61.0 x 7.0 x 187.7  vol 18.9 cm3  wt True
upper_back           up  bbox 61.0 x 4.0 x 187.7  vol 27.6 cm3  wt True
vendor_act_j3        up  bbox 57.0 x 54.4 x 57.0  vol 138.8 cm3  wt True
back_spacer_j3       up  bbox 57.0 x 4.7 x 57.0  vol 9.5 cm3  wt True
vendor_6803_j3       up  bbox 26.0 x 5.0 x 26.0  vol 1.5 cm3  wt True
front_spacer_j3      fo  bbox 34.8 x 5.0 x 34.8  vol 3.6 cm3  wt True
flange_j3            fo  bbox 34.8 x 10.8 x 34.8  vol 6.0 cm3  wt True
vendor_actout_j3     fo  bbox 44.0 x 2.9 x 44.0  vol 1.0 cm3  wt True
dogleg_l             fo  bbox 76.2 x 5.0 x 99.0  vol 19.4 cm3  wt True
dogleg_r             fo  bbox 76.2 x 5.0 x 99.0  vol 19.4 cm3  wt True
fore_l2              fo  bbox 171.6 x 4.0 x 57.0  vol 23.9 cm3  wt True
fore_r2              fo  bbox 171.6 x 4.0 x 57.0  vol 23.8 cm3  wt True
j4_cradle            fo  bbox 38.0 x 52.5 x 30.0  vol 28.7 cm3  wt True
vendor_sts3215_j4    fo  bbox 45.2 x 49.3 x 24.7  vol 42.8 cm3  wt True
link4                w4  bbox 66.6 x 60.6 x 69.1  vol 29.8 cm3  wt True
vendor_sts3215_j5    w4  bbox 24.7 x 45.2 x 49.3  vol 42.8 cm3  wt True
link5                w5  bbox 38.0 x 30.0 x 34.6  vol 11.2 cm3  wt True
vendor_sts3215_j6    w5  bbox 49.3 x 24.7 x 45.2  vol 42.8 cm3  wt True
grip_frame           w6  bbox 56.4 x 64.0 x 52.4  vol 20.9 cm3  wt True
vendor_sts3215_g     w6  bbox 49.3 x 24.7 x 45.2  vol 42.8 cm3  wt True
vendor_gear_grip     w6  bbox 6.0 x 18.0 x 18.0  vol 1.5 cm3  wt True
vendor_rack_u        w6  bbox 6.0 x 36.0 x 12.0  vol 2.4 cm3  wt True
vendor_rack_d        w6  bbox 6.0 x 36.0 x 12.0  vol 2.4 cm3  wt True
finger_u             w6  bbox 14.4 x 4.0 x 25.2  vol 1.3 cm3  wt True
finger_d             w6  bbox 14.4 x 4.0 x 25.2  vol 1.3 cm3  wt True
BUILD DONE 38 parts 18 s
   ```
   (the seconds may differ). Then `ls out/*.stl | wc -l` → `38` and `ls out/*.step | wc -l` → `38`. Part list rule: every printed part's largest bbox side ≤ 240 (biggest: base_plate 200.0, upper plates 187.7, fore plates 171.6; new wrist parts ≤ 69.1). If a line says `wt False` or a part is missing: STOP, `BLOCKED: build <part>`.
4. **GATE G1 — reach, holes, gripper, torque, ROM** (about 45 s): `$PY arm2b_checks.py 2>&1 | grep -v Warning; echo rc=$?`
   Expected exactly:
   ```
REACH J2 (np.float64(-20.0), np.float64(143.5)) J3 (np.float64(-20.0), np.float64(270.2)) J4 (np.float64(96.4), np.float64(216.2)) (J4 servo horn) J5 x 134.00 y 0.00 (vertical) J6 y 0.00 z 216.20 (along X) TCP x 228.20
REACH J4->J5 37.60 (want 37.6), J5 axis y 0.00 PASS
REACH J6 axis on the J4 height: dz 0.00 dy 0.00; J5->J6 frame 19.2 on it, J6 horn face at J4 + 63.0 PASS
REACH J4->TCP 131.80 (want 131.8 = 37.6 + 19.2 + 75.0) PASS
REACH J2->TCP 374.9 = 126.7 + 116.4 + 131.8 (want 375 +- 10) PASS
HOLE link4: 4 x d3.4 on the STS3215 horn PCD14 PASS
HOLE link5: 4 x d3.4 on the STS3215 horn PCD14 PASS
HOLE grip_frame: 4 x d3.4 on the STS3215 horn PCD14 PASS
HOLE link4: 4 horn holes measured, pattern centre on the servo horn axis (err 0.000) PASS
HOLE link5: 4 horn holes measured, pattern centre on the servo horn axis (err 0.000) PASS
HOLE grip_frame: 4 horn holes measured, pattern centre on the servo horn axis (err 0.000) PASS
HOLE fore_l2: old reBot d38 DM4310 pilot plugged PASS
HOLE fore_r2: old reBot d38 DM4310 pilot plugged PASS
HOLE fore_r2: 4 x d3.4 J4 cradle bolts clear PASS
HOLE j4_cradle: 4 x d2.5 pilots on the same centres, 8 deep PASS
HOLE STS3215 pockets: 0.15 per side on the 45.2 x 24.7 x 35.7 case PASS
GRIP open 25.0 mm (finger gap 2.0 -> 27.0): racks stay in the 64 mm channels and on the gear, no hits PASS
TORQUE masses: wrist+gripper (J4 horn onward) 0.246 kg, J4 servo+cradle 0.077 kg, payload 0.25 kg at J4 + 131.8
TORQUE J4 0.48 N.m (STS3215 rated 0.98 [U] / 1.4 = 0.70) PASS
TORQUE J5 0.30 N.m with J4 turned 90 (same limit 0.70) PASS
TORQUE J2 2.36 N.m with the real wrist (A2a need <= 2.50, limit 3.50) PASS
TORQUE J3 1.15 N.m with the real wrist (A2a need <= 1.50, limit 2.25) PASS
ROM home pose wrist + gripper clear of every part PASS
ROM J4 free -70..+70 deg (total 140, need >= 140) stops: + [vendor_sts3215_j6 x j4_cradle 1] - [vendor_sts3215_j5 x fore_r2 4] PASS
ROM J5 free -70..+70 deg (total 140, need >= 140) stops: + [grip_frame x fore_r2 2] - [grip_frame x fore_l2 2] PASS
ROM J6 free -180..+180 deg (total 360, need >= 360) stops: + [] - [] PASS
ROM J3 free -180..+30 deg (total 210, need >= 150) stops: + [fore_l2 x link1 147] - [] PASS
ROM J2 free -120..+60 deg (total 180, need >= 150) stops: + [vendor_sts3215_j6 x base_plate 564] - [upper_out x base_reinf 1] PASS
CHECKS PASS
rc=0
   ```
   The volume numbers inside `stops: [...]` may differ by a few mm3; every other number must match. What the lines mean: REACH is measured in the built STEP files (J2/J3 from the upper_back holes, J4/J5/J6 from the STS3215 horn cylinders, TCP = finger tip); HOLE checks the horn holes against the STS3215 horn (PCD14) and measures that each pattern is centred on its servo axis; GRIP moves racks + fingers to full open and checks for hits; TORQUE uses measured printed masses (60 % of solid PETG), 55 g per STS3215, 0.25 kg payload at the TCP, arm straight and horizontal; J4/J5 limit = STS3215 rated 0.98 N·m / 1.4; ROM sweeps J4, J5, J6, then J3 and J2 again with the wrist on, in 10° steps until a collision > 0.5 mm3 (servo × servo counts).
   If any line ends `FAIL` or rc is not 0: STOP, write `BLOCKED: checks <the exact FAIL line>` in STATUS, still do step 6 and the status/commit steps (no tag). Never edit ap2b.py or arm2b_checks.py to make it pass.
5. **GATE G2 — gate.py** on the whole arm (watertight, bbox, minwall, interference at the home pose). **Slow: about 8 min (designer's run: 8 min) with NO output until the end. This is normal. Do NOT kill it, do not press Ctrl-C, do not re-start it before 20 min.** Command:
   `$PY ../knuckle/gate.py out/*.stl; echo rc=$?`
   Expected (designer's run on this Mac):
   ```
back_spacer_j2: watertight=True bbox=57.0x4.7x56.8 max=57.0 minwall=1.89 OK
back_spacer_j3: watertight=True bbox=57.0x4.7x56.8 max=57.0 minwall=1.89 OK
base_link: watertight=True bbox=92.0x92.0x63.7 max=92.0 minwall=3.02 OK
base_plate: watertight=True bbox=140.0x200.0x14.0 max=200.0 minwall=13.99 OK
base_reinf: watertight=True bbox=92.0x92.0x6.9 max=92.0 minwall=1.84 OK
dogleg_l: watertight=True bbox=76.1x5.0x99.0 max=99.0 minwall=3.62 OK
dogleg_r: watertight=True bbox=76.1x5.0x99.0 max=99.0 minwall=3.68 OK
finger_d: watertight=True bbox=14.4x4.0x25.2 max=25.2 minwall=3.99 OK
finger_u: watertight=True bbox=14.4x4.0x25.2 max=25.2 minwall=3.99 OK
flange_j2: watertight=True bbox=34.8x9.7x34.8 max=34.8 minwall=2.60 OK
flange_j3: watertight=True bbox=34.8x10.7x34.8 max=34.8 minwall=2.58 OK
fore_l2: watertight=True bbox=171.6x4.0x57.0 max=171.6 minwall=3.99 OK
fore_r2: watertight=True bbox=171.6x4.0x57.0 max=171.6 minwall=3.99 OK
front_spacer_j2: watertight=True bbox=34.8x4.0x34.7 max=34.8 minwall=2.66 OK
front_spacer_j3: watertight=True bbox=34.8x5.0x34.7 max=34.8 minwall=2.38 OK
grip_frame: watertight=True bbox=56.4x64.0x52.4 max=64.0 minwall=1.89 OK
j1_cradle: watertight=True bbox=57.5x57.3x54.5 max=57.5 minwall=4.38 OK
j4_cradle: watertight=True bbox=38.0x52.5x30.0 max=52.5 minwall=2.49 OK
link1: watertight=True bbox=83.7x77.2x84.0 max=84.0 minwall=2.98 OK
link4: watertight=True bbox=66.6x60.6x69.0 max=69.0 minwall=2.11 OK
link5: watertight=True bbox=38.1x30.0x34.6 max=38.1 minwall=1.99 OK
upper_back: watertight=True bbox=61.0x4.0x187.5 max=187.5 minwall=3.80 OK
upper_out: watertight=True bbox=61.0x7.0x187.5 max=187.5 minwall=1.91 OK
vendor_6803_j2: watertight=True bbox=26.0x5.0x25.9 max=26.0 minwall=99.00 OK
vendor_6803_j3: watertight=True bbox=26.0x5.0x25.9 max=26.0 minwall=99.00 OK
vendor_act_j2: watertight=True bbox=57.0x54.4x56.8 max=57.0 minwall=99.00 OK
vendor_act_j3: watertight=True bbox=57.0x54.4x56.8 max=57.0 minwall=99.00 OK
vendor_actout_j2: watertight=True bbox=43.9x2.9x44.0 max=44.0 minwall=99.00 OK
vendor_actout_j3: watertight=True bbox=43.9x2.9x44.0 max=44.0 minwall=99.00 OK
vendor_gear_grip: watertight=True bbox=6.0x17.9x18.0 max=18.0 minwall=99.00 OK
vendor_rack_d: watertight=True bbox=6.0x36.0x12.0 max=36.0 minwall=99.00 OK
vendor_rack_u: watertight=True bbox=6.0x36.0x12.0 max=36.0 minwall=99.00 OK
vendor_sts3215_g: watertight=True bbox=49.3x24.7x45.2 max=49.3 minwall=99.00 OK
vendor_sts3215_j4: watertight=True bbox=45.2x49.3x24.7 max=49.3 minwall=99.00 OK
vendor_sts3215_j5: watertight=True bbox=24.7x45.2x49.3 max=49.3 minwall=99.00 OK
vendor_sts3215_j6: watertight=True bbox=49.3x24.7x45.2 max=49.3 minwall=99.00 OK
vendor_sts3250_j1: watertight=True bbox=45.2x24.7x49.8 max=49.8 minwall=99.00 OK
yaw_limit: watertight=True bbox=77.0x77.0x7.1 max=77.0 minwall=1.89 OK
GATE PASS
rc=0
   ```
   Must hold: all 24 printed (non-`vendor_`) lines `OK`, **zero** lines starting with `INTERF`, `GATE PASS`, `rc=0`. Minwall values may differ by ±0.05. No `--allow`, no `--pairs-only-with`.
   If any `BAD` or `INTERF`: STOP, write `BLOCKED: gate <the exact line>` in STATUS, still do step 6 and the status/commit steps (no tag), report FAIL.
6. **Render**. Write `/tmp/arm2b_list.txt`, one line each `<abs path stl> r g b` (abs path = `/Users/deepakdiwan/Vector-wt/arm2b/cad/arm2b/out/<name>.stl`), all 38 STLs:
   fore_l2, fore_r2, j4_cradle, link4, link5, grip_frame, finger_u, finger_d, upper_out, upper_back, back_spacer_j2, back_spacer_j3, front_spacer_j2, front_spacer_j3, j1_cradle, yaw_limit `0.95 0.55 0.10` (new or changed);
   base_plate, base_link, base_reinf, link1, flange_j2, flange_j3, dogleg_l, dogleg_r `0.85 0.85 0.88` (reBot shape);
   vendor_act_j2, vendor_act_j3, vendor_actout_j2, vendor_actout_j3 `0.20 0.45 0.85`; vendor_sts3250_j1, vendor_sts3215_j4, vendor_sts3215_j5, vendor_sts3215_j6, vendor_sts3215_g `0.25 0.25 0.28`; vendor_6803_j2, vendor_6803_j3, vendor_gear_grip, vendor_rack_u, vendor_rack_d `0.6 0.6 0.6`.
   Check: `wc -l < /tmp/arm2b_list.txt` → `38`.
   Command: `mkdir -p ~/Vector-wt/arm2b/renders && /usr/local/bin/blender -b -P ../knuckle/render_blend.py -- ~/Vector-wt/arm2b/renders/a2b /tmp/arm2b_list.txt 2>&1 | grep WROTE` → 6 `WROTE` lines (`renders/a2b_frontiso.png`, `_backiso`, `_side`, `_top`, `_front`, `_cutaway`). Look at each PNG, 1 line per view in STATUS. Pass: (a) L pose: upper arm vertical, forearm forward, wrist straight forward at the forearm tip; (b) J5 servo (dark) on top of the wrist, J6 and gripper servos on the tool axis; (c) gripper racks + gear at the tip, two flat fingers; (d) links are exposed flat plates, no covers; (e) nothing floats. PNGs ≤ 1.5 MB each (designer's run: 0.9–1.1 MB), else leave it out of the commit and note it.

## Gate before commit
- Step 3 (39 lines, all `wt True`), step 4 (`CHECKS PASS`, rc 0), step 5 (24 printed `OK`, no `INTERF`, `GATE PASS`, rc 0), 6 `WROTE`.
- `git status --short` shows only untracked `cad/arm2b/`, `docs/STATUS-arm2b.md`, the new `renders/a2b_*.png` (and old `cad/arm2/out/`, `cad/act2/out/`). You add files by name in S.3, never `git add .` or `git add -A`: `cad/arm2b/out/` and `__pycache__` must not be committed.

## Status + commit (always the last steps, also after a BLOCKED)
S.1 Create `docs/STATUS-arm2b.md`:
```
## Stage A2b — <today's date> — PASS or FAIL
- Gate lines (literal, copy-paste): <step 4 ALL lines incl. CHECKS PASS/FAIL and rc> | <step 5 ALL lines incl. GATE PASS/FAIL and rc>
- Part list (bbox + volume): <step 3 output>   Render review: <one line per view>
- Files changed: <git status --short>   BLOCKED: <none | lines>
- Source: Seeed reBot-DevArm 13bebbf (CERN-OHL-W-2.0), reBot_B601_DM_v1.1_20260425.step; changes in cad/arm2b/NOTICE.md (and cad/arm2/NOTICE.md).
- Assembly: J4 servo into j4_cradle, cradle to fore_r2 with 4x M3x10; link4 on the J4 horn with 4x M3x8; J5 servo into link4 (horn down), link5 on the J5 horn; J6 servo into link5, grip_frame on the J6 horn; gripper servo into grip_frame, gear on its horn (4x M3 countersunk), racks into the channels meshing the gear, fingers glued / M2 to the rack ends. Servo cables daisy-chained J4 -> J5 -> J6 -> gripper.
- Still UNVERIFIED: STS3215 rated torque 0.98 N.m; servo retention in the pockets (no case ears / screws modelled, 0.15 clearance); horn screw thread M3 in the STS3215 horn; gear drilling + countersink, rack-gear mesh and the rack cut (proxies only, mesh not simulated); rack retention by the lips; finger-to-rack joint; J6 horn face at a 63.0 vs the kinematic J6 frame 56.8 (same axis, roll only); fingers 12.1 deep only; J4-J5 37.6 vs rebot-adapt2.md ">= 50"; J4/J5 ROM +-70 (servo cases / bracket hit the forearm at 80); cable route; printed mass factor 0.6.
```
S.2 `cd ~/Vector-wt/arm2b && /usr/bin/git status --short`.
S.3 `/usr/bin/git add cad/arm2b/ap2b.py cad/arm2b/p_arm2b.py cad/arm2b/build_arm2b.py cad/arm2b/arm2b_checks.py cad/arm2b/NOTICE.md cad/arm2b/BOM.md cad/arm2b/rebot_src docs/STATUS-arm2b.md renders/a2b_*.png && /usr/bin/git status --short | grep -v "^??"` → only `A ` lines for those paths (2 `rebot_src` STEP files), NO `out/`, `.stl`, `__pycache__`. Then `/usr/bin/git commit -m "A2b: reBot wrist J4-J6 on 3x STS3215 + STS3215 rack gripper (0.48 span, reach 374.9)"` → `[arm-arm2b <hash>] A2b: ...`
S.4 Only if the stage PASSED: `/usr/bin/git tag arm-2-done`. Then (always): `/usr/bin/git push -u origin arm-arm2b --tags` → ends with `* [new tag] arm-2-done -> arm-2-done` (PASS) or the branch line (FAIL). If rejected: `/usr/bin/git pull --ff-only origin arm-arm2b` once, push again; else `BLOCKED: push`.
S.5 STOP. Do not start another stage. Do not touch `arm-arm2`, `arm-actuator2*` or `arm-knuckle`.
