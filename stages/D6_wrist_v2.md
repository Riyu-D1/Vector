# Stage D6 — Bolder wrist/gripper redesign: a slim, tapered, gripper-led outline (v2 of D5)
> Rules 0.1-0.10 of `~/Vector/ARM_KNUCKLE_V5.md` apply. Never edit existing branches. Create worktree `~/Vector-wt/wrist2` on new branch `arm-wrist2` from `arm-wrist`. Work only in new folder `wrist2/`. Tag `wrist-2-done`, push branch + tags, STOP. Do not merge to main.

## Why
D5 (`wrist/STATUS-wrist.md`) made the wrist 30% lighter with thin shells but KEPT every servo position and mounting face, so the outline still looks blocky (user feedback, seen in `wrist/renders/asm_frontiso.png`). User approved a bolder pass: move servo positions if needed so the wrist narrows and tapers into the gripper.

## Hard constraints
- PETG-CF only, Bambu A1, minimal supports. Same vendor parts: J4 = STS3250, J5/J6/gripper = STS3215. No new bought parts (any BOM delta in GBP with source+date).
- Payload 0.5 kg static, J4 worst static 0.801 N.m (rated 1.569). Wrist+gripper mass <= D5 (0.234 kg modelled) and ideally lighter.
- J4/J5/J6 ranges at least J4 140 deg, J5 140 deg, J6 free, no self-collision across the sweep. Keep 4 servo cable channels.
- Do not touch J2/J3 actuators or cyclo4. Keep the forearm (fore_l2/r2) interface unless you must change it; say so if you do.

## Tasks
1. Design intent: gripper sets the envelope; servos packed tight in line (shorter J4->J5->J6 offsets, J5/J6 axes closer, J6 servo inline with gripper servo where possible), a continuous tapered silhouette from the forearm into the gripper with filleted, flowing shell links (not stacked boxes). Try at least 2 layouts, pick one with measured reasons (reach, mass, ROM, silhouette width/volume).
2. Any axis/offset change: update the kinematics (`software/robot-os` FK/IK config, URDF/MJCF if present) and tests in the new branch folder or via a documented patch file in `wrist2/patches/` (do not edit existing branch files outside wrist2 unless on arm-wrist2 itself); re-run `python3 -m pytest -q` in software/robot-os and paste real results. Report new reach and the TCP change in mm.
3. Re-run D5-style checks (reach, hole fit, servo clearance, gripper rack engagement, ROM sweeps, wall thickness, cable probes, overhang scan) with real numbers, plus a hand-calc stress at J4 0.801 N.m (SF >= 2 on cross-layer 25 MPa [U]) and re-check payload torques at J2/J3/J4 using the new masses/offsets (J2 cap 3.0, J3 cap 2.0 N.m).
4. Renders: before(D5)/after side-by-side iso + side, full-arm iso/front/side with the arm-final assembly, and look at them yourself: iterate until the wrist visibly reads slim and tapered, not boxy. State honestly if it still looks boxy.
5. `wrist2/PRINT_LIST-wrist2.md`, `wrist2/STATUS-wrist2.md` with honest results incl. failures, and [U] list. Commit, tag, push. STOP.
