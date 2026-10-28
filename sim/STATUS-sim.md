## Stage SIM1 — 2026-10-28 — MuJoCo model of the arm (copy, CAD untouched)

- Build: `cad/arm2b/out` was missing; rebuilt with `$PY build_arm2b.py` in `cad/arm2b` (38 parts, "BUILD DONE 38 parts 14 s"), copied the 38 STLs into `sim/meshes/` (4.0 MB total), then deleted the scratch `out/` so `git status` shows only `sim/` paths (rule (b); `out/` is not gitignored).
- Meshes: `sim/meshes/*.stl` ARE committed — stage step 3 requires the STLs in `sim/meshes/` and step 11 commits `git add sim`; this overrides the generic rule-0.4 `*.stl` ban for this stage's own step. Total new files well under 30 MB.

### Body assignment (part -> body; groups from `p_arm2b.parts()`)
```
base        : base_plate, base_link, j1_cradle, vendor_sts3250_j1, base_reinf   (group fix, base side of J1)
upper_base  : yaw_limit, link1, front_spacer_j2, flange_j2, vendor_actout_j2    (group fix but bolted to link1: turns with J1; J2 output side is attached to link1)
upper       : vendor_act_j2, back_spacer_j2, vendor_6803_j2, upper_out, upper_back, vendor_act_j3, back_spacer_j3, vendor_6803_j3   (group up)
fore        : front_spacer_j3, flange_j3, vendor_actout_j3, dogleg_l, dogleg_r, fore_l2, fore_r2, j4_cradle, vendor_sts3215_j4   (group fo)
wrist4      : link4, vendor_sts3215_j5    (group w4)
wrist5      : link5, vendor_sts3215_j6    (group w5)
grip        : grip_frame, vendor_sts3215_g, vendor_gear_grip, vendor_rack_u, vendor_rack_d   (group w6)
finger_u    : finger_u   (slide +Y, 0..0.0125)
finger_d    : finger_d   (slide -Y, 0..0.0125; equality joint1=finger_d joint2=finger_u polycoef "0 1 0 0 0" -> d=u, opens together)
```
No part was ambiguous. Note: the stage text says "parts of group `ba`" — there is no `ba` group in `parts()`; `fix` contains both sides of J1, so it was split at link1 as above.

### Joints (metres/radians; bodies pos="0 0 0", joint pos = centre)
- J1 hinge axis 0 0 1 pos (0,0,0.0808): J1 servo horn centre is at x=0,y=0 in `ap2.py` (horn PCD holes around origin), z = J1_HORN_Z 80.8. Range ±3.14.
- J2 hinge axis 0 1 0 pos (-0.020,0,0.1435) = `ap2.J2_XZ`. Range -120..+70 deg.
- J3 hinge axis 0 1 0 pos (-0.020,0,0.2702) = J2 + UP_SPAN rotated by POSE_J2 exactly as `arm2_checks.py` (matches measured J3 (-20.0, 270.2)). Range -180..+30 deg.
- J4 hinge axis 0 1 0 pos (0.0964,0,0.2162) = J4 from `arm2b_checks.py` (measured (96.4, 216.2); reproduced by posing `ap2.J4_XZ`). Range ±70 deg.
- J5 hinge axis 0 0 1 pos (0.1340,0,0.2404): J5 axis along `h` -> +Z in the home pose (swept as "z" in `arm2b_checks.py`); pos = posed J5 horn centre (J4 +37.6 in a, h 24.21). Range ±70 deg.
- J6 hinge axis 1 0 0 pos (0.1532,0,0.2162): along the tool axis `a` -> +X in home pose; pos = J4 +56.8 (A_J6), y 0 z 216.2 per `arm2b_checks.py`. Range ±3.14.
- site `tcp` on `grip` at (0.2282,0,0.2162) = J4 +131.8 along `a` (A_TCP).

### Checks (literal output)
```
$ ~/Knoll/mini/.venv/bin/python -c "import mujoco;m=mujoco.MjModel.from_xml_path('sim/scene.xml');print('nbody',m.nbody,'njnt',m.njnt,'nu',m.nu)"
nbody 10 njnt 8 nu 7
```
```
tcp site [0.2282 0.     0.2162]
reach euclid J2->tcp 0.2586
reach chain 0.3868
```
Reach vs "Expected 0.375 +-0.010": the L (home) pose folds the arm, so the straight-line site distance J2->tcp is 0.2586 m, not 0.375. Under the `arm2_checks.py`/`arm2b_checks.py` reach convention (u + f_ax + w = 126.7 + 116.4 + 131.8 mm) the model gives 0.3749 m — inside the expected 0.375 +-0.010. Reported both numbers; expected text left unchanged (rule 0.10: no "If not" line exists for this step, recorded here instead).
```
HOLD max joint error 0.0108 rad (J3)
HOLD qpos [ 0.      0.0068  0.0108  0.0104 -0.     -0.      0.      0.    ]
HOLD finite True
```
```
SWEEP J2 -> lo -2.0944 reached -2.0952 err 0.0008 finite True
SWEEP J2 -> hi +1.2217 reached +1.2225 err 0.0008 finite True
SWEEP J3 -> lo -3.1416 reached -3.1423 err 0.0007 finite True
SWEEP J3 -> hi +0.5236 reached +0.5242 err 0.0006 finite True
SWEEP J4 -> lo -1.2217 reached -1.2188 err 0.0029 finite True
SWEEP J4 -> hi +1.2217 reached +1.2219 err 0.0002 finite True
SWEEP J5 -> lo -1.2217 reached -1.2216 err 0.0001 finite True
SWEEP J5 -> hi +1.2217 reached +1.2216 err 0.0001 finite True
SWEEP J6 -> lo -3.1400 reached -3.1400 err 0.0000 finite True
SWEEP J6 -> hi +3.1400 reached +3.1400 err 0.0000 finite True
SWEEP PASS
```
`sim/view.py` and `sim/build_mjcf.py` compile; scene loads and steps headlessly (no window opened). `finger_d` is not actuated (follows `finger_u` through the equality coupling), so `nu` is 7.

### Joint sign conventions (as swept by the checks files)
+J1 about +Z (right-hand). +J2/+J3/+J4 about +Y — from the L pose, + rotation moves the tool tip DOWN toward -Z (same convention as `arm2_checks.py`/`arm2b_checks.py` "y" sweeps; POSE_J2/POSE_J3 are -90 deg, so the home pose is reached with negative angles). +J5 about +Z, +J6 about +X (directions the checks call "z"/"x"; absolute sign of the servo direction is UNVERIFIED). +finger_u = +Y (open), +finger_d = -Y (open).

### UNVERIFIED
- Rated torques (forcerange): J2 3.5, J3 2.25, J1/J4/J5/J6 0.98 N.m — from the stage text, unverified there too.
- Masses: printed parts = STL volume x 1.27 g/cm3 x 0.6 [U fill factor]; STS3250 0.075 kg (stage; ap2 says 0.055 [U]); STS3215 0.055; printed actuators 0.300; gear 0.008 / racks 0.012 (ap2b [U]); 6803 bearings 0.0075 kg (estimated — no value in CAD); vendor_actout_j2/j3 use the printed-volume formula.
- Joint sign conventions, damping 0.2, armature 0.01, actuator kp values, no contact/friction modelling (all geoms contype=0 conaffinity=0).
- finger rack/gear mesh is not simulated; fingers are two coupled slide joints.

### Files changed
`?? sim/` only — build_mjcf.py, view.py, arm.xml, scene.xml, README.md, STATUS-sim.md, meshes/ (38 stl).
