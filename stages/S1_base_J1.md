# Stage 1 — setup + base drum + turret (J1, J2 mount)
> Before you start: you already read `~/Vector/ARM_KNUCKLE_V5.md`. Rules 0.1–0.10 apply to every step.
> Work dir for every command unless the step says otherwise: `~/Vector-wt/knuckle`.
> `PY=/Users/deepakdiwan/soma/.venv/bin/python` — type this first in every new shell: `export PY=/Users/deepakdiwan/soma/.venv/bin/python`.
> "Expected" = the output must match (numbers may differ by ±0.05 unless stated). If it does not match: re-run once, then do the "If not" line.


**Goal:** copy the tested CAD code into the repo, build the 4 base parts (drum, drum_cap, turret, kn_endcap), pass the gate, render, commit.
**Branch:** `arm-knuckle` (one commit for this stage, tag `stage-1-done`).
**Inputs:** `~/Vector/stages/code/*.py` (tested), `cad/vendor/*` (already in the worktree, untracked), `cad/arm/reference/sts3215_servo.step`.

## Steps
1. Command: `cd ~/Vector-wt/knuckle && /usr/bin/git branch --show-current && /usr/bin/git log --oneline -1`
   Expected: first line `arm-knuckle`; second line starts with `2eeda06` (or a later `stage N:` commit if someone re-runs). If not: STOP, write `BLOCKED: wrong branch` in STATUS.
2. Command: `ls cad/knuckle 2>/dev/null | wc -l`
   Expected: `0`. If not (a previous attempt): `rm -rf cad/knuckle` and repeat.
3. Command: `mkdir -p cad/knuckle && cp ~/Vector/stages/code/*.py cad/knuckle/ && ls cad/knuckle`
   Expected (14 files): `build.py cable.py frames.py gate.py gate_selftest.py kp.py p_base.py p_fore.py p_grip.py p_upper.py p_wrist.py render_blend.py rom.py selftest.py`
4. Command: `printf 'out/\n__pycache__/\n*.stl\n' > cad/knuckle/.gitignore && cat cad/knuckle/.gitignore`
   Expected: the 3 lines `out/`, `__pycache__/`, `*.stl`.
5. Command: `ls cad/vendor`
   Expected contains: `GIM-protocol.pdf GIM4305-10-2D.pdf GIM4305-10.STEP GIM4310-10-GDS-2D.pdf GIM4310-10-GDS.stp GIM4310-36-2D.pdf GIM4310-36.STEP sts3215.pdf`.
   Decide vendor tracking: run `du -sh cad/vendor`. If ≤ 15M: they will be committed in this stage. If bigger: add `cad/vendor/*.STEP` and `cad/vendor/*.stp` to the repo-root `.gitignore` and commit only the PDFs. Write which one in STATUS.
6. Command: `cd cad/knuckle && $PY selftest.py 2>&1 | grep -v Warning`
   Expected (≈30 s): exactly the block in "Expected selftest" below. If not: STOP, `BLOCKED: selftest` in STATUS (do not edit frames.py).
7. Command: `$PY gate_selftest.py && $PY gate.py out_selftest/a.stl out_selftest/b.stl out_selftest/thin.stl; echo rc=$?; $PY gate.py out_selftest/a.stl; echo rc=$?; rm -rf out_selftest`
   Expected: first gate output CONTAINS `minwall=0.49 BAD` (thin) and `INTERF a x b: 2000.00 mm3 BAD` and ends `GATE FAIL` then `rc=1`; second gate ends `GATE PASS` then `rc=0`. (Other INTERF lines with thin are fine.)
8. Command: `$PY build.py drum drum_cap turret kn_endcap vendor_J1 vendor_J2 2>&1 | grep -v Warning`
   Expected (≈20 s):
   ```
   drum: bbox=(-65.7, 65.7, -65.7, 65.7, 0.0, 74.0) vol=172.4
   drum_cap: bbox=(-48.0, 48.0, -48.0, 48.0, 74.0, 79.0) vol=16.5
   turret: bbox=(-51.0, 51.0, -51.0, 51.0, 51.0, 188.0) vol=212.2
   kn_endcap: bbox=(-38.0, 38.0, 31.0, 35.6, 112.0, 188.0) vol=12.5
   vendor_J1: bbox=(-26.5, 26.5, -26.5, 26.5, 18.0, 51.0) vol=53.7
   vendor_J2: bbox=(-27.5, 27.5, -27.5, 22.8, 122.5, 177.5) vol=91.1
   ```
9. **GATE** Command: `$PY gate.py out/drum.stl out/drum_cap.stl out/turret.stl out/kn_endcap.stl out/vendor_J1.stl out/vendor_J2.stl; echo rc=$?`
   Expected: every part line ends in `OK`; one line `PRESS kn_endcap x turret: 8.36 mm3 ok (press fit)`; last lines `GATE PASS` and `rc=0`.
   If not: copy the BAD lines into STATUS. Fallback (only these): none for geometry — do NOT edit kp.py. Stop and write `BLOCKED: S1 gate` with the BAD lines.
10. Render list. Command:
    ```
    mkdir -p out/renders && printf 'out/drum.stl 0.85 0.85 0.88\nout/drum_cap.stl 0.25 0.25 0.28\nout/turret.stl 0.85 0.85 0.88\nout/kn_endcap.stl 0.25 0.25 0.28\nout/vendor_J1.stl 0.9 0.4 0.1\nout/vendor_J2.stl 0.9 0.4 0.1\n' > out/renders/s1.txt
    /usr/local/bin/blender -b -P render_blend.py -- out/renders/s1 out/renders/s1.txt 2>&1 | grep WROTE
    ```
    Expected: 6 lines starting `WROTE` (frontiso, backiso, side, top, front, cutaway).
11. Review iteration 1: open each of the 6 PNGs in `out/renders/` with your image viewer/Read tool. For each write one line in a scratch note: what you see. Check: (a) orange motors J1 hidden inside the grey drum except in cutaway; (b) J2 motor (orange) hidden in the turret knuckle except in cutaway; (c) no gaps between drum and turret hat other than the thin ring; (d) nothing floating.
12. Review iteration 2: re-render only with `out/turret.stl` and `out/vendor_J2.stl` in the list (new list file `s1b.txt`) and confirm in the cutaway that the J2 cap passes through the bulkhead hole.
13. Review iteration 3: re-render the full list again (step 10 command) and confirm the PNGs are identical in content. Delete nothing. (Renders stay in `out/`, which is git-ignored.)
    Any visible problem → do NOT change geometry; write it under "Questions for Riyansh" in STATUS.

## Expected selftest
```
J1 (-26.5, 26.5, -26.5, 26.5, 18.0, 51.0)
J2 (-27.5, 27.5, -27.5, 22.8, 122.5, 177.5)
J3 (123.5, 176.5, -63.2, -24.2, 123.5, 176.5)
J4 (244.88, 290.11, -19.85, 22.6, 137.64, 162.36)
J5 (327.8, 370.25, -12.36, 12.36, 114.88, 160.11)
J6 (376.25, 400.97, -20.85, 21.6, 126.88, 172.11)
```
(The first 6 lines must match; further lines (pins, cyl tests, yprism, arc) just must print without a Traceback.)

## Gate before commit (all must be true)
- Step 9 printed `GATE PASS`.
- Step 10 printed 6 `WROTE` lines.
- `cad/knuckle/` has the 14 .py files + `.gitignore`, and nothing else is tracked from `out/`.
If any is false: write STATUS (step S.1, marked FAIL), do NOT commit, STOP.

## Status + commit (always the last steps)
S.1 Append to `docs/STATUS-knuckle.md` (create it if missing, first line `# STATUS — knuckle arm (branch arm-knuckle)`) a section:
```
## Stage 1 — <today's date> — PASS or FAIL
- Gate lines: <paste every line that ends in PASS/FAIL/BAD from this stage>
- Files added/changed: <list from `/usr/bin/git status --short`>
- Fallbacks used: <none | list>
- UNVERIFIED values touched: <none | list>
- Questions for Riyansh: <none | list>
```
S.2 Command: `cd ~/Vector-wt/knuckle && /usr/bin/git status --short`
Expected: only the files this stage names, plus `docs/STATUS-knuckle.md`. NO `out/`, NO `.stl`, NO `__pycache__`. If not: delete/unstage the extra paths (do not commit them).
S.3 Command: `/usr/bin/git add -A <the paths from S.2> && /usr/bin/git commit -m "stage 1: base drum, turret, CAD toolkit"`
Expected: `[arm-knuckle <hash>] stage 1: base drum, turret, CAD toolkit`
S.4 Command: `/usr/bin/git tag stage-1-done && /usr/bin/git push origin arm-knuckle --tags`
Expected: ends with `* [new tag]         stage-1-done -> stage-1-done`. If push is rejected: run `/usr/bin/git pull --ff-only origin arm-knuckle` once and push again; if still rejected write `BLOCKED: push` in STATUS and stop.
S.5 STOP. Do not start the next stage.

Files for this stage: `cad/knuckle/*.py`, `cad/knuckle/.gitignore`, `cad/vendor/*` (or only PDFs, see step 5), `docs/STATUS-knuckle.md`.
