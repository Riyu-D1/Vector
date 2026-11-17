# Stage A1b — fix the 3 minwall BADs of the printed actuator + real Tarot base screws
> Before you start: you already read `~/Vector/ARM_KNUCKLE_V5.md`. Rules 0.1–0.10 apply, with these overrides for this stage only:
> (a) branch is `arm-actuator2b` (made from `arm-actuator2` @ `b12dcd9`), worktree `~/Vector-wt/act2b`; never commit, push or tag on `arm-actuator2` or `arm-knuckle`;
> (b) every number lives in `cad/act2/ap.py`; rule 0.6 applies to ap.py. Change ONLY the lines this file names;
> (c) status file is `docs/STATUS-act2.md` (APPEND a new section, never rewrite the A1 section).
> Work dir: `~/Vector-wt/act2b/cad/act2`. Type first in every new shell: `export PY=/Users/deepakdiwan/soma/.venv/bin/python`.
> "Expected" = output must match (numbers ±0.05 unless stated). If not: re-run once, then do the "If not" line.
> Do NOT edit: `cad/knuckle/*` (gate.py, frames.py, render_blend.py), `cad/act2/cyc.py`, `cad/act2/act_checks.py`, `cad/act2/build_act.py`, any file in `~/Vector/stages/` (read only).

**Goal:** the same actuator as A1, with every printed part passing gate.py `minwall ≥ 1.60`, no INTERF, then renders, status, commit, tag `act-1b-done`, push.
**Why:** A1 (`docs/STATUS-act2.md`) failed only on minwall: housing 0.99, mid_plate 0.83, hub 1.24. The designer traced each one and tested the fixes below on a copy of `b12dcd9` (designer's literal gate output is in step 7). You apply them with a tested patch script, so you type no geometry yourself.
**Inputs (read only):** `~/Vector/stages/code/act2b/patch_a1b.py` (tested patch), `~/Vector/stages/code/act2b/tarot_meas.py` (tested STEP measurer), `docs/STATUS-act2.md` (A1 result), `~/Vector/stages/A1_printed_actuator.md` (A1 brief: Z stack, part recipes).

## 0. What was wrong and what changes (all checked by the designer with gate.py's own min_wall, seed 1, 3000 samples; the gate value is the 2nd percentile, so a part fails when more than 60 of 3000 samples are < 1.6)
| Part | A1 cause (measured) | A1b fix | ap.py / p_act.py change |
|---|---|---|---|
| housing 0.99 | (1) 41 pin grooves Ø3.05 at R 23.5, pitch 3.598 → 0.55 web tips at the Ø47.0 bore; 67 thin samples at r 23.5–24.1. (2) radial CSK tunnel: 1.0 ligament bore→tunnel; 36 more thin samples at Z 29–34 | (1) bore in the pin zone Ø47.0 → **Ø47.4** (bore radius 23.7 = R + 0.2): cuts off the thinnest 0.2 of each web tip. Pins stay at R 23.5, grooves 1.325 deep of the 1.5 pin radius. (2) the 3 radial M3 countersunk screws are **removed** | `BORE_PIN = 47.4`; `CSK_ANG = ()` (the CSK loops in housing() and mid_plate() then do nothing) |
| mid_plate 0.83 | Ø2.5 radial pilots centred in a 4.0 plate → 0.75 roof/floor; 118 of 129 thin samples | no radial holes. Anti-rotation instead by **3 round lugs** Ø(2·RP − 0.1) = Ø2.9 on the plate rim at the ring-pin centres k = 0, 14, 27 (0.00°, 122.93°, 237.07°), Z 29.5–33.5. The housing gets those 3 pin grooves extended down through Z 29.5–33.51 as keyways (0.075 per side). The plate slides in from the front, lugs riding in the 3 grooves; the 3 ring pins at k = 0/14/27 then stand on the lug tops | `KEY_PINS = (0, 14, 27)`, `KEY_CLR = 0.1` (new); 4 lines added to housing(), 4 to mid_plate() |
| hub 1.24 | grub pilot Ø2.5 at Z 35.8 → 0.75 roof to the hub back face Z 33.8; 76 thin samples | grub moved to **Z 37.95** (= Z_CAM_SPLIT): 2.9 to the back face, 3.05 to the cam2 top | `GRUB_Z = 37.95` |
| (motor) | MOT_PCD 25 / 4 screws was a guess [U] | from the BOPP community STEP: stator base has **4× M3 on PCD 19.0** and **3× M3 on PCD 32.0** (= the published "19 mm" and "27.7 mm triangle"). Use the 3× PCD 32 (the PCD 19 counterbores would leave 0.4 to the Ø12 stator hole) | `MOT_PCD = 32.0; MOT_SCREW_ANG = (30.0, 150.0, 270.0)` — only if step 2 succeeds |

Axial hold of mid_plate after the change: the housing step at Z 29.5 behind it, the ring pins → pin_ring → 6808 → front_ring stack in front (same stack as A1). At assembly: 1 drop of CA on each lug.
Nothing else changes: Z stack, OD 57, length 55, gear (40 lobes / 41 pins, E 0.42, CLR 0.15), discs, carrier, flange, rings.

## 1. Steps (in this order)
1. Command: `cd ~/Vector-wt/act2b && /usr/bin/git branch --show-current && /usr/bin/git log --oneline -1 && /usr/bin/git status --short`
   Expected: `arm-actuator2b`, then `b12dcd9 A1: printed 40:1 cycloid actuator module`, then nothing. If not: STOP, `BLOCKED: worktree`.
2. **Tarot 4008 community STEP** (motor data; never a failure).
   a. Command (≤ 1 min): `curl -sL -o /tmp/tarot4008_bopp.step "https://raw.githubusercontent.com/Biped-Open-Platform-Project/bopp-protoypes/main/SOLIDWORKS%20Models/Tarot%204008%20Motor%20Assembly.STEP"; ls -l /tmp/tarot4008_bopp.step; head -1 /tmp/tarot4008_bopp.step`
      Expected: size `7225904`, first line `ISO-10303-21;`.
   b. GrabCAD (`https://grabcad.com/library/tarot-mt4008-motor-1`) needs a login (HTTP 403 to scripts). Do NOT try to log in. Write in STATUS: `GrabCAD Tarot MT4008: login required, not downloaded`.
   c. If 2a failed (other size, or no `ISO-10303-21;`): write in STATUS `Tarot STEP not downloadable: kept guessed MOT_* values` and SKIP steps 2d and 3b. This is NOT a failure.
   d. Command (about 2 min, from `cad/act2`): `$PY ~/Vector/stages/code/act2b/tarot_meas.py /tmp/tarot4008_bopp.step 2>&1 | grep -v Warning | grep -E "ASSEMBLY|OD-solid|STATOR_BASE|on-axis|d=2.40"`
      Expected (the motor axis is Y in this file; stator base face Y −9.75):
      ```
      ASSEMBLY x -22.25..27.03 y -12.35..9.25 z -22.25..22.25
      OD-solid vol=2602 dia=44.50 y -9.75..4.00
      OD-solid vol=2235 dia=44.50 y -8.75..9.25
      OD-solid vol=1405 dia=44.50 y -4.75..5.05
      STATOR_BASE_Y -9.75
      on-axis solid ... (8 lines; the two smallest:)
      on-axis solid vol=87 dia=9.07 y -11.75..-9.25  below-base=2.00
      on-axis solid vol=55 dia=5.70 y -12.35..-5.70  below-base=2.60
      BASE_CIRCLE d=2.40 ... pcd=32.00   (3 lines, 120° apart)
      BASE_CIRCLE d=2.40 ... pcd=18.99   (4 lines, 90° apart)
      ```
      What the numbers mean (write each as one line in STATUS under `Tarot STEP measured:`):
      - OD 44.50 = MOT_D 44.5 → no change.
      - body height = bell top 9.25 − base −9.75 = **19.0** vs MOT_H 22.0 (Tarot's 22 probably includes the prop seat). **Keep MOT_H 22.0 and Z_MOTOR (7.5, 29.5)** (larger envelope = safe). Write `FLAG MOT_H: STEP 19.0 vs 22.0 kept (>0.5); if real, the bell top is 3.0 further from the AS5600 (magnet gap 1.25 → 4.25, over the 3.0 max) — next stage`.
      - shaft below the base: **none** — there is no Ø4 on-axis solid below Y −9.75; the shaft is held by an M3 button screw (head Ø5.70, 2.60 below the base) and a Ø9.07 washer (2.00 below). **Keep SHAFT_OUT 12 [U]** (the hub needs it). Write `FLAG SHAFT_OUT: STEP shows no shaft past the stator base (screw+washer only, 2.6 proud); hub-on-shaft drive needs redesign — next stage`.
      - centre boss: none; washer Ø9.07 and screw head Ø5.70 fit inside STATOR_HOLE_D 12.0 (Z 29.5–32.1 inside the 4.0 plate, hub starts Z 33.8) → no change. Write `STATOR_HOLE_D 12.0 kept: clears washer 9.07 / head 5.70`.
      - base holes: 3× Ø2.40 (M3 tap) on PCD 32.00 and 4× on PCD 18.99 → step 3b. Write `FLAG MOT_PCD: 25.0 → 32.0, 4 → 3 screws (>0.5)`.
      If the PCD 32 lines are missing or differ by > 0.3: do NOT run step 3b, write the measured lines in STATUS, continue (not a failure).
3. **Patch** (from `cad/act2`; each mode only once — a second run stops with AssertionError on purpose):
   a. `$PY ~/Vector/stages/code/act2b/patch_a1b.py minwall`
      Expected: 6 lines `PATCHED ...` (4 × ap.py, 2 × p_act.py), then `PATCH minwall OK`.
   b. Only if step 2d passed: `$PY ~/Vector/stages/code/act2b/patch_a1b.py motor` → 1 line `PATCHED ap.py: MOT_PCD = 32.0; ...`, then `PATCH motor OK`.
   c. `grep -nE "^(BORE_PIN|CSK_Z|GRUB_Z|MOT_PCD|KEY_PINS|KEY_CLR) " ap.py` → 6 lines (`BORE_PIN = 47.4`, `CSK_Z = 31.5; CSK_ANG = ()`, `GRUB_Z = 37.95`, `MOT_PCD = 32.0` or the old 25.0 if 3b skipped, `KEY_PINS = (0, 14, 27)`, `KEY_CLR = 0.1`).
   If any AssertionError in 3a: `/usr/bin/git checkout cad/act2/ap.py cad/act2/p_act.py` once and re-run 3a; if again: STOP, `BLOCKED: patch`.
4. **GATE G1** (gear maths, unchanged): `$PY cyc.py | head -1 && $PY cyc.py 40 | tail -2` → `RATIO 40.0`, `disc r_min 21.580 r_max 22.420  out-pin hole d 4.14  pin pitch 3.598`, `CYC PASS`. If not: STOP, `BLOCKED: cyc`.
5. **Build** (about 1 min): `rm -rf out && $PY build_act.py 2>&1 | grep -v Warning`
   Expected 19 lines, no Traceback. These bboxes changed or must hold (±0.05):
   - `housing: bbox=(-28.5, 28.5, -28.5, 28.5, 0.0, 54.4) vol=45.9`
   - `mid_plate: bbox=(-23.4, 24.95, -23.4, 23.4, 29.5, 33.5) vol=6.1` (x max 24.95 = the lug at 0°: 23.5 + 1.45)
   - `hub: bbox=(-7.92, 7.92, -7.5, 7.5, 33.8, 47.2) vol=1.5`
   - `disc1: bbox=(-21.78, 22.62, -22.2, 22.2, 33.8, 37.8) vol=4.3`, `disc2: bbox=(-22.69, 21.85, -22.27, 22.27, 38.1, 42.1) vol=4.3`
   - every other line identical to the A1 bboxes in STATUS-act2.md.
   Then `ls out/*.step | wc -l` → `19` and `ls out/*.stl | wc -l` → `19`. If a part fails: STOP, `BLOCKED: build <part>` (do not hand-edit geometry).
6. **GATE G2/G3**: `$PY act_checks.py; echo rc=$?` → 9 lines `watertight=True` (mid_plate `rmax=24.95`), `LENGTH 55.00 OK`, `OD 57.00 OK`, `ACT PASS`, `rc=0`. If not: STOP, `BLOCKED: act_checks`.
7. **GATE G4/G5** (minwall ≥ 1.60 + interference). Slow: about 15–20 min with no output until the end (normal; do not kill it before 30 min). Command:
   `$PY ../knuckle/gate.py out/housing.stl out/mid_plate.stl out/hub.stl out/disc1.stl out/disc2.stl out/carrier.stl out/out_flange.stl out/pin_ring.stl out/front_ring.stl out/vendor_*.stl; echo rc=$?`
   Expected (designer's run, motor patch applied):
   ```
   housing: watertight=True bbox=57.0x57.0x54.4 max=57.0 minwall=1.79 OK
   mid_plate: watertight=True bbox=48.3x46.8x4.0 max=48.3 minwall=2.09 OK
   hub: watertight=True bbox=15.8x15.0x13.4 max=15.8 minwall=3.05 OK
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
   vendor_motor: watertight=True bbox=44.5x44.5x34.0 max=44.5 minwall=99.00 OK
   vendor_outpins: watertight=True bbox=31.6x36.0x12.0 max=36.0 minwall=99.00 OK
   vendor_ringpins: watertight=True bbox=49.9x50.0x10.0 max=50.0 minwall=99.00 OK
   GATE PASS
   rc=0
   ```
   Must hold: all 9 printed lines `OK`, **zero** lines starting with `INTERF`, `GATE PASS`, `rc=0`. Minwall values may differ by ±0.05 (or more if step 3b was skipped; then only `OK` matters).
   No `--allow` and no fallbacks are allowed in this stage. If any `BAD` or `INTERF`: STOP, write `BLOCKED: gate <the exact line>` in STATUS, still do steps 8–9 and the status/commit steps, and report FAIL.
8. **GATE G6** (tooth clearance): `$PY -c "import cyc; print(cyc.mesh_clearance(40), cyc.mesh_clearance(40, second=True))"` → `(0.144..., 0.144...) (0.144..., 0.144...)`; both first numbers ≥ 0.10. If not: STOP, `BLOCKED: mesh`.
9. **50:1 dry run** (do not commit its STLs; this proves the lugs follow RP): `sed -i '' 's/^RATIO = 40 /RATIO = 50 /' ap.py && $PY build_act.py disc1 disc2 housing mid_plate 2>&1 | grep -v Warning && sed -i '' 's/^RATIO = 50 /RATIO = 40 /' ap.py && $PY build_act.py disc1 disc2 housing mid_plate 2>&1 | grep -v Warning && grep '^RATIO' ap.py`
   Expected: 8 bbox lines, no Traceback, last line `RATIO = 40 ...`. Record the four 50:1 bboxes in STATUS. Then re-run step 6 once → `ACT PASS`.
10. **Render** (same as A1 step 11). Write `/tmp/act_list.txt`, one line each `<abs path stl> r g b`:
    - housing 0.85 0.85 0.88; mid_plate, pin_ring, front_ring 0.25 0.25 0.28;
    - disc1 0.20 0.45 0.85; disc2 0.15 0.65 0.45; hub, carrier, out_flange 0.95 0.55 0.10;
    - all 10 vendor_* 0.6 0.6 0.6. (abs path = `/Users/deepakdiwan/Vector-wt/act2b/cad/act2/out/<name>.stl`)
    Command: `mkdir -p ~/Vector-wt/act2b/renders && /usr/local/bin/blender -b -P ../knuckle/render_blend.py -- ~/Vector-wt/act2b/renders/a1 /tmp/act_list.txt 2>&1 | grep WROTE`
    Expected: 6 `WROTE` lines (`a1_frontiso … a1_cutaway`), overwriting the A1 PNGs. Look at each PNG, 1 line per view in STATUS. Pass criteria:
    (a) cutaway order motor → mid plate → two discs → carrier → 6808 → flange; (b) ring pins half buried; (c) no part floats;
    (d) **no radial screw holes anywhere on the Ø57 outside** (A1 had 3; they are gone); (e) outline a plain Ø57 cylinder (only the wire notch at 90°).
    PNGs ≤ 1.5 MB each; if bigger, leave that PNG out of the commit and note it.
11. **BOM** — edit `cad/act2/BOM.md`, exactly these 2 table rows, nothing else:
    - delete the row `| 3 | M3×6 ISO 10642 countersunk (radial, housing → mid_plate) | | |`
    - if step 3b ran: change `| 4 | M3×6 ISO 7380 (stator → mid_plate) [U length, Q3] | | |` to `| 3 | M3×6 ISO 7380 (stator → mid_plate, PCD 32) [U length] | | |` (if those exact rows are not found, write `BOM rows not found` in STATUS and leave BOM.md as is).
12. Copy the measurer into the repo: `cp ~/Vector/stages/code/act2b/tarot_meas.py ~/Vector-wt/act2b/cad/act2/tarot_meas.py` (only if step 2d ran).

## Gate before commit
- Steps 4 (`RATIO 40.0`, `CYC PASS`), 6 (`ACT PASS`, `LENGTH 55.00 OK`, `OD 57.00 OK`), 7 (9 × `OK`, no `INTERF`, `GATE PASS`), 8 (≥ 0.10) all pass, 6 `WROTE`.
- `git status --short` shows only: `cad/act2/ap.py`, `cad/act2/p_act.py`, `cad/act2/BOM.md`, `cad/act2/tarot_meas.py` (if step 12), `renders/a1_*.png`, `docs/STATUS-act2.md`.

## Status + commit (always the last steps, also after a BLOCKED)
S.1 APPEND to `docs/STATUS-act2.md` (keep everything above it):
```
## Stage A1b — <today's date> — PASS or FAIL
- Gate lines (literal, copy-paste): <step 4 three lines> | <step 6 all lines> | <step 7 ALL lines incl. GATE PASS/FAIL and rc> | <step 8 line>
- Patch: <step 3a/3b PATCHED lines>   Tarot STEP: <step 2 lines + FLAG lines, or the not-downloadable note>   GrabCAD: <step 2b line>
- Part bboxes + volumes: <step 5 output>   50:1 dry run: <step 9 bboxes>
- Render review: <one line per view>
- Files changed: <git status --short>   BLOCKED: <none | lines>
- Assembly note: mid_plate goes in from the front, lugs in the 3 grooves at 0 / 122.9 / 237.1 deg, 1 drop CA per lug; then the 41 ring pins.
- Still UNVERIFIED: SHAFT_OUT 12 (STEP: no shaft past the base), MOT_H 22 (STEP 19.0), ENC_W, 6808 lands, link pilot grip.
```
S.2 `cd ~/Vector-wt/act2b && /usr/bin/git status --short` → only the files in the gate list. NO `out/`, `.stl`, `.step`, `__pycache__`. If others show: do not add them.
S.3 `/usr/bin/git add <those paths> && /usr/bin/git commit -m "A1b: actuator minwall fixes (pin bore 47.4, keyed mid_plate, grub at cam split), Tarot base PCD32"` → `[arm-actuator2b <hash>] A1b: ...`
S.4 Only if the stage PASSED: `/usr/bin/git tag act-1b-done`. Then (always): `/usr/bin/git push -u origin arm-actuator2b --tags` → ends with `* [new tag] act-1b-done -> act-1b-done` (PASS) or the branch line (FAIL). If rejected: `/usr/bin/git pull --ff-only origin arm-actuator2b` once, push again; else `BLOCKED: push`.
S.5 STOP. Do not start another stage. Do not touch `arm-actuator2` or `arm-knuckle`.
