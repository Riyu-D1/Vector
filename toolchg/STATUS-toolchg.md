# STATUS-toolchg — D10 automatic quick-change tool mount ("automounter")

Stage `stages/D10_toolchanger.md` executed against `ARM_KNUCKLE_V5.md`
rules 0.1–0.10. Work done entirely inside `~/Vector-wt/toolchg` on
branch `arm-toolchg` (base `d527be0`); the read-only checkout
`~/Vector` and all other branches/worktrees were not touched. This was
an EXPLORATION stage — everything below says plainly what is verified
in geometry/FEA/sim vs what stays `[U]` until hardware exists.

## Deliverables

- `toolchg/CONCEPTS.md` — Task 1 interface requirements + finger-swap vs
  tool-swap study + Task 2 three-concept trade study (sketches, tables).
- `toolchg/tc_params.py`, `p_toolchg.py`, `build_toolchg.py` —
  parametric CAD (build123d), 11 watertight parts → `out/` STL+STEP
  (not committed).
- `toolchg/tc_checks.py` — C1–C6 geometry checks (real output below).
- `toolchg/tc_analysis.py` — mass/CoG/joint-torque study on
  `soma_arm.gravity` (Task 4c).
- `toolchg/tc_collision.py` — posed-mesh collision + dock-path sim
  (final2 `f2_collision.py` pattern).
- `toolchg/fea/` — CalculiX FEM pipeline + interactive HTML + PNGs.
- `toolchg/mjcf_tc/` — MuJoCo dock scene (cradlefix mjcf_cf pattern).
- `software/robot-os/soma_arm/toolchange.py` + `tests/test_toolchange.py`
  — dock planner + unit tests (new files only).
- `toolchg/renders/` — concept sheet, wrist+tool, tool-in-rack, arm iso.

## Task 1 — interface requirements + architecture decision

Full write-up in `CONCEPTS.md` §1–2. Through the coupling must pass:
mechanical (tool ~0.09 kg, 0.5 kg payload → ~0.42 N·m plate moment,
J6 static ~0.2 N·m, alignment target radial ≤0.2 mm / backlash <0.5 mm
at TCP) and electrical (GND/+12 V/DATA for the tool's STS3215 + 2 spare
signal lines → 5 pogo pins).

**Decision: TOOL-SWAP** — each powered tool carries its own servo;
passive tools (pen, camera, hook) need none. Numbers (gravity model):

| | stock grip | tool-swap | finger-swap |
|---|---|---|---|
| J6-out mass while gripping | 0.1018 kg | 0.0945 kg | 0.1075 kg |
| J2 τ @ AB pose, 0.5 kg | 3.249 N·m | 3.283 (+0.034) | 3.325 (+0.076) |
| J4 τ | 0.828 | 0.879 (+0.051) | 0.891 (+0.063) |
| electrical pass-through | — | 5 pogo | none |
| works for non-gripper tools | — | yes | no |

Tool-swap J6-out is *lighter* than stock (94.5 vs 101.8 g; the socket
prints slimmer than w_grip_frame's horn cage). Finger-swap is heavier
during gripping AND needs a blind rotary drive re-mesh [U].

## Task 2 — concepts (CONCEPTS.md §3)

- **A — 3-lug bayonet twist-lock on the J6 axis** (built): insert −a,
  J6 rolls +60° → lugs under catches, spring-ball detent clicks a lug
  dimple at lock. Zero extra actuators — J6 does insert/twist/detent;
  unlock = −60° twist + pull. Rack fork in the OD groove steadies the
  tool; key notch sets roll phase for blind engagement.
- **B — kinematic 3-V-groove/3-ball + cam latch**: best repeatability
  (closed-form seat) but can't carry 0.42 N·m on a Ø40 plate without
  a big preload spring, and needs a moving release cam on the rack the
  arm must find blind — a 4th DOF in the dock problem.
- **C — magnetic kinematic + pogos**: magnet pull-off at this scale
  ~10–20 N [U] vs 0.42 N·m payload moment (≈21 N at r20) — fails
  SF ≥ 2 on its own, so still needs a mechanical latch = concept A
  with extra mass + pinch hazard. Rejected.

**Picked A** for zero actuators, blind-capable docking, least added
mass, and all-loads-in-material capture.

## Task 3 — parametric CAD (11 parts, all watertight)

`build_toolchg.py`: tc_master 7.3 cm³, tc_plate 7.4, tool_grip 23.5,
tool_pen 29.0, tc_vendor_g 42.8 (servo proxy), tc_gear 1.5,
tc_rack_u/d 2.4 ea, tc_finger_u/d 1.3 ea, tc_rack 156.3 (4 slots,
46 mm pitch). Print orientation: coupling pair drawn along the a-axis —
print −a face down (the −a lead chamfers double as support-free ramps);
tool_grip back-face down; tool_pen plate-face down; tc_rack flat on its
base (z=0). Min wall ≥1.8 mm is designed-in; D11 measured suspended
flat-down (support-needed) areas on 7 of 11 parts — tc_plate ~2865 mm²
(incl. ~1040 mm² socket-floor ceiling inside the bore), tool_pen ~2892,
tool_grip ~2825, tc_vendor_g ~1840, tc_master ~403 (incl. ~267 mm² lug −a
bearing faces, which print on support — a surface-quality risk exactly
where capture loads bear — bench item), tc_finger_u/d ~160 ea,
tc_rack 0 mm². Slicer pass not
verified `[U bench]`. The gripper is a NEW copy (`tool_grip` +
`tc_*` vendor set) — product `w_grip_frame`/vendor files untouched.
Note: `tool_grip` inherits two detached slivers measured 10.80 + 33.79
= **44.6 mm³** present in the shipped `w_grip_frame` STL (10.80 + 33.66
there) — confirmed inherited, left as-is (product file).

## Task 4a — FEM (PASS vs [U] material data)

CalculiX via the cad3/lighten pipeline; worst static wrist case:
NFIX at the horn-face bolt ring, 0.5 kg+tool wrench applied through a
rigid-body ref node at the TCP.

- `tc_master`: 28641 nodes / 16932 C3D10 — max|U| 0.001 mm,
  filtered maxVM **0.79 MPa** (raw 1.26 at constraint nodes).
- `tc_plate`: 110430 nodes / 68040 C3D10 — filtered maxVM **0.60 MPa**.
- vs PETG-CF 25 MPa cross-layer / 50 MPa along-layer `[U]`:
  SF ≈ 32× cross-layer. SF ≥ 2 by a wide margin **if** the material
  numbers hold — they are unverified assumptions `[U]`.
- Interactive HTML: `fea/tc_master.html`, `fea/tc_plate.html`;
  renders `fea/tc_*_{iso,front}.png`.

## Task 4b — collision + dock path (PASS)

`tc_collision.py` (posed-mesh, declared-pair audit, J6 conditional
sublimit honoured when J5 < 0):

```
PASS  J4 sweep -70..+70        PASS  J5 sweep -70..+70
PASS  J6 sweep -180..+180      PASS  J6/J5 grid (sublimit)
PASS  named poses / corners    PASS  800-pose Monte-Carlo (0 arm hits)
PASS  DOCK slot 0-3 / UNDOCK slot 0-3   CHECKS PASS
```

- Two **inherited** product pairs declared (measured identical on the
  stock part set): `w_j4_cradle × w_link5` ~3.4 mm³ and J4 vendor case ×
  link5 at combined extreme corners — not D10 geometry.
- Declared by design: master × docked-tool socket engagement (the
  capture itself), carried tool × rack groove seat ≤12 mm³ bound —
  measured 8.4 mm³.
- Fixes the sweep caught: `TC_J6O` 59.3→**53.0** (6.3 mm pose error),
  C3 pullout tested +a instead of −a (entry free / lock 153.4 mm³),
  rack STL stale at old x=240 and base z=−2 (rebuilt at corrected
  `RACK_PLATE_X`, base z=0), and joint-space interpolation grinding
  slot walls — planner densified (insert 6/2/0 mm, lift 8/16/24/35 mm).

## Task 4c — mass & payload (PASS, under budget)

- master 5.8 g, grip tool 79.8 g, pen tool 22.2 g; J6-side total
  (master + grip tool) **85.6 g vs 234 g budget** — 37% of budget.
- Gravity-model J6-out 94.5 g vs stock 101.8 g → payload bound at the
  reach pose *improves* ~0.007 kg (d_tau_J2 −0.025 N·m; stock bound
  0.412 kg, J2-limited).
- Worst torque ratio 1.17× at J2 in the AB pose (3.249→3.283 N·m) —
  within derated margins. Not over budget.

## Task 4d — MuJoCo dock (PASS, real output)

`mjcf_tc/build_tc.py` → scene_tc.xml (75 meshes; nbody 10 njnt 8 nu 6
neq 10); `run_tc.py` headless scripted dock:

```
grip tool: initial pose err 0.0 mm; seat gap 1.41 mm; seated err 0.2 mm
           quat w=1.000; lift 35.6 mm (target ~35); undock+park err 0.2
pen tool:  seat gap 2.48 mm; lift 33.8 mm
master retreat 12.7 mm; all qpos/xpos finite; CHECKS PASS
```

Lock/unlock is weld-toggle in sim; real-world engagement is the C3-verified
lug/catch geometry. Pose after docking within tolerance.

## Task 5 — firmware planner (13/13 tests PASS)

`soma_arm/toolchange.py`: constrained `_solve_dock()` (position + tool
axis ∥+x), `dock_q()`, `plan_dock()` (approach → insert ×2 → seat →
pure-roll lock → lift ×4 → clear), `plan_undock()` mirror,
velocity/accel caps, `verify_latch()` on J6 position error + load
signature, J6 sublimit respected when J5 < 0.
`pytest tests/test_toolchange.py`: **13 passed**.

## Task 6 — renders + 3 review iterations

`render_poses.py` poses the sim-verified meshes (same loader/body map as
`tc_collision.py`); `render_blend.py` = wrist2 workbench pattern.

- iter 1: `asm_frontiso/side` cropped the tool — ortho_scale too small
  vs bounding-diagonal worst case → 1.4→2.1; concept internals hidden
  between plates.
- iter 2: concept mockups exploded (balls/pogos/latch now visible);
  `concept_frontiso` readable.
- iter 3: added `rackonly_*` close-up (tools seated, no arm) for the
  tool-in-rack deliverable; re-verified all views.
- Final set: `concept_frontiso/top`, `asm_frontiso/side`,
  `rack_frontiso/top` (arm at lock waypoint), `rackonly_front/frontiso`,
  `arm_frontiso/side` — all <1.5 MB.

## BOM — non-printed parts (all `[U]` — not verified live)

| Part | Qty | Where | Source/price |
|---|---|---|---|
| STS3215 serial servo | 1 per powered tool | tool body | ~£7 `[U]` |
| Pogo pins Ø~1 mm | 5 per tool | socket floor ↔ spigot face | `[U]` |
| Steel ball Ø4 + compression spring ~Ø3.2×8 + M4 grub/plunger (or one commercial M4 ball plunger) | 1 set | master detent | `[U]` |
| M2/M3 heat-set inserts + screws | ~10 | master↔horn, tool↔servo | `[U]` |
| PETG-CF | ~200 cm³ | all prints | `[U]` |

No magnets in the built design (concept C rejected).

## Real risks

- **Repeatability** `[U]` — detent fixes roll to the dimple width;
  spigot/bore runout bounded by print tolerance ~0.15 mm `[U]`;
  TCP repeatability est. ≤0.5 mm — needs a dial-gauge bench pass.
- **Pogo reliability** `[U]` — contact under vibration/cycling
  unverified; the powered-tool bus is the weakest link by inspection.
- **Cable fatigue** `[U]` — tool servo wires flex at every dock/undock;
  strain relief drawn but not cycle-tested.
- **PETG-CF creep** `[U]` — lug/catch under a constant 0.42 N·m moment
  may relax over weeks; detent preload decays. Bench soak needed.
- **Print tolerances** `[U]` — phase alignment of lugs/catches and the
  detent dimple position assume ~0.15 mm accuracy; a 0.3 mm error eats
  the entry allowance (C2 worst case is the margin).
- **Lock-torque margin** `[U]` — J6 twist friction against the detent
  ball is unmeasured; planner caps q6 torque anyway.

## Bench test list (after printing)

1. Manual dock/undock ×50 on a printed master+plate; measure TCP
   repeatability with the pen tool on paper (target <0.5 mm).
2. Pull-out: hang 0.5 kg at TCP arm on a locked tool; measure slip.
3. Pogo continuity + voltage drop over 100 dock cycles.
4. J6 current/position signature during lock twist vs `verify_latch()`.
5. Creep: locked tool under rated moment 24 h; re-measure backlash.
6. Full `plan_dock`/`plan_undock` on hardware at all 4 slots.

## Recommendation

**ADOPT LATER.** The design is verified everywhere a CAD/sim pipeline
can verify it (geometry, FEM, collision, dynamics, planner tests) and
costs only 5.8 g arm-side; but repeatability, pogo life and creep are
unprovable without a printed prototype. Print the master + one tool
plate + pen first (bench list above); if repeatability ≤0.5 mm and the
detent survives a few hundred cycles, adopt for the rack station.

## Safety

No mains anywhere — the tool bus is the existing 12 V servo bus
(fused upstream `[U wiring]`). The detent uses a small ball + spring —
small-part hazard, keep assembled. Strong magnets were evaluated and
rejected (concept C); if ever revisited: pinch hazard, keep >150 mm
from pacemakers and magnetic media/electronics.

## Files

New files only: `toolchg/**` (code, docs, fea html/png, renders, lists)
plus `software/robot-os/soma_arm/toolchange.py` and
`software/robot-os/tests/test_toolchange.py`. Not committed per rules:
`out/`, `renders/scratch/`, `fea/` solver scratch, `mjcf_tc/meshes/`,
`__pycache__/`, regenerated `cad/arm2b/out/`.
