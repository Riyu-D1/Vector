# Stage 3 — elbow (J3) + forearm + J4 servo pocket
> Before you start: you already read `~/Vector/ARM_KNUCKLE_V5.md`. Rules 0.1–0.10 apply to every step.
> Work dir for every command unless the step says otherwise: `~/Vector-wt/knuckle`.
> `PY=/Users/deepakdiwan/soma/.venv/bin/python` — type this first in every new shell: `export PY=/Users/deepakdiwan/soma/.venv/bin/python`.
> "Expected" = the output must match (numbers may differ by ±0.05 unless stated). If it does not match: re-run once, then do the "If not" line.


**Goal:** build forearm, fa_endcap, fa_elbow_cap and the J4 servo solid; gate them against the upper arm and J3; render; commit.
**Branch:** `arm-knuckle`, tag `stage-3-done`. **Inputs:** stage 2 commit; `out/upper_arm.stl`, `out/vendor_J3.stl` (rebuild with S2 step 3 if missing).

## Steps
1. Command: `cd ~/Vector-wt/knuckle && /usr/bin/git describe --tags --abbrev=0` → Expected `stage-2-done`. If not: STOP.
2. Command: `cd cad/knuckle && $PY build.py forearm fa_endcap fa_elbow_cap vendor_J4 2>&1 | grep -v Warning`
   Expected:
   ```
   forearm: bbox=(117.0, 298.6, -31.25, 29.8, 117.0, 183.0) vol=140.8
   fa_endcap: bbox=(290.41, 301.0, -24.2, 29.8, 123.0, 177.0) vol=12.9
   fa_elbow_cap: bbox=(124.97, 175.03, 27.4, 29.8, 124.97, 175.03) vol=4.7
   vendor_J4: bbox=(244.88, 290.11, -19.85, 22.6, 137.64, 162.36) vol=11.4
   ```
3. **GATE** Command: `$PY gate.py out/upper_arm.stl out/vendor_J3.stl out/forearm.stl out/fa_endcap.stl out/fa_elbow_cap.stl out/vendor_J4.stl; echo rc=$?`
   Expected: all part lines `OK`; `PRESS fa_elbow_cap x forearm: 9.41 mm3 ok`, `PRESS fa_endcap x forearm: 21.95 mm3 ok`; `GATE PASS`; `rc=0`. Same 1.59 upper_arm fallback as S2 step 4. Other BAD → STOP, `BLOCKED: S3 gate`.
4. Torque check (no CAD; masses in kg, lengths in mm from kp.py). Command:
   `$PY -c "import kp; m=(kp.PAYLOAD_G/1000*(kp.L_FORE+kp.L_TIP)+3*kp.M_STS3215/1000*(kp.L_FORE+80)+0.15*kp.L_FORE/2)*9.81/1000; print(round(m,2), round(m/kp.RATED_NM['J3'],2))"`
   Expected: `1.0 0.49` (holding torque N·m, fraction of J3 rated). Gate: second number ≤ 0.70. If > 0.70: write `J3 torque margin low` in STATUS questions (do not change geometry).
5. Render list s3 (forearm, fa_endcap, fa_elbow_cap grey/dark as before; upper_arm grey; vendor_J3, vendor_J4 orange) → 6 `WROTE`. Review ×3: (1) J4 servo hidden in the forearm end, only the horn shows through the side hole; (2) cutaway shows the blister at −Y (servo plug room) and the pass channel; (3) re-render, confirm. 1 line per view in STATUS.

## Gate before commit
Step 3 `GATE PASS`; step 5 6 `WROTE`; git status shows only `docs/STATUS-knuckle.md`.

## Status + commit (always the last steps)
S.1 Append to `docs/STATUS-knuckle.md` (create it if missing, first line `# STATUS — knuckle arm (branch arm-knuckle)`) a section:
```
## Stage 3 — <today's date> — PASS or FAIL
- Gate lines: <paste every line that ends in PASS/FAIL/BAD from this stage>
- Files added/changed: <list from `/usr/bin/git status --short`>
- Fallbacks used: <none | list>
- UNVERIFIED values touched: <none | list>
- Questions for Riyansh: <none | list>
```
S.2 Command: `cd ~/Vector-wt/knuckle && /usr/bin/git status --short`
Expected: only the files this stage names, plus `docs/STATUS-knuckle.md`. NO `out/`, NO `.stl`, NO `__pycache__`. If not: delete/unstage the extra paths (do not commit them).
S.3 Command: `/usr/bin/git add -A <the paths from S.2> && /usr/bin/git commit -m "stage 3: elbow and forearm checked"`
Expected: `[arm-knuckle <hash>] stage 3: elbow and forearm checked`
S.4 Command: `/usr/bin/git tag stage-3-done && /usr/bin/git push origin arm-knuckle --tags`
Expected: ends with `* [new tag]         stage-3-done -> stage-3-done`. If push is rejected: run `/usr/bin/git pull --ff-only origin arm-knuckle` once and push again; if still rejected write `BLOCKED: push` in STATUS and stop.
S.5 STOP. Do not start the next stage.

Files for this stage: `docs/STATUS-knuckle.md`.
