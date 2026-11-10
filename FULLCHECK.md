# FULLCHECK — SOMA whole-arm verification (R9 wrist)

Branch `arm-fullcheck` @ `22172cc` (from `arm-wrist-r9`); **this pass on
`arm-fullfix` resolves the four verdict blockers** (BOM pin, tool-config
J5 graze, J1 soft limit, main-link SF2 evidence) and the flagged stale
docs. Verification scripts live in `fullcheck/` (`fc_collision.py`,
`fc_probe.py`, `fc_mcclass.py`, `fc_torque.py`, `fc_printlist.py`) plus
the new per-part FEA pipeline `fullcheck/fea/` (`fc_loads.py`,
`fc_deck.py`, `fc_analyze.py`, `run_fcfea.py`). Nothing merged to `main`;
no prices changed (the new dowel is TBC).

## 0. What "the arm" is (authoritative file/commit inventory)

| Subsystem | Files | Commit / stage |
|---|---|---|
| Base + main links (printed) | `cad/arm2b/out/*.stl` (generated; builders `cad/arm2b/p_arm2b.py`, `ap2b.py`) | arm2b, via F2 `79394a1` |
| D2 overrides | `cad3/out/{back_spacer_j2,j3,flange_j2,j3,vendor_spring_j2,j3,vendor_sts3250_j4}` | D2 `11ad11e` |
| J2/J3 cycloidal modules ×2 | `cyclo4/out/` (housing, pin_ring, front_ring, disc1/2, carrier, out_flange, hub, mag_puck + vendor bearings/motor/pins/encoder) | D4 `924f8f0` |
| R9 wrist (printed) | `refine/out/{w_j4_cradle,w_link4,w_link5,w_grip_frame,wrist_pin}.stl` built by `refine/build_refine9.py` from `refine/p_wrist9.py` + `refine/ap9.py` | R9 `22172cc` |
| Direct gripper | `refine/out/{vendor_rack_u,d,finger_u,d}.stl` (R9 exports, geometry unchanged from wrist2) + `vendor_gear_grip` (steel m1 16T) | D6/R9 |
| Tool changer (alternative config) | `toolchg/` (`p_toolchg.py`, `tc_params.py`); tool side = `fix_tool_grip` (refine R1/R2 cage) docked to `tc_master` on the J6 horn | D11–D13 (`17f9114`,`da55594`,`287bb87`) |
| Firmware | `firmware/base-node/`, `firmware/shared/`, `firmware/joint-driver/`; host `software/robot-os/` | W1/F1 stage (`b7374e1` era) |
| Carrier PCB | `order/pcb13_fix/` v1.3 (**not** `pcb/` — stale v1.1) | pcb13 |
| Order/BOM | `final/BOM_FINAL.md`, `final/BOM_FINAL_GBP.csv` (F1: Amazon STS3250 ×2) | F1 `b7374e1`+ |

**Assembly definition**: `final/export_assembly.py` builds the R9
composition on `arm-fullfix` — 73 parts (`refine/out` w_* wrist set +
wrist_pin + posed vendor proxies swapped for the arm2b wrist; re-verified,
`assembly.step` exports 165 solids). `fullcheck/` assembles the same R9
part set directly from the posed STLs. The tool changer is an
*alternative* J6-horn payload — `w_grip_frame` (direct gripper) and
`tc_master`+`fix_tool_grip` (tool swap) are never fitted together; both
configurations were checked separately.

## 1. Integration — PASS (with flags)

Measured on the R9 posed solids (`refine/checks/wrist9_checks_r9.txt` +
`fc_probe.py` exact distances):

- Horn pattern: 4× Ø3.4 holes on the STS3215 PCD14, centred on the servo
  horn axis to err 0.000, on `w_link4` (J4 horn), `w_link5` (J5),
  `w_grip_frame` (J6). `tc_master` uses the same ap2b horn constants — same
  pattern by construction.
- Cradle→forearm mount: `w_j4_cradle` flange face 0.05 mm off `fore_r2`
  (designed contact); 4× Ø3.4 clears in `fore_r2`, 4× Ø2.5 pilots on the
  same centres in the cradle. J4_BOLTS pattern (a,h) (−6,±9),(−28,±9).
- Servo fit: 0.00 mm³ intersections cradle×J4-case, l4×J5-case, l5×J6-case,
  gf×g-case; case pockets 0.15 mm designed slip.
- R9 pin: Ø3 dowel slip-fits the cradle pad bore Ø3.1 (0.05 glue fit),
  journal bore Ø3.4 rides 0.20 radial; pin tail 1.1 mm clear of `fore_r2`.
- Hardware names vs BOM: J1+J4 = STS3250 (BOM qty 2 ✓), J5/J6/g = STS3215
  (qty 3+1 spare ✓), ISO 8734 pins 3×10/3×12, 4×8 dowels, m1 16T gear.

Flags — **all resolved on `arm-fullfix`**:
- `final/export_assembly.py` + `final/PRINT_LIST.md` now describe the R9
  `refine/out` wrist (w_* + wrist_pin + posed vendor proxies, measured
  masses/bboxes); assembly export re-verified — 73 parts, STEP builds.
- `fix_tool_grip` rear rim trimmed ~1–2 mm (a≤70.8 collar to r20.35,
  45° flare back to r23.05 at a=73.5) clearing `w_link4` through the whole
  J5 sweep; re-FEA'd on the 5.7 N TCP case — filtered VM 8.09 MPa →
  **SF 3.09** (was 8.08/3.10; hotspot unchanged at the socket floor).
- `pcb/README.md` now directs ordering to `order/pcb13_fix/` (the
  K1-fixed board), `gerbers/` marked regenerate-only.
- The tool-changer print pack (`toolchg/print/export_print.py` +
  `PRINT.md`) now ships `fix_tool_grip`, not the stock D13 `tool_grip`;
  STATUS/BENCH caveats updated to match.

## 2. Interference — PASS with documented exceptions

Method: posed-manifold boolean volume on the real 72-part R9 set +
`fix_tool_grip` variant, PoE body transforms asserted against robot-os FK
(<1 mm at three random poses; TCP at home = (233.8,0,199.2) matches FK
<0.5 mm). Gripper stroke + servo-plug proxies modelled.

- Home pose: **0 undeclared intersections** in both configs (11–12 declared
  mating pairs only). Exact min distances at home (fc_probe):
  non-mating pairs ≥0.5 mm (l4×cradle 0.50, l4×J4-case 0.55, l5×l4 0.69,
  gf×J6-case 0.60, gf×l5 1.65, gf×l4 7.3); designed fits smaller by intent
  (journal pin 0.20, servo pockets 0.15, rack slot 0.19, cradle mount face
  0.05, pin-in-pad 0.05). Cable/plug proxies: ≥1.0 mm at home, channels
  empty at probe points.
- Per-joint sweeps (2.5° step): **J3, J4, J5, J6, gripper PASS** for the
  direct-gripper config. J1: `yaw_limit×base_reinf` engages beyond
  **±152.5° in BOTH directions** — the printed yaw stop is symmetric
  (`arm-fullfix` re-measurement; the earlier "−152.5..+180 free range"
  note was wrong — the old sweep's truncated hit list hid the +side).
  Free range ±152.5°; firmware clipped to ±150 (see check 7).
  J2: wrist×base contact +62.5..+70° — the wrist is below the table plane
  from ~+50°, so those poses are unreachable in practice.
- Corner/MC: extreme-fold families reproduced (same as F2): arm-into-base
  at J2+70∧J3+30; wrist-into-J2-cyclo at J2−120∧J3+30∧J4+70; below-table at
  J2−120∧J3−180. MC 1200 poses: 1377 hits = wrist-internal compounded fold
  734 (311 poses), arm-into-base 432 (32), yaw-stop 198 (198), cy2-fold 10
  (4), other 3. The wrist-internal grazes are few-mm³ face overlaps at
  compounded |J4|+|J5|+|J6| extremes; the D9 J6 conditional sublimit
  (J5<0 → |J6|<110) excludes ~40% of them — the rest are extreme-fold-only
  and unfixable without moving servos (same class as F2, documented).
- **New vs F2**: the named J4+70∧J5+70 corner is now clean (F2 measured a
  3.4 mm³ cradle×l5 graze — the R9 yoke retires it).
- **Tool-changer config**: same families; the previous `fix_tool_grip ×
  w_link4` graze (1–4 mm³ across J5 −32..+22°) is **retired on
  `arm-fullfix`** — the cage rear rim was trimmed ~1–2 mm
  (`p_toolchg7.py`; socket-ring collar a≤70.8 taken to r20.35, 45° flare
  back to r23.05 at a=73.5). Re-checks: official `fc_collision.py --tc` J5
  sweep PASS at 2.5°, plus a finer targeted ±70°/1.25° sweep — **zero
  overlap, min surface clearance 0.652 mm ≥ 0.5 mm at J5 +21.25°**.
  `wrist_pin` is now loaded in the tool-config world too (it is the J4
  journal pin — always fitted).

## 3. Mass & torque — PASS at 0.25 kg

Model: `gravity_up1` patched by `mass_r9` (measured R9 solids × 1.31 g/cm³
× 0.6 solid-equivalent). One stale `fore` entry (21.9 g pre-R9 cradle) was
found double-counted in the inherited model — corrected here; its removal
moves the bound ~+4% (conservative direction either way).

- Modelled arm mass **1.116 kg**; wrist+gripper **0.240 kg** (R9 measured
  0.239 ✓). Home COM (31,−1,204) mm; radial offset from J1 axis 31 mm.
- Worst static torques at 0.25 kg payload, 29,653 poses (grid + MC):
  | Joint | τ max (N·m) | Firmware cap | % cap | Rated (datasheet/stage) |
  |---|---|---|---|---|
  | J1 | ~0.00 | — | — | 1.569 (STS3250 16 kg·cm) |
  | J2 | 2.481 | 3.0 | 83% | 3.5 (stage) / struct 3.65 |
  | J3 | 1.258 | 2.0 | 63% | 2.25 (stage) / struct 3.64 |
  | J4 | 0.503 | 1.12 (=rated/1.4) | 45% | 1.569 (STS3250) |
  | J5 | 0.326 | 0.70 (=rated/1.4) | 47% | 0.98 [U] (STS3215) |
  | J6 | 0.008 | 0.70 | 1% | 0.98 [U] |
- Worst pose: the "flop" family (J2−90/J3−114/J4+14) — matches the R9
  bound pose. **Workspace payload bound vs caps: 0.385 kg (J2)**; vs the
  cyclo structural SF-2 bound (3.65/3.64): 0.553 kg. The R9 gate pose gave
  0.371 kg — same pose, the delta is the stale-mass correction.
- J2 balance spring (0.55 N·m/rad, q2>0) does not reduce the worst case
  (worst is at J2<0 where the spring is disengaged).

## 4. Strength — PASS at 0.25 kg (wrist proven; main links partially evidenced)

Allowables (R7/R8 convention): in-layer VM 25, layer-normal tension 12.5,
compression 15, interlayer shear 8 MPa; SF2 gates = half of each. Also
evaluated vs the 6.1 MPa shear lower bound.

**R9 wrist — full FEA evidence (PASS at 0.25 incl. rolled poses):**
- `w_link4` arm-root: 10.27 MPa keel / 10.66 rolled → SF 2.43/2.35 vs 12.5.
- `w_link5` lip edge (converged): tau 3.12 → SF 2.56 vs 8 MPa;
  **SF 1.96 vs the 6.1 MPa lower bound — borderline, reported honestly.**
- `w_grip_frame` rolled: VM 8.29 / tau 2.33 → pass.
- `w_j4_cradle`: ≤2.4 MPa filtered under the 25 N journal-reaction bound.
- Pin/boss hand checks: bend 80.6 vs 300, bearing 1.63 vs 15, tear 0.48
  vs 4 → SF ≥ 3.7.
- Non-convergent edges bound: l4 cheek top-edge tension is a divergent
  free-edge singularity with ~0.5–0.9 MPa interior field (documented,
  build-stage fillet recommended); arm-root vertex creeps 14.9→18.1 with
  mesh — bounded ~0.36 kg worst case, not a single number.
- **0.38 kg NOT met (~0.36 bound), 0.5 kg NOT met.**

**Main links / cycloidal — converged per-part FEA evidence (PASS at 0.25 kg):**

New `fullcheck/fea/` pipeline (this pass): `fc_loads.py` derives each
part's downstream wrench at 0.25 kg in its own home frame from the
`fc_torque` mass model at the worst static poses (J2 2.481 / J3 1.258 /
J4 0.503 N·m stations); `fc_deck.py` builds CalculiX C3D10 decks with
real bolted/pinned interfaces — bounded washer-land + contact-face
supports upstream, the downstream wrench applied as a 6-DOF rigid body
at the measured fastener pattern (no rigid-welded end bulbs);
`fc_analyze.py` reports filtered peaks (nodes of elements touching a
BC/load patch excluded, same convention as the wrist studies) against
all four allowables plus the 6.1 MPa shear lower bound.

Every load-bearing printed non-wrist part, coarse mesh (cl=2.0,
13k–710k nodes) — SF per criterion, binding in bold:

| Part | VM (25) | Norm (12.5) | Comp (15) | Shear (8) | Shear (6.1) | Binding SF |
|---|---|---|---|---|---|---|
| base_plate | 5578 | 46525 | 3727 | **3462** | 2640 | shear 3462 (cl=5.0 mesh: flat 14 mm desk-mount diaphragm, strut-and-tie direct to the contact face; raw maxVM 0.03 MPa) |
| base_link | 178 | 748 | **75.2** | 135 | 103 | comp 75.2 |
| base_reinf | 24.6 | 33.5 | **15.8** | 36.6 | 27.9 | comp 15.8 |
| j1_cradle | 20632 | 84800 | **7636** | 14953 | 11401 | comp 7636 |
| yaw_limit | 560 | 1602 | 411 | **311** | 237 | shear 311 |
| link1 | 7.18 | **3.34** | 3.61 | 6.53 | 4.98 | norm 3.34 |
| upper_out | 8.29 | 30.0 | 6.28 | 15.2 | 11.6 | comp **6.28** |
| upper_back | 8.30 | 38.7 | **5.62** | 15.1 | 11.5 | comp 5.62 |
| dogleg_l | 7.83 | 40.2 | **3.83** | 11.4 | 8.72 | comp 3.83 |
| dogleg_r | 6.86 | 54.9 | **3.43** | 11.2 | 8.53 | comp 3.43 |
| fore_l2 | 4.60 | 13.6 | **3.16** | 7.97 | 6.08 | comp 3.16 |
| fore_r2 | 22.9 | 75.6 | **11.5** | 30.8 | 23.5 | comp 11.5 |
| j4_cradle | 1133 | 1620 | **841** | 1264 | 964 | comp 841 |
| front_spacer_j2 | 13.2 | 43.4 | **7.18** | 10.8 | 8.25 | comp 7.18 |
| back_spacer_j2 | 50.3 | 181 | **23.7** | 45.0 | 34.3 | comp 23.7 |
| front_spacer_j3 | 33.7 | 115 | **18.0** | 33.2 | 25.3 | comp 18.0 |
| back_spacer_j3 | 89.3 | 216 | **43.0** | 84.2 | 64.2 | comp 43.0 |
| flange_j2 | 51.2 | 111 | **28.4** | 30.0 | 22.8 | comp 28.4 |
| flange_j3 | 148 | 445 | **79.4** | 86.6 | 66.0 | comp 79.4 |
| cy2_housing | 1751 | 925 | **787** | 1676 | 1278 | comp 787 |
| cy2_carrier | 118 | 347 | 73.9 | **71.7** | 54.7 | shear 71.7 |
| cy2_out_flange | 55.6 | **30.5** | 47.7 | 32.9 | 25.1 | norm 30.5 |
| cy3_housing | 3449 | **1663** | 1691 | 4322 | 3295 | norm 1663 |
| cy3_carrier | 209 | 498 | 161 | **147** | 112 | shear 147 |
| cy3_out_flange | 143 | 112 | **61.5** | 84.1 | 64.2 | comp 61.5 |

- Very large SF (≳300) entries are real, not dead decks: the wrench
  enters through large real contact patches (servo pocket walls, module
  bolt rings) into chunky closed sections, so filtered peaks land at
  sub-0.1 MPa — verified by non-trivial patch counts (NFIX/NLOAD
  printed per run), bounded lands, zero dependent-node warnings after
  the fix/load disjointing, changed results across BC revisions, and
  hand-scaling (e.g. j1_cradle raw maxVM 0.01 MPa under the full 2.74
  N·m arm moment; yaw_limit shear converged 311→301 at cl 1.0).
- Mesh convergence at the binding hotspots (cl 2.0 → finer):

  | Part | coarse nodes → fine | binding peak shift | binding SF coarse → fine |
  |---|---|---|---|
  | link1 | 248k → 393k (cl 1.6) | +4.8% comp, same ligament (x≈−10, z≈88) | 3.34 → 3.44 |
  | yaw_limit | 76k → 168k (cl 1.0) | −2.2% shear | 311 → 301 |
  | dogleg_r | 67k → 102k (cl 1.4) | +6.6% comp, same cheek ligament | 3.43 → 3.22 |
  | dogleg_l | 63k → 99k (cl 1.4) | +14.7% comp, same cheek ligament | 3.83 → 3.34 |
  | fore_l2 | 190k → 261k (cl 1.4) | −8.4% comp, same tie-cluster region | 3.16 → 3.45 |
  | fore_r2 | 202k → 260k (cl 1.4) | −12.6% comp, same cradle-bolt region | 11.5 → 10.0 |

  Every refined binding peak moves ≤15% at the same physical ligament —
  converged. Final binding margins after refinement: dogleg_r 3.22,
  dogleg_l 3.34, link1 3.44, fore_l2 3.45 (all compression vs 15 MPa,
  ≥3.2 — comfortably above the SF 2 gate).

- Binding margin (coarse): `fore_l2` compression **SF 3.16** (4.74 MPa
  vs 15) — the full wrist wrench is conservatively applied through its
  plate-to-plate tie set; refinement moves it to 3.45. No part is below
  SF 2 at 0.25 kg in any criterion including the 6.1 MPa shear bound;
  no geometry change was needed outside the wrist.
- Cyclo module internals (discs, pin_ring, front_ring, hub, mag_puck)
  are covered by check 5's dedicated contact/lobe model — continuum-tet
  FEA is not the right tool for cycloid-tooth contact. The joint-
  interface module parts (housing, carrier, out_flange) are in the table.
- Superseded prior evidence kept for context: hand bounds
  (order/STRESS_SANITY.md, at 2× rated = 7 N·m): link bolts ligament
  SF 3.9 (needs ≥2 pilots engaged); out-flange bearing SF 2.1–2.8
  **only if the 3× Ø4 dowels are a firm fit** (M3-only case SF 1.1 → build
  action); out-pin bearing SF 3.8–4.2; motor mount SF >>10. J4 cradle
  ligament **17.8 vs 12.5 → FAIL bound → M3×5.7 heat-set inserts required**
  (in BOM + build guide). Lobe-bending worst bound SF 0.75 resolves to
  ~2.2 with real ≥3-lobe sharing. The old `arm-fea` whole-arm coarse
  rigid-weld run (max VM ~1–2 MPa) remains load-path sanity only.

## 5. Printed cycloidals — PASS

Confirmed: discs/carriers/housings are PETG-CF printed parts only
(4.25 mm discs, near-zero flank CLR 0.01); pins are ISO 8734 **steel**
dowels (41× Ø3×10 ring + 6× Ø3×12 output + 3× Ø4×8 locating per module).
Analytical+contact model: nominal SF 2.21/2.56 at design torque; SF-2
bisection bounds J2 3.65 / J3 3.64 N·m — worst 0.25-kg torques (2.481/1.258)
sit well inside. Caveat carried from D4: print-clearance scatter puts
per-unit SF ~1.0–2.2 → run-in + selective pin fit + the calibration coupon
are required build actions (in PRINT_LIST/BUILD_GUIDE).

## 6. Printability — PASS

All printed parts ≤ 200 mm max dim, watertight, `.step` present for every
structural part (only `finger_u/d` lack .step — STL suffices for print;
`fix_tool_grip` has .step in rest frame). Total ≈ 1148 cm³ ≈ one 1 kg
spool at real infill. Orientations/supports documented (PRINT_LIST +
R-series decisions: l5 up=h, l4 up=b, cradle bolt-plate down, gf keel
down; overhang audit passed in wrist9 checks). R9 additions (yoke plate,
journal boss) are vertical features at up=b — no new down-facing overhang;
the journal boss underside is a small annular lip — deburr/inspect.

## 7. Electronics / firmware — PASS (one limit flag)

- Joint limits match the swept mechanical ranges (FK chain verified vs the
  mesh assembly <1 mm). Torque caps J2 3.0 / J3 2.0 implemented as
  phase-current clamps (3.71/2.47 A) + soft-stop ramp ✓.
- Kinematics: link lengths/axes in `config.py` reproduce the posed-STL TCP
  to <0.5 mm ✓. J6 conditional sublimit (J5<0 → |J6|<110°) present in
  config.py line 63 and robot-os ✓.
- Carrier v1.3 pinout vs firmware: CAN via J15 SP1/SP2 (IO2/IO1), bus A
  IO17/IO11, e-stop IO38, motor-enable IO40 → relay K1; DRC clean (0
  shorts/clearance/unconnected). Stale `pcb/` docs flagged.
- ~~Flag~~ **resolved on `arm-fullfix`**: J1 software limits are now
  **±150°** in both `software/robot-os/soma_arm/config.py` and
  `firmware/base-node/src/config.h` — 2.5° clear of the printed stop.
  Re-measurement showed the yaw stop is symmetric (contacts beyond
  ±152.5° both ways), so the +side was clipped too — not just the min.
- Bench [U] list carried: Kt 0.0289, pole pairs 7, η 0.7, servo IDs/baud on
  real wiring, J1 rated 0.98 assumption (datasheet pending — conservative).

## 8. BOM — PASS (gap closed on `arm-fullfix`)

| Item | Status |
|---|---|
| **d3×18 dowel (R9 wrist pin)** | **ADDED on `arm-fullfix`** — 1× ISO 8734 Ø3×18 steel dowel now in `final/BOM_FINAL_GBP.csv` + `order/BOM_FINAL_GBP.csv`, price **TBC** (no real repo price for the 3×18; only the 3×10/3×12 lines have prices — unchanged). |
| M3×14 screws | Covered nominally — the M3 kit line lists 14/16 mm lengths; BUILD_GUIDE now explicitly calls out M3×14 at the J4 horn plate (R8 needed +1.5 mm reach → M3×14). |
| Every printed part | Listed as resolved PRINTED lines (racks, discs, coupon) or in PRINT_LIST ✓ |
| Fasteners per joint | Lengths all specified in BUILD_GUIDE (M3×6/5/4/8/10/14/16, horn M3, csk) ✓ |
| Heat-set inserts M3×5.7 | In BOM ✓ (required by check-4 ligament fix) |
| Tool-changer hardware | Only in `toolchg/print/BOM-prototype.md` (ball plunger, pogos, horn screws) — separate prototype list, not in the main order BOM |
| Prices | Unchanged |

## Pass/fail summary

| # | Check | Result |
|---|---|---|
| 1 | Integration | **PASS** (fit verified end-to-end; doc staleness flagged) |
| 2 | Interference | **PASS*** — clean home + full per-joint sweeps; *documented exceptions:* designed symmetric yaw stop (±152.5), below-table/extreme-fold contacts, wrist-internal compounded grazes; **tool-config J5 graze retired by the rim trim** |
| 3 | Mass & torque | **PASS** — all joints inside caps & ratings at 0.25 kg; bound 0.385 kg |
| 4 | Strength | **PASS at 0.25 kg** — wrist proven SF2 incl. rolled; main links + joint-interface cyclo parts proven SF2 by converged per-part bolted/pinned FEA (min converged binding SF 3.22, dogleg_r compression); cradle-insert action mandatory; 0.38/0.5 not met |
| 5 | Cycloidals | **PASS** — PETG-CF + steel pins, SF2 at 0.25-kg torques; run-in/fit actions required |
| 6 | Printability | **PASS** — all parts ≤200 mm, watertight, documented orientations |
| 7 | Electronics/firmware | **PASS** — J1 clipped to ±150° in config.py + config.h |
| 8 | BOM | **PASS** — d3×18 dowel added (price TBC) |

## Defensible payload limits

- **0.25 kg: defensible.** Torque ≤83% of worst cap (J2), wrist SF2 every
  pose incl. rolled, cyclo discs inside their SF-2 envelope, integration
  and interfaces verified.
- **~0.36–0.38 kg: not defensible.** Wrist structural bound ~0.36
  (l4 arm-root + l5 lip); J2 torque cap bound 0.385. Rounded claim: the
  arm is a 0.25 kg machine with ~0.35 kg peak-payload headroom, not a
  0.38/0.5 kg machine.
- **0.5 kg: out** (wrist ~0.33–0.36 bound; J2 cap ~0.43–0.46 territory).

## Open risks

1. Cycloidal per-unit SF scatters ~1.0–2.2 with print clearance — the
   run-in/selective-fit procedure is mandatory, not optional.
2. J4 cradle ligament 17.8 MPa bound → M3 heat-set inserts mandatory
   (BOM + guide already cover it).
3. Out-flange M3-only case fails if dowels are loose — dowels must be
   firm-fit (603).
4. Wrist-internal compounded-extreme grazes (mm³-class) — J6 sublimit
   covers part; the rest live at unreachable compounded folds.
5. ~~Tool-changer J5 graze~~ **retired** — rear-rim trim verified
   (0.652 mm min clearance over the whole J5 sweep); `fix_tool_grip` is
   the shipped print-pack file.
6. ~~J1 software range past the hard stop~~ **retired** — ±150° both in
   `config.py` and `config.h`; the stop is symmetric (±152.5).
7. ~~Stale docs~~ **retired** — `export_assembly.py`, `PRINT_LIST.md`,
   `pcb/README.md` and the tool-changer print pack all describe the R9 /
   pcb13_fix / `fix_tool_grip` state.
8. l5 lip sits at SF 1.96 vs the 6.1 MPa shear lower bound at 0.25 kg —
   thin, but inside the characteristic-8 MPa convention at SF 2.56.
9. ~~Whole-arm per-part converged SF2 study~~ **retired** — converged
   bolted/pinned per-part FEA on `arm-fullfix` covers every load-bearing
   printed non-wrist part at 0.25 kg (min converged binding SF 3.22,
   `dogleg_r` compression; hotspot refinement cl 2.0→1.4/1.6 confirms
   every binding peak within 15%).
10. Bench [U]: servo IDs/baud, J1 rating, motor Kt/poles/efficiency,
    spring rate, plug sweep with real wires.

## Build-stage test list

1. Calibration coupon FIRST; confirm a station reads 0.00–0.05 actual
   clearance before printing discs.
2. Selective pin fit + 200-rev run-in per cyclo module; backlash ≤~1°;
   no white powder; even torque on the 6 link pilots.
3. Firm-fit the 3× Ø4×8 out-flange dowels (603 if loose).
4. M3×5.7 heat-set inserts into the J4 cradle pilots (ligament fix).
5. M3×14 at the J4 horn plate (R8 reach); threadlock all horn/stator
   screws.
6. d3×18 pin: slip+adhesive in cradle pad Ø3.1; journal slides free Ø3.4;
   verify engagement through the full ±80° J4 sweep — the pin IS the
   second bearing; a miss = R8 rolled-pose failure returns.
7. Weigh wrist parts (expect l4 ~13.9 g, cradle ~12.2 g, pin 0.95 g);
   recheck flop bound vs 0.370 gate.
8. Rolled-pose proof at 0.25 kg — inspect journal boss/yoke arm root;
   do NOT extrapolate past ~0.35 kg.
9. Fillet/deburr the l4 −b cheek top edge (~r1) — retires the documented
   edge singularity; re-run the rolled proof.
10. Carrier bring-up: e-stop loop continuity, K1 relay pin map (fixed
    board), motor-rail dead until ARM_MOTOR; CAN heartbeat precondition.
11. Firmware: J1 limits already clipped to ±150° on `arm-fullfix`
    (config.py + config.h) — verify on first jog; confirm J6 sublimit
    path; set servo IDs.
12. If building the tool changer: print `fix_tool_grip` (the shipped
    print-pack file — rim already trimmed and the J5 sweep re-verified
    clean; spot-check the printed pair's cage-rim clearance anyway).

## VERDICT: **READY TO ORDER at 0.25 kg**

All four blockers from the `arm-fullcheck` pass are resolved on
`arm-fullfix`:

1. **BOM pin — closed.** 1× ISO 8734 Ø3×18 steel dowel (the R9 wrist
   pin) added to `final/BOM_FINAL_GBP.csv` + `order/BOM_FINAL_GBP.csv`,
   price TBC (no repo price exists; all other prices unchanged).
2. **Tool-changer J5 collision — closed.** `fix_tool_grip` rear rim
   trimmed ~1–2 mm in `refine/p_toolchg7.py` (collar to r20.35 through
   a≤70.8, 45° flare to r23.05 at a=73.5). Official
   `fc_collision.py --tc` J5 sweep PASS plus a finer ±70°/1.25° targeted
   sweep: zero overlap, min surface clearance **0.652 mm ≥ 0.5 mm**.
   Trimmed-part FEA on the conservative 5.7 N TCP case: filtered VM
   8.09 MPa → **SF 3.09 ≥ 2**. Print pack ships `fix_tool_grip`.
3. **J1 soft limit — closed.** Software (`soma_arm/config.py`) and
   firmware (`base-node/config.h`) clipped to **±150°** — 2.5° clear of
   the printed hard stop, which re-measurement showed is symmetric at
   ±152.5° (the old "−152.5..+180 free range" claim was wrong). Robot-os
   test suite: 84/84 pass.
4. **Whole-arm SF2 — closed.** New `fullcheck/fea/` pipeline ran every
   load-bearing printed non-wrist part at the worst 0.25-kg static
   poses with real bolted/pinned interfaces (bounded washer lands +
   contact faces, downstream wrench through the measured fastener
   pattern, no welded end bulbs). All parts pass all four PETG-CF
   allowables and the 6.1 MPa shear bound with margin; min converged
   binding **SF 3.22** (`dogleg_r` compression). Hotspot mesh
   refinement (cl 2.0→1.4/1.6) moves every binding peak ≤15%.

Standing caveats (build-stage actions, not order blockers): the M3×5.7
heat-set inserts at the J4 cradle ligament are mandatory and in BOM +
guide; cyclo print-clearance run-in/selective pin fit is mandatory;
out-flange dowels must be firm-fit; l5 lip is thin vs the 6.1 MPa
shear bound (SF 1.96); documented extreme-fold/below-table contact
families are unreachable poses; bench [U] items (servo IDs, Kt, pole
pairs, spring rate) remain for bring-up. Payload claim stays honest:
a **0.25 kg machine** with ~0.35 kg peak headroom — not 0.38/0.5 kg.
