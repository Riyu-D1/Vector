# FULLCHECK — SOMA whole-arm verification (R9 wrist)

Branch `arm-fullcheck` @ `22172cc` (from `arm-wrist-r9`). Verification
scripts live in `fullcheck/` (`fc_collision.py`, `fc_probe.py`,
`fc_mcclass.py`, `fc_torque.py`, `fc_printlist.py`). Nothing merged to
`main`; no product files edited; no prices changed.

## 0. What "the arm" is (authoritative file/commit inventory)

| Subsystem | Files | Commit / stage |
|---|---|---|
| Base + main links (printed) | `cad/arm2b/out/*.stl` (generated; builders `cad/arm2b/p_arm2b.py`, `ap2b.py`) | arm2b, via F2 `79394a1` |
| D2 overrides | `cad3/out/{back_spacer_j2,j3,flange_j2,j3,vendor_spring_j2,j3,vendor_sts3250_j4}` | D2 `11ad11e` |
| J2/J3 cycloidal modules ×2 | `cyclo4/out/` (housing, pin_ring, front_ring, disc1/2, carrier, out_flange, hub, mag_puck + vendor bearings/motor/pins/encoder) | D4 `924f8f0` |
| R9 wrist (printed) | `refine/out/{w_j4_cradle,w_link4,w_link5,w_grip_frame,wrist_pin}.stl` built by `refine/build_refine9.py` from `refine/p_wrist9.py` + `refine/ap9.py` | R9 `22172cc` |
| Direct gripper | `refine/out/{vendor_rack_u,d,finger_u,d}.stl` (symlinks → `wrist2/out`, geometry unchanged) + `vendor_gear_grip` (steel m1 16T) | D6/R9 |
| Tool changer (alternative config) | `toolchg/` (`p_toolchg.py`, `tc_params.py`); tool side = `fix_tool_grip` (refine R1/R2 cage) docked to `tc_master` on the J6 horn | D11–D13 (`17f9114`,`da55594`,`287bb87`) |
| Firmware | `firmware/base-node/`, `firmware/shared/`, `firmware/joint-driver/`; host `software/robot-os/` | W1/F1 stage (`b7374e1` era) |
| Carrier PCB | `order/pcb13_fix/` v1.3 (**not** `pcb/` — stale v1.1) | pcb13 |
| Order/BOM | `final/BOM_FINAL.md`, `final/BOM_FINAL_GBP.csv` (F1: Amazon STS3250 ×2) | F1 `b7374e1`+ |

**Assembly definition caveat**: `final/export_assembly.py` still builds the
F2/D6 composition (72 parts, `wrist2/out` wrist). The R9 build is defined by
`refine/` sources; `fullcheck/` assembles the real R9 part set directly from
the posed STLs. The tool changer is an *alternative* J6-horn payload —
`w_grip_frame` (direct gripper) and `tc_master`+`fix_tool_grip` (tool swap)
are never fitted together; both configurations were checked separately.

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

Flags (branch/documentation mismatches, none blocking fit):
- `final/export_assembly.py` + `final/PRINT_LIST.md` still describe the D6
  `wrist2/out` wrist (dims/masses differ from R9 — same interface, so fit
  claims hold, but the printed table is stale).
- `fix_tool_grip` (the tool cage) is at the R1/R2 fix level — it does not
  carry the R7 `w_grip_frame` ribs/tab changes. Its last FEA (R1/R2) gave
  SF 3.10 on the D11 load case; acceptable, but note it is not the R9 cage.
- `pcb/README.md` is v1.1-era (bus B, HTD-45H, wrist UART — all removed);
  use `order/pcb13_fix/` + firmware `pins.h` only.
- The tool-changer print pack (`toolchg/print/`, D13) predates the R fixes;
  print `fix_tool_grip` (refine) not the stock `tool_grip`.

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
  direct-gripper config. J1: `yaw_limit×base_reinf` engages below −152.5° —
  the *designed* yaw hard stop (free range −152.5..+180 vs ±180 firmware).
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
- **Tool-changer config**: same families, plus one NEW real graze —
  `fix_tool_grip × w_link4` 1–4 mm³ across **J5 −32..+22°** (the +12 mm
  shifted cage rim sweeps the l4 collar). Inside the plain J5 range, not an
  extreme fold → see risks.

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

**Main links / cycloidal — partial evidence:**
- Hand bounds (order/STRESS_SANITY.md, at 2× rated = 7 N·m): link bolts
  ligament SF 3.9 (needs ≥2 pilots engaged); out-flange bearing SF 2.1–2.8
  **only if the 3× Ø4 dowels are a firm fit** (M3-only case SF 1.1 → build
  action); out-pin bearing SF 3.8–4.2; motor mount SF >>10. J4 cradle
  ligament **17.8 vs 12.5 → FAIL bound → M3×5.7 heat-set inserts required**
  (in BOM + build guide). Lobe-bending worst bound SF 0.75 resolves to
  ~2.2 with real ≥3-lobe sharing.
- Whole-arm FEA (`arm-fea`, coarse 157k tets, rigid-welded joints): max VM
  ~1–2 MPa at 0.5–1.0 kg — load-path sanity only; joints welded, contact
  smeared, no convergence study. It does NOT prove per-part SF2.
- Honest position: the wrist is proven to SF2 at 0.25; the main-link chain
  is argued by hand bounds + a coarse FEA + prior stage passes, with the
  cradle-ligament fix being mandatory at assembly. A converged whole-arm
  per-part SF2 study remains open evidence debt.

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
- **Flag**: firmware J1 ±180° vs hard stop at −152.5° — recommend pulling
  J1 min to −150° (or accept stop contact as designed — it's a printed stop
  under a 50 kg·cm servo; clipping is safer).
- Bench [U] list carried: Kt 0.0289, pole pairs 7, η 0.7, servo IDs/baud on
  real wiring, J1 rated 0.98 assumption (datasheet pending — conservative).

## 8. BOM — FAIL (one real gap)

| Item | Status |
|---|---|
| **d3×18 dowel (R9 wrist pin)** | **MISSING from `final/BOM_FINAL_GBP.csv` + `order/BOM_FINAL_GBP.csv`** — the wrist's second J4 bearing has no purchased pin. Add 1× ISO 8734 Ø3×18 (a few pence). |
| M3×14 screws | Covered nominally — the M3 kit line lists 14/16 mm lengths; BUILD_GUIDE doesn't explicitly call out M3×14 at the J4 horn plate (R8 needed +1.5 mm reach → M3×14) — doc note. |
| Every printed part | Listed as resolved PRINTED lines (racks, discs, coupon) or in PRINT_LIST ✓ |
| Fasteners per joint | Lengths all specified in BUILD_GUIDE (M3×6/5/4/8/10/14/16, horn M3, csk) ✓ |
| Heat-set inserts M3×5.7 | In BOM ✓ (required by check-4 ligament fix) |
| Tool-changer hardware | Only in `toolchg/print/BOM-prototype.md` (ball plunger, pogos, horn screws) — separate prototype list, not in the main order BOM |
| Prices | Unchanged |

## Pass/fail summary

| # | Check | Result |
|---|---|---|
| 1 | Integration | **PASS** (fit verified end-to-end; doc staleness flagged) |
| 2 | Interference | **PASS*** — clean home + full per-joint sweeps; *documented exceptions:* designed yaw stop, below-table/extreme-fold contacts, wrist-internal compounded grazes, **tool-config J5 graze** |
| 3 | Mass & torque | **PASS** — all joints inside caps & ratings at 0.25 kg; bound 0.385 kg |
| 4 | Strength | **PASS at 0.25 kg** — wrist proven SF2 incl. rolled; main links partially evidenced (hand bounds + coarse FEA; cradle-insert action mandatory); 0.38/0.5 not met |
| 5 | Cycloidals | **PASS** — PETG-CF + steel pins, SF2 at 0.25-kg torques; run-in/fit actions required |
| 6 | Printability | **PASS** — all parts ≤200 mm, watertight, documented orientations |
| 7 | Electronics/firmware | **PASS** (J1 limit flag) |
| 8 | BOM | **FAIL** — d3×18 dowel missing |

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
5. Tool-changer config: `fix_tool_grip` grazes `w_link4` 1–4 mm³ across
   J5 −32..+22° — needs a ~1–2 mm trim on the tool cage rear rim or a J5
   usage note; also `fix_tool_grip` predates the R7 cage ribs.
6. J1 software range extends ~27° past the designed hard stop.
7. Stale docs: `final/export_assembly.py` + `PRINT_LIST` describe the D6
   wrist; `pcb/README` describes v1.1 wiring; the D13 tool pack predates
   R fixes — authoritative sets are `refine/` (R9) and `order/pcb13_fix/`.
8. l5 lip sits at SF 1.96 vs the 6.1 MPa shear lower bound at 0.25 kg —
   thin, but inside the characteristic-8 MPa convention at SF 2.56.
9. Whole-arm per-part converged SF2 study on non-wrist parts is evidence
   debt (hand bounds + coarse FEA only).
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
11. Firmware: pull J1 min to −150° before first jog (or confirm stop
    contact intent); confirm J6 sublimit path; set servo IDs.
12. If building the tool changer: print `fix_tool_grip` (not the stock
    D13 file) and re-check the J5 graze on the printed pair before relying
    on tool-swap.

## VERDICT: **NOT READY**

Exact blockers:

1. **BOM is incomplete** — the d3×18 dowel (the R9 wrist pin, the part
   that makes the second J4 bearing real) is not on the order list. One
   line fixes it (~£0.30, ISO 8734 Ø3×18); without it the wrist reverts to
   the R8 horn-only support that failed rolled poses.
2. **Tool-changer config has an in-range collision** — `fix_tool_grip` ×
   `w_link4` 1–4 mm³ across J5 −32..+22°. Needs a small cage-rim trim or a
   J5 usage note; plus print `fix_tool_grip`, not the D13 stock file.
3. **J1 firmware range extends past the designed hard stop** (−152.5° vs
   −180°) — clip to −150° or sign off stop contact as intended.
4. **Whole-arm SF2 is proven for the wrist, partially evidenced for the
   main links** — hand bounds + coarse rigid-weld FEA only; the cradle-
   ligament insert fix is mandatory at assembly. If an order needs the
   whole chain proven to SF2 at 0.25 kg, a focused FEA/hand-check pass on
   the main links is the remaining work.

Everything else verifies cleanly at 0.25 kg — integration fits end-to-end,
torques sit ≤83% of caps, the R9 wrist meets SF2 in every pose including
rolled, all parts print on the A1 bed, and firmware/PCB pinout is
consistent. This is close to orderable — the gaps above are the honest
list standing between this design and a clean order.
