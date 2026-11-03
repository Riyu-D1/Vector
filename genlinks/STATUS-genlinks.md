# STATUS-genlinks — D8 generative links (exploratory)

Stage: `stages/D8_genlinks.md` on branch `arm-genlinks` (worktree
`~/Vector-wt/genlinks`), base `main` = arm-final2 `79394a1`. Scope: long
printed links only. Wrist (`w_*`), cradle and cradlefix files untouched.
Everything lives under `genlinks/`; no product files changed.

**Verdict up front: the study succeeds as "see how it would look" — the
generative forms are striking and printable-shaped — but NOT ONE generated
link is a safe drop-in. The stock links are 10–30× over-built for the real
static worst case, yet the free-form SIMP results overshoot the other way:
they fail SF ≥ 2 (or become near-mechanisms) and have interface regressions.
Adoption as-is: NO. What the study does show is a large mass headroom that a
hybrid design (keep the plate web, add SIMP-informed rib/window layout)
could capture.**

## Method (all code in `genlinks/`)

1. **Loads** — `genloads.py`: worst-pose gravity wrench per link from
   `software/robot-os/soma_arm/gravity.py` at `Q_WORST = [0, +70, −70, 0, 0, 0]°`
   (same pose + 0.41 kg full-reach payload as `upgrade1/gravity_up1.py`).
   Downstream bodies reduced to (F, M) at the link's downstream joint point,
   expressed in the part's STL frame; asserted equal to `gravity_torques()`
   on the joint axis (<1 N·mm residual). Link's own non-printed hardware
   applied as lumped masses (lumps inside the printed shell dropped — that's
   the shell's own mass, carried by `*DLOAD` gravity instead).
2. **Optimiser** — `gen_common.py`: voxel SIMP (min compliance, OC update,
   cone sensitivity filter r≈2.2·pitch ≥2 mm, 8-node brick elements verified
   by a uniaxial patch test, `spsolve` direct solve — CG/Jacobi measured at
   >25 % residual after 4000 it on these grids). Volume fraction applies to
   the FREE design volume; keep-out elements are passive solid at ρ=1.
   Interfaces (bolt lands, bearing/actuator seats, horn faces, joint axes)
   are keep-out cylinders/strips from the part geometry.
3. **Extraction** — `extract.py`: density isosurface bisected to a true-volume
   target (voxel-domain vf over-counts thin walls ~40 %) → Taubin smooth →
   largest body (+fragments >8 %) → STL. PETG-CF 1.31 g/cc.
   `redrill.py` then boolean-subtracts the exact source hole cylinders back
   through the smoothed solid (smoothing shrinks lands ~0.4 mm).
4. **Verification** — `fea/`: gmsh 2nd-order C3D10 remesh → `msh2gen.py`
   CalculiX deck (cad3/fea conventions: `*RIGID BODY` ref node at the
   centre-of-action offset r = F×M/|F|², residual dM measured 0.000 N·mm,
   NFIX/NLOAD/NLUMP nsets, `*DLOAD` gravity in the link frame,
   E=4000 MPa ν=0.35 ρ=7.62e-10 t/mm³) → ccx → `analyze_gen.py`
   (patch-filtered von Mises; patch stress reported separately) →
   `view_gen.py` pyvista interactive HTML + PNG.
   Voxel stair-steps produce knife-edge tets: 26 collapsed tets
   (corner volume < 1e-4 mm³ of 34 k) dropped on link1, 6 on fore_l2 —
   the earlier "drop every sliver" attempt carved voids into the load path
   and produced a mechanism (|U|=361 m, rejected). gmsh midnodes sit at
   exact edge midpoints so corner sub-tet tests cannot flag these; the
   parent-volume floor is the working check.
5. **Collision** — `collision_gen.py`: f2_collision.py posed-mesh machinery,
   generated STL swapped in, J1/J2/J3 sweeps at 2.5° (<5° required).
6. **Renders** — `render_gen.py` builds the export_assembly.py part set
   (meshes read from the sibling final2 worktree outputs, same commit) with
   generated links swapped in (orange); `render_blend.py` = copied verbatim
   workbench render.

## Load cases (Q_WORST, 0.41 kg at TCP)

| link body   | B (STL mm)        | F (N)           | M (N·mm)        | τ check |
|-------------|-------------------|-----------------|-----------------|---------|
| upper_plate | (−20.0, 0, 270.2) | (7.18, 0, −2.61)| (0.56, 1531.9, 1.5) | M·axis = τ_J3 1532 N·mm OK |
| fore_plate  | (96.4, 0, 216.2)  | (0, 0, −6.24)   | (0.71, 706.7, 0)    | M·axis = τ_J4 707 N·mm OK |
| link1       | (−20.0, 0, 143.5) | (0, 0, −14.16)  | (14.2, 2829.3, 0)   | M·axis = τ_J2 2829 N·mm OK |

Conservative: each upper plate carries the FULL shared J3 wrench (real split
~50/50 between upper_out/upper_back) [U]; each fore plate likewise. No
dynamic factors (stage rule). Plate self-weight = FE gravity of the material
that remains.

## Candidates

Chosen: **upper_out** (long upper plate, real free span), **link1** (heaviest
single printed part), **fore_l2** (fore plate pair representative).
Skipped: doglegs (76×5×99 mm connector plates, almost all interface),
fore_r2 (near-mirror of fore_l2; fore_l2 numbers bound the pair).
**upper_back** SIMP ran 30 iterations (converging, keep-frac 0.41 like
upper_out) but was deprioritised before extraction — upper_out is the
representative of the plate pair and was analysed carrying the full shared
wrench, so its result bounds upper_back's.

## Results

| part | mass solid g (src→gen) | print g (src→gen) | max VM MPa | max\|U\| mm | SF ≥ 2? | verdict |
|------|----------------------|-------------------|------------|------------|---------|---------|
| upper_out    | 24.8 → 17.4 (−30 %) | 18.8 → 13.2 (−5.6) | 66.5 | 2.96 | NO (0.4–0.75) | FAIL |
| upper_out_hi | 24.8 → 20.7 (−17 %) | ~15.7 | 56.7 | 2.01 | NO (~0.4–0.9) | FAIL |
| upper_out BASELINE | 24.8 | 18.8 | 1.74 | 0.055 | yes, huge | stock over-built ~30× |
| link1        | 55.8 → 41.7 (−25 %) | 42.4 → 31.7 (−10.7) | 442.6 | 59.1 | NO | near-mechanism |
| link1_hi     | 55.8 → 49.6 (−11 %) | ~37.7 | 212.1 | 28.4 | NO | still fails |
| link1 BASELINE | 55.8 | 42.4 | 25.3 | 0.54 | ~2× ok | stock comfortable |
| fore_l2      | 31.3 → 28.7 (−8 %)  | 23.8 → 21.8 (−2.0) | 15.6 | 0.32 | 1.6–3.2 [U] | marginal pass, pointless |

Total nominal saving if printed as generated: **≈18 g printed**
(upper_out 5.6 + link1 10.7 + fore_l2 2.0) — but see failures below.

### upper_out — A-frame truss, looks great, fails strength

The optimiser turned the 7 mm plate into a genuine A-frame truss between the
two preserved Ø56 bearing lands (see `renders/upper_out_ba_*.png`).
Filtered max VM 66.5 MPa at a mid-span web junction vs 25–50 MPa allowable
(→ SF 0.4–0.75), tip deflection 3.0 mm. The heavier variant (20.7 g) still
fails at the same hot spot (56.7 MPa): it is a geometric stress
concentration, not a bulk-stress problem, so adding volume barely helps.
Baseline sanity check under identical BCs: stock plate = **1.74 MPa /
0.055 mm** — the original is ~30× over-built for this load, which is why
the truss felt plausible. It is not safe.

### link1 — ring-ends on struts, a structural non-starter

The density field concentrated into the two preserved ring lands (J1 horn
seat, J2 flange seat) joined by 2–3 thin struts each over a thin base plate.
The struts cannot carry the 2.8 N·m J2 moment: |U|max 59 mm, filtered VM
443 MPa at the strut necks. The 89 %-mass variant still fails (212 MPa /
28 mm). This is the clearest case where free-form min-compliance topology
optimisation is the wrong tool — the interface-dominated part leaves too
little free design volume to form a competent load path at the target mass.
Stock baseline: 25.3 MPa / 0.54 mm — fine as-is.

### fore_l2 — almost nothing to remove

Keep-outs (dogleg bolt lands, J4 seat, horn bores) cover **88.8 %** of the
plate, so the optimiser could only shave ~8 % (2 g printed). The result is
essentially the stock plate with a few shallow pockets; FEA passes
(15.6 MPa, 0.32 mm) — but so would the untouched original, and 42 % of the
generated surface area sits beyond 45° overhang. Not worth printing.

## Interfaces & collision

- Bolt/bearing holes: smoothing shrinks lands ~0.2–0.7 mm; `redrill.py`
  restores the exact cylinders — upper_out both Ø56 bores, link1 all 7
  holes, fore_l2 12 of 18 (the 6 non-cylindrical/partially-open pockets
  left as-found, dr −0.1…−0.7 mm [U]).
- Home-pose check `genlinks/out/collision.log`: **3 interface regressions**
  — gen `upper_out` intrudes 280 mm³ into `cy2_housing` and 278 mm³ into
  `cy3_housing` (ring-land rim inflation into the bearing-seat envelope),
  gen `link1` intrudes 412 mm³ into `front_spacer_j2` (spacer pocket was
  not a keep-out). Both fixable only by local trimming or wider keep-outs.
- J1/J2/J3 sweeps at 2.5°: **CLEAR** — no pose-dependent collisions.

## Failures & [U] — honest list

- **FAIL** upper_out gen + hi: VM over allowable, SF < 1. Not adoptable.
- **FAIL** link1 gen + hi: near-mechanism deflection. Not adoptable.
- **FAIL** home-pose intrusions above (3 parts would need trim/redesign).
- **FAIL** fore_l2: 42 % >45° overhang fraction for only 2 g saved.
- [U] PETG-CF modelled isotropic E = 4000 MPa; allowables 25 MPa
  cross-layer / 50 MPa along-layer taken from the rules table — the SF
  column brackets both. fore_l2's pass flips between them (1.6 vs 3.2).
- [U] Patch loads model the bolt group as a rigid body on the land nodes;
  real load spread through each bolt differs. Patch-zone stress reported
  separately (upper_out patch 6.4 MPa, link1 24.2, fore_l2 5.2).
- [U] No fatigue/creep — PETG creeps under sustained gravity load; even a
  "passing" design needs derating for a robot that holds poses for hours.
- [U] SIMP uses voxel bricks at 1–1.5 mm; sub-voxel features (1 mm wall
  ribs) are under-resolved — real printed struts could be weaker OR absent.
- [U] link1 FEA dropped 26 collapsed knife-edge tets (0.07 % of elements,
  all at stair-step notches); fore_l2 dropped 6. Reported, not hidden.
- [U] Wrench uses conservative full-shared-wrench-per-plate; real split is
  ~50 %, i.e. the reported stresses are an upper bound, not a lower one —
  safe direction for a FAIL verdict, conservative for fore_l2's pass.
- [U] "Printable mass" uses the PRINT_LIST convention (shell+infill); gen
  parts would slice differently (struts ≈ solid anyway).

## Was it worth it?

As an exploration: yes — the renders answer "how it would look" (dramatic,
organic, obviously lighter) and the study quantified that the stock long
links carry ~10–30× the static worst-case margin. As a redesign input:
**not adoptable** — every generated candidate fails SF ≥ 2, collision, or
printability. The correct next step is not lighter SIMP targets but a
different formulation: constrain stiffness/stress (not compliance-only),
keep plate webs solid and let the optimiser place windows/ribs, and widen
interface keep-outs to include the cyclo housing and spacer envelopes.

## Environment / deviations

- `/Users/deepakdiwan/soma/.venv/bin/python` (rules' CAD python) does not
  exist → used system python3.12 (numpy/scipy/trimesh/manifold3d) + the
  existing `Vector-wt/fea/fea/.venv` pyvista for extraction/HTML. No installs.
- skimage absent → trimesh marching-cubes unusable → VTK/pyvista contour.
- Source STLs read from prebuilt `Vector-wt/final2` outputs (same commit);
  `cad/arm2b/out/` is gitignored build output.
- CalculiX solve wall-times kept short (~1–4 min/deck, spooles direct);
  no solves left running (stage: don't let solves crawl).

## Artifacts

- `genlinks/out/` — source + generated STL/STEP, `*_field.npz` optimiser
  fields, `*_report.json` mass/interface census, `collision.log`, run logs.
- `genlinks/fea/` — `.geo` remesh scripts, interactive `*.html` + `*.png`
  per run (gen / _hi / _base variants), `*_step1.vtu`-derived views.
  Heavy regenerables (.frd/.msh/.inp/.vtu) gitignored.
- `genlinks/renders/` — `arm_before_*` / `arm_after_*` 6-view sets,
  per-candidate `*_ba_*` before/after 6-view sets.
- `genlinks/` scripts — `genloads.py`, `gen_common.py`, `gen_parts.py`,
  `extract.py`, `redrill.py`, `report.py`, `collision_gen.py`,
  `render_gen.py`, `render_blend.py`, `fea/{gen_geo,msh2gen,run_fea,
  analyze_gen,view_gen}.py`.
