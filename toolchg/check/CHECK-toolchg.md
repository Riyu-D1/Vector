# D11 audit — `toolchg/` (D10 tool-changer) — independent check

Branch `arm-toolchg-check`, worktree `~/Vector-wt/toolchgchk`, base
`origin/arm-toolchg` @ `7003ea8` (tag `toolchg-1-done`). Audit-only:
no product file was edited; everything below is reproduced evidence or
marked `[U]`. Helper scripts + logs live under `toolchg/check/`.

Interpreter note: the stage's `PY=/Users/deepakdiwan/soma/.venv/bin/python`
does not exist on this machine. CAD reruns used the same interpreter the
tested product scripts pin
(`/Users/deepakdiwan/Vector-wt/cradlefix/.venv/bin/python`, build123d
0.13.0); pytest via `/Users/deepakdiwan/opt/anaconda3/bin/python3`
(pytest 7.1.1, py3.9); MuJoCo via `/Users/deepakdiwan/Vector-wt/sim/.venv-mj/bin/python`
(mujoco 3.10.0); FE html via the fea venv (pyvista 0.49.2); ccx 2.23 +
gmsh 4.15.0 from FreeCAD.app.

## 1. Summary

| method | result |
|---|---|
| 1 geometry rebuild (11 parts) | 10/11 single-solid watertight; `tool_grip` = 1 body + 2 inherited slivers (44.6 mm³, not the claimed ~1 mm³) |
| 2 coupling fits (tc_checks C1–C6 + own probes) | C1–C6 PASS; **2 real defects found** (key notch, thin catch/groove wall) |
| 3 FEM (re-run + 4 added cases) | re-run reproduces D10 exactly; **2 added cases FAIL SF<2** (single-catch fault 16.85, tool_grip clevis 28.73 vs 25 `[U]`) |
| 4 collision + dock path | PASS all sweeps/grid/corners/MC-800/dock×4/undock×4 |
| 5 mass/torque/payload | PASS — all STATUS numbers reproduced |
| 6 MuJoCo dock | PASS 9/9 (seat 1.41/2.48 mm, lift 35.6/33.8 mm, finite qpos) |
| 7 firmware planner | PASS 13/13 + code review |
| 8 BOM/hardware fit | **2 mismatches** (Ø5 ball vs Ø4.2 bore; dowels without holes) |
| 9 STATUS claim audit | 19 PASS / 5 FAIL / 1 partial / 8 `[U]` (33 itemised) |

Verdict: **fix then print** — three CAD defects (F1–F3) and two BOM
mismatches (F4–F5) must be corrected before the prototype prints; none
changes the architecture. See `proposed_fixes.md` for exact patches.

## 2. Per-part geometry & printability

Rebuild via `toolchg/build_toolchg.py` (PYCAD): all 11 reported
"watertight". Independent measures by `toolchg/check/audit_geom.py`
(BRep solids, ray-section walls, trimesh overhangs):

| part | solids | vol cm³ | print-mass g | STATUS vol | bbox mm (fits 256³?) | min wall measured | suspended flat-down mm² |
|---|---|---|---|---|---|---|---|
| tc_master | 1 | 7.33 | 5.8 | 7.3 ✓ | 13.1×32.2×33.1 ✓ | spigot wall 9.4, lug band 13.75, lug span 3.40 axial, lug tip 2.27 | 403 (lug −a faces, detent ceiling) |
| tc_plate | 1 | 6.76 | 5.3 | 6.8 ✓ | 9.4×46×46 ✓ | ring 6.95, groove floor **1.75–1.82**, catch r13.5 **1.14** / r15 1.75 / r16 2.16, floor 2.40 | 2865 (incl. ~1040 socket-floor ceiling) |
| tool_grip | **3** | 22.84 (22.80+0.01+0.03) | 18.0 | 22.8 ✓ | 68.1×64×60.4 ✓ | neck 10.7–16.5, keel/cage 2.00 | 2825 |
| tool_pen | 1 | 28.30 | 22.2 | 28.3 ✓ | 79×46×46 ✓ | barrel 5.25–5.32, neck 12.25, bore floor 2.40 | 2892 |
| tc_vendor_g | 1 | 42.75 | (proxy) | 42.8 ✓ | 49.3×24.7×45.2 ✓ | n/a (vendor proxy solid) | 1840 |
| tc_gear | 1 | 1.53 | 1.2 | 1.5 ✓ | 6×18×18 ✓ | — | 0 |
| tc_rack_u/d | 1 ea | 2.35 ea | 1.8 ea | 2.4 ✓ | 6×36×12 ✓ | fork plate 4.00 | 0 |
| tc_finger_u/d | 1 ea | 1.27 ea | 1.0 ea | 1.3 ✓ | 14.4×4×25.2 ✓ | — | 160 ea |
| tc_rack | 1 | 157.03 | 123.4 | 157.0 ✓ | 44×202×118 ✓ | fork plate 4.00, spine 18.0, base ~91 | **0** |

- `tool_grip` 3 solids: 22799.91 + 10.80 + 33.79 mm³. The shipped
  product `w_grip_frame` STL contains the same 3 bodies (10.80 + 33.66
  mm³) → inheritance confirmed, not a D10-introduced sliver. But
  STATUS's "~1 mm³" is off by ~45×; they are real floating bits a
  slicer will drop or string.
- Print orientations (STATUS): coupling pair −a down, tool_grip
  keel/back down, tool_pen plate-face down, tc_rack base-down.
  Suspended flat-down faces (support-needed) exist on 7 parts — largest
  concern: **master lug −a bearing faces (~267 mm² of the 403) print on
  support**, a surface-quality risk exactly where capture loads bear.
  `tc_rack` is clean (0 mm² suspended). STATUS's "≤45° overhangs
  designed-in" is optimistic — true overhang ramps exist, but ~10%
  flat-down needs support. `[U bench]` stands.

## 3. Coupling fits — independent measures

`toolchg/tc_checks.py` re-run (verbatim output in `logs/tc_checks.txt`):

```
PASS C1 entry sweep clean                                 worst 0.00 mm3
PASS C2 twist sweep within allowance                      worst 0.00 mm3
PASS C3 lugs captured at lock                             lock pull 153.4 mm3, entry pull 0.00 mm3
PASS C4 detent ball clear at entry                        0.00
PASS C5 tool seats in rack                                8.40 mm3
PASS C6 mass budget                                       informational
ALL CHECKS DONE
```

Own probes vs `tc_params.py` claims (audit_geom.py §D):

| item | claimed | measured | verdict |
|---|---|---|---|
| lug outer r | 17.3 | 17.30 (verts) | PASS |
| socket bore r | 18.2 | 18.20 | PASS |
| catch inner r | 13.2 | 13.20 | PASS |
| spigot r | 13.0 | 13.00 (probe 3.60–13.00; verts band shows 10.1 because the smooth cylinder has no mid-span vertices) | PASS |
| lug −a face | 72.4 | 72.40 | PASS |
| catch +a face | 72.2 | 72.20 (0.2 running gap) | PASS |
| spigot tip | 75.8 | 75.80 vs floor 76.0 (0.2) | PASS |
| floor thickness | 2.4 | 2.40 | PASS |
| pogo bores ×5 | Ø1.8 at pin r/ph | all 5 present (empty axial probe) | PASS |
| horn pattern | PCD14, Ø3.4, cb Ø6.2×2.0, recess Ø7×2.2, CB_A 67 | identical to `w_grip_frame` (`TC_CB_A == GF_CB_A`) | PASS |
| detent bore | Ø4.2 radial at a74 ph110 through ring wall | present (radial probe void at a74 ph110) | PASS |
| dimple | Ø3.0×0.8 on lug1 OD, master ph 110−(−12+60)=62 | rcyl present; phase arithmetic matches | PASS |
| dock groove band | 5.0 vs rack plate 4.0 (±0.5) | TC_DOCK_A (72.25,77.25); RACK_PLATE_T 4.0 | PASS |
| slot opening | 40.5 vs groove floor Ø40 (+0.5) | RACK_SLOT_W 40.5 vs 2×DOCK_R 40 | PASS |
| rack seat/fork | fork plate 4.0, seat ~r20.3, key tab 2.5×1.4 at each slot | fork 4.00, tab measured z88–91.1 (protrudes ~1.1 above seat floor) | geometry ok; engagement **FAIL → F1** |
| pogo pad arcs | 72°/68° arc on spigot tip vs 48° entry→lock sweep | TC_PAD_ARC (72,68,68,68,68) > 48; copper pads non-printed spec | PASS `[D]` |
| **key notch depth** | TC_KEY_D 1.5 | **0.05** — box cut goes −1.5 *outside* the part, +0.05 inside | **FAIL → F1** |
| **catch tip wall** | ≥1.8 | **1.14** at r13.5 (ramp `a0+2.2` leaves a wedge) | **FAIL → F2** |
| **groove-floor wall** | ≥1.8 | 1.80 nominal → **1.75** at the notch nick; a corrected 1.5 mm notch would leave 0.3 mm | **FAIL → F3** |

Note on C5: the gate `v < 40 mm³` passes an 8.40 mm³ interference whose
size ≈ the RACK_KEY tab (2.5 × ~4.2 × 1.35). The seat CANNOT physically
happen at 0 stand-off — the tool is propped ~1.35 mm high on the tab.
The check is too weak to detect the defect it names ("key in notch").

## 4. FEM (CalculiX re-run + added cases)

Pipeline: `gen_geo.py`/`view_tc.py` copied verbatim into
`toolchg/check/fea/` (they write beside themselves; product scripts
`msh2tc.py`/`analyze_tc.py` run unmodified on my meshes). PETG-CF
E=4000 MPa, ν=0.35 `[U]`; wrench F=(0,0,−5.7) N at TCP
(149.4,0,−17) via rigid-body ref node + gravity — D10's worst-case BCs.

| case | mesh | BC / load | max\|U\| | raw maxVM | filtered maxVM | SF vs 25 MPa `[U]` | verdict |
|---|---|---|---|---|---|---|---|
| tc_master (re-run) | 28641 n / 16932 C3D10 — identical to D10 | NFIX horn ring, wrench at TCP | 0.001 mm | 1.26 | 0.79 MPa | ~32× | PASS (reproduces D10 exactly) |
| tc_plate (re-run) | 110430 n / 68040 C3D10 — identical | NFIX back face, wrench at TCP | 0.001 mm | 0.66 | 0.60 MPa | ~42× | PASS (reproduces D10) |
| plate_1catch (added) | 110430 n / 68040 C3D10 (same mesh) | NFIX back; whole wrench on ONE catch +a face (single-lug fault) | 0.049 mm | **32.00** | **16.85** MPa | **1.48× filt / 0.78× raw** | **FAIL — SF<2** |
| tool_pen (added) | 134154 n / 83466 C3D10 | NFIX 3 catch +a faces; 5 N lateral at tip region | 0.024 mm | 0.71 | 0.71 MPa | ~35× | PASS |
| tool_grip (added) | 125393 n / 70160 C3D10 | NFIX catch faces + socket-floor face; payload wrench at TCP, NLOAD a≥120 | **7.95 mm** | **28.73** | **28.73** MPa | **0.87×** | **FAIL — SF<2** |
| tc_rack (added) | 200487 n / 113271 C3D10 (cl 2.0) | NFIX base; 1.2 N on slot-2 seat (80 g tool ×1.5 bump) | 0.000 mm | 0.01 | 0.01 MPa | huge | PASS |

Interactive HTML + iso/front PNGs under `toolchg/check/fea/<tag>.{html,png}`.
Material values remain `[U]` — SF gates hold **only if** the 25 MPa
cross-layer assumption does.

Notes on the two failures:

- **plate_1catch**: hotspot @ (71.2, −11.2, −10.0) = a 71.2, r≈13.2 —
  exactly the thin catch tip measured in §3 (F2). The nominal 3-catch
  case is SF ~42, so the margin depends entirely on symmetric lug
  engagement.
- **tool_grip**: hotspot @ (110.0, ±12.5, −52.0) = the **clevis/bracket
  pin bore** on the inherited `w_grip_frame` body — a real Kt feature,
  not a BC edge (NFIX+NLOAD regions are excluded by the filter). The
  stock wrist part was checked at the spine-rib junction only
  (11.9 MPa, STATUS-wrist2) — this section was never separately gated.
  So this is an **inherited margin concern**, surfaced by the new check,
  not D10-introduced geometry. Also max|U| 7.95 mm at the rail tip under
  the full wrench: the tool body is compliant — a repeatability caveat
  for the bench list (coupling repeatability claims are sub-mm, body
  flex is mm-class).

## 5. Collision + dock path — `tc_collision.py` re-run (verbatim `logs/tc_collision.txt`)

```
== A) J4/J5/J6 sweeps, gripper tool mounted (step 2.5 deg) ==
SWEEP  J4 swept -70..+70: min bbox gap 0.0, min z 0.0  (rack-zone hits at 18 poses - informational) PASS
SWEEP  J5 swept -70..+70: min bbox gap 0.0, min z 0.0                           PASS
SWEEP  J6 swept -180..+180: min bbox gap 0.0, min z 0.0                         PASS
== J6 x J5 grid (sublimit applied when J5 < 0) ==
GRID   J6 x J5 grid: 0 arm collisions, 0 rack-zone hits (informational)         PASS
== named/corner poses ==
POSE   home        q=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0] tcp=[234.0, 0.0, 199.0] z_min 0.0 clean PASS
POSE   stow        q=[0.0, 70.0, -160.0, 70.0, 0.0, 0.0] tcp=[288.0, 0.0, 334.0] z_min 0.0 clean PASS
POSE   wrist-flex  q=[0.0, 45.0, -45.0, 70.0, 70.0, 0.0] tcp=[193.0, 100.0, 110.0] z_min 0.0 clean PASS
CORNER J4-70 J5-70 J6-110 clean                                                 PASS
CORNER J4-70 J5-70 J6+110 clean                                                 PASS
CORNER J4-70 J5+70 J6-180 clean                                                 PASS
CORNER J4-70 J5+70 J6+180 clean                                                 PASS
CORNER J4+70 J5-70 J6-110 clean                                                 PASS
CORNER J4+70 J5-70 J6+110 clean                                                 PASS
CORNER J4+70 J5+70 J6-180 clean                                                 PASS
CORNER J4+70 J5+70 J6+180 clean                                                 PASS
== Monte-Carlo 800 wrist poses (tool mounted) ==
MC     800 poses: min bbox gap 0.0, min z 0.0, arm hits 0, rack-zone 640        PASS
== B) dock and undock paths (all slots) ==
DOCK   slot 0: min bbox gap 0.0, max master<->tool engagement 0 mm3             PASS
UNDOCK slot 0: min bbox gap 0.0, max master<->tool engagement 0 mm3             PASS
DOCK   slot 1: min bbox gap 0.0, max master<->tool engagement 0 mm3             PASS
UNDOCK slot 1: min bbox gap 0.0, max master<->tool engagement 0 mm3             PASS
DOCK   slot 2: min bbox gap 0.0, max master<->tool engagement 0 mm3             PASS
UNDOCK slot 2: min bbox gap 0.0, max master<->tool engagement 0 mm3             PASS
DOCK   slot 3: min bbox gap 0.0, max master<->tool engagement 0 mm3             PASS
UNDOCK slot 3: min bbox gap 0.0, max master<->tool engagement 0 mm3             PASS
CHECKS PASS
```

"rack-zone hits" are informational declared pairs (tools resting in the
rack); "engagement 0 mm³" is consistent with the 0.2 mm design running
gaps (contact, not overlap). No new D10 collision found; the two
inherited wrist pairs documented by D10 stand. Note: the collision map
places the tool AT the seat — it does not model the un-seated +1.35 mm
F1 condition, so F1 is not double-counted here.

## 6. Mass / CoG / torque / payload — `tc_analysis.py` re-run (verbatim `logs/tc_analysis.txt`)

```
stock J6-out: 0.1018 kg ; tool-swap 0.0945 kg ; finger-swap 0.1075 kg
AB pose 0.5 kg: J2 3.249->3.283  J3 1.756->1.799  J4 0.828->0.879  worst 1.17 (J2)
stock reach max payload 0.412 kg (J2); tool-swap d_payload +0.007 kg
J6-side (master 5.8 + grip tool 79.8) = 85.6 g vs budget 234 g -> 37%
```

All STATUS numbers reproduce. PASS.

## 7. MuJoCo dock — `run_tc.py` headless (verbatim `logs/mujoco.txt`)

The product `build_tc.py` ran unmodified (driven by
`toolchg/check/build_mjcf_stl.py`); it regenerates `arm_tc.xml` /
`scene_tc.xml` + `meshes/` in-place. The regenerated `arm_tc.xml`
differed from the committed file only in `g_tc_master` mass
0.0054 → 0.0056 kg — the committed scene is ~0.2 g stale vs current
sources (minor; F8). The committed XML was restored and run against the
regenerated meshes. 75 meshes, nbody 10 njnt 8 nu 6 neq 10.

```
init tool pose err 0.0 mm (slot2 tool, slot0 pen)
SEAT   master-face to socket gap 1.41 mm / pen 2.48 mm (want <3)   PASS
SEATED tool still seated after lock twist: 0.2 mm, quat w 1.000    PASS
LIFT   tool 35.6 mm (want ~35) / pen 33.8 mm                       PASS
PARKED slot3 pose err 0.2 mm ; CLEAR master retreated 12.7 mm      PASS
FINAL  all qpos/xpos finite: True                                  PASS
CHECKS PASS
```

Roll behaviour matches CAD: entry q6 = −12°, lock = +48°
(−12 + 60 twist). PASS.

## 8. Firmware planner — review + pytest

`pytest software/robot-os/tests/test_toolchange.py -q`:
**13 passed in 1202.73 s**.

Review of `soma_arm/toolchange.py` (unmodified product file):

- J6 sublimit: every `dock_q()` waypoint is `kin.within_limits`-checked
  (raises IKError otherwise); `j6_sublim_ok()` enforces the D9
  conditional sublimit when J5<0 — tested. PASS
- lock/unlock = **pure J6 roll**: `plan_dock` seat→lock changes only
  q[5] (−12°→+48°, i.e. the +60° twist; test asserts q[:5] identical),
  `plan_undock` mirrors (+48°→−12°). Both the ±60° twist and the net
  +48° entry-to-lock conventions match CAD (`TC_ENTRY_REL`/`TC_TWIST`).
  PASS
- caps: per-waypoint `DOCK_VEL`/`DOCK_ACC` + `TWIST_VEL 0.6 rad/s`;
  test asserts caps on all waypoints. Torque "cap" is the conservative
  dock profile + derated gravity model — no explicit per-move torque
  limiter in the module (servo-side limit `[U]`). PASS-with-note
- `verify_latch`: position error tol 2.5° + load-signature ≥5% —
  exactly the stated mechanism. PASS
- no product module edited. PASS

## 9. BOM / hardware fit

| BOM item | CAD feature | fit | verdict |
|---|---|---|---|
| STS3215 servo (45.2×24.7×35.7 + horn) | `g_pocket()` = inherited `servo_kp` (SV_CLR 0.15) — the wrist-proven pocket | same generator as shipped wrist pockets | PASS `[S cad3]` |
| — servo price | BOM "~£7 `[U]`" | live UK 5 Nov 2025: RC Hobby-Models £25.00 (ST-3215-C018 12V/30kg, 45.2×24.7×35); eBay UK ~£24 (19kg variant) | sourced — claim low ~3.5× (was `[U]`) |
| pogo ~Ø1–1.5 barrel `[U]` | 5× Ø1.8 bores on socket floor, 0.8 proud tip | Ø1.5 barrel in Ø1.8 = 0.15/side; P75/P100-class test probes exist (100pcs ~£7.70–9.83 eBay UK, 5 Nov 2025) | CAD side PASS; spring force/travel `[U]` |
| **steel ball Ø5 + spring ~Ø4 + M3 grub** | detent bore **Ø4.2** smooth, dimple Ø3.0×0.8; params say "M4 plunger / ~3mm ball" | **Ø5 ball cannot enter Ø4.2; M4 thread needs Ø3.3 tap; Ø4 spring is 0.1 from wall** | **FAIL → F4** |
| — M4 ball plunger option | bore Ø4.2 | Ganter GN615-M4-KN £3.79 (ted.co.uk, in stock 5 Nov 2025): M4 thread, Ø2.5 ball, 9 mm, stroke 0.8 — matches dimple Ø3.0/0.8 and DET_PR 1.0 intent, but needs an M4 **tap** hole (Ø3.3), not Ø4.2 | sourced alternative `[S]` |
| M2/M3 heat-set inserts ~10 | horn holes Ø3.4+cb Ø6.2 (screws into vendor horn); servo bosses inherited; pen Ø3.0 pilot | M3 insert needs hole 4.0–4.1 + wall ≥1.6 (Shop4Fasteners M3×4 £7.16/100); horn holes are screw clearance, not insert pockets | `[U]` count/kind |
| **2× Ø3×10 dowels "tool-plate keying"** | **no dowel bores anywhere — plate is fused to tool body** | stale BOM row | **FAIL → F5** |
| pen clamp | 2× Ø3.0 radial bores at a136 | M3 grub self-tap ok; "insert" wording wrong if heat-set meant (needs Ø4.0–4.1) | minor → F6 |
| PETG-CF ~200 cm³ | print mass sums: 5.8+5.3+18+22.2+33.6+1.2+3.6+2+123.4 ≈ 215 g → ~164 cm³ eff | consistent with ~200 cm³ incl. brim/support | `[U]` |

## 10. STATUS claim audit

| # | STATUS claim | result | verdict |
|---|---|---|---|
| 1 | 11 parts watertight | 11/11 build watertight | PASS |
| 2 | volumes 7.3/6.8/22.8/28.3/42.8/1.5/2.4/1.3/157.0 cm³ | 7.33/6.76/22.84/28.30/42.75/1.53/2.35/1.27/157.03 | PASS |
| 3 | tool_grip inherits 2 slivers from w_grip_frame | confirmed (same 2 extra bodies in both) | PASS |
| 4 | slivers "~1 mm³" | measured 10.80+33.79 = 44.6 mm³ | **FAIL (magnitude)** |
| 5 | "Min wall ≥1.8 mm designed-in" | catch tip 1.14, groove floor 1.75 at notch | **FAIL** |
| 6 | "≤45° overhangs designed-in `[U bench]`" | suspended flats 403–2892 mm² on 7 parts | partial-FAIL/`[U]` |
| 7 | C1–C5 all PASS | reproduce | PASS (but C5 gate too loose — F1 note) |
| 8 | FEM master 0.79 filt / plate 0.60 filt | 0.79 / 0.60 — identical | PASS |
| 9 | collision suite PASS incl. MC-800 | reproduce | PASS |
| 10 | J6-out 94.5 vs 101.8 g | reproduce | PASS |
| 11 | J6-side 85.6 g vs 234 g | reproduce (5.8+79.8) | PASS |
| 12 | AB torques 3.283/1.799/0.879, worst 1.17 | reproduce | PASS |
| 13 | payload 0.412 → +0.007 kg | reproduce | PASS |
| 14 | MuJoCo seat 1.41/2.48, lift 35.6/33.8, finite | reproduce | PASS |
| 15 | pytest 13/13 | 13 passed | PASS |
| 16 | lock = pure J6 roll +60° (net +48) | verified in planner + sim (q6 −12→+48) | PASS |
| 17 | detent ball clear at entry (C4) | 0.00 mm³ both poses | PASS |
| 18 | capture: lock pull 153.4 mm³ / entry 0 | reproduce | PASS |
| 19 | rack STL at corrected RACK_PLATE_X/base z0 | rack base z=0, slots at x145/yslot | PASS |
| 20 | BOM hardware (servo/pogo/ball/inserts/dowels) `[U]` | servo pocket inherited PASS; **ball Ø5 vs Ø4.2 FAIL; dowels absent FAIL**; servo sourced ~£25 vs claimed ~£7 | **2 FAIL + 1 wrong price** |
| 21 | key notch sets roll phase (C5 "key in notch") | notch 0.05 mm deep — cannot key | **FAIL → F1** |
| 22 | no magnets in built design | concept C rejected; no magnet geometry | PASS |
| 23 | 12 V tool bus, no mains | params GND/+12V/DATA+2 spare | PASS |
| 24 | repeatability/pogo life/creep/cable fatigue | not measurable without hardware | `[U]` |
| 25 | live UK source/price for BOM | sourced 5 Nov 2025: STS3215 £24–25, M4 plunger £3.79, pogos ~£0.10, M3 inserts £7.16/100; detent spring/dowel/copper pads unsourced | `[U]` partial |
| 26 | PETG-CF material allowables (25/50 MPa) | assumption only | `[U]` |
| 27 | print tolerance/surface finish of fits | `[U bench]` stands | `[U]` |
| 28 | lock-torque margin | unmeasured | `[U]` |
| 29 | detent preload over time | unmeasured | `[U]` |
| 30 | cycle life (few hundred docks) | unmeasured | `[U]` |
| 31 | 12 V bus current budget per tool | `[U wiring]` stands | `[U]` |
| 32 | J6 sublimit honoured when J5<0 | within_limits + tested helper | PASS |

## 11. FAIL register (severity → proposed_fixes.md)

| id | severity | what | evidence |
|---|---|---|---|
| F1 | **blocks-dock** | key notch depth 0.05 mm vs RACK_KEY 1.4 mm tab | C5 8.40 mm³ ≈ tab volume; box bounds inverted (p_toolchg.py:167-168); groove-floor probe 1.75 at ph270 |
| F2 | **blocks-adopt** | catch tip wall 1.14 mm < 1.8 min; single-catch fault FEM 32.0 raw / 16.85 filt MPa → **SF 1.48<2** | axial probe r13.5 ph118: 71.06–72.20; ramp `a0+2.2` wedge; hotspot @ (71.2,−11.2,−10.0) = the thin tip itself |
| F3 | **blocks-adopt** | groove floor 1.8 nominal / 1.75 at notch; correct notch leaves 0.3 mm | probe 1.75–1.82; params arithmetic 20.0−18.2−1.5 |
| F4 | **blocks-build** | BOM Ø5 ball vs Ø4.2 bore, Ø4 spring vs Ø4.2 | tc_params TC_DET_D 4.2 / DIMPLE 3.0 vs STATUS:181 |
| F5 | minor | BOM 2× dowels, zero holes in CAD | STATUS:183; p_toolchg has no dowel bores |
| F6 | minor | pen "M3 insert" Ø3.0 pilot wording | tc_params.py:144 |
| F7 | minor | STATUS sliver "~1 mm³" (45×), overhang claim | §2/§3 measurements |
| F8 | minor | committed `arm_tc.xml` 0.2 g stale vs rebuild | mass attr 0.0054 vs 0.0056 regenerated |
| F9 | **blocks-adopt** (inherited) | tool_grip body peaks 28.73 MPa > 25 `[U]` at clevis pin bore under payload wrench; ~8 mm tip flex | fea/tool_grip.*; hotspot (110,±12.5,−52); inherited `w_grip_frame` section, applies to stock grip too |

The nominal cases pass with wide margin (SF ~32–42×); the added
single-catch fault case fails the SF≥2 gate (1.48× filtered, 0.78× raw)
with the hotspot exactly at the thin catch tip — the design's margin
depends on symmetric 3-lug engagement, which tolerances + detent seating
must guarantee `[U bench]`. Per the stage rule this is a blocking
adoption failure until F2 lands or symmetric engagement is proven.

## 12. Safety notes

- 12 V tool bus only (GND/+12 V/DATA+2 spare through 5 pogos); fused
  upstream `[U wiring]`. No mains anywhere.
- Detent uses a small ball+spring — keep assembled; small-part hazard.
- No magnets in the built design (concept C rejected).
- The F1 stand-off means a real dock would press the tool 1.35 mm high
  against the fork — first bench attempt would have shown it; fix F1
  before printing.

## 13. Recommendation

**fix then print.** The architecture, kinematics, collision envelope,
mass budget, planner and sim all check out and are exactly reproducible.
But the anti-rotation key cannot engage (F1, blocks first dock), the
catch tip and groove floor violate the stated 1.8 mm min wall on the
capture path (F2/F3), and the detent hardware as specified cannot be
assembled (F4). All five fixes are small, localised and documented in
`proposed_fixes.md`; the D10 "ADOPT LATER" verdict stands once they
land, pending the same bench validations STATUS already lists.
