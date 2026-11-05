# STATUS-toolchgfix — D12 applied D11 fixes to the D10 tool-changer

Stage `stages/D12_toolchg_fix.md` executed against `ARM_KNUCKLE_V5.md`
rules 0.1–0.10. Work done entirely inside `~/Vector-wt/toolchgfix` on
branch `arm-toolchg-fix` (base `origin/arm-toolchg-check` @ `17f9114`,
tag `toolchgchk-done`); the read-only checkout `~/Vector` and every
product file outside the `toolchg/` lineage were not touched. The
D11 findings F1–F8 from `toolchg/check/proposed_fixes.md` are applied;
F9 is documented (inherited `w_grip_frame` geometry unchanged).

Interpreter note: the stage's preferred CAD interpreter
`/Users/deepakdiwan/soma/.venv/bin/python` does not exist on this
machine — same situation as D11. CAD reruns used
`/Users/deepakdiwan/Vector-wt/cradlefix/.venv/bin/python` (build123d
0.13.0); pytest via `/Users/deepakdiwan/opt/anaconda3/bin/python3`
(pytest 7.1.1, py3.9); MuJoCo via
`/Users/deepakdiwan/Vector-wt/sim/.venv-mj/bin/python` (mujoco 3.10.0);
FE html via the fea venv (pyvista); ccx 2.23 + gmsh 4.15.0 from
FreeCAD.app. Raw logs: `toolchg/fix_logs/`; FEA cases/html:
`toolchg/fix_fea/`.

## What changed (fixes applied)

| # | file:line | before | after |
|---|---|---|---|
| F1 key notch | `p_toolchg.py:175` | notch box cut `H_AX-DOCK_R-KEY_D .. +0.05` → down into empty space, leaving a 0.05 mm nick | box cut `H_AX-DOCK_R-0.5 .. +TC_KEY_D` → up into the plate; notch void now real |
| F1 check gate | `tc_checks.py:111` | `v < 40.0` (passed an 8.4 mm³ interference) | `v < 0.5` |
| F1 engagement probe | `tc_checks.py:113-127` | — | new: slot-2 RACK_KEY tab vs plate ~0 mm³; widened tab must hit walls |
| F2 catch ramp | `p_toolchg.py:152` | ramp `a0+2.2` → tip wall 1.14 mm | ramp `a0+1.2` → tip wall 2.08 mm |
| F2 fault margin | `tc_params.py:60`, `p_toolchg.py:155-162` | `TC_CATCH_ARC 60` | `TC_CATCH_ARC 75` + corner-fillet wedge behind each catch +a face (see note) |
| F3 groove floor | `tc_params.py:76` | `TC_DOCK_R 20.0` → wall 1.75/0.3 at notch | `TC_DOCK_R 20.6` → wall 2.40, 1.20 at notch |
| F3 key depth | `tc_params.py:79` | `TC_KEY_D 1.5` | `TC_KEY_D 1.2` |
| F3 rack fits | `tc_params.py:122-123` | `RACK_SLOT_W 40.5`, `RACK_SEAT_R 20.3` | `RACK_SLOT_W 41.7`, `RACK_SEAT_R 20.9` (re-derived from Ø41.2 floor) |
| F4 detent BOM | `STATUS-toolchg.md` BOM | "Steel ball Ø5 + spring ~Ø4×8 + M3 grub" (Ø5 cannot enter the Ø4.2 bore) | "Steel ball Ø4 + spring ~Ø3.2×8 + M4 grub/plunger (or one commercial M4 ball plunger)"; CAD `TC_DET_D=4.2`/`TC_DIMPLE_D=3.0` unchanged and consistent |
| F5 dowel BOM | `STATUS-toolchg.md` BOM | stale "Steel dowel Ø3 × 10, 2×" row (no dowel holes exist) | row removed |
| F6 pen screw | `tc_params.py:144` | `PEN_SET_D=3.0` "M3 set-screw insert" | comment now "M3 grub self-tap pilot for the pen (not a heat-set insert; an insert would need ~Ø4.3)" |
| F7 slivers | `STATUS-toolchg.md` Task 3 | "~1 mm³" slivers | measured 10.80 + 33.79 = **44.6 mm³**, confirmed inherited from `w_grip_frame` |
| F7 overhangs | `STATUS-toolchg.md` Task 3 | "min wall ≥1.8 mm and ≤45° overhangs designed-in" | replaced with D11 measured suspended flat-down areas (403–2892 mm² on 7 parts) + bench note that master lug −a bearing faces print on support |
| F8 MJCF | `mjcf_tc/arm_tc.xml` | `g_tc_master` mass 0.0054 (stale) | regenerated via `build_tc.py`: 0.0056 (matches 7.33 cm³ rebuild); also g_tool_grip 0.0179, g_tool_pen 0.0220, g_tc_rack 0.1985 |
| F8 scene | `mjcf_tc/scene_tc.xml` | — | regenerated; output byte-identical (no change needed) |

### F2 fault-case iteration (the SF≥2 gate)

`proposed_fixes.md` says: after the wall fix re-run `plate_1catch`; if
SF<2 the alternatives are deeper catches, wider catch arc
(`TC_CATCH_ARC 60→70`), or a bench-verified seating precondition.

- ramp fix only (arc 60): catch-tip wall 1.14→2.08 mm, but filtered
  maxVM **17.08 MPa → SF 1.46** — still <2. Peak moved off the tip to
  the ring corner behind the catch face (a73.3, r18.2, ph145).
- arc 70: filtered **13.15 MPa → SF 1.90** — closer, still <2.
- arc 75 **+ corner fillet** (a ~1.4 mm chamfer wedge revolved over the
  catch arc behind the +a face, bottoming at r17.6 = 0.3 mm clear of
  the lug sweep at r17.3): filtered **11.89 MPa → SF 2.10** ✓ PASS.
  Entry gap is now 45° (6.5° lug margin each side — C1 sweep re-passed
  with 0.00 mm³ at every roll).

The fillet is a local relief inside the D11-named "wider catch arc"
fallback — no new [D] dimension was invented (wedge dims are derived:
leg 1.4 mm along the bore, 0.6 below it, bounded by the r17.3+0.3 lug
clearance already in the model).

## F9 (inherited tool_grip clevis stress) — documented, geometry left stock-shifted

D11: `tool_grip` filtered maxVM 28.73 MPa at the cheek-window bottom
corner (a110, ±12.5, −52.0) → SF 0.87 vs 25 `[U]`. The stage allows a
small local relief on the tool copy only if it reaches SF≥2.
Attempted: window0's cut clipped to −46 (leaving a 6.4 mm web at the
keel corner). Result: peak **worsened to 33.61 MPa** — the fill just
relocated the sharp re-entrant corner to the new fill edge. A local
relief cannot plausibly close the ~60% gap to SF 2, so the attempt was
reverted: `tool_grip` ships the exact `w_grip_frame` cage geometry.
Proof the revert is faithful — the re-run reproduces D11 bit-for-bit:
filtered **28.73 MPa at node (110.0, 12.5, −52.0)**, same value, same
node. The payload caveat stands — see [U]/bench below.

## Proof (re-run on the fixed geometry)

### 1. Build — 11 parts (`build_toolchg.py`, cradlefix venv)

```
tc_master      w6  bbox 13.1 x 32.2 x 33.1  vol 7.3 cm3  wt True
tc_plate       w6  bbox 9.4 x 46.0 x 46.0  vol 7.4 cm3  wt True
tool_grip      w6  bbox 68.1 x 64.0 x 60.4  vol 23.5 cm3  wt True
tool_pen       w6  bbox 79.0 x 46.0 x 46.0  vol 29.0 cm3  wt True
tc_vendor_g    w6  bbox 49.3 x 24.7 x 45.2  vol 42.8 cm3  wt True
tc_gear        w6  bbox 6.0 x 18.0 x 18.0  vol 1.5 cm3  wt True
tc_rack_u      w6  bbox 6.0 x 36.0 x 12.0  vol 2.4 cm3  wt True
tc_rack_d      w6  bbox 6.0 x 36.0 x 12.0  vol 2.4 cm3  wt True
tc_finger_u    w6  bbox 14.4 x 4.0 x 25.2  vol 1.3 cm3  wt True
tc_finger_d    w6  bbox 14.4 x 4.0 x 25.2  vol 1.3 cm3  wt True
tc_rack        fix bbox 44.0 x 202.0 x 118.0  vol 156.3 cm3  wt True
BUILD DONE 11 parts
```

`tool_grip` remains 3 solids: 23479.63 mm³ main + inherited slivers
10.80 + 33.79 (44.6 mm³ total — matches `w_grip_frame`'s own
10.80 + 33.66 within STL mesh noise).

### 2. Wall probes (`check/audit_geom.py`, post-fix)

```
catch axial r13.5 ph118: 70.12-72.20 (2.08)   <- catch tip 2.08 >= 1.8
catch axial r15.0 ph118: 69.79-72.20 (2.41)
groove floor a74.75 ph0:  18.20-20.60 (2.40)  <- groove wall 2.40 >= 1.8
groove floor a74.75 ph270:35.20-36.40 (1.20)  <- notch residual 1.20 >= 1.2
groove floor a74.75 ph270±3:            (1.23)
groove floor a74.75 ph270±6:            (2.42)
groove floor a72.60 ph270: 34.60-36.40 (1.80)
floor a-axial r5:         76.00-78.40 (2.40)
```

(before: tip 1.14, groove 1.75–1.82, notch residual 0.3 — all now in
spec. Full probe dump: `fix_logs/audit_geom.txt`.)

### 3. `tc_checks.py` C1–C6 with the tightened C5

```
PASS C1 entry sweep clean                                 worst 0.00 mm3
PASS C2 twist sweep within allowance                      worst 0.00 mm3
PASS C3 lugs captured at lock                             lock pull 171.7 mm3, entry pull 0.00 mm3
PASS C4 detent ball clear at entry                        0.00
PASS C5 tool seats in rack                                0.00 mm3
PASS C5 key tab engages notch void                        tab 0.00, widened 4.11 mm3
PASS C6 mass budget                                       informational
ALL CHECKS DONE
```

C3 lock pull improved 153.4→171.7 mm³ (wider catches capture more lug
area). `fix_logs/tc_checks.txt`.

### 4. FEM (`toolchg/fix_fea/`, ccx 2.23, PETG-CF `[U]` vs 25 MPa)

| case | mesh nodes | raw maxVM | filtered maxVM | patch | SF vs 25 `[U]` | verdict |
|---|---|---|---|---|---|---|
| tc_master | 28.6k | 1.26 | 0.79 | 1.07 | 31.6 | PASS |
| tc_plate (nominal wrench) | 112k | 0.71 | 0.48 | 0.71 | 52 | PASS |
| **plate_1catch** (fault) | 112k | **11.89** | **11.89** | 8.66 | **2.10** | **PASS ≥2** |
| tool_pen | 136k | 0.78 | 0.78 | 0.50 | 32 | PASS |
| tool_grip | 127k | **28.73** | **28.73** | 4.91 | 0.87 | F9 — inherited, see note |
| tc_rack | 200k | 0.01 | 0.01 | 0.01 | >1000 | PASS |

HTML/PNG per case in `toolchg/fix_fea/<case>.{html,iso.png,front.png}`.
`tool_grip`'s 28.73 is the documented inherited F9 value — it
reproduces D11's 28.73 at the same node (110.0, ±12.5, −52.0); it is
not a D12 regression.

### 5. `tc_collision.py` full suite

```
== A) J4/J5/J6 sweeps, gripper tool mounted (step 2.5 deg) ==
SWEEP  J4 swept -70..+70: min bbox gap 0.0, min z 0.0  (rack-zone hits at 18 poses - informational) PASS
SWEEP  J5 swept -70..+70: min bbox gap 0.0, min z 0.0                           PASS
SWEEP  J6 swept -180..+180: min bbox gap 0.0, min z 0.0                         PASS
GRID   J6 x J5 grid: 0 arm collisions, 0 rack-zone hits (informational)         PASS
POSE   home/stow/wrist-flex + 8 corner poses                                   PASS x11
MC     800 poses: min bbox gap 0.0, min z 0.0, arm hits 0, rack-zone 637        PASS
== B) dock and undock paths (all slots) ==
DOCK   slot 0..3: min bbox gap 0.0, max master<->tool engagement 0 mm3          PASS x4
UNDOCK slot 0..3: min bbox gap 0.0, max master<->tool engagement 0 mm3          PASS x4
CHECKS PASS
```

Full log: `fix_logs/tc_collision.txt`. The 18-sweep / 637-MC rack-zone
counts are informational (arm near the parked rack, as in D11).

### 6. `tc_analysis.py` mass/torque (re-measured volumes)

```
stock J6-out: 0.1018 kg, centroid [ 0.0513  0.     -0.008 ] m
tool-swap J6-out: 0.0949 kg, centroid [ 0.0495  0.     -0.0118] m
finger-swap J6-out while gripping: 0.1076 kg

== TOOL SWAP (each tool has its servo) ==
  AB (horiz)  J2 3.249->3.284  J3 1.756->1.800  J4 0.828->0.880  worst ratio 1.17 (J2)
== FINGER SWAP (arm keeps grip mech) ==
  AB (horiz)  J2 3.249->3.325  J3 1.756->1.825  J4 0.828->0.891  worst ratio 1.19 (J2)
== max_payload (80% derated) ==
stock reach-pose max payload 0.412 kg (limit J2)
tool-swap: d_tau_J2 -0.0229 Nm -> d_payload +0.006 kg
```

### 7. MuJoCo dock (`mjcf_tc/run_tc.py`, regenerated MJCF)

```
SEAT    master-face to socket-mouth gap 1.41 mm at seat (want < 3)         PASS
SEATED  tool still seated after lock twist: 0.3 mm, quat w 1.000           PASS
LIFT    tool lifted 35.7 mm with the arm (want ~35)                        PASS
PARKED  tool parked in slot 3: pose err 0.3 mm, quat w 1.000               PASS
CLEAR   master retreated 12.7 mm from the socket mouth                     PASS
SEAT    master-face to pen socket gap 2.49 mm at seat                      PASS
LIFT    pen lifted 33.8 mm with the arm                                    PASS
FINAL   all qpos/xpos finite at end: True                                  PASS
CHECKS PASS
```

### 8. Firmware tests

```
tests/test_toolchange.py .............                                   [100%]
============================== 13 passed in 1.97s ==============================
```

### 9. BOM corrections

| item | status | source check (today) |
|---|---|---|
| Detent: steel ball Ø4 + spring ~Ø3.2×8 + M4 grub, or one commercial M4 ball plunger | corrected | commercial M4 ball plungers verified live UK: WDS 823 M4×10 (£6.23, stock<10), Good Hand K0316 M4×10 (£2.50, 45 in stock), Ross Handling M4 (£6.72). Note: commercial plungers carry a Ø2.5 ball — Ø3.0 dimple still engages ~0.35 mm; body needs an M4 thread/insert at the bore mouth `[U bench fit]` |
| Stale Ø3×10 dowels | removed | n/a — no holes exist (plate fused to body) |
| Pen set screw | comment fixed | M3 grub self-tap into Ø3.0 pilot — consistent; heat-set insert would need Ø4.3 `[U if changed]` |
| Pogo pins Ø~1 ×5 | `[U]` | unverified |
| STS3215 ~£7 | `[U]` | unverified |
| PETG-CF ~200 cm³ | `[U]` | unverified |

## Remaining `[U]` / bench items

- PETG-CF allowables remain `[U]` (25 MPa cross-layer used throughout).
- F9: `tool_grip` cheek/clevis SF ~0.87 vs 25 `[U]` under the full
  0.5 kg+tool payload wrench — inherited from `w_grip_frame`, unchanged
  here. Payload caveat: treat max payload on the printed grip tool as
  unverified until bench-tested; revisit the stock part on its own
  lineage if the margin proves real (bench item carried from D11).
- Master lug −a bearing faces (~267 mm²) print on support — surface
  quality exactly where capture loads bear; inspect after print.
- Detent: commercial M4 plunger ball Ø2.5 vs CAD Ø4 ball — either is
  accommodated by the Ø4.2 bore / Ø3.0 dimple, but the threaded mouth
  (insert or print-thread) is `[U bench fit]`.
- Slicer pass for the quoted overhang areas still `[U bench]`.
- Coupling repeatability ±0.3 mm claim is still `[U bench]`.

## Recommendation

**Ready to print prototype.** Every D11 blocking defect is closed with
measured margin: notch real (key engagement probe positive), catch tip
2.08 mm, groove wall 2.40/1.20 mm, single-catch fault SF 2.10, detent
and BOM consistent, MJCF regenerated, C1–C6 PASS, collision suite PASS,
MuJoCo dock PASS, 13/13 tests pass. The two standing caveats are
inherited/informational (F9 tool_grip bench payload test; master lug
support-face print quality) and are called out above.
