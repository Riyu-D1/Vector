# Stage 2 — shoulder (J2) + upper arm + J3 mount
> Before you start: you already read `~/Vector/ARM_KNUCKLE_V5.md`. Rules 0.1–0.10 apply to every step.
> Work dir for every command unless the step says otherwise: `~/Vector-wt/knuckle`.
> `PY=/Users/deepakdiwan/soma/.venv/bin/python` — type this first in every new shell: `export PY=/Users/deepakdiwan/soma/.venv/bin/python`.
> "Expected" = the output must match (numbers may differ by ±0.05 unless stated). If it does not match: re-run once, then do the "If not" line.


**Goal:** build upper_arm and upper_cover, check them against the turret, J2 and J3 motors, render, commit.
**Branch:** `arm-knuckle`, tag `stage-2-done`. **Inputs:** stage 1 commit (cad/knuckle code, `out/` STLs from S1 — rebuild them if `out/` is missing).

## Steps
1. Command: `cd ~/Vector-wt/knuckle && /usr/bin/git describe --tags --abbrev=0`
   Expected: `stage-1-done`. If not: STOP, `BLOCKED: stage 1 not done`.
2. Command: `cd cad/knuckle && ls out/turret.stl out/vendor_J2.stl`
   Expected: both paths printed. If "No such file": run `$PY build.py drum drum_cap turret kn_endcap vendor_J1 vendor_J2 2>&1 | grep -v Warning` (output = S1 step 8).
3. Command: `$PY build.py upper_arm upper_cover vendor_J3 2>&1 | grep -v Warning`
   Expected:
   ```
   upper_arm: bbox=(-38.0, 183.0, -74.8, -25.0, 112.0, 188.0) vol=127.8
   upper_cover: bbox=(-38.0, 183.0, -79.8, -74.8, 112.0, 188.0) vol=72.8
   vendor_J3: bbox=(123.5, 176.5, -63.2, -24.2, 123.5, 176.5) vol=67.2
   ```
4. **GATE** Command: `$PY gate.py out/turret.stl out/kn_endcap.stl out/vendor_J2.stl out/upper_arm.stl out/upper_cover.stl out/vendor_J3.stl; echo rc=$?`
   Expected: all part lines end `OK`; `PRESS kn_endcap x turret` line ok; `GATE PASS`; `rc=0`.
   Known risk: `upper_arm ... minwall=1.59 BAD` (limit 1.6, it is the 2nd percentile of random rays). Fallback (only this one, only if that is the ONLY BAD line): re-run step 4 once; if still 1.59 write `minwall 1.59 accepted (thin rim at pillar fillet), needs Riyansh OK` in STATUS and treat the gate as PASS. Any other BAD line → STOP, write the lines, `BLOCKED: S2 gate`.
5. Render: `printf 'out/turret.stl 0.85 0.85 0.88\nout/kn_endcap.stl 0.25 0.25 0.28\nout/upper_arm.stl 0.85 0.85 0.88\nout/upper_cover.stl 0.25 0.25 0.28\nout/vendor_J2.stl 0.9 0.4 0.1\nout/vendor_J3.stl 0.9 0.4 0.1\n' > out/renders/s2.txt && /usr/local/bin/blender -b -P render_blend.py -- out/renders/s2 out/renders/s2.txt 2>&1 | grep WROTE`
   Expected: 6 `WROTE` lines (`mkdir -p out/renders` first if it says no such directory).
6. Review ×3 (as S1 steps 11–13): (1) look at all 6; J3 motor hidden in upper arm, cover closes the −Y side flush; (2) re-render without upper_cover (list `s2b.txt`) and check the 4 pillars + magnet pockets and the cable groove around J2; (3) re-render full list, confirm. Write 1 line per view in STATUS.

## Gate before commit
- Step 4 `GATE PASS` (or the single allowed fallback). Step 5: 6 `WROTE`.
- `/usr/bin/git status --short` shows only `docs/STATUS-knuckle.md` (code is unchanged in this stage).

## Status + commit (always the last steps)
S.1 Append to `docs/STATUS-knuckle.md` (create it if missing, first line `# STATUS — knuckle arm (branch arm-knuckle)`) a section:
```
## Stage 2 — <today's date> — PASS or FAIL
- Gate lines: <paste every line that ends in PASS/FAIL/BAD from this stage>
- Files added/changed: <list from `/usr/bin/git status --short`>
- Fallbacks used: <none | list>
- UNVERIFIED values touched: <none | list>
- Questions for Riyansh: <none | list>
```
S.2 Command: `cd ~/Vector-wt/knuckle && /usr/bin/git status --short`
Expected: only the files this stage names, plus `docs/STATUS-knuckle.md`. NO `out/`, NO `.stl`, NO `__pycache__`. If not: delete/unstage the extra paths (do not commit them).
S.3 Command: `/usr/bin/git add -A <the paths from S.2> && /usr/bin/git commit -m "stage 2: shoulder and upper arm checked"`
Expected: `[arm-knuckle <hash>] stage 2: shoulder and upper arm checked`
S.4 Command: `/usr/bin/git tag stage-2-done && /usr/bin/git push origin arm-knuckle --tags`
Expected: ends with `* [new tag]         stage-2-done -> stage-2-done`. If push is rejected: run `/usr/bin/git pull --ff-only origin arm-knuckle` once and push again; if still rejected write `BLOCKED: push` in STATUS and stop.
S.5 STOP. Do not start the next stage.

Files for this stage: `docs/STATUS-knuckle.md` only.
