# Stage 4 — wrist (J4 pitch, J5 roll) + gripper (J6)
> Before you start: you already read `~/Vector/ARM_KNUCKLE_V5.md`. Rules 0.1–0.10 apply to every step.
> Work dir for every command unless the step says otherwise: `~/Vector-wt/knuckle`.
> `PY=/Users/deepakdiwan/soma/.venv/bin/python` — type this first in every new shell: `export PY=/Users/deepakdiwan/soma/.venv/bin/python`.
> "Expected" = the output must match (numbers may differ by ±0.05 unless stated). If it does not match: re-run once, then do the "If not" line.


**Goal:** build head, cup_cap, pod_front, gripper, grip_lid, jaw, jaw_cap and servo solids J5, J6; gate; render; commit.
**Branch:** `arm-knuckle`, tag `stage-4-done`. **Inputs:** stage 3 commit; `out/forearm.stl`, `out/vendor_J4.stl`.

## Steps
1. `cd ~/Vector-wt/knuckle && /usr/bin/git describe --tags --abbrev=0` → `stage-3-done`. If not: STOP.
2. Command: `cd cad/knuckle && $PY build.py head cup_cap pod_front gripper grip_lid jaw jaw_cap vendor_J5 vendor_J6 2>&1 | grep -v Warning`
   Expected:
   ```
   head: bbox=(255.0, 366.65, -16.11, 38.6, 111.13, 175.0) vol=67.5
   cup_cap: bbox=(259.98, 300.02, 36.6, 38.6, 129.97, 170.03) vol=2.5
   pod_front: bbox=(366.65, 368.3, -16.11, 20.11, 111.13, 163.86) vol=2.5
   gripper: bbox=(368.6, 448.61, -18.0, 19.65, 124.33, 174.66) vol=31.9
   grip_lid: bbox=(368.6, 404.72, -32.25, -18.0, 124.33, 174.66) vol=6.3
   jaw: bbox=(375.61, 448.61, -10.0, 26.95, 149.0, 175.0) vol=12.6
   jaw_cap: bbox=(378.09, 399.13, 24.95, 26.95, 151.47, 172.53) vol=0.7
   vendor_J5: bbox=(327.8, 370.25, -12.36, 12.36, 114.88, 160.11) vol=11.4
   vendor_J6: bbox=(376.25, 400.97, -20.85, 21.6, 126.88, 172.11) vol=11.4
   ```
3. **GATE** Command: `$PY gate.py out/forearm.stl out/vendor_J4.stl out/head.stl out/cup_cap.stl out/pod_front.stl out/vendor_J5.stl out/gripper.stl out/grip_lid.stl out/jaw.stl out/jaw_cap.stl out/vendor_J6.stl; echo rc=$?`
   Expected: all part lines `OK`; `PRESS cup_cap x head: 6.13 mm3 ok`, `PRESS jaw x jaw_cap: 3.30 mm3 ok`; `GATE PASS`; `rc=0`.
   Allowed fallback (only): a line `INTERF vendor_J4 x head ... BAD` or `vendor_J5 x gripper` or `vendor_J6 x jaw` with depth ≤ 0.6 mm = horn face contact; re-run with `--allow=vendor_J4:head` (etc., one per such line) and record it in STATUS. Anything else BAD → STOP, `BLOCKED: S4 gate`.
4. Render s4 (forearm grey, head/gripper/jaw grey, caps/lid/pod_front dark, vendor_J4..J6 orange) → 6 `WROTE`. Review ×3: (1) servos hidden; only M2 heads on pod_front and grip_lid visible (expected, flagged); (2) cutaway shows J5 servo in pod, J6 servo in gripper, wire slot in gripper back wall; (3) re-render, confirm.

## Gate before commit
Step 3 `GATE PASS` (or allowed fallback recorded); 6 `WROTE`; git status shows only `docs/STATUS-knuckle.md`.

## Status + commit (always the last steps)
S.1 Append to `docs/STATUS-knuckle.md` (create it if missing, first line `# STATUS — knuckle arm (branch arm-knuckle)`) a section:
```
## Stage 4 — <today's date> — PASS or FAIL
- Gate lines: <paste every line that ends in PASS/FAIL/BAD from this stage>
- Files added/changed: <list from `/usr/bin/git status --short`>
- Fallbacks used: <none | list>
- UNVERIFIED values touched: <none | list>
- Questions for Riyansh: <none | list>
```
S.2 Command: `cd ~/Vector-wt/knuckle && /usr/bin/git status --short`
Expected: only the files this stage names, plus `docs/STATUS-knuckle.md`. NO `out/`, NO `.stl`, NO `__pycache__`. If not: delete/unstage the extra paths (do not commit them).
S.3 Command: `/usr/bin/git add -A <the paths from S.2> && /usr/bin/git commit -m "stage 4: wrist and gripper checked"`
Expected: `[arm-knuckle <hash>] stage 4: wrist and gripper checked`
S.4 Command: `/usr/bin/git tag stage-4-done && /usr/bin/git push origin arm-knuckle --tags`
Expected: ends with `* [new tag]         stage-4-done -> stage-4-done`. If push is rejected: run `/usr/bin/git pull --ff-only origin arm-knuckle` once and push again; if still rejected write `BLOCKED: push` in STATUS and stop.
S.5 STOP. Do not start the next stage.

Files for this stage: `docs/STATUS-knuckle.md`.
