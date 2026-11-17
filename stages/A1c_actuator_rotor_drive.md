# Stage A1c — motor turned round: hub bolts to the Tarot bell top (no shaft grip), magnet on a printed puck
> Before you start: you already read `~/Vector/ARM_KNUCKLE_V5.md`. Rules 0.1–0.10 apply, with these overrides for this stage only:
> (a) branch is `arm-actuator2c` (made from `arm-actuator2b` @ `87508f4`), worktree `~/Vector-wt/act2c`; never commit, push or tag on `arm-actuator2`, `arm-actuator2b` or `arm-knuckle`;
> (b) every number lives in `cad/act2/ap.py`; rule 0.6 applies to ap.py. You change files ONLY with the patch script (step 2) and the BOM edit (step 9);
> (c) status file is `docs/STATUS-act2.md` (APPEND a new section, never rewrite the A1 / A1b sections).
> Work dir: `~/Vector-wt/act2c/cad/act2`. Type first in every new shell: `export PY=/Users/deepakdiwan/soma/.venv/bin/python`.
> "Expected" = output must match (numbers ±0.05 unless stated). If not: re-run once, then do the "If not" line.
> Do NOT edit by hand: `cad/knuckle/*`, `cad/act2/cyc.py`, `cad/act2/build_act.py`, any file in `~/Vector/stages/` (read only).

**Goal:** the A1b actuator with a new motor coupling, every printed part passing gate.py `minwall ≥ 1.60`, no INTERF, length 55.00, then renders, status, commit, tag `act-1c-done`, push.
**Why:** A1b kept a 12 mm shaft grip with a grub screw. The Tarot 4008 has **no shaft past the stator base** (community STEP: only an M3 screw + washer). Dongil Choi's 40:1 actuator (same motor) bolts the input cam to the **rotor bell top** through Tarot's 34 mm prop-mount holes, and screws a magnet puck to the shaft-end M3 at the base. A1c copies that. The designer tested the patch on a copy of `87508f4` (literal gate output in step 6).
**Inputs (read only):** `~/Vector/stages/code/act2c/patch_a1c.py` (tested patch), `docs/STATUS-act2.md` (A1, A1b results).

## 0. What changes (all numbers already inside the patch; you type no geometry)
| Item | A1b | A1c |
|---|---|---|
| Motor orientation | bell top → back (Z 7.5), stator base on mid_plate (Z 29.5) | **stator base on the housing back plate at Z 10.2, bell top → gearbox at Z 29.2** (`Z_STATOR = 10.2`, `Z_MOTOR = (Z_STATOR, Z_STATOR + MOT_H)`) |
| Body height | `MOT_H = 22.0` | `MOT_H = 19.0` (community STEP) [U]. New `DZ = MOT_H - 19.0` shifts every part in front of the motor |
| Stator screws | 3× M3 on PCD 32 into mid_plate | same 3× M3 PCD 32 (30/150/270°), now through the housing back: Ø3.4 holes, Ø6.2 counterbores from the back face to Z 7.2 (3.0 plate under the heads), M3×6 ISO 7380 |
| mid_plate | keyed plate Z 29.5–33.5 | **deleted** (part, KEY_*, MID_*, CSK_*). The 41 ring-pin grooves are blind: pins stand on the groove floors at Z 33.5 |
| hub | cams on a Ø4 shaft bore + M3 grub | **one piece**: rotor flange Z 29.2–33.2 (44 × 20 bar, ends trimmed to Ø44, 4.0 thick) + cam1 + cam2 + stub (cams, E 0.42, stub unchanged). 2× Ø3.4 at (0, ±17) = Tarot 34 mm prop holes, Ø6.2 × 1.9 counterbores in the front face, 2× M3×5 ISO 7380 into the bell; Ø3.0 × 4.0 centre clearance in the back face |
| Magnet | glued on the bell top, Z 5.0–7.5 | in new printed part **`mag_puck`** Z 4.7–10.7: Ø12 body to Z 9.9 + Ø8 × 0.8 nose (sits where Tarot's Ø9.07 washer was), Ø6.05 × 4.15 pocket open to the back (M3×4 ISO 7380 head 1.65 + magnet 2.5), Ø3.2 hole, 1.85 floor. Magnet Z 4.7–7.2 → gap 0.95 to the AS5600 chip (0.5–3 allowed) |
| Housing back | wall 0–3.6, magnet space behind it | solid to Z 10.2 with a Ø13 puck cavity (3.6–10.2), wire channel at 90° now to Z 10.2, new wire groove 4 × 1.5 in the plate front face at 90° (r 6.5 → bore) |
| Removed from ap.py | — | `SHAFT_OUT`, `STATOR_HOLE_D`, `HUB_BORE`, `HUB_BORE_L`, `GRUB_Z`, `GRUB_PILOT`, `Z_MID`, `MID_*`, `KEY_*`, `CSK_*`; p_act.py `radial_hole`, `radial_csk`, `mid_plate` |
Why one-piece hub and not Dongil's 2 screws 9 mm apart into the cam: Ø3.4 holes at ±4.5 inside a Ø15 cam offset 0.42 leave ≈1.3 mm walls (minwall fails at 1.6). The 2 rotor screws do the job instead.
Nothing else changes: OD 57, length 55, gear (40/41, E 0.42, CLR 0.15), discs, carrier, flange, rings, bearings.

## 1. Steps (in this order)
1. Command: `cd ~/Vector-wt/act2c && /usr/bin/git branch --show-current && /usr/bin/git log --oneline -1 && /usr/bin/git status --short`
   Expected: `arm-actuator2c`, then `87508f4 A1b: actuator minwall fixes (pin bore 47.4, keyed mid_plate, grub at cam split), Tarot base PCD32`, then nothing. If not: STOP, `BLOCKED: worktree`.
2. **Patch** (from `cad/act2`, ONCE): `$PY ~/Vector/stages/code/act2c/patch_a1c.py`
   Expected: 32 lines `PATCHED ap.py: ...`, 6 lines `PATCHED p_act.py: ...` (radial_hole, radial_csk deleted; housing; mid_plate; hub; vendor_motor), 1 `PATCHED p_act.py: PARTS mid_plate -> mag_puck`, 1 `PATCHED act_checks.py: P mid_plate -> mag_puck`, last line `PATCH a1c OK`.
   Then: `$PY -c "import ap; print(ap.DZ, ap.Z_MOTOR, ap.Z_ADAPT, ap.Z_PUCK, ap.Z_MAG)"` → `0.0 (10.2, 29.2) (29.2, 33.2) (4.7, 10.7) (4.7, 7.2)`
   and `grep -cE "SHAFT_OUT|GRUB|HUB_BORE|KEY_PINS|Z_MID|mid_plate|CSK_" ap.py p_act.py act_checks.py` → three lines each ending `:0`.
   If AssertionError: `/usr/bin/git checkout cad/act2/ap.py cad/act2/p_act.py cad/act2/act_checks.py` once and re-run step 2; if again: STOP, `BLOCKED: patch`.
3. **GATE G1** (gear maths, unchanged): `$PY cyc.py | head -1 && $PY cyc.py 40 | tail -2` → `RATIO 40.0`, `disc r_min 21.580 r_max 22.420  out-pin hole d 4.14  pin pitch 3.598`, `CYC PASS`. If not: STOP, `BLOCKED: cyc`.
4. **Build** (about 1 min): `rm -rf out && $PY build_act.py 2>&1 | grep -v Warning`
   Expected exactly these 19 lines, no Traceback:
   ```
   housing: bbox=(-28.5, 28.5, -28.5, 28.5, 0.0, 54.4) vol=55.7
   mag_puck: bbox=(-6.0, 6.0, -6.0, 6.0, 4.7, 10.7) vol=0.5
   hub: bbox=(-10.0, 10.0, -22.0, 22.0, 29.2, 47.2) vol=4.9
   disc1: bbox=(-21.78, 22.62, -22.2, 22.2, 33.8, 37.8) vol=4.3
   disc2: bbox=(-22.69, 21.85, -22.27, 22.27, 38.1, 42.1) vol=4.3
   carrier: bbox=(-21.5, 21.5, -21.5, 21.5, 42.4, 52.4) vol=12.1
   out_flange: bbox=(-22.0, 22.0, -22.0, 22.0, 52.4, 55.0) vol=3.8
   pin_ring: bbox=(-25.95, 25.95, -25.95, 25.95, 43.5, 45.4) vol=1.0
   front_ring: bbox=(-26.0, 26.0, -26.0, 26.0, 52.4, 54.4) vol=0.9
   vendor_motor: bbox=(-22.25, 22.25, -22.25, 22.25, 10.2, 29.2) vol=29.5
   vendor_magnet: bbox=(-3.0, 3.0, -3.0, 3.0, 4.7, 7.2) vol=0.1
   (vendor_ringpins, vendor_outpins, vendor_dowels, vendor_6808, vendor_6702a, vendor_6702b, vendor_685, vendor_as5600: identical to A1b)
   ```
   Then `ls out/*.step | wc -l` → `19` and `ls out/*.stl | wc -l` → `19`. If a part fails: STOP, `BLOCKED: build <part>` (do not hand-edit geometry).
5. **GATE G2/G3**: `$PY act_checks.py; echo rc=$?` → 9 lines `watertight=True` (first two `housing ... rmax=28.50`, `mag_puck ... rmax=6.00`; `hub ... rmax=22.00`), `LENGTH 55.00 OK`, `OD 57.00 OK`, `ACT PASS`, `rc=0`.
   If `LENGTH` is BAD: STOP. Write `BLOCKED: length <the exact LENGTH line>` in STATUS and do the status/commit steps (no tag). Never change L_TOTAL, MOT_H, Z_* or act_checks.py to make it pass. Other failures: STOP, `BLOCKED: act_checks`.
6. **GATE G4/G5** (minwall ≥ 1.60 + interference). **Slow: about 15–20 min with NO output until the end. This is normal. Do NOT kill it, do not press Ctrl-C, do not re-start it before 30 min.** Command:
   `$PY ../knuckle/gate.py out/housing.stl out/mag_puck.stl out/hub.stl out/disc1.stl out/disc2.stl out/carrier.stl out/out_flange.stl out/pin_ring.stl out/front_ring.stl out/vendor_*.stl; echo rc=$?`
   Expected (designer's run):
   ```
   housing: watertight=True bbox=57.0x57.0x54.4 max=57.0 minwall=1.78 OK
   mag_puck: watertight=True bbox=12.0x12.0x6.0 max=12.0 minwall=1.84 OK
   hub: watertight=True bbox=20.0x44.0x18.0 max=44.0 minwall=2.09 OK
   disc1: watertight=True bbox=44.4x44.4x4.0 max=44.4 minwall=3.63 OK
   disc2: watertight=True bbox=44.5x44.5x4.0 max=44.5 minwall=3.51 OK
   carrier: watertight=True bbox=43.0x43.0x10.0 max=43.0 minwall=2.99 OK
   out_flange: watertight=True bbox=44.0x44.0x2.6 max=44.0 minwall=2.59 OK
   pin_ring: watertight=True bbox=51.9x51.9x1.9 max=51.9 minwall=1.89 OK
   front_ring: watertight=True bbox=52.0x52.0x2.0 max=52.0 minwall=1.99 OK
   vendor_6702a: watertight=True bbox=21.0x21.0x4.0 max=21.0 minwall=99.00 OK
   vendor_6702b: watertight=True bbox=21.0x21.0x4.0 max=21.0 minwall=99.00 OK
   vendor_6808: watertight=True bbox=52.0x52.0x7.0 max=52.0 minwall=99.00 OK
   vendor_685: watertight=True bbox=11.0x11.0x5.0 max=11.0 minwall=99.00 OK
   vendor_as5600: watertight=True bbox=23.0x23.0x1.8 max=23.0 minwall=99.00 OK
   vendor_dowels: watertight=True bbox=22.0x24.8x8.0 max=24.8 minwall=99.00 OK
   vendor_magnet: watertight=True bbox=6.0x6.0x2.5 max=6.0 minwall=99.00 OK
   vendor_motor: watertight=True bbox=44.5x44.5x19.0 max=44.5 minwall=99.00 OK
   vendor_outpins: watertight=True bbox=31.6x36.0x12.0 max=36.0 minwall=99.00 OK
   vendor_ringpins: watertight=True bbox=49.9x50.0x10.0 max=50.0 minwall=99.00 OK
   GATE PASS
   rc=0
   ```
   Must hold: all 9 printed lines `OK`, **zero** lines starting with `INTERF`, `GATE PASS`, `rc=0`. Minwall values may differ by ±0.05.
   No `--allow`, no fallbacks. If any `BAD` or `INTERF`: STOP, write `BLOCKED: gate <the exact line>` in STATUS, still do steps 7 and 8 and the status/commit steps (no tag), report FAIL.
7. **GATE G6** (tooth clearance): `$PY -c "import cyc; print(cyc.mesh_clearance(40), cyc.mesh_clearance(40, second=True))"` → `(0.1439..., 0.1444...) (0.1439..., 0.1444...)`; both first numbers ≥ 0.10. If not: STOP, `BLOCKED: mesh`.
8. **MOT_H 22 check** (proves the DZ switch; do not commit its output): `sed -i '' 's/^MOT_D = 44.5; MOT_H = 19.0;/MOT_D = 44.5; MOT_H = 22.0;/' ap.py && $PY build_act.py 2>&1 | grep -v Warning | head -3 && $PY act_checks.py | tail -3; sed -i '' 's/^MOT_D = 44.5; MOT_H = 22.0;/MOT_D = 44.5; MOT_H = 19.0;/' ap.py && grep -c "MOT_H = 19.0" ap.py && rm -rf out && $PY build_act.py 2>&1 | grep -v Warning | head -2 && $PY act_checks.py | tail -1`
   Expected: `housing ... 0.0, 57.4) vol=58.5`, `mag_puck ... 4.7, 10.7)`, `hub ... 32.2, 50.2)`, `LENGTH 58.00 BAD`, `OD 57.00 OK`, `ACT FAIL` (this FAIL is expected: with a 22 mm body the module needs **58.0 mm**), then `1`, the step-4 housing and mag_puck lines again, `ACT PASS`. Write in STATUS: `MOT_H 22 check: LENGTH 58.00 (needs +3.0 mm); MOT_H restored 19.0`. If the last line is not `ACT PASS`: STOP, `BLOCKED: restore MOT_H`.
9. **BOM** — edit `cad/act2/BOM.md`, exactly these rows:
   - change `| 3 | M3×6 ISO 7380 (stator → mid_plate, PCD 32) [U length] | | |` to `| 3 | M3×6 ISO 7380 (stator base → housing back plate, PCD 32, from the back) [U thread depth] | | |`
   - change `| 1 | M3×5 ISO 4026 set screw (hub on shaft) + Loctite 243 | | |` to `| 2 | M3×5 ISO 7380 (hub flange → Tarot bell top, 34 mm prop holes) + Loctite 243 [U thread depth; kit screws M3×11.3 are too long] | | |`
   - add right below it: `| 1 | M3×4 ISO 7380 (mag_puck → shaft end, replaces Tarot's button screw + washer) [U] | | |`
   - add right below that: `| 1 | mag_puck, printed (Ø12 × 6, magnet pocket Ø6.05) | | |`
   If a row is not found exactly, write `BOM row not found: <row>` in STATUS and leave that row.
10. **Render** (same as A1b step 10, with `mag_puck` instead of `mid_plate`). Write `/tmp/act_list.txt`, one line each `<abs path stl> r g b`:
    housing 0.85 0.85 0.88; pin_ring, front_ring 0.25 0.25 0.28; mag_puck 0.80 0.20 0.20; disc1 0.20 0.45 0.85; disc2 0.15 0.65 0.45; hub, carrier, out_flange 0.95 0.55 0.10; all 10 vendor_* 0.6 0.6 0.6 (abs path = `/Users/deepakdiwan/Vector-wt/act2c/cad/act2/out/<name>.stl`).
    Command: `mkdir -p ~/Vector-wt/act2c/renders && /usr/local/bin/blender -b -P ../knuckle/render_blend.py -- ~/Vector-wt/act2c/renders/a1 /tmp/act_list.txt 2>&1 | grep WROTE` → 6 `WROTE` lines, overwriting the a1_* PNGs. Look at each PNG, 1 line per view in STATUS. Pass: (a) cutaway order: AS5600 → red puck → motor (base at the back) → orange hub flange on the bell top → two discs → carrier → 6808 → flange; (b) ring pins half buried, standing on groove floors; (c) nothing floats; (d) outside is a plain Ø57 cylinder (wire notch at 90° only). PNGs ≤ 1.5 MB each, else leave it out of the commit and note it.

## Gate before commit
- Steps 3 (`CYC PASS`), 5 (`ACT PASS`, `LENGTH 55.00 OK`, `OD 57.00 OK`), 6 (9 × `OK`, no `INTERF`, `GATE PASS`), 7 (≥ 0.10), 8 (restored, `ACT PASS`) all pass, 6 `WROTE`.
- `git status --short` shows only: `cad/act2/ap.py`, `cad/act2/p_act.py`, `cad/act2/act_checks.py`, `cad/act2/BOM.md`, `renders/a1_*.png`, `docs/STATUS-act2.md`.

## Status + commit (always the last steps, also after a BLOCKED)
S.1 APPEND to `docs/STATUS-act2.md` (keep everything above it):
```
## Stage A1c — <today's date> — PASS or FAIL
- Gate lines (literal, copy-paste): <step 3 three lines> | <step 5 all lines> | <step 6 ALL lines incl. GATE PASS/FAIL and rc> | <step 7 line>
- Patch: <step 2 line count + PATCH a1c OK>   MOT_H 22 check: <step 8 line>
- Part bboxes + volumes: <step 4 output>   Render review: <one line per view>
- Files changed: <git status --short>   BLOCKED: <none | lines>
- Assembly: motor in from the front, 3x M3x6 from the back into the stator base; puck + magnet + M3x4 onto the shaft end before the AS5600 board; hub onto the bell top with 2x M3x5 + Loctite; then 6702s, discs, ring pins, carrier, 6808, rings, flange.
- Still UNVERIFIED (check on the first real motor): MOT_H 19.0 vs 22.0 (22 needs length 58.0); 34 mm rotor-hole positions and thread depth; stator-base thread depth; washer recess for the puck nose (>= d8 x 0.5); what sits at the bell-top centre (d3.0 x 4.0 clearance); where the phase wires leave the motor; AS5600 chip height (gap 0.95); ENC_W; 6808 lands; link pilot grip.
```
S.2 `cd ~/Vector-wt/act2c && /usr/bin/git status --short` → only the files in the gate list. NO `out/`, `.stl`, `.step`, `__pycache__`.
S.3 `/usr/bin/git add <those paths> && /usr/bin/git commit -m "A1c: motor turned round, hub bolted to Tarot bell top (34 mm holes), magnet puck on shaft end, mid_plate removed"` → `[arm-actuator2c <hash>] A1c: ...`
S.4 Only if the stage PASSED: `/usr/bin/git tag act-1c-done`. Then (always): `/usr/bin/git push -u origin arm-actuator2c --tags` → ends with `* [new tag] act-1c-done -> act-1c-done` (PASS) or the branch line (FAIL). If rejected: `/usr/bin/git pull --ff-only origin arm-actuator2c` once, push again; else `BLOCKED: push`.
S.5 STOP. Do not start another stage. Do not touch `arm-actuator2`, `arm-actuator2b` or `arm-knuckle`.
