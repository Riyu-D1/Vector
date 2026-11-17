# Stage 5 — hidden cables + covers check
> Before you start: you already read `~/Vector/ARM_KNUCKLE_V5.md`. Rules 0.1–0.10 apply to every step.
> Work dir for every command unless the step says otherwise: `~/Vector-wt/knuckle`.
> `PY=/Users/deepakdiwan/soma/.venv/bin/python` — type this first in every new shell: `export PY=/Users/deepakdiwan/soma/.venv/bin/python`.
> "Expected" = the output must match (numbers may differ by ±0.05 unless stated). If it does not match: re-run once, then do the "If not" line.


**Goal:** prove every cable route is hidden and clear (cable.py), full-arm gate, cutaway renders, write the wiring table. Reference files: `cad/knuckle/cable.py`, `gate.py`, `render_blend.py` (already in repo from S1).
**Branch:** `arm-knuckle`, tag `stage-5-done`. **Inputs:** stage 4 commit.

## Steps
1. `cd ~/Vector-wt/knuckle && /usr/bin/git describe --tags --abbrev=0` → `stage-4b-done`. If not: STOP.
2. `cd cad/knuckle && $PY build.py 2>&1 | grep -v Warning | wc -l` → Expected `22` (16 parts + 6 vendor; lines = S1–S4 step outputs).
3. **GATE A** `$PY cable.py 2>&1 | grep -v Warning` → Expected:
   ```
   A_base_to_J2face: samples=551 CLEAR
   B_upperarm: samples=642 CLEAR
   C_forearm_in: samples=519 CLEAR
   D_wrist: samples=361 CLEAR
   E_gripper: samples=280 CLEAR
   CABLE PASS
   ```
   If BLOCKED: copy the line to STATUS, `BLOCKED: cable`, STOP (no geometry edits).
4. **GATE B** `$PY gate.py out/*.stl; echo rc=$?` (slow, up to 10 min) → `GATE PASS`, `rc=0` (S2–S4 fallbacks apply, same `--allow` flags).
5. Render all 22 STLs (printed parts grey 0.85 0.85 0.88, caps/lids 0.25 0.25 0.28, vendor 0.9 0.4 0.1) to `out/renders/s5` → 6 `WROTE`. Review ×3: no cable path, connector or wire hole visible from outside in frontiso/backiso/side/top/front; only exception: gripper lid rear bump.
6. Write `cad/knuckle/WIRING.md`: table Joint | device | CAN id / servo id | cable route (A–E from cable.py) | connector. J1–J3 GIM CAN ids 1,2,3 (CAN H/L + 24 V daisy chain); J4–J6 STS3215 ids 4,5,6 (12 V + TTL bus daisy chain).

## Gate before commit
Steps 3 and 4 PASS, 6 `WROTE`. Files: `cad/knuckle/WIRING.md`, `docs/STATUS-knuckle.md`.

## Status + commit (always the last steps)
S.1 Append to `docs/STATUS-knuckle.md` (create it if missing, first line `# STATUS — knuckle arm (branch arm-knuckle)`) a section:
```
## Stage 5 — <today's date> — PASS or FAIL
- Gate lines: <paste every line that ends in PASS/FAIL/BAD from this stage>
- Files added/changed: <list from `/usr/bin/git status --short`>
- Fallbacks used: <none | list>
- UNVERIFIED values touched: <none | list>
- Questions for Riyansh: <none | list>
```
S.2 Command: `cd ~/Vector-wt/knuckle && /usr/bin/git status --short`
Expected: only the files this stage names, plus `docs/STATUS-knuckle.md`. NO `out/`, NO `.stl`, NO `__pycache__`. If not: delete/unstage the extra paths (do not commit them).
S.3 Command: `/usr/bin/git add -A <the paths from S.2> && /usr/bin/git commit -m "stage 5: hidden cable routes and wiring table"`
Expected: `[arm-knuckle <hash>] stage 5: hidden cable routes and wiring table`
S.4 Command: `/usr/bin/git tag stage-5-done && /usr/bin/git push origin arm-knuckle --tags`
Expected: ends with `* [new tag]         stage-5-done -> stage-5-done`. If push is rejected: run `/usr/bin/git pull --ff-only origin arm-knuckle` once and push again; if still rejected write `BLOCKED: push` in STATUS and stop.
S.5 STOP. Do not start the next stage.

