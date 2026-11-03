# STATUS-lighten.md — Stage D9: hybrid lightening of stock link plates + J6 firmware sublimit

Date: 2026-11-03. Branch `arm-lighten` off `origin/main` e0b3966 (D7 merged).
Worktree `~/Vector-wt/lighten`; all work under `lighten/` plus the one
firmware patch in `software/robot-os/soma_arm`.

## Bottom line — nothing on the plates pays; J6 sublimit adopted

Every lightened candidate was FEM-gated against the proven stock plate and
**all variants failed the D9 gate** (SF ≥ 2 AND tip deflection growth
≤ ~15 %). The verified answer is **do not lighten the plates**: the stock
plates already carry a neutral-axis slot that spans almost the entire legal
opening — its ends sit 34.4 mm from the joint axes vs the 33 mm keep-out —
and every remaining near-zero-stress region lies *inside* the r≈31.5 mm
bolt/bearing keep-outs. Mass saved on structure: **0.0 g**. The firmware
J6 sublimit is the stage's real deliverable and IS adopted.

## Gate lines (real output)

| Check | Command | Result |
|---|---|---|
| Loads derived | `python3 lighten/l_loads.py` → `lighten/out/loads.json` | PASS — upper_plate wrench |M|=1532 N·mm = J3 torque 1.532 N·m exactly; fore_plate |M|=707 = J4 torque |
| Free-material census | `lighten/l_census.py` | PASS (info) — see Task 1 |
| FEM, 8 decks | `lighten/fea/run_fea.py <tag> 1.4` (gmsh→ccx→analyze→pyvista) | **all lightened variants FAIL** — table below |
| Unit tests | `cd software/robot-os && python3 -m pytest -q` | **71 passed in 5.00s** (66 prior + 5 new) |
| Collision | `lighten/l_collision.py` (f2_collision.py verbatim, seed 20261103) | CHECKS FAIL *identical to final2 baseline* — MC **2457** undeclared (same count), same documented families; **no new collisions** |
| Mass | `lighten/l_mass.py` | adopted none → **saved 0.00 g** |
| Renders | `lighten/l_render.py` ×3 (Blender workbench) | 18 PNGs, all views reviewed — observations below |

## Task 1 — load cases (`l_loads.py`, from `soma_arm/gravity.py`)

Full-reach `Q_WORST = [0, +70, −70, 0, 0, 0]°`, 0.41 kg payload →
J2 2.829 / J3 1.532 / J4 0.707 N·m. Close-in
`Q_CLOSE = [0, +30, −150, +90, 0, 0]°`, 0.5 kg → J2 1.445 / J3 0.699 /
**J4 0.774** N·m — the close-in case governs J4-side parts (fore plates);
recorded in `loads.json` `q_close`. Upper plates verify against the J3
wrench (1532 N·mm about its axis), fore plates against J4 (worst of
707/774 → 774 N·mm governs; the genlinks fore BCs use 707 — noted below).

Candidate census (`l_census.py`, voxel keep-out census at 1 mm pitch,
holes = enclosed voids detected by flood-fill):

| part | vol cm³ | free cm³ (%) | verdict |
|---|---|---|---|
| upper_out | 18.9 | 10.1 (53 %) | candidate — but see Task 3 |
| upper_back | 27.6 | 10.3 (37 %) | candidate — but see Task 3 |
| fore_l2 / fore_r2 | 23.9 / 23.8 | 2.5 (~10 %) | **skip** — the only "free" band is the J3→J4 load web; ≤1.9 g for halved ligament |
| dogleg_l / dogleg_r | 19.4 ea | 8.7 (45 %) | **skip** — free voxels are the diagonal load web between the two bolt clusters (same conclusion as genlinks: interface/keep-out dominated) |

## Task 2 — design (`build_lighten.py`, parametric build123d)

New geometry only under `lighten/out/` (stock files untouched). The
builder calls `p_arm2`'s own stadium/collar/ring functions verbatim and
swaps the window set; keep-out check asserts every cutter point ≥33 mm
from both joint axes (printed: 34.4 mm). All exported STLs watertight.

- `_l`  — two rounded-rect windows (x 14.5–38, 48.8–72.3, z 143.5±22,
  fillet r8 ≥ 3) + mid-rib + 8.5 mm rails; replaces the stock slot.
  Removes 2.50 cm³.
- `_lp` — `_l` + blind pockets 1.6 mm deep off the outboard face on rails
  + rib (floor 2.4 mm = min wall). Removes 4.25 cm³.
- `_l2` — **keeps** the stock slot + shallow z±10 extension windows,
  fillet r6. Removes 0.01 cm³ ≈ **0 g** — the stock slot (x 13–73.7
  with r12 caps, z±12) already spans the legal opening.

## Task 3 — FEM (FreeCAD gmsh + CalculiX 2.23 + pyvista)

Pipeline `lighten/fea/run_fea.py`: STEP→gmsh C3D10 (h 1.4 mm)→`msh2gen.py`
(genlinks deck writer: distributed NFIX/NLOAD patch nodes, NLUMP hardware
lumps, `*RIGID BODY` ref node for the wrench, gravity `*DLOAD`)→ccx→
`analyze_gen.py` (raw/patch-filtered VM, max |U|)→`view_gen.py`
(pyvista HTML + iso/front PNG in `lighten/fea/`).

**Mesh trustworthiness — real fix made**: ccx aborted with
`*ERROR in e_c3d: nonpositive jacobian` on 6 elements. Diagnosis:
knife-edge tets on the curved collar edges pass the parent-volume check
but invert at ccx's 4 Gauss points. `msh2gen.py` now drops any C3D10
whose quadratic Jacobian is nonpositive at the Gauss points and reports
the count (2–6 per deck, all surface slivers; documented, not hidden).
Decks: 63–116 k nodes, 33–67 k C3D10. Solves ~2–6 min each — no cap hit.
Residual wrench offset error |dM| = 0.000 N·mm.

Results (governing full-reach wrench, cross-layer allowable 25 MPa [U]):

| variant | max \|U\| mm | ΔU vs stock | hot VM MPa | SF(25) | gate |
|---|---|---|---|---|---|
| upper_out stock | 0.811 | — | 4.00 @ slot top edge | 6.3 | ref |
| upper_out_l | 1.465 | **+81 %** | 7.54 @ rib edge | 3.3 | **FAIL ΔU** |
| upper_out_lp | 2.630 | **+224 %** | 16.90 @ corner | 1.5 | **FAIL ΔU + SF** |
| upper_out_l2 | — | — | — | — | moot: 0.01 cm³ removed |
| upper_back stock | 0.786 | — | 3.94 | 6.3 | ref |
| upper_back_l | 1.425 | **+81 %** | 7.41 | 3.4 | **FAIL ΔU** |
| upper_back_lp | 2.555 | **+225 %** | 16.78 | 1.5 | **FAIL ΔU + SF** |

**Why every cut fails**: per-node VM sampling of the stock fields
(`l_hotmap.py`) shows all VM < 0.4 MPa material is inside r50 of the
J2/J3 axes (bolt lands, bearing seats — keep-out). The working web is
only z 183–231 between the keep-outs: left ligament ~1.2 MPa, right
~2.3 MPa — genuinely loaded. Deflection tracks web section stiffness
almost 1:1, so any ligament cut or face pocket blows the +15 % gate long
before it saves a gram. The stock R12 neutral-axis slot is already the
optimal cut; it sits exactly on the bending neutral axis.

**Adopted: none.** The six candidates stay stock.

## Task 4 — collision, mass, renders

- `lighten/l_collision.py` = `final2/f2_collision.py` verbatim (mesh set
  identical — nothing swapped): HOME PASS; J3/J4/J5/J6/gripper sweeps
  PASS; J1 contacts below −152.5° (designed yaw stop), J2 +62.5..70° and
  below-table (documented); named poses 5/6 (wrist-fully-flexed
  w_j4_cradle×w_link5 3.4 mm³ graze, same as final2); MC seed 20261103 →
  **2457 undeclared — bit-identical to the final2 baseline**; servo
  clearances 0.18–0.26 mm unchanged. ⇒ **zero new collisions**.
- Mass (`l_mass.py`, 1.31 g/cm³ per final/PRINT_LIST convention on
  effectively-solid 4 mm parts): upper_out 24.8 g, upper_back 36.1 g
  stock; `_l` would save 3.28 g/plate, `_lp` 5.57 g/plate — both
  rejected by FEA. **Total adopted saving 0.00 g.**
- Renders (`lighten/rend/`): `plates_stock_*` vs `plates_l_*` six views
  each + `arm_*` full-arm six views. Observations: stock pair shows the
  single neutral-axis slot flanked by full ligaments and intact
  bolt-ring lands; `_l` shows the two-window + rib pattern (visibly
  thinner side rails — matches the +81 % deflection); cutaway confirms
  collars/rings and the 4 mm web; arm iso/side show the upper plates in
  pose spanning J2→J3 with the fore plates and wrist clear. All 18
  reviewed; nothing anomalous.

## Task 5 — J6 conditional sublimit (ADOPTED)

`config.py`: `J6_SUBLIM_J5_NEG = radians(110)` — cradlefix residual:
gripper servo plug rolls into the J5 vendor case at |J6|>~110° when
J5 < 0 (vendor pair, unfixable in print). `kinematics.py`: new
`j6_bounds(q5)`; `clamp_limits`, `within_limits`, and the IK candidate
check all honour it; J6 keeps ±180° whenever J5 ≥ 0 (boundary: J5 = 0 →
full range). `tests/test_j6_sublimit.py` (5 tests: sublim value,
full-range at J5≥0, rejection at J5<0, clamp, IK refusal) →
`71 passed in 5.00s`.

## Files changed

- `software/robot-os/soma_arm/config.py` (+J6_SUBLIM_J5_NEG)
- `software/robot-os/soma_arm/kinematics.py` (+j6_bounds, wired into
  clamp_limits / within_limits / IK check)
- `software/robot-os/tests/test_j6_sublimit.py` (new, 5 tests)
- `lighten/`: `l_loads.py l_census.py l_hotmap.py build_lighten.py
  l_mass.py l_collision.py l_assembly.py l_render.py`,
  `fea/{gen_geo,msh2gen,analyze_gen,run_fea,view_gen}.py` +
  12 result PNGs, `rend/` 18 review PNGs, this STATUS, PRINT_LIST.
- Generated but not committed (>1.5 MB or out/ rules): `lighten/out/*`
  STL/STEP/loads.json, `lighten/fea/*.html` (6 interactive pyvista
  views, 1.1–3.1 MB each), `*.inp/.msh/.frd/.vtu` decks — all
  reproducible: `build_lighten.py` → `fea/run_fea.py <tag> 1.4`.
- `cad/arm2b/out/` rebuilt locally (untracked build product,
  `build_arm2b.py`, unchanged sources).

## [U] unverified values encountered

- PETG-CF allowables 25 MPa cross-layer / 50 along-layer `[U]` (stage).
- RING_D 57.15 bears `[U slip + CA]` note in ap2 (untouched).
- rebot `[S]` dims reused via p_arm2 unchanged.
- FEM material E=4000 MPa, ν=0.35 `[U]` (genlinks deck values, reused).

## Fallbacks used

- CAD venv: `~/Vector-wt/cradlefix/.venv` (rules' `~/soma/.venv` absent
  on this machine) — build123d 0.13.0, also supplies manifold3d/trimesh/
  scipy for `l_collision.py` and `l_census.py`.
- pyvista venv: `~/Vector-wt/fea/fea/.venv` (no trimesh → `l_hotmap.py`
  uses pv.read for STLs).
- gmsh/ccx from FreeCAD.app bundle (`…/Resources/bin/`); blender
  `/usr/local/bin/blender` workbench.
- `l_collision.py` is a verbatim copy (not import) because f2_collision
  is stage code — reviewed, no edits beyond the header line.

## Worth adopting?

**Plates: NO** — verified negative result; stock design is already
near-optimal for the governing load. Revisit only if a genuinely
different load case or a topology-optimised web (not windows) is wanted.
**Firmware: YES** — J6 ±110° sublimit at J5<0 is cheap insurance for a
proven vendor-pair graze.

## Open questions / honest limits

- FEM uses the genlinks rigid-ref-node wrench (patch = distributed, but
  the load introduction is still a rigid body — local patch-edge stress
  is filtered, reported as "patch VM"; hot spots are at real geometry
  edges, not BC artifacts).
- No PETG creep/fatigue model; static only, as scoped.
- `within_limits`/`clamp_limits` enforce the J6 sublimit on targets and
  IK; `planner.check_in_limits` sees post-clamp targets via `arm.py` —
  a direct `plan()` call with J5<0 ∧ |J6|>110° would not be pre-rejected
  (clamp still applies at execution). Minimal patch per stage.
- `random_reachable_q` still samples raw limits (test helper only).
- MC uniform space includes unreachable fold poses by design — the
  identical-count match to final2 is the evidence, not the count.
- 0.5 kg close-in J4 governs fore plates (774 N·mm); fore FEA BCs
  documented at 707 — moot since fore plates were not modified.
