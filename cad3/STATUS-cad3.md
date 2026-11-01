# STATUS — Stage D2 (cad3): D1 upgrades applied to the arm CAD + housing/bolt FEA

Worktree `~/Vector-wt/cad3`, branch `arm-cad3`, based on `arm-up1` (994c983).
CAD copied from **`arm-arm2b`** (9a67e12) — `sim/STATUS-sim.md` and
`fea_arm3/STATUS-fea-arm3.md` both name the arm2b assembly as the one they ran,
so this CAD copy is the same lineage. No existing product files or branches
touched; all new work is in `cad3/` plus the checked-out `cad/` copy that the
stage instructs to modify. Date: 1 Nov 2026.

## What was applied (D1 set)

1. **J4 STS3215 → Feetech STS3250** (ST-3250-C001). `ap2b.py`:
   `M_STS3250 = 0.0745`, `STS3250_RATED = 1.569` N·m (16 kg·cm, Feetech
   datasheet rev A/0 [S]); part renamed `vendor_sts3250_j4`. Same
   45.22×24.72×35 mm envelope and 25T spline → fit verified by interference
   (0.0 total) and the unchanged servo pockets in `j4_cradle` (checks PASS).
   (J1 already carried an STS3250 proxy upstream on arm2b — unchanged here.)
2. **Coaxial one-way torsion balance spring at J2** — target k ≈ 0.55 N·m/rad,
   engages only for q2 > 0, assist ≈ 0.67 N·m at +70°. Fits **inside the
   existing knuckle envelope** (proxy max radius 19.2 < 28.5 mm) by reclaiming
   the **6803 bearing cavity**: `back_spacer` is bored through Ø23.2 (was
   6803 seat) with a fixed-leg anchor notch at 90°; `flange` hub is turned to
   the Ø14.8 suggested mandrel with a Ø23.2 coil recess in the disc face and a
   free-leg stop notch at 0°. Stock spring: **Springmasters 471671**
   (stainless, wire Ø2.0, OD 22, mandrel 14.8, legs fig-B 70 mm —
   [S springmasters.com/shop/471671, 1 Nov 2026]); the 6803s are removed
   (BOM −2). One-way engagement: `sgn = −1` at J2.
3. **J3 evaluation**: the same spring **fits without envelope growth** (the
   J3 stack is symmetric — dogleg cheeks where link1 sits at J2; the 6803
   cavity is identical) → **implemented** (`sgn = +1`, mirrored sense).
   The elbow mass-cut alternative is therefore not needed; J3 check torque
   1.15–1.17 N·m vs 2.25 limit passes with margin 1.9× either way.

## Exported parts (STEP + STL) — `cad3/out/`

`back_spacer_j2`, `back_spacer_j3`, `flange_j2`, `flange_j3`,
`vendor_spring_j2`, `vendor_spring_j3`, `vendor_sts3250_j4` (7 changed/added
parts; all other part files remain in `cad/arm2b/out/`).

## Check results (all re-run 1 Nov 2026, real output)

- **Build**: 38 parts build clean.
- **A2a `arm2_checks.py` — PASS.** Reach J2→TCP 375.0 (want 375±10); all
  HOLE/pattern checks PASS; J2 −120..+70° (190°, need ≥150), J3 −180..+30°
  (210°); torques J2 2.34 N·m (≤3.50), J3 1.15 N·m (≤2.25).
- **A2b `arm2b_checks.py` — PASS.** Reach/horn/horn-hole/pocket checks PASS;
  J4 torque 0.48 N·m vs STS3250 derated 1.569/1.4 = 1.12; J5/J6 ROM PASS;
  grip open 25 mm clear; J2 wrist-inclusive −120..+60° (180°, need ≥150).
- **`cad/act2/act_checks.py` — PASS.** Housing 55.00 length / 57.00 OD, all
  module parts watertight, rmax in spec.
- **Interference sweep — total 0.0 mm³** (spring leg/coil vs back_spacer,
  flange, link1, dogleg cheeks all clear after the full-depth notches).
- **`cad3/checks/spring_check.py` — SPRING CHECKS PASS.**
  J2 −120..+70° hooked-leg sweep vs fixed members + free leg: clear;
  engagement winds correctly for q>0 (inter-leg 90→31→21° over 0/60/70°),
  2.5 mm leg-leg clearance at +70°; J3 −180..+30° sweep clear; pocket
  clearances: coil OD22 in Ø23.2 pocket (0.6 radial), mandrel Ø14.8 vs coil
  ID18 (1.6), coil y24.4..33.9 vs recess floor 33.96 PASS; envelope
  r_max 19.2 < 28.5 PASS both joints.

## Task 2 — FEA (housing + bolt holes), `cad3/fea/`

Pipeline reused from `fea_link/` (gmsh → C3D10 → ccx → frd2vtu → pyvista).
New: `housing.geo` (imports `act2/out/housing.step`, physical surface
`pinbores` tagged from the 41 ring-pin bores at R23.5), `cradle.geo` (imports
the posed `j4_cradle`), `msh2housing.py` / `msh2cradle.py` (deck writers with
`reorder_tet` midside fallback), `analyze2.py`, `view_stress.py`.

- **Material** PETG-CF: E = 4000 MPa, ν = 0.35, ρ = 7.62e-10 t/mm³
  (parts_AB.json / fea_link convention [S repo]). Failure limits per repo
  convention: **25 MPa cross-layer / 50 MPa along-layer** (layer-direction
  strength ≈ 50% of datasheet, per stage rule).
- **Loads** from `upgrade1/gravity_up1.py` @ 0.5 kg full reach
  (Q_WORST = [0,+70,−70,0,0,0]°), **×2 dynamic factor**, applied as
  (M, F) at a rigid ref node spider-linked to the back-pilot bolt patches:
  J2: 2.565 N·m → **M 5130 N·mm**, F 31.0 N (downstream 1.581 kg×2);
  J3: ROM-max 1.837 N·m → **M 3674 N·mm** (conservative — exceeds the
  reach-pose 3556), F 23.9 N (incl. module self-weight);
  J4: 0.801 N·m → **M 1602 N·mm**, F 16.1 N.
- **Boundary conditions** (spread bolt-preload-free approximations, stated
  per stage): housing reaction = all nodes on the tagged `pinbores` surface
  within Ø1.62 of a pin axis — the real pin contact band (pins saturate ~85%
  of the land pitch, so this ≈ the pin-land clamp); cradle reaction = the 4
  real M3 bolt-hole wall patches at the corrected posed coordinates
  (68.4/90.4, 207.2/225.2). Loads spread over the 6 back-pilot stacks /
  servo pocket faces via NLOAD spiders — bolt patches stay in the stress
  ranking (reported as "patch max").

| Case | Mesh (nodes / C3D10) | max\|U\| mm | raw maxVM | filtered maxVM | patch maxVM | SF vs 25 MPa |
|---|---|---|---|---|---|---|
| J2 housing | 275,769 / 164,418 | 0.007 | **4.16 MPa** | 4.16 | 1.64 | **6.0** |
| J3 housing | 275,769 / 164,418 | 0.005 | **3.01 MPa** | 3.01 | 1.20 | **8.3** |
| J4 cradle | 122,524 / 77,580 | ~0.000 | 1.07 | **0.22** | 0.87 | **28.7** (patch) / 113 (filt) |

- Hot spots (filtered): J2 housing 4.16 MPa at (2.0, 22.6, 10.2) — motor-bore
  rim on the module shell, scales ∝ applied torque; patch (pin-bore land)
  peaks 1.64 at (21.9, −9.1, 33.5). Cradle: 0.22 filtered at (94.4, 24.3,
  221.6) cradle wall; 0.87 at the bolt patch (92.6, 23.5, 227.5).
- **All SF ≥ 2** → no local fix needed; no re-run.
- Evidence in `cad3/fea/`: `cad3_J2_{iso,front}.png`, `cad3_J3_{iso,front}.png`,
  `cad3_cradle_{iso,front}.png` + interactive `cad3_{J2,J3,cradle}.html`
  (trame-pyvista export); inputs `housing_4_2.msh`, `cradle.msh`, `run/*.inp`,
  `run/*.frd`, `run/*.vtu`.

## Other docs

- `cad3/PRINT_LIST.md` — every printed part (arm 26 + 2×9 module parts), vol
  1258 cm³ solid eq / ~0.8–0.9 kg [U] print mass; all fit the A1 256³ bed;
  PETG-CF recommended (PAHT-CF rejected — open frame); real UK prices.
- `cad3/BOM_delta.md` — +1 STS3250, +2 Springmasters 471671 (~£9.4),
  −1 STS3215, −2 6803ZZ; net carried mass ≈ +43 g [U].
- `cad3/checks/spring_check.py`, `cad3/checks/print_audit.py` — new D2 checks.

## [U] / unverified table

| Item | Status |
|---|---|
| Spring achieved rate k ≈ 0.55 N·m/rad | **[U]** — verify on bench, shim; D1 analysis tolerates ~−15% |
| 471671 leg forming (70 mm stock legs → notches) | [U] bench operation; proxy legs are schematic |
| Spring mass 20 g ea in torque model | [U] (steel coil est.) |
| Spring helix handedness LH/RH ordering | [U] both variants stocked |
| STS3250 74.5 g, 1.569 N·m, envelope | [S] Feetech datasheet rev A/0 |
| PETG-CF E=4000 / strength 25/50 MPa | repo convention [S]; filament TDS density 1.31 [S] |
| Actuator module mass 0.3 kg in J3 F | [U] as in arm2_checks |
| J3 moment used 3674 vs stage-reach 3556 | conservative +3.3%, documented |
| Print mass ~0.8–0.9 kg total | [U] slicer-dependent |
| Horn-thread grip M3×8 [U], link1 grip 1.3 mm | pre-existing [U] flags, unchanged |

## Open questions

- 6803 removal: joint radial location at the back side is now the Ø14.8
  printed mandrel + coil pocket instead of a ball bearing — adequate for the
  balance-spring function but relies on the actuator output bearing for the
  main radial load; confirm on the first assembly.
- J2 ROM in the wrist-inclusive A2b sweep reads +60° (J6 servo hits the base
  plate) vs +70° in the A2a sweep — both ≥150° total; the real hard stop is
  the +70° design limit from D1.
- If a bigger spring is ever needed, 471672 (OD 27) does **not** fit the
  Ø23.2 pocket — it was rejected for envelope growth.

## Commit/tag

Single stage commit on `arm-cad3`, tag `cad-3-done`, pushed with tags.
