# Stage D9 — Hybrid lightening of the stock link plates (printable windows, safe) + J6 firmware sublimit
> Rules 0.1-0.10 of `~/Vector/ARM_KNUCKLE_V5.md` apply. Never edit existing branches. Create worktree `~/Vector-wt/lighten` on new branch `arm-lighten` from `origin/main` (= arm-cradlefix e0b3966, now merged). Work only in `lighten/` plus the one firmware patch in Task 5. Tag `lighten-1-done`, push branch+tags, STOP. Do not merge to main.

## Goal
The earlier free-form generative pass (`origin/arm-genlinks`, `genlinks/STATUS-genlinks.md`) was NOT safe as generated (upper_out SF 0.4-0.75, link1 near-mechanism). Do the safe hybrid instead: keep the proven stock plates, and cut lightening windows/pockets only in the low-stress zones that the genlinks stress fields and the real worst-case loads show, with fillets, ribs left around every bolt/bearing/horn keep-out. Candidates: upper_out, upper_back, dogleg_l/r, fore_l2/fore_r2 (not link1, not wrist parts). Pick those where it pays.

## Constraints
PETG-CF only (cross-layer 25 MPa [U], along-layer 50 MPa [U]), Bambu A1, no/minimal supports (overhang <=45 deg), print orientation so bending runs along layers. Keep ALL interfaces exactly (bolt holes, bearing/actuator seats, horn faces, axes, wall around fasteners, cable paths, cradle clearance from D7). Realistic static loads only (0.5 kg close in, 0.41 kg full reach, `software/robot-os/soma_arm/gravity.py`, Q_WORST), SF >= 2 on real static worst case, no stacked dynamic factors. Free tools only (FreeCAD FEM + CalculiX, gmsh, pyvista; existing venvs). Lessons: real bolt-load patches as distributed loads (no rigid glue), B32 not B31, check C3D10 inversions, cap solve time and say so. Do not edit original STLs/STEP: generate new ones from copies in `lighten/`.

## Tasks
1. Load cases per chosen plate from the worst poses; reuse genlinks domains/stress maps where helpful.
2. Design windows/pockets (parametric Python CAD export STL+STEP), minimum wall 2.4 mm, window fillets >= 3 mm, orientation noted.
3. Verify each lightened plate by FEM at real load vs the stock plate: max stress vs allowable, tip deflection, SF; interactive pyvista HTML (Fusion-style gradient) in `lighten/fea/`. Keep a variant only if SF >= 2 holds and deflection does not grow more than ~15 %. Honest if untrustworthy; say what was capped.
4. Re-run the posed-mesh collision sweeps (`final2/f2_collision.py` pattern, J1-J3 sweeps <=5 deg plus the Monte-Carlo seed 20261103) with the swapped plates; confirm no new collisions. Report mass before/after (g, at print infill) and total saved, plus before/after renders and a full-arm iso.
5. Firmware: add a J6 sublimit of about +-110 deg whenever J5 < 0 (covers vendor servo plug vs J5 case, see `cradlefix/STATUS-cradlefix.md`), in `software/robot-os/soma_arm` config/kinematics as a minimal patch with a unit test that passes (run it; show real output). Keep the J6 full range otherwise.
6. `lighten/STATUS-lighten.md` (honest, failures, [U] list, mass saved, worth adopting or not), `lighten/PRINT_LIST-lighten.md`, commit, tag, push. STOP.
