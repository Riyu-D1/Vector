# Stage SIM1 — MuJoCo model of the SOMA arm (a COPY; the arm CAD is never touched)
> Rules 0.1–0.10 of `~/Vector/ARM_KNUCKLE_V5.md` apply, with these overrides for this stage only:
> (a) Work ONLY in worktree `~/Vector-wt/sim`, branch `arm-sim` (made from tag `arm-2-done`). New files go ONLY in the folder `sim/` inside that worktree. Never edit, move, rename or delete any existing file. Never commit or push to `arm-arm2`, `arm-arm2b`, `arm-actuator2*` or `arm-knuckle`. Never edit anything in `~/Vector/stages/` or in other worktrees.
> (b) Before the final commit run `git status --short`. Every line must start with `??` or `A ` and the path must start with `sim/`. If any other path appears, run `git checkout -- <that path>` and re-check.
> (c) Python for CAD scripts: `/Users/deepakdiwan/soma/.venv/bin/python`. Viewer python: `~/Knoll/mini/.venv/bin/python` and `~/Knoll/mini/.venv/bin/mjpython` (has mujoco 3.10.0, trimesh, numpy). Do not install packages; do not touch `~/Knoll` at all (read only; copy ideas from `~/Knoll/mini/view.py`, never edit it).
> (d) Status file: `sim/STATUS-sim.md`.

**Goal:** a MuJoCo model of the finished arm (`arm-2-done`) that opens in a live viewer with joint sliders and real physics, plus `sim/view.py`, started with `~/Knoll/mini/.venv/bin/mjpython sim/view.py manual`.

## Steps
1. `cd ~/Vector && git -C ~/Vector-wt/arm2b rev-parse arm-2-done` then `git -C ~/Vector-wt/arm2b worktree add -b arm-sim ~/Vector-wt/sim arm-2-done`. `cd ~/Vector-wt/sim && mkdir sim sim/meshes`. Expected: branch `arm-sim`, clean status.
2. Read (do not edit): `cad/arm2/ap2.py`, `cad/arm2b/ap2b.py`, `cad/arm2b/p_arm2b.py` (function `parts()` lists `(name, group, builder)`), `cad/arm2/arm2_checks.py` and `cad/arm2b/arm2b_checks.py` (they compute the joint positions and axes; reuse the same formulas), `~/Knoll/mini/view.py` (viewer pattern).
3. Meshes: the printed and vendor STL files are in `cad/arm2b/out/*.stl` if present. If that folder is missing, rebuild it by running in `cad/arm2b`: `$PY build_arm2b.py` (see `docs/STATUS-arm2b.md` for the exact command and the ~8 min wait). Copy (never move) the STLs into `sim/meshes/`. All STL units are millimetres; MuJoCo uses metres: set `<compiler meshdir="meshes" angle="radian"/>` and give every mesh `scale="0.001 0.001 0.001"`. Rule: do NOT modify the original STLs.
4. Write `sim/build_mjcf.py` that writes `sim/arm.xml` and `sim/scene.xml` (scene = arm.xml + floor + light, include arm.xml). Bodies and joints, in this order (a serial chain, parts keep their world coordinates because the STLs are posed at the home pose, so each body has `pos="0 0 0"` and each joint `pos` is the joint centre in metres):
   - `base` (fixed to world): parts of group `ba` and the base-side parts.
   - `J1` yaw: axis 0 0 1 through world x=0,y=0 (confirm by finding the J1 servo horn centre in `ap2.py`; use that x,y if it differs). Child body `upper_base`: link1 and its group parts.
   - `J2` pitch: axis 0 1 0 at (J2_XZ[0], 0, J2_XZ[1]) mm from `ap2.py`. Child body `upper`: upper-arm plates, spacers, flanges, the J3 side housing parts.
   - `J3` pitch: axis 0 1 0 at the J3 position computed exactly as in `arm2_checks.py` (J2 + UP_SPAN rotated by POSE_J2). Child body `fore`: fore_l2, fore_r2, j4_cradle and group `fo` parts.
   - `J4` pitch: axis 0 1 0 at the J4 position from `arm2b_checks.py`. Child `wrist4`: link4, J5 servo.
   - `J5`: axis as in `arm2b_checks.py` (the J5 axis is along its `h` direction). Child `wrist5`: link5, J6 servo.
   - `J6` roll: axis along the tool axis (the `a` direction) from `arm2b_checks.py`. Child `grip`: grip_frame, gripper servo, racks.
   - `finger_u` and `finger_d`: each a slide joint along the gripper opening direction, range 0 to 0.0125 m, equality-coupled so they open together (`<equality><joint joint1=... joint2=... polycoef="0 1 0 0 0"/></equality>`; use the sign that opens them).
   Assign each part to a body with the group letter in `parts()`; any part not clearly assigned: print its name and the body you chose in the status file.
5. Joint ranges (radians) from the measured ROM: J1 ±3.14 (no stop modelled), J2 -120..+70 deg, J3 -180..+30 deg, J4 -70..+70 deg, J5 -70..+70 deg, J6 -3.14..+3.14. Signs: copy the sign convention of the ROM sweep (positive = the direction the checks call positive); if unsure print which way the +J2 pose moves the tool tip and state it in the status.
6. Masses and limits: set body masses from printed volume × 1.27 g/cm³ × 0.6 (PETG, fill factor), plus servo masses: STS3250 J1 0.075 kg, STS3215 0.055 kg each (J4, J5, J6, gripper), printed actuators 0.300 kg each (J2, J3 bodies). Use `<inertial>` from mesh via `<geom ... mass=...>` (MuJoCo computes inertia). Actuators: position servos, `kp` so that the arm holds home under gravity, `forcerange` ±3.5 for J2, ±2.25 for J3, ±0.98 for STS3215 joints, ±0.98 for J1 (all N·m; these are the rated torques, unverified). Joint `damping="0.2"`, `armature="0.01"`. Add a `home` keyframe equal to the home pose (all joints 0).
7. Add a site `tcp` at the tool tip (J4→TCP 131.8 mm along the tool axis from J4).
8. Checks (print literal output into the status file):
   - `~/Knoll/mini/.venv/bin/python -c "import mujoco;m=mujoco.MjModel.from_xml_path('sim/scene.xml');print('nbody',m.nbody,'njnt',m.njnt,'nu',m.nu)"` → `njnt` must be 8 (6 arm joints + 2 fingers), no error.
   - Reach: set `home`, `mj_forward`, print the distance from J2 (`-0.020, 0, 0.1435`) to site `tcp`. Expected 0.375 ±0.010.
   - Hold test: step 2 s with ctrl = home angles; print the max joint error (rad). Expected < 0.05.
   - Sweep test: for each of J2..J6 drive it to both limits and print that it reaches within 0.05 rad and that no NaN appears.
9. `sim/view.py`: copy the pattern of `~/Knoll/mini/view.py` but load `sim/scene.xml`, mode `manual` = `mujoco.viewer.launch_passive` with the arm free to be moved with the viewer's sliders (Control panel shows the actuator sliders), mode `sweep` = each joint swept in turn (4 s each). Do not hold or move any free base; the arm base is fixed. Test only headlessly: import and compile the model; do not open a window in your shell.
10. Write `sim/README.md` (3 lines): how to start the viewer, units, what is a guess. Write `sim/STATUS-sim.md` with the literal check output, the body assignment list, and UNVERIFIED: rated torques, masses, joint sign conventions, friction.
11. `git status --short` (rule (b)). `git add sim && git commit -m "SIM1: MuJoCo model of the arm (copy, CAD untouched)" && git tag sim-1-done && git push -u origin arm-sim --tags`. STOP.
