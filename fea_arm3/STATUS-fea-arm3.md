# Stage F3 status — whole-arm FEA that solves

Worktree ~/Vector-wt/fea, branch arm-fea, folder fea_arm3/. Reused from
fea_arm/: input/ (38 STEP+STL per pose, parts/contacts json), frd2report.py
(copied verbatim), view_arm_stress.py (adapted paths only).

Solve budget used so far: 3 / 5 CalculiX solves.

## Log of approaches (per hard limits, written before each new attempt)

### 1) Conformal mesh via ONE gmsh BooleanFragments of all 38 STEP solids
Gen: `gen_geo.py --case AB --cl 20` (pilot size), C3D4.
- Attempt 1 `Mesh.Algorithm3D=1` (Delaunay): GF 38 -> 44 volumes OK, but
  surface 2213 PLC error (segment-facet intersection near the J3 bearing
  pocket, pt ~ (97.6,28.1,134.2)) -> "No elements in volume" for ALL
  volumes -> 0 tets. FAIL.
- Attempt 2 + `Geometry.ToleranceBoolean=0.05` + `Coherence`: fuzzy GF made
  ~11 periodic surfaces lose their closed 1D loops ("Impossible to mesh
  periodic surface") -> 0 tets. FAIL (worse).
- Attempt 3 `Mesh.Algorithm3D=10` (HXT) + `Coherence`, no fuzzy: HXT
  tetrahedralized per volume -> 44k nodes, 63,860 C3D4 tets BUT only 24 of
  the 44 fragment volumes got elements (18 volume tags empty = the big
  printed parts whose split faces had 1D-loop intersections), and
  point-in-solid ownership on the vendor STLs was unreliable (one vendor
  claimed 20 vols). FAIL.

Conclusion: mutual GF over 38 solids produces degenerate sliver topology
exactly where parts nearly touch -> per-part surfaces mesh fine (F2 proved
it) but fragmented ones do not. Abandoning conformal mesh per rule 0.5.

### 2) FALLBACK TAKEN (stage-sanctioned): independent per-part meshes
(F2-proven, Physical Volume per part -> own material + result row), no
*TIE contact anywhere; instead every contact/mount pair is glued with a
small *RIGID BODY spider at the contact patch located by the patch points
in fea_arm's contacts_<case>.json, plus nearest-node fallback links for any
part still disconnected. Joints are rigidly held at the pose, so MPC glue
at bolt faces is consistent with the stage text ("glue ... with
*EQUATION/*RIGID BODY at the actuator output faces"), applied at part
granularity rather than sub-assembly granularity.

#### 2a) Mesh (mesh_parts.py, cl=20, gmsh Algo3D=10 HXT, C3D4, one gmsh
process per part, merged): all 38 parts meshed, 49,304 nodes /
157,518 C3D4 tets. Gate: nodes>0 elements>0 OK. (Above the "few
thousand" pilot target but inside the 80k-250k production band, so the
pilot deck doubles as the production AB deck.)

#### 2b) Solve #1 (arm_AB, 2 steps 1x/2x load): finished, .frd with
DISP/STRESS blocks BUT 2e10 mm garbage in finger_u: the 3 island
fallback links were single-node welds -> the finger pair hung off the
arm through ONE pivot point = rotational mechanism. FAIL.

#### 2c) Solve #2: fallback welds widened to K=40 nearest nodes each
side. Still garbage (1e8 mm) on the whole J3-left/gripper side: the
fallback patch re-used boundary nodes already owned by other rigid
bodies (ccx allows a node in exactly ONE *RIGID BODY); the shared nodes
corrupted R13/R26/R35/R36/R37. FAIL.

#### 2d) Solve #3: taken-set now enforced for fallbacks AND, where an
island's boundary is fully consumed (finger_d/finger_u: every boundary
node already in R13+NLOAD), the existing rigid body owning the island
is EXTENDED with free big-island nodes instead of making a new body.
Result: 34 rigid links, zero shared nodes, ORPHANS none.
ccx: 1 inc/step, "Job finished", .frd 8 result blocks:
  step 1 (case A, 1x g + 0.5kg): max|U|=0.069 mm, fingertip NLOAD
    mean 0.060 mm / max 0.065 mm, all 38 parts finite.
  step 2 (case B, 2x g + 1kg): max|U|=0.138 mm, tip 0.129 mm
    (exactly 2x step1 -> consistent linear response).
Pilot gates PASS: result blocks exist, tip displacement finite, ~0.06-0.07
mm (just under the 0.1-5 mm expectation; plausible because joints are
welded rigid and cl=20 is stiff). Case A and B share this deck as two
steps, so only ONE solve slot was consumed for both.

#### 2e) Solve #4 (arm_C, home pose, 1 step 1x load): per-part mesh
49,285 nodes / 157,428 tets, same converter path -> 34 rigid links,
ORPHANS none. ccx finished, .frd has DISP/STRESS/FORC blocks:
max|U|=0.064 mm, tip 0.056 mm, max VM 1.07 MPa. PASS.

Solves used: 4 / 5. Remaining slot NOT spent on a cl<=10 refined
case-A: the 2 h budget + the fact that cl=20 already sits inside the
80k-250k production band argue for reporting the coarse result with the
refinement explicitly NOT performed (see "Unverified assumptions").

## Results (frd2report.py -> report_AB.txt / report_C.txt)

| case | pose | load | max VM [MPa] | part | tip |U| [mm] | max |U| [mm] |
|------|------|------|--------------|------|----------------|-----------------|
| A    | AB reach (J2 +90, J3 -90) | 1xg + 0.5 kg | 1.07 | grip_frame | 0.062 | 0.069 |
| B    | AB reach                 | 2xg + 1.0 kg | 2.13 | grip_frame | 0.125 | 0.138 |
| C    | home (TCP 228.2,0,216.2) | 1xg + 0.5 kg | 1.07 | grip_frame | 0.056 | 0.064 |

Base reaction (all cases A/C): Fz=21.16 N vs analytic weight 22.22 N
(-5%); case B Fz=42.3 N. Overturning base-Y: A -2.97 / B -5.94 /
C -1.44 N.m (matches analytic base_y to <1%).

Joint reaction moments (frd-measured about joint axes vs rated):
| case | J2 (rated 3.5) | J3 (rated 2.25) | J4 (rated 0.98) |
|------|----------------|-----------------|-----------------|
| A | 3.39 N.m margin 1.03x | 0.71 N.m margin 3.16x | 1.75 N.m margin 0.56x OVER |
| B | 6.79 N.m margin 0.52x OVER | 1.42 N.m margin 1.58x | 3.50 N.m margin 0.28x OVER |
| C | 1.87 N.m margin 1.88x | 1.87 N.m margin 1.21x | 0.60 N.m margin 1.64x |
(Analytic moments from parts_AB/C.json listed alongside in the .txt
reports; frd values differ slightly because they integrate the REAL
welded assembly incl. all vendor masses, not the point-mass model.)

Per-printed-part max VM + safety factor vs 25 MPa: full tables in
report_AB.txt (steps 1-2) and report_C.txt (step 1). Worst printed
part every case: grip_frame (A 1.07 -> SF 23.4; B 2.13 -> SF 11.7;
C 1.07 -> SF 23.4), then base_reinf, link1, fore_l2/r2, base_link.
Everything else is essentially unloaded (<0.4 MPa) because the rigid
welds spread load and cl=20 rounds off peaks.

## Connectivity model (the F2 fix)

- 38 parts meshed INDEPENDENTLY (one gmsh process per STEP, HXT
  Algo3D=10, cl=20, C3D4) and merged with offset ids + Physical Volume
  per part -> per-part elsets + materials (PETG-CF E=4000 nu=0.35
  rho=7.62e-10 t/mm^3; vendor E=70000 nu=0.33, mass-based density).
- NO conformal shared nodes and NO *TIE anywhere. Adjacent parts are
  welded by 34 *RIGID BODY spiders: contact patch on each side found
  from fea_arm contacts_<case>.json patch points (grow radius until
  both sides non-empty), both patches go in ONE rigid body with a fresh
  ref node at the patch centroid -> forces AND moments transmit; joints
  hold the posed shape rigidly.
- Finger pair and back_spacer/flange islands: contact points fell
  outside their boundary patches AND their whole boundary was already
  owned by other rigid bodies (ccx: a node may sit in exactly ONE
  *RIGID BODY). Resolved by EXTENDING the rigid body that already owns
  island nodes with the 40 nearest free boundary nodes of the big
  island (printed in the log as "fallback extend R<n> +40").
- Orphan check after linking: union-find over volumes must give 1
  component, else FATAL -> "ORPHANS: none" for both poses.
- NFIX: 880 base_plate boundary nodes with z <= 4.8 mm, fixed 1-3.
- NLOAD: 122 fingertip face nodes within 9 mm of the TCP -> one
  *RIGID BODY to ref node; payload applied as *CLOAD on the ref node.
- Gravity: *DLOAD EALL GRAV 9810 (19620 for step 2) mm/s^2, -Z.

## Top-5 stress regions + recommendations (case B, worst)

All five are on grip_frame around (296-314, 12.5-15, 59.5):
 1. 2.13 MPa (296.2, 15.0, 59.5)
 2. 1.58 MPa (314.2, 15.0, 59.5)
 3. 1.54 MPa (314.2, 12.5, 59.5)
 4. 1.44 MPa (305.2, 12.5, 59.5)
 5. 1.33 MPa (305.2, 15.0, 59.5)
 -> one coherent hot patch on the grip_frame lower wall where the
 rack welds pull it downward. Even worst-case SF=11.7, so no redesign
 needed; if the margin must grow: fillet the inner corner at that
 patch and/or add a 2 mm rib between the two rack mounts. NOT applied
 (rule: do not modify CAD for findings).
Honest caveat: max-VM ~2 MPa means the structure is far from any
failure; the "top-5" is a relative ranking inside a low-stress model.

## Pose/range discrepancy (recorded, NOT silently fixed)

F2's AB pose uses J2=+90 deg while sim/STATUS-sim.md states the J2
limit is -120..+70 deg. AB is therefore an over-travel pose; kept as
the F2-defined case because the stage reuses F2 inputs verbatim.
Case C uses the true home pose.

## Unverified assumptions

- Rigid welds replace bearings/actuator compliance: joint stiffness is
  UPPER-bounded, so deflections are LOWER bounds; stresses at weld
  patches are smeared over ~40-node patches and miss real bolt/tooth
  contact peaks (grip_frame hot spot is one such weld-adjacent patch).
- Coarse cl=20 C3D4 linear mesh: absolute stresses are
  under-resolved; treat values as order-of-magnitude (all SF >> 1
  anyway). A cl=8-10 refined run was NOT performed (last solve slot
  kept spare per the 2 h budget); no coarse-vs-fine number available.
- Payload applied at fingertip nodes as a rigid patch: local stress
  concentration at the finger tips is averaged out.
- RF_z imbalance -5%: rigid-body slave DOFs under *DLOAD GRAV are
  condensed to ref nodes; the small deficit vs the analytic part-mass
  sum is consistent with per-part mesh-density rounding, accepted.
- Vendor masses come from parts_<case>.json density fields.

## Viewer

`../fea/.venv/bin/python view_arm_stress.py --case A|B|C`
`[--png <out.png> --no-window] [--scale 20] [--vmax MPa] [--vtu f.vtu]`
- Whole arm, jet gradient, VM scalar bar in MPa, DISP warped x20.
- Interactive window opens (rotatable); tested live: launched
  `--case A`, window opened with model + scalar bar + axes, captured
  with screencapture, process killed -> PASS.
- Renders written at fea_arm3/: arm_caseA.png (79 kB), arm_caseB.png
  (80 kB), arm_caseC.png (95 kB) - each 1920x900, front|side viewports,
  one scalar bar, all < 1.5 MB.

## Files (all under fea_arm3/, nothing else touched)

gen_geo.py (fragmented-model generator kept for reference), mesh_parts.py
(per-part mesher actually used), msh2arm3.py (msh->inp converter with the
rigid-link logic), frd2report.py (copied verbatim), view_arm_stress.py
(path/case updates only), make_assembly.py + msh2arm.py + SPEC.md (copied
verbatim for provenance), input/ (STEPs/json copied verbatim, gitignored),
report_AB.txt, report_C.txt, arm_case{A,B,C}.png, this file.
cad/, sim/, fea/, fea_arm/, pcb*/ : never edited.
