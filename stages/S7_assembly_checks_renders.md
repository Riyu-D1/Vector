# Stage 7 — full assembly checks, ROM, final renders, BUILD.md
> Before you start: you already read `~/Vector/ARM_KNUCKLE_V5.md`. Rules 0.1–0.10 apply to every step.
> Work dir for every command unless the step says otherwise: `~/Vector-wt/knuckle`.
> `PY=/Users/deepakdiwan/soma/.venv/bin/python` — type this first in every new shell: `export PY=/Users/deepakdiwan/soma/.venv/bin/python`.
> "Expected" = the output must match (numbers may differ by ±0.05 unless stated). If it does not match: re-run once, then do the "If not" line.


**Goal:** range-of-motion check, final gates, 6 final renders committed, BUILD.md. Reference: `cad/knuckle/rom.py`, `gate.py`, `cable.py`, `render_blend.py`.
**Branch:** `arm-knuckle`, tag `stage-7-done`. **Inputs:** stage 6 commit.

## Steps
1. `/usr/bin/git describe --tags --abbrev=0` → `stage-6-done`.
2. `cd cad/knuckle && $PY build.py 2>&1 | grep -v Warning | wc -l` → `22`.
3. **GATE ROM** `$PY rom.py` (≈10–20 min) → one line per joint `Jn: lo=.. hi=.. safe=[..] OK` and `ROM PASS`.
   Fallback: for a `BAD` joint, put its printed `safe=[a, b]` into `kp.LIM` (exact text edit of that one entry), re-run `$PY rom.py Jn` until OK (max 3 times), then re-run S6 step 7–9 so firmware limits match. Record in STATUS.
4. **GATE** `$PY cable.py` → `CABLE PASS`; `$PY gate.py out/*.stl` → `GATE PASS` (same allowed fallbacks as S2–S4).
5. Final renders: list of all printed parts only (no vendor), colours as S5 → `mkdir -p renders && /usr/local/bin/blender -b -P render_blend.py -- renders/final out/renders/final.txt 2>&1 | grep WROTE` → 6 `WROTE`. Each PNG ≤ 1.5 MB (`ls -la renders`). Review ×3 (look, note, re-render); sleek, nothing visible but caps/lids.
6. Write `cad/knuckle/BUILD.md`: print table (spec §4 + §8), fastener list (§5), assembly order (drum→J1→turret→J2→upper arm→J3→forearm→J4→head→J5→gripper→J6→jaw→caps), cable order (WIRING.md), user-check list: 5-DOF, visible M2 on pod_front/grip_lid, 12 V STS3215, GIM bit rate, plug sizes, J3 torque margin, forearm blister.

## Gate before commit
ROM PASS (or fallback recorded), CABLE PASS, GATE PASS, 6 renders. Files: `cad/knuckle/renders/final_*.png`, `cad/knuckle/BUILD.md`, kp.py (only if fallback), STATUS.
## Status + commit (always the last steps)
S.1 Append to `docs/STATUS-knuckle.md` (create it if missing, first line `# STATUS — knuckle arm (branch arm-knuckle)`) a section:
```
## Stage 7 — <today's date> — PASS or FAIL
- Gate lines: <paste every line that ends in PASS/FAIL/BAD from this stage>
- Files added/changed: <list from `/usr/bin/git status --short`>
- Fallbacks used: <none | list>
- UNVERIFIED values touched: <none | list>
- Questions for Riyansh: <none | list>
```
S.2 Command: `cd ~/Vector-wt/knuckle && /usr/bin/git status --short`
Expected: only the files this stage names, plus `docs/STATUS-knuckle.md`. NO `out/`, NO `.stl`, NO `__pycache__`. If not: delete/unstage the extra paths (do not commit them).
S.3 Command: `/usr/bin/git add -A <the paths from S.2> && /usr/bin/git commit -m "stage 7: ROM, final renders, BUILD.md"`
Expected: `[arm-knuckle <hash>] stage 7: ROM, final renders, BUILD.md`
S.4 Command: `/usr/bin/git tag stage-7-done && /usr/bin/git push origin arm-knuckle --tags`
Expected: ends with `* [new tag]         stage-7-done -> stage-7-done`. If push is rejected: run `/usr/bin/git pull --ff-only origin arm-knuckle` once and push again; if still rejected write `BLOCKED: push` in STATUS and stop.
S.5 STOP. Do not start the next stage.

