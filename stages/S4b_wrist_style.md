# Stage 4b — round the wrist, gripper and forearm blister (look only; no inner changes)
> Before you start: you already read `~/Vector/ARM_KNUCKLE_V5.md`. Rules 0.1–0.10 apply to every step.
> Work dir: `~/Vector-wt/knuckle`. `export PY=/Users/deepakdiwan/soma/.venv/bin/python` first in every new shell.
> "Expected" = output must match. If not: re-run once, then do the "If not" line.

**Why:** Riyansh rejected the S4 look: the wrist head is a square box, the forearm underside has a square block (the blister), the gripper is a square box with a big square bump on its lid. Fix = round the OUTSIDE EDGES ONLY. Do NOT touch any cavity, pocket, channel, hole position (except the 4 pod M2 screws in step 5), servo, wall thickness, or any x/y/z number in `kp.py` other than `POD_M2`.
**Branch:** `arm-knuckle`. **Tag to create:** `stage-4b-done` (not stage-4-done). **Input:** stage 4 commit (tag `stage-4-done`).

## Method (use this exact one, do not invent another)
Round a solid BEFORE any cuts or unions by filleting the plain box, then use that rounded box where the plain box was. Do not edit frames.py. Create NEW file `cad/knuckle/style.py`:
```python
from build123d import Axis, fillet
from frames import gbox

def rbox(x0, x1, y0, y1, z0, z1, r, axis=None):
    """gbox with outer edges rounded by r. axis 'X','Y','Z' = only edges parallel to that axis; None = all 12 edges."""
    b = gbox(x0, x1, y0, y1, z0, z1)
    es = b.edges() if axis is None else b.edges().filter_by(getattr(Axis, axis))
    return fillet(es, r)
```
If `fillet` raises, retry with r-0.5, repeat down to r=2.0; if still failing write `BLOCKED: fillet` in STATUS and STOP.

## Steps
1. `git describe --tags --abbrev=0` -> `stage-4-done`. If not: STOP.
2. Baseline: `cd cad/knuckle && $PY build.py head pod_front gripper grip_lid forearm 2>&1 | grep -v Warning` and save the output to `/tmp/s4b_before.txt`.
3. **Wrist head** — in `cad/knuckle/p_wrist.py` function `head()` replace ONLY `gbox(*kp.POD)` by `rbox(*kp.POD, 8.0, "X")` (import `from style import rbox`). Everything else in `head()` unchanged. Expected effect: the 4 long edges of the pod (parallel to X) are rounded r=8; the min wall stays ≥ 1.78 mm (hand-checked).
4. **pod_front** — in `pod_front()` replace the first line `gbox(x0, x1, kp.POD[2], kp.POD[3], kp.POD[4], kp.POD[5])` by `rbox(x0, x1, kp.POD[2], kp.POD[3], kp.POD[4], kp.POD[5], 8.0, "X")`.
5. **pod_front screws** — the 4 M2 screws sit in the corners that step 3 removes. In `cad/knuckle/kp.py` change ONLY `POD_M2` to:
   `POD_M2 = ((-6.0, 112.93), (10.0, 112.93), (-6.0, 162.06), (10.0, 162.06))`
   (same z as before, so they still go into the top and bottom 3.6 mm walls; y values are on the flat part of the rounded edge). Do not change anything else that uses POD_M2.
6. **Gripper body** — in `p_grip.py` `gripper()` replace `gbox(*kp.GR)` by `rbox(*kp.GR, 2.5, "X")`. (Max r is 2.5: wall there is only 2.4.) Keep `+ gbox(*kp.FINGER_FIX)`.
7. **Gripper lid** — in `grip_lid()` replace `gbox(*kp.GR_LID)` by `rbox(*kp.GR_LID, 2.0, "X")` and `gbox(*kp.GR_BUMP)` by `rbox(*kp.GR_BUMP, 5.0)` (all edges; the bump is 28.8 x 14.25 x 15 mm). Keep `l -= gbox(*kp.GR_PLUG)`: after rounding, the plug cut must still leave ≥ 1.6 mm wall — the gate checks it; if gate says minwall BAD for grip_lid, change the bump radius to 4.0 then 3.0 and re-run.
8. **Lid screws flush** — in `grip_lid()` after the clearance holes add a countersink for each of the 4 pilots in `kp.GR_PILOTS`: a cone from d4.2 at y=GR_LID[2] (outer face, y=-20.4) to d2.2 at y=GR_LID[2]+1.2. Use `build123d.Cone(bottom_radius=1.1, top_radius=2.1, height=1.2)` rotated so its axis is along Y, placed with its wide face at y=-20.4. Subtract it. If you cannot get the cone orientation right in 3 tries, skip this step and record `lid countersink skipped` in STATUS.
9. **Forearm blister** — in `p_fore.py` `forearm()` replace `f += gbox(*kp.BLISTER_OUT)` by `f += rbox(*kp.BLISTER_OUT, 4.0)` (all edges). Leave `f -= gbox(*kp.BLISTER_IN)` as is. Wall check: blister wall must stay ≥ 1.6; if gate reports forearm minwall BAD use radius 3.0.
10. Rebuild: `cd cad/knuckle && $PY build.py 2>&1 | grep -v Warning | wc -l` -> `22`. Save `$PY build.py head pod_front gripper grip_lid forearm 2>&1 | grep -v Warning` to `/tmp/s4b_after.txt`; the bbox numbers must be the SAME as before except: pod_front/head y,z extents unchanged (fillets do not change bbox), grip_lid bbox unchanged. Volumes get smaller by a few mm³ — that is expected. If a bbox min/max changed by more than 0.05: STOP, `BLOCKED: bbox moved`.
11. **GATE A (cables)** `$PY cable.py 2>&1 | grep -v Warning` -> `CABLE PASS` (all 5 lines CLEAR). If a line is BLOCKED: undo step 5 only (restore old POD_M2) and re-run; if still BLOCKED, `BLOCKED: cable` and STOP.
12. **GATE B** `$PY gate.py out/*.stl; echo rc=$?` (slow, up to 10 min) -> `GATE PASS` rc=0 with the same allowed `--allow` flags used in S2–S4. Any NEW BAD line = fix by reducing the radius of that part (steps above name the fallback radii) and re-run once.
13. **Range-of-motion check** `$PY rom.py 2>&1 | grep -v Warning` -> must print the same result lines as before this stage (record both in STATUS). If it was not runnable before, just record the output.
14. **Render** same views and colours as S4 step 4, names prefixed `s4b_` (6 `WROTE`). Review ×3. Pass criteria, check each by LOOKING at the PNGs, and write one line per view:
    (a) `s4b_side`: wrist head has rounded top and bottom edges (no square corners at the top/bottom of the head); (b) blister under the forearm is a rounded lozenge, not a square block; (c) gripper lid bump is rounded; (d) no part floats; (e) no cable visible.
    If any criterion fails, adjust the radius (down by 1.0) once and re-render once. Do not claim "identical" without actually diffing.
15. Open items to record, do not decide: the 4 pod_front M2 screw heads and 4 lid screws stay (lid ones flush if step 8 worked).

## Gate before commit
Steps 11, 12 pass; 6 `WROTE`; `git status` shows only: `cad/knuckle/style.py`, `p_wrist.py`, `p_grip.py`, `p_fore.py`, `kp.py`, `docs/STATUS-knuckle.md`.

## Status + commit (always the last steps)
S.1 Append to `docs/STATUS-knuckle.md` a section `## Stage 4b — <date> — PASS or FAIL` with: Gate lines; Files changed; radii finally used per part; min wall lines for head, pod_front, gripper, grip_lid, forearm; Fallbacks used; Questions for Riyansh.
S.2 `/usr/bin/git status --short` — only the files above. NO `out/`, NO `.stl`, NO `__pycache__`.
S.3 `/usr/bin/git add -A <those paths> && /usr/bin/git commit -m "stage 4b: round wrist, gripper, forearm blister"`
S.4 `/usr/bin/git tag stage-4b-done && /usr/bin/git push origin arm-knuckle --tags` (if rejected: `git pull --ff-only origin arm-knuckle` once, push again; else `BLOCKED: push`).
S.5 STOP. Do not start the next stage.
