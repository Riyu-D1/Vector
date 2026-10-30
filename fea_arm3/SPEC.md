# FEA arm pipeline spec (stage F2 — internal working doc)

Worktree: /Users/deepakdiwan/Vector-wt/fea (branch arm-fea). ALL new files go under
`fea_arm/` ONLY. NEVER create or edit files in cad/, sim/, fea/, pcb*/ or anywhere
else in the worktree. Scratch work may go in /tmp.

## Tools / interpreters
- CAD python `$PY` = /Users/deepakdiwan/soma/.venv/bin/python  (build123d 0.13.0, trimesh 5.1.1, rtree, numpy, manifold3d)
- Viewer python = /Users/deepakdiwan/Vector-wt/fea/fea/.venv/bin/python  (pyvista 0.49.2, numpy)
- GMSH = /Applications/FreeCAD.app/Contents/Resources/bin/gmsh  (4.15.0)
- CCX  = /Applications/FreeCAD.app/Contents/Resources/bin/ccx   (CalculiX 2.23)
- In every script: build ALL paths as ABSOLUTE from `Path(__file__).resolve().parent`.
- After every mesh step assert nodes > 0 and elements > 0, stop with a clear message if not.

## Source geometry (read-only)
- sys.path += cad/arm2, cad/arm2b ; `import p_arm2b as PB`
- `PB.parts()` -> list of 38 (name, grp, fn); grp in fix/up/fo/w4/w5/w6.
- `PB.pose(shape, grp)` -> solid in the HOME pose (= L pose = sim qpos all-zero = sim/meshes/*.stl frames, world mm, +Z up, arm along +X).
- sim bodies/joints: see sim/build_mjcf.py and sim/STATUS-sim.md (read-only).

## Bodies and joints (authoritative, home-pose coords, mm)
BODIES (chain order):
- base        : base_plate, base_link, j1_cradle, vendor_sts3250_j1, base_reinf
- upper_base  : yaw_limit, link1, front_spacer_j2, flange_j2, vendor_actout_j2        (joint J1)
- upper       : vendor_act_j2, back_spacer_j2, vendor_6803_j2, upper_out, upper_back, vendor_act_j3, back_spacer_j3, vendor_6803_j3   (J2)
- fore        : front_spacer_j3, flange_j3, vendor_actout_j3, dogleg_l, dogleg_r, fore_l2, fore_r2, j4_cradle, vendor_sts3215_j4      (J3)
- wrist4      : link4, vendor_sts3215_j5                                              (J4)
- wrist5      : link5, vendor_sts3215_j6                                              (J5)
- grip        : grip_frame, vendor_sts3215_g, vendor_gear_grip, vendor_rack_u, vendor_rack_d   (J6)
- finger_u    : finger_u   (slide joint, axis +Y, child of grip)
- finger_d    : finger_d   (slide joint, axis -Y, child of grip)

JOINTS (home anchors/axes, mm):
- J1 (0,0,80.8)     axis (0,0,1)
- J2 (-20,0,143.5)  axis (0,1,0)
- J3 (-20,0,270.2)  axis (0,1,0)
- J4 (96.4,0,216.2) axis (0,1,0)
- J5 (134,0,240.4)  axis (0,0,1)
- J6 (153.2,0,216.2) axis (1,0,0)
- finger slide axes at (125,0,216.2)
Sign convention (sim): + about +Y moves the tool tip DOWN toward -Z.
TCP home = (228.2, 0, 216.2) (= J4 + 131.8 along tool axis +X).

Pose transform for a body = apply each ancestor joint rotation (LEAF joint first,
then up to root) to the home-pose solid, each about its HOME anchor/axis. Slides
translate by q mm along the axis (used q=0).

## Load cases
- CASE "AB" pose: J2 = +90 deg, J3 = -90 deg, all others 0  -> arm fully stretched
  horizontal along +X (longest reach; TCP ~ (354.9, 0, 89.5)). Two steps:
    step 1 (case A): gravity 9810 mm/s2 -Z on all mass + 0.5 kg payload = -4.905 N at TCP
    step 2 (case B): same at 2x (gravity 19620, payload -9.81 N)
- CASE "C" pose: all joints 0 (home/demo L pose). One step: 1x gravity + payload.
- J1 = 0 in every case.
- Fix: base_plate bottom face (nodes with z <= base_plate zmin + 1.5).
- Payload: ref node at posed TCP, rigid-body coupled to fingertip region
  (finger_u/finger_d boundary faces within ~18 mm of TCP).

## Materials (assumptions, flagged unverified)
- printed parts (every non-vendor_* name): PETG-CF  E=4000 MPa, nu=0.35,
  rho = 7.62e-10 t/mm3  (1.27 g/cm3 x 0.6 fill), working limit 25 MPa.
- vendor_* parts: metal block, E=70000 MPa, nu=0.33; rho_i = mass_i / vol_i (t/mm3)
  so each block has the right mass. Masses (kg): vendor_sts3250_j1 0.075;
  vendor_sts3215_j4/j5/j6/g 0.055; vendor_act_j2/j3 0.300; vendor_gear_grip 0.008;
  vendor_rack_u/d 0.012; vendor_6803_j2/j3 0.0075; vendor_actout_j2/j3 use the
  printed-formula rho (7.62e-10).
- Vendor parts are NOT judged for stress (stiffness + mass only).

## Files (all under fea_arm/)
Inputs (generated, gitignored):
- input/step_home/<part>.step + .stl          (38, home pose; .stl also copied from sim/meshes/)
- input/posed_AB/<part>.step + .stl           (38, straight-arm pose)
- input/posed_C/  -> reuse step_home (identity)
- input/contacts_AB.json, contacts_C.json:
  {"contacts":[{"a":part,"b":part,"kind":"auto"|"mount","pts":[[x,y,z],...]}]}
  pts = sample points on the touching patch (subsample <=400) for tri matching.
- input/parts_<CASE>.json:
  {"parts":{name:{"body":..,"cls":"printed"|"vendor","mass_kg":..,"rho":..,
                 "centroid":[x,y,z],"bbox":[..]}},
   "joints":{"J2":{"pos":[x,y,z],"axis":[0,1,0]},...},"tcp":[x,y,z],
   "moments_nm":{"J2":..,"J3":..,"J4":..,"base_y":..}}
- arm_AB.geo / arm_C.geo : gmsh scripts -> run/arm_<case>.msh (v2.2 ascii),
  Physical Volume per part named "p_<part>", C3D10 (ElementOrder=2).

Run artifacts (gitignored): run/arm_<case>.msh, run/arm_<case>.inp,
run/arm_<case>.frd, run/res_<tag>_step<n>.vtu, run/report_<tag>.txt

Committed: SPEC.md, *.py, *.geo, .gitignore, STATUS-fea-arm.md, arm_case*.png (<1.5 MB each).

## Connectivity contract (msh2arm.py)
- Non-conformal per-part meshes -> connect EVERY touching/mounted pair with a
  CalculiX *TIE (TYPE=ELEMENT surfaces of the tet faces whose centroid is within
  ~5 mm of the pair's patch points; *TIE, POSITION TOL=1.5, ADJUST=YES).
- Auto-detected pairs = surfaces closer than ~0.3 mm or interpenetrating.
- Extra mount pairs (vendor pockets / horn faces / racks / fingers), proximity tol <=0.6 mm:
  (vendor_sts3250_j1,j1_cradle) (vendor_sts3250_j1,yaw_limit) (vendor_sts3250_j1,base_link)
  (vendor_act_j2,vendor_actout_j2) (vendor_act_j2,upper_out) (vendor_act_j2,upper_back) (vendor_act_j2,back_spacer_j2)
  (vendor_6803_j2,back_spacer_j2) (vendor_6803_j2,link1)
  (vendor_act_j3,vendor_actout_j3) (vendor_act_j3,upper_out) (vendor_act_j3,upper_back) (vendor_act_j3,back_spacer_j3)
  (vendor_6803_j3,back_spacer_j3) (vendor_6803_j3,fore_l2) (vendor_6803_j3,fore_r2)
  (vendor_actout_j2,front_spacer_j2) (vendor_actout_j2,link1) (vendor_actout_j2,flange_j2)
  (vendor_actout_j3,front_spacer_j3) (vendor_actout_j3,flange_j3) (vendor_actout_j3,dogleg_l) (vendor_actout_j3,dogleg_r)
  (vendor_sts3215_j4,j4_cradle) (vendor_sts3215_j4,link4) (vendor_sts3215_j4,fore_l2) (vendor_sts3215_j4,fore_r2)
  (vendor_sts3215_j5,link4) (vendor_sts3215_j5,link5)
  (vendor_sts3215_j6,link5) (vendor_sts3215_j6,grip_frame)
  (vendor_sts3215_g,grip_frame) (vendor_gear_grip,grip_frame) (vendor_gear_grip,vendor_sts3215_g)
  (vendor_gear_grip,vendor_rack_u) (vendor_gear_grip,vendor_rack_d)
  (vendor_rack_u,grip_frame) (vendor_rack_d,grip_frame)
  (vendor_rack_u,finger_u) (vendor_rack_d,finger_d)
  (finger_u,grip_frame) (finger_d,grip_frame)
- Connectivity assert: union-find over tied pairs; every part must be connected to
  base_plate; print the tie list; fail loudly listing orphan parts.

## Deliverable numbers
For each case: max von Mises overall, max |U| at TCP region (report global max too),
per-PRINTED-part table {max VM, SF vs 25 MPa}, reaction torque at base (sum r x RF on
fixed nodes), analytic J2/J3/J4 moments vs rated 3.5 / 2.25 / 0.98 N.m,
top-5 highest-stress regions. Coarse vs refined max stress for case A.
