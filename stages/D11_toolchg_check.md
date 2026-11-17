# Stage D11 — Full proper check of every tool-changer part designed in D10 (read-only audit, report only)
> Rules 0.1-0.10 of `~/Vector/ARM_KNUCKLE_V5.md` apply. Never edit existing product files. Step 0: `cd ~/Vector && /usr/bin/git fetch origin --tags`; create worktree `~/Vector-wt/toolchgchk` on new branch `arm-toolchg-check` from `origin/arm-toolchg` (tip of D10, tag `toolchg-1-done`, commit 7003ea8). Work ONLY in new files under `toolchg/check/`. Tag `toolchgchk-done`, push branch+tags, STOP. Do not merge to main or to `arm-toolchg`. If you find a real error, DO NOT fix the CAD/firmware: list it with severity and an exact proposed fix in `toolchg/check/proposed_fixes.md`.

## Context (read first)
Read `toolchg/STATUS-toolchg.md`, `toolchg/CONCEPTS.md`, `toolchg/tc_params.py`, `toolchg/p_toolchg.py`, `toolchg/build_toolchg.py`, `toolchg/tc_checks.py`, `toolchg/tc_collision.py`, `toolchg/tc_analysis.py`, `toolchg/fea/`, `toolchg/mjcf_tc/`, `software/robot-os/soma_arm/toolchange.py`, `software/robot-os/tests/test_toolchange.py`, and the wrist/cradle sources they import (`cradlefix/ap6.py`, `final2/f2_collision.py` pattern, `software/robot-os/soma_arm/gravity.py`). Python for CAD: `PY=/Users/deepakdiwan/soma/.venv/bin/python`. MuJoCo: the existing `~/Vector-wt/sim/.venv-mj` / mjpython path used by cradlefix. This is a CHECK of D10, not a redesign.

## Goal
One complete, honest check of EVERY part D10 designed, plus the coupling fits, FEM, collisions, mass/torque, MuJoCo dock, firmware planner and BOM claims. Re-run the existing scripts with real output pasted into the report. Never invent a number; quote script output and datasheet lines. Mark anything you cannot verify `[U]`.

## Parts under check (all 11 from `p_toolchg.parts()`)
1. `tc_master` — arm-side master plate + spigot + 3 lugs + detent dimple + pogo pads
2. `tc_plate` — tool socket plate + 3 catches + dock groove + key notch + detent bore + pogo bores
3. `tool_grip` — gripper body adapted to the tool plate (new copy)
4. `tool_pen` — pen/pointer holder tool
5. `tc_vendor_g` — STS3215 servo proxy (geometry envelope only)
6. `tc_gear` — gripper gear
7. `tc_rack_u` / `tc_rack_d` — gripper racks
8. `tc_finger_u` / `tc_finger_d` — gripper fingers
9. `tc_rack` — 4-slot docking rack on the table

Also check the non-printed interface: 5 pogo pins, Ø5 steel ball + spring + grub, M2/M3 heat-set inserts + screws, Ø3×10 dowels, STS3215 envelope vs `tool_grip` pocket.

## Method

### 1. Per-part geometry (every printable part)
For each of the 11 parts, rebuild with `PY build_toolchg.py <name>` (or the existing build path) and record:
- watertight? (manifold / closed solid; volume finite and > 0)
- volume cm³, bbox mm, claimed mass g vs `volume * RHO_PETGCF * INFILL_EFF`
- min wall thickness anywhere ≥ 1.8 mm (measure critical sections: lug root, catch shelf, dock-groove floor under the OD, spigot wall, finger roots, rack fork tines, plate around bolt holes). If you cannot run an automatic thickness tool, cut named sections and measure, and say which method you used.
- overhangs ≤ 45° for the stated print orientation in STATUS; list any face that needs support
- Bambu A1 bed fit (256×256×256 mm usable): does `tc_rack` and every other part fit in the stated orientation?
- detached/sliver solids: STATUS admits ~1 mm³ slivers on `tool_grip` inherited from `w_grip_frame` — confirm count/volume on every part; FAIL any NEW sliver not inherited
Paste real script output. One row per part in the report table.

### 2. Coupling fit & claimed clearances (re-run + independent measure)
Re-run `PY tc_checks.py` and paste full C1–C6 output. Independently measure (BRep / section) and compare to `tc_params.py` claims:
- lug tip r 17.3 vs socket bore 18.2 → 0.9 mm radial gap
- catch inner r 13.2 vs spigot r 13.0 → 0.2 mm
- lug −a face 72.4 vs catch face 72.2 → 0.2 mm running gap
- spigot tip 75.8 vs floor 76.0 → 0.2 mm (pogo bridge)
- entry roll −12° puts lugs in catch gaps with claimed margin; +60° twist centres them under catches
- detent: ball path clear at entry, seated in dimple at lock; dimple phase = 62° master frame
- dock groove band vs rack plate thickness (±0.5 claimed); key notch engages rack anti-rotation
- master horn bolt pattern vs the real J6 horn / `w_grip_frame` CB pattern (`GF_CB_A`, PCD) — must match so the master bolts on
- pogo bore Ø1.8 and pad arcs: pads span the full entry→lock 48° sweep; pin phases do not collide with structure
FAIL any claimed clearance that the solid geometry does not actually provide. Allowances in C2 (≤12 mm³) must be justified by named interfering features (detent poke etc.), not hand-waved.

### 3. FEM — every load-bearing part, not just master/plate
Re-run the existing CalculiX pipeline on `tc_master` and `tc_plate` and paste real maxVM / max|U| / SF vs 25 MPa cross-layer `[U]`. ADD checks (same free tools, interactive HTML under `toolchg/check/fea/`):
- catch shelf / lug pair at lock under the 0.5 kg+tool wrench (the actual capture path)
- `tool_pen` body + plate under tip load (pen tip force ≥ 5 N lateral `[U]` state assumption)
- `tool_grip` servo-pocket / neck under servo + 0.5 kg TCP
- `tc_rack` fork/tine at one occupied slot under tool weight + a 1.5× docking bump `[U]`
Report SF; if SF < 2 against 25 MPa cross-layer `[U]`, mark FAIL (blocks adopt) with the number. Mesh size, BC and load must be written so the run is reproducible. Material numbers stay `[U]`.

### 4. Collision + dock path
Re-run `PY tc_collision.py` (full J4/J5/J6 sweeps, J6/J5 grid with sublimit, named corners, Monte-Carlo, DOCK/UNDOCK slots 0–3). Paste real output. Confirm the two inherited wrist grazes are still only the declared product pairs and that no NEW collision is introduced by D10 geometry. FAIL any new hit.

### 5. Mass, CoG, joint torque, payload
Re-run `PY tc_analysis.py` (or equivalent gravity path). Confirm J6-side mass ≤ 234 g budget, and the claimed improvement vs stock grip (94.5 vs 101.8 g J6-out). Confirm worst-case J2/J3/J4/J5 torque ratios under 0.5 kg close / ~0.41 kg full-reach still inside derated margins. FAIL if over budget or if STATUS numbers do not match the script output.

### 6. MuJoCo dock
Rebuild `mjcf_tc` if needed, run `run_tc.py` headless, paste real output (seat gap, seated err, lift, undock, finite qpos). Confirm seated pose error ≤ 0.5 mm and no assertion failures. FAIL otherwise.

### 7. Firmware planner
Run `pytest software/robot-os/tests/test_toolchange.py -q` from the worktree and paste real output. Independently review `toolchange.py`:
- J6 sublimit when J5 < 0 is enforced on every waypoint
- lock/unlock is a pure J6 roll of the designed ±60° (or the net +48° entry→lock — state which, and that it matches CAD)
- speed/accel/torque caps present; `verify_latch` uses position error + load signature
- no edits to existing product modules (new files only)
FAIL any mismatch with CAD twist/entry numbers or a missing sublimit guard.

### 8. BOM / hardware vs CAD holes
For each non-printed BOM line in STATUS, either (a) find a live UK source with price and today's date, or (b) leave `[U]` and say why. Separately check CAD feature sizes against typical real parts (do not invent a part that does not fit):
- pogo barrel vs Ø1.8 bore and 0.8 tip proud
- Ø5 ball + ~Ø4×8 spring + M3 grub vs detent bore Ø4.2 and dimple
- M2/M3 heat-set insert OD/length vs boss/hole sizes in master and tool plate
- Ø3×10 dowel vs tool-plate keying holes
- STS3215 body 45.2×24.7×35.7 + horn vs `tool_grip` pocket / `vendor_g`
FAIL any CAD hole that cannot accept the named hardware class.

### 9. STATUS claim audit
Build a table of every quantitative claim in `STATUS-toolchg.md` (masses, SF, pose errors, clearances, test counts, payload deltas). Tick PASS if the re-run matches within rounding; FAIL if STATUS and scripts disagree; `[U]` if still unverifiable. Be harsh: D10 wrote the STATUS, this stage is the independent check.

## Deliverable
`toolchg/check/CHECK-toolchg.md`:
1. Summary counts: parts checked, checks run, PASS / FAIL / `[U]`
2. Per-part table (geometry + printability)
3. Coupling/clearance table with measured vs claimed
4. FEM table with SF numbers and HTML paths under `toolchg/check/fea/`
5. Collision, mass, MuJoCo, pytest: pasted real output + verdict
6. BOM / hardware fit table
7. STATUS claim audit table
8. Every FAIL with severity (`blocks-print` / `blocks-dock` / `blocks-adopt` / `cosmetic`), exact evidence, and a proposed fix written in `toolchg/check/proposed_fixes.md` (patch description only — do not apply)
9. Safety notes: 12 V tool bus, small spring/ball parts, no mains, no magnets in the built design
10. Honest recommendation: `ready to print prototype` / `fix then print` / `do not adopt` — based only on this check

Also keep any helper scripts you wrote for thickness/section/audit under `toolchg/check/` (not in product paths). Commit, tag `toolchgchk-done`, push branch+tags, STOP. Do not merge. Do not start a redesign.
