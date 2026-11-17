# Stage A2a — reBot arm around our actuator: base + J1 (STS3250), Link1, J2, upper arm, J3, forearm plates
> Before you start: you already read `~/Vector/ARM_KNUCKLE_V5.md`. Rules 0.1–0.10 apply, with these overrides for this stage only:
> (a) branch is `arm-arm2` (made from tag `act-1c-done` = `954a3f3` on `arm-actuator2c`), worktree `~/Vector-wt/arm2`; never commit, push or tag on `arm-actuator2*` or `arm-knuckle`;
> (b) every number lives in `cad/arm2/ap2.py`; rule 0.6 applies to ap2.py. The code is a tested bundle: you copy it (step 2) and run it. You type no geometry and edit no `.py` file;
> (c) status file is `docs/STATUS-arm2.md` (new file).
> Work dir: `~/Vector-wt/arm2/cad/arm2`. Type first in every new shell: `export PY=/Users/deepakdiwan/soma/.venv/bin/python`.
> "Expected" = output must match (numbers ±0.05 unless stated). If not: re-run once, then do the "If not" line.
> Do NOT edit by hand: `cad/knuckle/*`, `cad/act2/*`, `cad/arm2/*.py`, `cad/arm2/rebot_src/*`, any file in `~/Vector/stages/` (read only).

**Goal:** the J1–J3 half of the arm as printable parts (STEP + STL), built from the Seeed reBot-DevArm CAD around our printed actuator, passing `arm2_checks.py` (reach, holes, torque, ROM) and `gate.py` (watertight, bbox ≤ 240, minwall ≥ 1.60, no INTERF at the home pose), then renders, status, commit, tag `arm-2a-done`, push.
**Why:** keep the reBot layout and its exposed, minimal side plates, but at 0.48 span (reach ≈ 375 mm) so the printed actuator (J2 3.5 N·m, J3 2.25 N·m) can hold it. Joint ends stay full reBot size; only the spans shrink: upper arm 264 → 126.7, forearm 242.6 → 116.4. Wrist + gripper are stage A2b. The designer ran the whole bundle on this Mac (literal outputs below).
**Inputs (read only):** `~/Vector/stages/code/arm2/` (tested bundle: `ap2.py`, `p_arm2.py`, `build_arm2.py`, `arm2_checks.py`, `NOTICE.md`, `BOM.md`, `rebot_src/` = 14 reBot STEP parts re-exported unchanged in their assembly position from `reBot_B601_DM_v1.1_20260425.step`, reBot commit `13bebbf`, CERN-OHL-W-2.0), `cad/act2/ap.py` (actuator interface, imported by ap2.py), `~/Vector/stages/ref/rebot-adapt2.md`.

## 0. What the bundle does (for your understanding; all numbers are already in ap2.py)
| Item | reBot (DM motors, metal) | A2a |
|---|---|---|
| World frame | reBot assembly, folded rest pose, Z up | same; build_arm2.py then puts the arm in the **home (L) pose**: upper arm vertical (J2 −90°), forearm forward (J3 −90°) |
| J1 | DM-J4340P in `01_BASE_Link` | **STS3250** (horn face Z 80.8, body Z 43.0–78.7, long axis along X), pocket +0.15/side cut into base_link, new printed `j1_cradle` fills the old Ø57.8 motor pocket; `02_Arm_Yaw_Limit` Ø14 plugged, 4× Ø3.2 on PCD14 + Ø6.2 × 2.0 counterbores + Ø7 × 2.2 horn recess. Base plate, reinforcement, AXK5578, 6707, Link1 unchanged |
| J2, J3 motor | DM-J4340P | **printed actuator** (cad/act2): output face at Y −31.6 (the reBot DM output face), back face at Y +23.4, module X = world X |
| Front spacers | 6× Ø3.2 PCD27 at 0/60/…, 3× Ø4 PCD24 at 30/150/270 | reBot spacer, every hole plugged, **3× Ø3.2 PCD27 at 0/120/240, 3× Ø4.1 PCD24 at 60/180/300** (= actuator out M3 + dowels). J3 spacer 5.0 thick |
| Back spacer | Ø57 × 5 | new Ø57 × 4.7 (Y 23.4–28.1), **6× Ø3.4 PCD50** (= actuator back pilots), reBot 6803 seat Ø26.05 + Ø22 lip |
| Upper arm | `03_Link2` C-channel, 3 mm sheet, J2→J3 264 | **two flat 4 mm plates** `upper_out` (Y −32.1..−28.1, Ø57.15 rings + 3 mm collars grip the two housings) and `upper_back` (Y 28.1..32.1, Ø38 end holes, 12× M3 countersunk), R30.5 ends, J2→J3 **126.7**, R12 lightening slot |
| Forearm | `03_Link3_L/_R` 3-layer sheet, 242.6 | **flat 4 mm plates** `fore_l` (Y −36.6..−32.6) / `fore_r` (Y 32.6..36.6) = reBot J3-end sheet moved −137.3 in X + reBot J4-end sheet moved −11.1, joined by a 32 mm band (Z 185–217). J3→J4 **116.4** axial, 54.0 offset (reBot dogleg) |
| Doglegs, FLANGE | metal | printed; doglegs moved 1.0 / 2.0 outboard; FLANGE bore plugged → Ø8, J3 FLANGE +1.0 thick |
| Not in A2a | — | wrist J4–J6, gripper (A2b). No covers, fillers or handle (on purpose) |

## 1. Steps (in this order)
1. Command: `cd ~/Vector-wt/arm2 && /usr/bin/git branch --show-current && /usr/bin/git log --oneline -1 && /usr/bin/git status --short`
   Expected: `arm-arm2`, then `954a3f3 A1c: motor turned round, hub bolted to Tarot bell top (34 mm holes), magnet puck on shaft end, mid_plate removed`, then nothing (or only `?? cad/act2/out/`). If not: STOP, `BLOCKED: worktree`.
2. **Copy the bundle** (ONCE): `mkdir -p ~/Vector-wt/arm2/cad/arm2 && cp -R ~/Vector/stages/code/arm2/. ~/Vector-wt/arm2/cad/arm2/ && cd ~/Vector-wt/arm2/cad/arm2 && ls && ls rebot_src/*.step | wc -l`
   Expected: `BOM.md NOTICE.md ap2.py arm2_checks.py build_arm2.py p_arm2.py rebot_src` and `14`.
   Then: `$PY -c "import ap2; print(ap2.J3_XZ, round(ap2.J4_XZ[0],1), ap2.DX_UP, round(ap2.DX_FORE,1), ap2.ACT_BACK_Y, ap2.ACT_HOUSING_END_Y, ap2.A.OD, ap2.A.L_TOTAL)"` → `(106.7, 143.5) -9.7 -137.3 -11.1 23.4 -31.0 57.0 55.0`. If ImportError on `ap`: STOP, `BLOCKED: cad/act2/ap.py missing` (wrong base commit).
3. **Build** (about 20 s): `rm -rf out && $PY build_arm2.py 2>&1 | grep -v Warning`
   Expected exactly these 26 lines, no Traceback:
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
   fore_l               fo  bbox 171.6 x 4.0 x 57.0  vol 19.4 cm3  wt True
   fore_r               fo  bbox 171.6 x 4.0 x 57.0  vol 19.4 cm3  wt True
   BUILD DONE 25 parts 17 s
   ```
   (the seconds may differ). Then `ls out/*.stl | wc -l` → `25` and `ls out/*.step | wc -l` → `25`. Part list rule: every printed part's largest bbox side ≤ 240 (biggest: base_plate 200.0, upper plates 187.7). If a line says `wt False` or a part is missing: STOP, `BLOCKED: build <part>`.
4. **GATE G1 — reach, holes, torque, ROM** (about 15 s): `$PY arm2_checks.py 2>&1 | grep -v Warning; echo rc=$?`
   Expected exactly:
   ```
   REACH J2 (np.float64(-20.0), np.float64(143.5)) J3 (np.float64(-20.0), np.float64(270.2)) J4 (np.float64(96.4), np.float64(216.2))
   REACH upper J2->J3 126.70 (want 126.7) PASS
   REACH forearm J3->J4 axial 116.40 (want 116.4), offset 54.00 (want 54.0) PASS
   REACH J2->TCP 375.0 = 126.7 + 116.4 + A2b 131.9 (want 375 +- 10) PASS
   HOLE back_spacer_j2: 6 x d2.5 on actuator back pilots PCD50 PASS
   HOLE back_spacer_j3: 6 x d2.5 on actuator back pilots PCD50 PASS
   HOLE upper_back: 12 x d2.5 on actuator back pilots PCD50 PASS
   HOLE front_spacer_j2: 3 x d3.0 on actuator M3 PCD27 PASS
   HOLE front_spacer_j2: 3 x d4.0 on actuator dowels PCD24 PASS
   HOLE front_spacer_j2: old reBot dowel holes plugged PASS
   HOLE front_spacer_j3: 3 x d3.0 on actuator M3 PCD27 PASS
   HOLE front_spacer_j3: 3 x d4.0 on actuator dowels PCD24 PASS
   HOLE front_spacer_j3: old reBot dowel holes plugged PASS
   HOLE link1: 3 x d3.0 J2 cheek on actuator M3 PASS
   HOLE dogleg_l: 3 x d3.0 J3 end on actuator M3 PASS
   HOLE upper_out ring d57.15 on housing OD 57.00 (clearance 0.15) PASS
   HOLE upper_out: housing OD free and ring wall present at both ends PASS
   HOLE fore_l: 4 dogleg top-end holes clear PASS
   HOLE yaw_limit: 4 horn holes PCD14 clear, old d14 plugged, horn recess open PASS
   TORQUE masses: upper printed 0.050 kg, forearm printed 0.066 kg, J3 actuator 0.300 [U], wrist+grip 0.315, payload 0.25; J4->TCP 131.8
   TORQUE J2 2.34 N.m (rebot_torque 0.48: 2.23, limit 3.50, margin 1.50x, need <= 2.50) PASS
   TORQUE J3 1.15 N.m (rebot_torque 0.48: 1.15, limit 2.25, margin 1.96x, need <= 1.50) PASS
   ROM home pose J2 joint clear PASS
   ROM J3 free -180..+30 deg (total 210, need >= 150) stops: + [fore_l x link1 147] - [] PASS
   ROM J2 free -120..+70 deg (total 190, need >= 150) stops: + [fore_l x base_plate 142] - [upper_out x base_reinf 1] PASS
   CHECKS PASS
   rc=0
   ```
   The volume numbers inside `stops: [...]` may differ by a few mm3; every other number must match. What the lines mean: REACH is measured from hole axes in the built STEP files (A2b must add J4→TCP 131.9); HOLE checks each hole against the actuator numbers in `cad/act2/ap.py`; TORQUE is the rebot_torque.py `soma` model with the measured printed masses (60 % of solid PETG) and the arm straight and horizontal; ROM sweeps J3 then J2 from the home pose in 10° steps until a collision > 0.5 mm3.
   If any line ends `FAIL` or rc is not 0: STOP, write `BLOCKED: checks <the exact FAIL line>` in STATUS, still do step 6 and the status/commit steps (no tag). Never edit ap2.py or arm2_checks.py to make it pass.
5. **GATE G2 — gate.py** (watertight, bbox, minwall, interference at the home pose). **Slow: about GATE_MIN min with NO output until the end. This is normal. Do NOT kill it, do not press Ctrl-C, do not re-start it before 15 min.** Command:
   `$PY ../knuckle/gate.py out/*.stl; echo rc=$?`
   Expected (designer's run on this Mac):
   ```
GATE_BLOCK
   ```
   Must hold: all 18 printed (non-`vendor_`) lines `OK`, **zero** lines starting with `INTERF`, `GATE PASS`, `rc=0`. Minwall values may differ by ±0.05. No `--allow`, no `--pairs-only-with`.
   If any `BAD` or `INTERF`: STOP, write `BLOCKED: gate <the exact line>` in STATUS, still do step 6 and the status/commit steps (no tag), report FAIL.
6. **Render**. Write `/tmp/arm2_list.txt`, one line each `<abs path stl> r g b` (abs path = `/Users/deepakdiwan/Vector-wt/arm2/cad/arm2/out/<name>.stl`), all 25 STLs:
   upper_out, upper_back, fore_l, fore_r, back_spacer_j2, back_spacer_j3, front_spacer_j2, front_spacer_j3, j1_cradle, yaw_limit `0.95 0.55 0.10` (new or re-drilled);
   base_plate, base_link, base_reinf, link1, flange_j2, flange_j3, dogleg_l, dogleg_r `0.85 0.85 0.88` (reBot shape);
   vendor_act_j2, vendor_act_j3, vendor_actout_j2, vendor_actout_j3 `0.20 0.45 0.85`; vendor_sts3250_j1 `0.25 0.25 0.28`; vendor_6803_j2, vendor_6803_j3 `0.6 0.6 0.6`.
   Check: `wc -l < /tmp/arm2_list.txt` → `25`.
   Command: `mkdir -p ~/Vector-wt/arm2/renders && /usr/local/bin/blender -b -P ../knuckle/render_blend.py -- ~/Vector-wt/arm2/renders/a2 /tmp/arm2_list.txt 2>&1 | grep WROTE` → 6 `WROTE` lines (`renders/a2_*.png`). Look at each PNG, 1 line per view in STATUS. Pass: (a) L pose: upper arm vertical, forearm forward and 54 mm below the J3 axis; (b) the two blue actuators sit between the two orange upper plates, one at each end; (c) the plates are exposed flat plates, no covers; (d) the dark servo is inside the base, horn up; (e) nothing floats. PNGs ≤ 1.5 MB each, else leave it out of the commit and note it.

## Gate before commit
- Step 3 (25 lines, all `wt True`), step 4 (`CHECKS PASS`, rc 0), step 5 (18 printed `OK`, no `INTERF`, `GATE PASS`, rc 0), 6 `WROTE`.
- `git status --short` shows only untracked `cad/arm2/`, `docs/STATUS-arm2.md`, the new `renders/a2_*.png` (and the old `cad/act2/out/`). You add files by name in S.3, never `git add .` or `git add -A`: `cad/arm2/out/` and `__pycache__` must not be committed.

## Status + commit (always the last steps, also after a BLOCKED)
S.1 Create `docs/STATUS-arm2.md`:
```
## Stage A2a — <today's date> — PASS or FAIL
- Gate lines (literal, copy-paste): <step 4 ALL lines incl. CHECKS PASS/FAIL and rc> | <step 5 ALL lines incl. GATE PASS/FAIL and rc>
- Part list (bbox + volume): <step 3 output>   Render review: <one line per view>
- Files changed: <git status --short>   BLOCKED: <none | lines>
- Source: Seeed reBot-DevArm 13bebbf (CERN-OHL-W-2.0), reBot_B601_DM_v1.1_20260425.step; changes in cad/arm2/NOTICE.md.
- Assembly: J1 servo + horn into j1_cradle in base_link, yaw_limit on the horn with 4x M3x8 from the top, then reBot J1 stack (AXK5578, 6707, reinforcement) and Link1. J2/J3: actuator housing into the upper_out ring (slip + CA), back_spacer + upper_back with 6x M3x10 countersunk into the back pilots; front spacer + Link1 cheek (J2) / dogleg_l (J3) with 3x M3x14 / M3x16 into the carrier inserts; 6803 in the back spacer on the reBot FLANGE.
- Still UNVERIFIED: STS3250 case = STS3215 case (45.2 x 24.7 x 35, horn PCD14, horn thread); upper_out ring grip (0.15 clearance + CA); M3x10 countersunk grip in the 3.2 pilots (1.3 mm); J3 actuator mass 0.300 kg; printed mass factor 0.6; servo cable route (cradle d10 hole -> base floor d16); Link1 printed at reBot 3 mm sheet thickness; forearm band 32 mm (reBot neck).
```
S.2 `cd ~/Vector-wt/arm2 && /usr/bin/git status --short`.
S.3 `/usr/bin/git add cad/arm2/ap2.py cad/arm2/p_arm2.py cad/arm2/build_arm2.py cad/arm2/arm2_checks.py cad/arm2/NOTICE.md cad/arm2/BOM.md cad/arm2/rebot_src docs/STATUS-arm2.md renders/a2_*.png && /usr/bin/git status --short | grep -v "^??"` → only `A ` lines for those paths (14 `rebot_src` STEP files), NO `out/`, `.stl`, `__pycache__`. Then `/usr/bin/git commit -m "A2a: reBot-DevArm J1-J3 around the printed actuator (0.48 span, flat 4 mm plates, STS3250 J1)"` → `[arm-arm2 <hash>] A2a: ...`
S.4 Only if the stage PASSED: `/usr/bin/git tag arm-2a-done`. Then (always): `/usr/bin/git push -u origin arm-arm2 --tags` → ends with `* [new tag] arm-2a-done -> arm-2a-done` (PASS) or the branch line (FAIL). If rejected: `/usr/bin/git pull --ff-only origin arm-arm2` once, push again; else `BLOCKED: push`.
S.5 STOP. Do not start A2b. Do not touch `arm-actuator2*` or `arm-knuckle`.
