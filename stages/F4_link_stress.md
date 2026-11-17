# Stage F4 — REAL stress numbers for the shoulder (upper) link, loaded with the whole-arm loads. Work in the existing worktree.
> Rules 0.1–0.10 of `~/Vector/ARM_KNUCKLE_V5.md` apply, with these overrides:
> (a) Worktree `~/Vector-wt/fea`, branch `arm-fea`. Work ONLY in a NEW folder `fea_link/`. Copy what you need from `fea/` (F1 single-link pipeline: make_input.py, msh2inp.py, frd2vtu.py, view_stress.py, input/link_fea.step) and `fea_arm3/` (parts_AB.json, parts_C.json, report_AB.txt, report_C.txt, STATUS-fea-arm3.md). Never edit existing files elsewhere. Do not commit `cad/arm2b/out/` or any .frd/.inp/.msh/.db/.vtu bigger than 5 MB. Absolute paths only, built from `Path(__file__).resolve().parent`; assert nodes > 0, elements > 0, result blocks > 0 after each stage.
> (b) HARD LIMITS: 2 hours total, at most 4 CalculiX solves. Write in `fea_link/STATUS-fea-link.md` what each solve returned before starting another. If the limit runs out, write the honest status and STOP. No loops.

## Why
The whole-arm run (F3) used rigid welds, so its stress colours were unrealistic (about 1 MPa). But its joint moments are credible: case A (full reach, 0.5 kg) J2 = 3.39 N·m, J3 = 0.71, J4 = 1.75; case B (2x) J2 = 6.79. Now take the real printed shoulder link and load it properly, alone, with a fine quadratic mesh, so its stress is believable.

## Steps
1. Link = the printed shoulder link between the J2 axis and the J3 axis (bodies `upper`: `upper_out`, `upper_back`, plus `back_spacer_j2/j3` if they carry load; check `fea_arm3/SPEC.md` and `sim/STATUS-sim.md`). Use `fea/input/link_fea.step` if it is that link, and say which parts are in the model.
2. Boundary conditions and loads, written down with numbers in the status:
   - Fix the bolt-hole faces where the link bolts to the J2 actuator (use the real hole faces and a washer-sized patch, not the whole face).
   - At the J3 end apply the real resultant of everything beyond J3 (force from the weight of fore, wrist, gripper, actuator and 0.5 kg payload, plus the moment about the Y axis) as a distributed load through a rigid coupling (`*RIGID BODY`/`*COUPLING` on the J3 bolt faces), computed from masses and positions in `fea_arm3/parts_AB.json`. Also add the link's own weight.
   - Cases A (full reach, 1x) and B (2x). Case C (home pose) if there is a solve left.
   - Print the resulting J2 moment from the link model and compare with 3.39 N·m (A) to prove the load is right (within 10%).
3. Mesh: quadratic tets (C3D10). Solve a coarse mesh (about 5 mm) and a fine mesh (about 2.5 mm, finer at holes and fillets). Report max von Mises for both so the convergence is visible. Ignore single-node peaks at the rigid-coupling and fixed patches; report stress away from them (say how).
4. Material: PETG-CF E = 4.0 GPa, nu = 0.35, cross-layer limit 25 MPa, along-layer 50 MPa [assumptions, unverified]. Report the safety factor for A and B against 25 MPa. Also run the same case A with PLA-like E = 2.5 GPa, limit 15 MPa as a pessimistic check.
5. Viewer and pictures: `fea_link/view_link_stress.py` (pyvista from `/Users/deepakdiwan/Vector-wt/fea/fea/.venv/bin/python`) with the von Mises colour gradient, rotatable, displacement ×20; PNGs `link_caseA.png` and `link_caseB.png` (colour bar in MPa, two angles, hot-spot marked). Test that the viewer opens (launch, `screencapture`, kill).
6. Top 3 hot spots with concrete suggestions (fillet radius, wall, rib), and a plain verdict: does the link survive A and B with SF >= 2? Do NOT modify the CAD.
7. `git add fea_link && git commit -m "F4: shoulder link stress under whole-arm loads (copy)" && git tag fea-4-done && git push origin arm-fea --tags`. STOP.
