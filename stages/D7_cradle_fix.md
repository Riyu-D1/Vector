# Stage D7 — Fix the wrist-corner graze (w_j4_cradle x w_link5) with a small cradle reshape
> Rules 0.1-0.10 of `~/Vector/ARM_KNUCKLE_V5.md` apply. Never edit existing branches. Create worktree `~/Vector-wt/cradlefix` on new branch `arm-cradlefix` from `main` (= arm-final2 79394a1). Work only in new folder `cradlefix/` (plus the minimum edits to wrist build scripts copied into it). Tag `cradle-1-done`, push branch+tags, STOP. Do not merge to main. Another Devin runs in parallel on `arm-genlinks` in a different worktree: do not touch its files.

## Problem (from `final2/STATUS-final2.md`)
Each wrist joint sweeps its full range alone, but at combined |J4|+|J5| extremes (J4 +-70, J5 +-70, any sign mix) the w_link5 shell grazes the w_j4_cradle ear / vendor_sts3250_j4 case edge: 606 of 2200 Monte-Carlo poses hit w_j4_cradle x w_link5 (1-18 mm3), 194 hit vendor_sts3250_j4 x w_link5, others w_grip_frame x w_link4 (50), plug_g/vendor_sts3215_g x vendor_sts3215_j5 (137 each).

## Constraints
PETG-CF, Bambu A1, minimal supports. Keep ALL servo positions, horn faces, bolt patterns, joint axes and ranges (J4 +-70 etc.) so kinematics/firmware/tests do not change (if impossible, say so and stop). Wall >= 1.8 mm, cable channels kept, J4 stress SF >= 2 at 0.801 N.m (hand calc). Mass must not increase vs D6. No BOM change.

## Tasks
1. Reproduce the graze with `final2/f2_collision.py` / `f2_mc_hist.py` (use the venv/tools they used). Identify exactly which cradle/link5/link4/grip faces collide and at which angles.
2. Reshape the cradle ear (and, if needed, trim link5/link4/grip_frame shell corners) with small cuts/chamfers/relief so the collision count in the wrist-pair family goes to 0 across the full +-70/+-70 combined envelope, at <=2.5 deg steps over the J4xJ5 grid and across the J6 and gripper strokes. Keep 0.3 mm min clearance if achievable; report real min clearance.
3. Rebuild the full assembly via `final/export_assembly.py` pattern with the fixed parts; re-run the 2200-pose Monte-Carlo (same seed) and show before/after histogram numbers for every wrist pair. Re-run `wrist2/wrist2_checks.py` equivalents (hole fit, servo clearance, wall, cable probes, overhang) and `python3 -m pytest -q` in software/robot-os. Paste real numbers; report any remaining hit honestly.
4. Renders (close-up of the cradle before/after, full arm iso), look at them yourself. Write `cradlefix/STATUS-cradlefix.md`, updated print list lines (parts/masses only), commit, tag, push. STOP.
