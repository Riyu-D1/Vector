# Stage D5 — Redesign the wrist + gripper end (J4 -> gripper) so it is slim, organic and gripper-led, not blocky
> Rules 0.1-0.10 of `~/Vector/ARM_KNUCKLE_V5.md` apply. Never edit existing branches. Create worktree `~/Vector-wt/wrist` on new branch `arm-wrist` from `arm-final`. Work only in a new folder `wrist/`. Tag `wrist-1-done`, push branch + tags, STOP. Do not merge to main.

## Why
User feedback on the final renders: "the front part, the actual arm bit, is very blocky". Parts at fault (from `final/PRINT_LIST.md`): j4_cradle (38x52.5x30), link4 (66.6x60.6x69), link5 (38x30x34.6), grip_frame (56x64x52). The fix must be built AROUND THE GRIPPER: the gripper (4th STS3215 + rack-and-pinion jaws) sets the envelope, and the wrist links wrap close around the servos.

## Hard constraints (do not break)
- PETG-CF only, Bambu A1 (256 mm bed), printed without support wherever possible (min overhang 45 deg; list any support).
- Keep the SAME vendor parts and mounting: J4 = STS3250, J5/J6/gripper = STS3215, same horn/axis positions and joint axes/ranges so arm kinematics and `software/robot-os` config do not change. If an axis must move, say so and update the kinematics + tests.
- Payload 0.5 kg static; J4 static torque max 0.801 N.m at 0.5 kg (rated 1.569). Keep wrist+gripper mass <= current mass (measure it) and ideally lighter.
- Cable routing for 4 servo TTL cables must be kept (internal channels or clips).
- Do not touch J2/J3 actuators or the cyclo4 geometry.

## Tasks
1. Measure the current wrist/gripper parts (mass, bbox, volume) from the STLs and render a before-view close-up (Blender workbench, as in final/renders).
2. Research (brief, cite sources in `wrist/RESEARCH.md`): how small 3D-printed or commercial desk arms (reBot-DevArm, SO-100/SO-101, Koch, etc.) build the wrist and gripper around the gripper servo: shell-style links, ribbed/tapered forms, servo-wrapping clamshells. Pick an approach and say why.
3. Design as code (CadQuery or the same CAD-as-code tooling used in cad3), exporting STEP+STL: tapered, filleted clamshell links that wrap the STS3250/STS3215 bodies with ~1.5-2 mm wall, ribs only where load needs it, a slimmer grip_frame hugging the gripper servo and rack, smooth transitions from the forearm. No new bought parts if avoidable; list any BOM delta in GBP with source and date.
4. Check: interference check against servos/forearm/rack across the full joint range (real numbers); wall thickness and overhang check; mass vs before; hand-calc stress at J4 0.801 N.m on the worst section (use realistic static load, SF >= 2 on cross-layer 25 MPa [U]); if FreeCAD FEM is used, remember rigid-glue gives optimistic stresses and state it. Flag [U] for anything unverified.
5. Render new iso/front/side/closeup with the full assembly (compose with arm-final assembly export script `final/export_assembly.py`), side-by-side before/after image. Produce `wrist/out/*.stl|step`, an updated print list section, and `wrist/STATUS-wrist.md` with honest results, including failures.
6. Commit, tag `wrist-1-done`, push. STOP.
