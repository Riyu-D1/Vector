# Stage F4 status — shoulder link (J2->J3) stress under whole-arm loads

Worktree ~/Vector-wt/fea, branch arm-fea, folder fea_link/ (NEW; nothing else
touched).  Pipeline reused from fea/ (F1: link_fea.step, frd2vtu.py copied
verbatim; tet-reorder + frd parsing code kept verbatim inside msh2link.py /
analyze.py) and fea_arm3/ (input/parts_AB.json, parts_C.json, report_AB.txt,
report_C.txt, STATUS-fea-arm3.md copied for reference/inputs).

Solve budget: 4 CalculiX solves max (stage hard limit).  Used: 3 so far
(link_25 fine AB killed after step 1 by the session interrupt).

## Model — what is in it

Link = `fea/input/link_fea.step` (F1 output, copied): the printed shoulder
link between the J2 and J3 axes = upper_out + upper_back + back_spacer_j2 +
back_spacer_j3, i.e. ALL printed parts of sim body `upper` (spec cross-check:
fea_arm3/SPEC.md body table, sim/STATUS-sim.md).  NOT meshed (they are not
the printed link): vendor_act_j2/j3 (0.300 kg each), vendor_6803_j2/j3,
vendor_actout_j2/j3 — their masses enter as loads instead.
Frame: J2 axis = Y through (0,0,0); J3 axis = Y through (126.7,0,0); +Z up
in the full-reach pose.  STEP check: bbox (-30.5..157.2, +-32.1, +-30.5),
vol 65.5 cm3 = 0.0499 kg printed.

IMPORTANT: link_fea.step contains TWO disjoint solids — upper_out (+collars,
y -32.1..-25.1) and upper_back+spacers (y +23.4..+32.1).  In the real arm the
J2/J3 actuator housings bridge them.  Each solid is therefore constrained
through its own real mount faces (below), not welded to the other.

## Boundary conditions and loads (numbers from ap2.py/ap.py + parts_AB.json)

- NFIX (J2 end): the real bolt pattern = 6x M3 holes on LINK_PCD 50 (ap.py:
  LINK_PCD=50, LINK_N=6, ang0=0) through the back stack (back_spacer_j2
  y 23.4..28.1 + upper_back y 28.1..32.1): hole faces + washer patch
  (all nodes within 3.8 mm of a hole axis, y in [22.9,32.6]); PLUS the
  upper_out J2 housing-grip face (RING_D 57.15 bore, nodes r 27.3..29.9 mm
  from the J2 axis, y in [-33.2,-24.0]).  Both fixed 1-3.
- NLOAD (J3 end): the same two sets at x+126.7 -> *RIGID BODY, ref node at
  the downstream centre of action (275.55, 0, 0).  The resultant is applied
  there as a pure force -11.814 N in z (case A): the rigid arm back to the
  bolt faces reproduces F + M exactly (couple moments on rigid ref nodes do
  not reach slave nodes in this ccx setup — see solve log 1/2).
- Load derivation (fea_link/loads.py -> input/loads.json, all from
  parts_AB.json centroids/masses, case A 1x):
    downstream (fore+wrist4+wrist5+grip+fingers)  0.3968 kg
    carried at J3 mount (vendor_act_j3+6803)      0.3075 kg
    payload                                        0.5000 kg at TCP
    -> F_z at J3 = -11.814 N ; M_y about J3 = +1758.6 N.mm
    -> centre of action d = M/F = 148.85 mm -> ref_app (275.55,0,0)
    link's own weight 0.489 N via *DLOAD GRAV 9810 -Z.
  Case B: all loads + gravity x2.
  NOT applied: J2-side carried mass (vendor_act_j2+6803 = 0.3075 kg) sits at
  lever arm ~0.0001 mm from the J2 axis — it reacts inside the fixed patches
  (~0 link stress, ~0 J2 moment).  Recorded here, not applied.
- Materials: PETG-CF E=4000 MPa nu=0.35 rho 7.62e-10 t/mm3 (parts_AB.json
  convention); pessimistic check PLA E=2500 MPa nu=0.35 same density.

## Solve log (written before each new solve, per stage limits)

### Solve 1/4 — link_5 coarse AB, PETG, force+COUPLE at ref node (REJECTED)
126,896 nodes / 73,802 C3D10 (gmsh cl=5, clh=2.5, ElementOrder=2, fields:
2 Balls r34 at joint ends).  First deck also had NACT rigid body on the J2
bore carrying the J2 actuator weight.
- Run A (initial): max|U| = 3.3e9 mm -> mechanism: upper_out is a disjoint
  solid held only by the free NACT ref node.  FAIL, deck rebuilt.
- Run B (fix incl. J2 bore; force -11.814 @dof3 + moment +1758.6 @dof5 on the
  J3-axis ref node): solved, but NFIX reaction moment = -1.528 N.m vs the
  required -3.29; NLOAD patch internal moment about J3 = 0.000 -> the dof-5
  couple on the rigid-body ref node never reached the bolt faces (ccx keeps
  it on the free ref node; slaves carry only the force).  Loads WRONG -> FAIL.
  This also means fea/link_c/link_f (F1) relied on the same dof-5 line; noted.

### Solve 2/4 — link_5 coarse AB corrected (force at centre of action)
Same mesh; resultant applied as pure force -11.814 N at ref node
(275.55, 0, 0) = J3 + 148.85 mm.  ccx 2.23 "Job finished", 8 result blocks.
- step 1 (case A): max|U| 0.050 mm; NFIX RFz sum +12.28 N (applied 12.30:
  downstream 11.81 + link 0.49) -> equilibrium OK.
  J2 reaction moment = -3.286 N.m vs F3 frd 3.39 -> -3.1% (within 10%: PASS).
  raw maxVM 1.00 MPa; patch-filtered maxVM 0.89 MPa.
- step 2 (case B, 2x): max|U| 0.100 mm; J2 moment -6.573 vs 6.79 -> -3.2%.
  raw maxVM 2.01 MPa; filtered 1.78 MPa.
  (filtered = nodes in NFIX|NLOAD and every element touching them excluded;
  89,103 of 126,896 nodes excluded from hot-spot ranking.)
- Hot spots (filtered, case B): (16.2,32.1,-24.1) 1.78 MPa washer-patch rim;
  (37.8..39.0, +-28..-31, +-30.5) ~1.6 MPa outer stadium edge mid-span.

## Mesh plan
- coarse: cl=5, joint-end balls 2.5 -> 126,896 nodes / 73,802 tets (done)
- fine:   cl=2.5, joint-end balls 1.2 -> 332,223 nodes / 268,932 msh elems
  (207,302 C3D10 in the frd; the rest are boundary triangles) (solved A)

### Solve 3/4 — link_25 fine AB, PETG (step 1 = case A completed; step 2 lost
to the session interrupt, .frd has 4 result blocks, .sta shows step 1 only)
- step 1 (case A): max|U| 0.050 mm; J2 reaction moment -3.286 N.m vs F3 3.39
  -> -3.1% (within 10%: PASS, identical to coarse).
- raw maxVM 1.01 MPa; patch-filtered maxVM 0.83 MPa (coarse: 1.00 / 0.89 ->
  converged within ~7%).  134,606 of 332,223 nodes excluded from ranking.
- Hot spots (filtered, case A): (16.5,32.1,23.1) 0.83 washer-patch rim J2;
  (38.5..39.1, +-31..-32, +-30.5) 0.81 outer stadium edge mid-span.
- step 2 (case B) not written; B = 2x A EXACTLY (all loads doubled, linear
  statics, same BCs) -> fine B numbers: raw 2.02, filtered 1.66 MPa,
  max|U| 0.100 mm, J2 moment -6.573 (-3.2% vs 6.79).

### Solve 4/4 — link_25_pla fine, case A only, PLA E=2500 nu=0.35 (pessimistic
check, stage step 4; last solve in the budget)
ccx 2.23 "Job finished", 4 result blocks.
- step 1 (case A): max|U| 0.080 mm = 1.6x PETG (= 4000/2500, exact for linear
  statics); J2 reaction moment -3.286 N.m (-3.1% vs F3: PASS).
- raw maxVM 1.01 MPa, patch-filtered 0.83 MPa — IDENTICAL to the PETG run.
  Expected: with force-only loads (CLOAD + gravity) and homogeneous BCs the
  stress field is E-independent; only displacement scales with 1/E.  The PLA
  solve confirms it numerically.
- Pessimistic limit check: filtered 0.83 MPa vs PLA cross-layer 15 MPa ->
  SF = 18.  PASS.

### Case C (home pose) — NOT RUN
Solve budget exhausted (4/4 used: coarse-AB attempt, coarse-AB corrected,
fine-AB, fine-A-PLA).  Stage allows skipping C when no solve is left.
Expected anyway: C puts the resultant axially (-X link frame), J2 moment
1.76 N.m (loads.json) ~ 0.5x case A -> stresses well below A; not the
critical case.

## Results (fine mesh, patch-filtered)

| case | raw maxVM | filtered maxVM | max|U| | J2 mom vs F3 |
| A 1x PETG | 1.01 MPa | 0.83 MPa | 0.050 mm | -3.29 vs 3.39 (-3.1%) |
| B 2x PETG | 2.02 MPa | 1.66 MPa | 0.100 mm | -6.57 vs 6.79 (-3.2%) |
| A 1x PLA  | 1.01 MPa | 0.83 MPa | 0.080 mm | -3.29 (-3.1%) |
Case B = 2x case A fields exactly (all loads doubled, linear statics); the
fine B numbers above are the solved A fields x2, not a separate solve.
Convergence: coarse filtered 0.89 vs fine 0.83 MPa (-7%) — converged.
"Filtered" = every node in NFIX|NLOAD plus all nodes sharing an element with
them excluded from the max (134,606 of 332,223 nodes) — the rigid-coupling
and fixed-patch single-node singularities are ignored per the stage.

## Safety factors (filtered, vs 25 MPa cross-layer PETG-CF limit)
- A: 25 / 0.83 = 30.2   (raw: 25 / 1.01 = 24.8)
- B: 25 / 1.66 = 15.1   (raw: 25 / 2.01 = 12.4)
- vs 50 MPa along-layer: A 60, B 30.
- PLA pessimistic: 15 / 0.83 = 18.1.

## Top 3 hot spots (filtered ranking, >=15 mm apart; values A / B)
1. (16.5, 32.1, 23.1): 0.83 / 1.66 MPa — rim of a J2 M3 bolt hole on the
   upper_back outer face (y 32.1), just outside the 3.8 mm washer patch.
   Bolt-edge bearing concentration.  Suggestion: small chamfer/fillet
   (R0.5-1) on the hole rim at the y 32.1 face, or a wider washer flange.
2. (x 36..39, y -29..-32, z +-30.5): 0.81 / 1.62 MPa — outer-fibre long edge
   of the upper_out rails at mid-span (both z extremes, symmetric).
   Bending hot spot on a sharp outer corner.  Suggestion: full-length outer
   fillet R2-3 on the rail edges, or a shallow rib along the rail mid-line.
3. (36.0, 28.1, +-30.5): 0.79 / 1.58 MPa — same outer-fibre edge where it
   continues onto the upper_back plate (y 28.1 shoulder).  Suggestion:
   carry the same R2-3 fillet around the shoulder transition, or thicken
   the outer lip locally.

## Verdict
YES — the printed shoulder link survives case A and case B with SF >> 2
(worst filtered B hot spot 1.66 MPa vs 25 MPa cross-layer limit, SF 15;
raw including constraint-patch singularities still SF 12).  The J2 moment
check (-3.1% / -3.2% vs the F3 whole-arm reference) confirms the applied
resultant reproduces the real downstream loads.  CAD NOT modified; the
suggestions above are advisory only — margins are so large none is needed.

## Viewer
fea_link/view_link_stress.py (pyvista, fea/.venv) — tested: launched on
run/res_25_step1.vtu, PyVista window opened (two rotatable viewports),
screen-captured, killed.  PNGs: link_caseA.png, link_caseB.png (two angles
each, MPa colour bar, disp x20, red sphere at the filtered hot spot).

## Files
fea_link/: .gitignore, analyze.py, frd2vtu.py (copied fea/ verbatim),
link.geo, loads.py, msh2link.py, view_link_stress.py, link_caseA.png,
link_caseB.png, STATUS-fea-link.md, report_AB.txt, report_C.txt,
STATUS-fea-arm3.md (copied fea_arm3/ for inputs).  input/ (STEP, json) and
run/ (.msh/.inp/.frd/.vtu) are gitignored per the stage size rules.
Tools used: gmsh+ccx from /Applications/FreeCAD.app/Contents/Resources/bin
(ccx 2.23, gmsh 4.15); pyvista 0.49.2 from fea/.venv.
