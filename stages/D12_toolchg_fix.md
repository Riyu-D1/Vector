# Stage D12 — Apply D11 proposed fixes to the tool-changer (F1–F8; leave F9 as documented inherited)
> Rules 0.1-0.10 of `~/Vector/ARM_KNUCKLE_V5.md` apply. Step 0: `cd ~/Vector && /usr/bin/git fetch origin --tags`; create worktree `~/Vector-wt/toolchgfix` on new branch `arm-toolchg-fix` from `origin/arm-toolchg-check` (tip of D11, tag `toolchgchk-done`, commit 17f9114). Work only under `toolchg/` and the D10-added firmware files already on that lineage (`software/robot-os/soma_arm/toolchange.py`, `software/robot-os/tests/test_toolchange.py`). Do NOT edit unrelated product files, and do NOT edit the stock `w_grip_frame` (F9 is inherited — document only). Tag `toolchgfix-done`, push branch+tags, STOP. Do not merge.

## Context (read first)
Read `toolchg/check/CHECK-toolchg.md` and `toolchg/check/proposed_fixes.md` in full — they are the authority for what to change. Also `toolchg/tc_params.py`, `toolchg/p_toolchg.py`, `toolchg/tc_checks.py`, `toolchg/STATUS-toolchg.md`, `toolchg/mjcf_tc/`. Python for CAD: prefer `/Users/deepakdiwan/soma/.venv/bin/python` if it exists, else the cradlefix venv used by D11 (`/Users/deepakdiwan/Vector-wt/cradlefix/.venv/bin/python`). MuJoCo: `~/Vector-wt/sim/.venv-mj`. Pytest: anaconda `python3`.

## Goal
Apply the exact F1–F8 patches from `proposed_fixes.md`, re-run the D11 check suite on the fixed geometry, and show real PASS output. Leave F9 (inherited tool_grip clevis stress) as a documented note — do not modify the stock wrist part; optionally add a local relief on the *tool_grip copy only* if a small local change brings SF≥2 without touching product files, otherwise document the payload caveat.

## Fixes to apply (exact)
1. **F1 key notch** (`p_toolchg.py` `tc_plate`): flip the box cut so KEY_D = 1.5 mm goes *into* the plate (toward the axis), not into empty space. Use the patch in proposed_fixes.md. Tighten `tc_checks.py` C5 gate from `v < 40` to `v < 0.5` and add an explicit key-tab engagement probe (notch void present at TC_KEY_PH; RACK_KEY tab × plate intersection ~0 at seat).
2. **F2 catch tip wall** (`p_toolchg.py` `_catch`): shorten ramp `a0+2.2` → `a0+1.2` so wall at r13.5 ≥ 1.8 mm (target ~2.1). Re-check C1 entry clearance.
3. **F3 groove floor wall** (`tc_params.py`): `TC_DOCK_R 20.0 → 20.6`, `TC_KEY_D 1.5 → 1.2` (or the alternative in proposed_fixes if that fails rack seat). Re-check rack fork seat radius and C5.
4. **F4 detent BOM**: update STATUS BOM to Ø4 ball + ~Ø3.2×8 spring + M4 grub/plunger (or commercial M4 ball plunger). Confirm CAD `TC_DET_D=4.2` / `TC_DIMPLE_D=3.0` stay consistent; do not enlarge the bore unless the chosen hardware needs it.
5. **F5 dowels**: remove the stale 2× Ø3×10 dowel BOM row (plate is fused to body).
6. **F6 pen set screw**: rename comment / clarify `PEN_SET_D=3.0` as M3 grub self-tap pilot (not heat-set insert), unless you deliberately switch to an insert and open the hole to ~4.3.
7. **F7 STATUS numbers**: correct sliver volume to measured 44.6 mm³ (inherited), and replace the “≤45° overhangs designed-in” claim with the measured suspended flat-down areas + a bench note that master lug −a faces print on support.
8. **F8 mjcf**: regenerate `arm_tc.xml` / scene so `g_tc_master` mass matches rebuild (0.0056), or drop stale generated xmls per repo rules — pick one and document.
9. **F9 inherited** (optional local only): if a small relief on the *tool_grip copy* (boss ring / bore tweak) raises SF≥2 under the D11 load case without editing stock `w_grip_frame`, do it and re-run that FEA. Otherwise leave geometry, write the payload caveat into STATUS, and keep the bench item.

## Prove (real output required)
Re-run and paste into `toolchg/STATUS-toolchgfix.md`:
- `build_toolchg.py` all 11 parts (watertight, volumes)
- wall probes: catch tip ≥1.8, groove floor ≥1.8, notch residual wall ≥1.2
- `tc_checks.py` C1–C6 with the tightened C5 (must PASS; key engagement positive)
- FEM: re-run master, plate, **plate_1catch** (must SF≥2 filtered vs 25 MPa `[U]` after F2), tool_pen, tool_grip (note F9), tc_rack — HTML under `toolchg/fea/` or `toolchg/fix_fea/`
- `tc_collision.py` full suite
- `tc_analysis.py` mass/torque
- MuJoCo `run_tc.py` headless
- `pytest …/test_toolchange.py -q` (13 pass)
- Updated BOM with live UK sources where you can verify today, else `[U]`

## Deliverable
`toolchg/STATUS-toolchgfix.md`: what changed (file:line), before/after numbers for F1–F8, pasted proof output, remaining `[U]` / F9 note, recommendation (`ready to print prototype` / still blocked). Keep helper scripts under `toolchg/` as needed. Commit, tag `toolchgfix-done`, push, STOP. Do not merge.
