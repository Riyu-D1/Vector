# STATUS-ver — SOMA V1 verification (stage `V1_actuator_fea.md`)

Branch `arm-ver` from `arm-ord`@95d045d. All work in `verify/`. No product files changed.
Hardware: 16 GB Mac; tools: FreeCAD-bundled `freecadcmd`, `ccx` (2025-11-07 build), `gmsh`, pyvista venv.
Time-box rules applied throughout: <=3 attempts per solve, hard kill at 40 min per solve.

## Verdict headline

**No FEA model completed a loaded increment inside the time-box.** The contact models are
built, geometry-verified, Jacobian-clean and demonstrably Newton-converging, but every run was
killed at the 40-min cap before the disc reached pin engagement (~0.16 mm of drive). Design
conclusions therefore rest on the stage-prescribed fallback: **Hertz hand cross-check**, which
predicts **the cycloidal disc lobes fail** (SF 0.14–0.33 < 2) at the J2/J3 service torques.
Do NOT order parts on the strength of the previous ~11 MPa sanity figure — see §1.

## Case ledger

| # | Case | Status | Result |
|---|------|--------|--------|
| 1 | Cycloidal contact FEA, 40:1 module (J2 & J3 share geometry), 3 phases | **FAILED (incomplete)** | 7 solves, all killed at cap or invalid; model verified, converged seating increments only |
| 1b | Hertz hand cross-check (mandated fallback) | **SOLVED (hand calc)** | lobe contact p0 128–289 MPa, equiv SF 0.14–0.33 → FAIL |
| 2a | J2 bolted whole-joint model | **NOT DONE** | deck built (203,910 n / 114,475 tets), validated, never launched |
| 2b | J3 bolted whole-joint model | **NOT DONE** | deck built (188,170 n / 107,165 tets), validated, never launched |
| 2c | J4 STS3250 cradle model | **FAILED** | 4 attempts: 2×killed at cap while converging, 2×invalid (0-spring/untied) |
| 3a | Shock/E-stop torque (0.1 s stop) | **SOLVED (hand calc)** | J2 9.19, J3 4.21, J4 1.19 N·m |
| 3b | Fatigue/lifetime estimate | **SOLVED (estimate, [U])** | Basquin + literature endurance ~10–15 MPa |
| 4 | Whole-arm sanity FEA (optional) | **NOT DONE** | deferred per stage (optional if time) |
| 5/6 | Fix loop for SF<2 | **NOT DONE** | no converged FEA SF to fix against; Hertz flag below |
| 7 | Interactive viz | **PARTIAL** | cyc1_eng seating increments → `verify/fea/` vtu+html+png |

## §1 Cycloidal stage — what was run and why it failed

Model (single disc = half the symmetric two-disc 40:1 module): real 40-lobe disc
(thickness 4 mm, E=4000 MPa PETG-CF [U], ν=0.35), 41 ring pins Ø3 @ R23.5, 6 output
pins Ø3 PCD33, eccentric E=0.42 mm, tooth clearance ~0.15 mm. Kinematic crank drive on
the disc-centre reference node; ring pins fixed; output-pin reactions = torque read-out.
C3D10 tets, hard contact + μ=0.2, `*CONTACT PAIR`/`SURFACE TO SURFACE`.

**Attempt history (all honest):**

1. `cyc_th0` 412k-node deck — silent death ≈30 min. Root cause found later (see #5).
2. `cyc_th0` retry — silent death ≈30 min.
3. `cyc_th0` clean-mesh retry — silent death ≈10 min.
4. `cyc_tie` `*TIE,POSITION TOLERANCE=0.35` — **invalid**: tie snap relocated slave nodes
   ~0.16 mm across the clearance and inverted thin pin-wall tets (nonpositive Jacobians).
5. `cyc_tie` `PRESSURE-OVERCLOSURE=TIED` — **invalid**: zero contact springs formed across
   the 0.16 mm gap in this ccx build (same trap as J4); free-flight, stress ≡ 0.
   All "converged" TIED runs were physically meaningless — the disc orbits freely.
6. `cyc1_short` 198k nodes, tied, drive 0.7 rad — converged 3 increments to ~0.08 mm
   (40 min) — still inside the clearance → stress ≡ 0.
7. `cyc1_eng` 198k nodes, hard contact, deep drive (step-1 = 70 % of 1.2-rad orbit,
   inc 0.15–0.35) — **converged 2 increments to ~0.11 mm drive** before the user-directed
   stop at ~30 min. Engagement needs ~0.16 mm; next increment would have loaded contacts.

**Why the solves were slow — three real bugs found and fixed:**
- `SOLVER=ITERATIVE SCALING/CHOLESKY` belongs on the `*STATIC` line, not `*STEP` —
  on `*STEP` this build warns "parameter not recognized" and silently uses SPOOLES,
  which OOM-died at ≥1.2 M DOF (all the "silent deaths" above).
- Gmsh C3D10 midside inversions (pin walls, housings) — detected by `check_jac.py`
  (Gauss-point detJ in ccx ordering) and repaired by remesh/`fix_jac.py`.
- `PRESSURE-OVERCLOSURE=TIED` and `*TIE` both fail across a designed 0.15 mm gap here —
  tied fallback is NOT viable for this model; only hard contact transfers load.

**Verification of the model itself (all done):** surface classification measured against
the real STEP geometry — ring-pin↔lobe gap 0.163 mm, output-pin↔hole gap 0.198 mm
(`code/gap.py`); all 7 component meshes Jacobian-clean; Newton iteration converges on
every launch (residual → 0 within 2–3 iterations per increment).

## §1b Hertz hand cross-check — the stage's fallback (real numbers)

`code/hertz_cyc.py`: line contact, pin R 1.5 mm vs effective flank radius ρ {8,12,18} mm [U],
load shared over n {1,2,3} lobes [U], disc thickness 4 mm, steel-on-PETG-CF.

- **J2** (T=7.0 N·m design torque): p0 = 289/205/167 MPa (n=1/2/3, ρ=8); equivalent
  stress seq ≈ 174/123/100 MPa → **SF 0.14–0.26 vs 50 MPa along-layer — FAIL**,
  best case n=3,ρ=18 still SF 0.26.
- **J3** (T=4.5 N·m): p0 = 232/164/134 MPa → **SF 0.18–0.33 — FAIL**.
- Output-pin bearing (projected): J2 11.8–17.7 MPa → SF 1.4–2.1 (marginal);
  J3 7.6–11.4 MPa → SF 2.2–3.3 (OK).
- Steel pin bending ~225 MPa (J2) / 144 MPa (J3) — fine.

**Caveat [U]:** lobe flank is near-conforming (ρ→large ⇒ p0 falls); the true FEA
contact area could sit between these bounds. Even at the most optimistic sharing
(n=3, ρ=18) Hertz still exceeds the 25/50 MPa print limits by >2.5×.

## §2 Joint models — status

- **J2/J3 decks exist and are structurally sound** (`code/msh2joint.py`): real bolted
  stack (housing/back_spacer/upper_clip + carrier/out_flange/front_spacer/link_clip),
  B32 bolt beams (this ccx rejects B31 with circular sections), 400 N/bolt thermal
  preload, flat preload faces `*TIE`-clamped, 9 pilot/dowel shear interfaces kept as
  hard contact, F/M service wrench via distributing couplings, `*STATIC,SOLVER=ITERATIVE
  CHOLESKY`. Never launched — no CPU time left inside the session budget.
- **J4 cradle**: 157k-node deck, cradle↔fore clip interface + 4×M3 pilots + bolts.
  Hard-contact attempt converged preload increments but hit the cap twice;
  `*TIE` attempt first failed (unsupported `TYPE=` keyword in this build → 0 MPCs →
  2e8 rigid-body mechanism), then after the syntax fix was SPOOLES-converging
  (residual 1920→489→207 through the thermal-preload spike) when killed at the cap.

## §3 Shock + fatigue (hand-calc, done)

`code/shock.py` from `upgrade1/gravity_up1.py` masses, worst-case AB pose (horizontal),
release through joint range, 0.1 s stop:

- J2: static 3.30 N·m → ×2 = 6.60 N·m; shock peak **9.19 N·m** (×2.8) ← governs
- J3: static 1.75 N·m → ×2 = 3.49 N·m; shock peak **4.21 N·m** (×2.4) ← governs
- J4: static 0.77 N·m → ×2 = 1.54 N·m; shock peak **1.19 N·m** (×1.5)

Fatigue [U]: Basquin fit on PETG-CF; printed-FDM endurance limit ~10–15 MPa at 1e6+
cycles per Shanmugam et al. 2021 (FDM polymer fatigue review, iris.uniroma1.it/11573/1688097)
and PETG fatigue studies (Theor. Appl. Fract. Mech., sciencedirect S0142112322004637) —
FDM polymers show ~0.2–0.4×UTS endurance. At any contact-side stress above ~15 MPa the
design is fatigue-limited; the Hertz lobe stresses are far beyond it.

## §4 Visualizations

`verify/fea/cyc1_eng_step2.{vtu,html,png}` — last converged increment of the hard-contact
pilot (seating phase: real disc-orbit displacement ≤0.11 mm, stresses ≈0 because contact
had not yet engaged; presented as convergence/geometry evidence, not a strength result).
No other case produced an frd worth visualizing.

## Design consequence & required fixes (recommendation, not executed)

- **Cycloidal PETG-CF disc lobes: predicted FAIL at service torque** (SF 0.14–0.33).
  Before ordering: (a) re-run the hard-contact single-disc deck on a faster machine /
  longer cap to confirm with FEA (deck `out/inp/cyc1_eng.inp` is ready), and/or
  (b) redesign: reduce module clearance, increase disc thickness/lobe count sharing,
  or move lobe material to machined acetal/aluminium insert. Treat lobe contact as
  the design-critical item — the earlier ~11 MPa figure was projected bearing stress,
  not contact pressure.
- Output-pin bearing is marginal at J2 (SF 1.4–2.1): verify with the joint FEA or
  thicken the carrier wall at the pin lands.
- J4 cradle unverified; the converging SPOOLES deck can be resumed
  (`out/inp/jt_j4_spooles.inp`).

## Artifacts kept

`verify/code/*.py` (generators, analyzers, validators), `verify/out/inp/*.inp`
(decks), `verify/out/inp/cyc1_*.frd` (partial real output), `verify/fea/` (viz).
Scratch `out/msh|step|vtu` are regenerable.
