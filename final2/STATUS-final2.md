# STATUS-final2 — F2 merge + whole-arm validation (arm-final2)

Stage `stages/F2_merge_wrist_test.md` executed against
`ARM_KNUCKLE_V5.md` rules 0.1–0.10. Work done entirely inside
`~/Vector-wt/final2` on branch `arm-final2`; the read-only checkout
`~/Vector` and all other branches/worktrees were not touched.

## Merge report

- `arm-final2` created at `arm-final` tip `b7374e1`.
- `git merge arm-wrist2` → **fast-forward `b7374e1..14096c0`, zero
  conflicts.** `arm-wrist2` already contained `arm-final` (D5→D6
  commits on top of F1), so there was nothing to resolve.
- Nothing merged to `main`; no `--force` anywhere; `/usr/bin/git` only.

## Task 1 — full-assembly rebuild (PASS)

`final/export_assembly.py` now loads the D6 wrist set from `wrist2/out`
following the tested `wrist2/export_wrist2_asm.py` pattern: drops
arm2b `j4_cradle/link4/link5/grip_frame` + the old J5/J6/gripper servo
proxies, racks, gear, fingers; loads `w_*` + D6 vendor parts; keeps
`vendor_sts3250_j4` from cad3 (wrist2's `vendor_sts3215_j4` proxy is
skipped). Result: **72 parts / 175 solids**, `assembly.stl` 10.6 MB,
`assembly.step.gz` 5.7 MB (34.1 MB expanded). Finger tip at a=233.8 mm
= FK TCP (233.8, 0, 199.2). No arm2b wrist part remains in the part
set (name audit).

## Task 2 — posed-mesh collision sim (`final2/f2_collision.py`)

Method = D6 `wrist2_checks.py` posed-mesh: all 72 assembly parts as
manifold solids, PoE transform per body (verified against robot-os FK
at 3 multi-joint poses, err < 1 mm), pair booleans with declared mating
exclusions measured on this exact mesh set. Step 2.5° ≤ 2.5°.
Cable-plug sweep tubes modelled as sourced servo-frame plug boxes
(`ap2b SV_PLUG_*` through the ap6 servo frames — real plug dims, no
padding invented). Same-body grip internals checked across the stroke.

### Home-pose audit — 11 declared contacts, 0 undeclared

| Pair | Vol mm³ | Why declared |
|---|---|---|
| cy2/cy3_carrier × vendor_outpins | 5.0 | outpins engage carrier by design |
| cy2/cy3_disc1 × vendor_outpins | 165.1 | drive mesh (precesses) |
| cy2/cy3_disc2 × vendor_outpins | 180.0 | drive mesh (precesses) |
| flange_j2/j3 × vendor_spring_j2/j3 | 2.6 / 2.5 | spring seats |
| plug_{g,j5,j6} × own servo case | 2415.6 ea | plug proxy inside own servo |

### Per-joint sweeps (others at 0, grip closed)

| Joint | Range | Min bbox gap | Min z | Result |
|---|---|---|---|---|
| J1 | −180..+180 | 0.0 | 3.3 | **contacts below −152.5°** (yaw stop) |
| J2 | −120..+70 | 0.0 | −80.3 | **contacts +62.5..+70 + below-table** |
| J3 | −180..+30 | 0.0 | 3.3 | PASS |
| J4 | −70..+70 | 0.0 | 3.3 | PASS |
| J5 | −70..+70 | 0.0 | 3.3 | PASS |
| J6 | −180..+180 | 0.0 | 3.3 | PASS |
| Gripper | 0..25 mm | 0.0 | — | PASS |

- **J1**: `yaw_limit × base_reinf` 8→102 mm³ from −152.5° to −180°. This
  is the *designed* yaw hard stop engaging (the stop disc is named for
  it) — mechanical free range ≈ **−152.5..+180**, software limit ±180.
  Asymmetric: no contact on the + side within limits.
- **J2**: `w_link5/vendor_sts3215_j6 × base_plate` starting +62.5°
  (29..6790 mm³), plus `w_link5 × base_link` at +70; z < 0 below ~+50°.
  Free contact range −120..+62.5. The D6 keel hangs 17 mm under the
  axis → base contact ~7.5° earlier than the D5 wrist (measured: D5
  first contacts at +70). **Not a capability loss**: the wrist is
  already below the table plane from ~+50° in both designs, so those
  poses are unreachable anyway.

### Named poses

| Pose | q (deg) | TCP mm | z min | Result |
|---|---|---|---|---|
| home | all 0 | (234,0,199) | 3.3 | PASS |
| stow | 0,70,−160,70,0,0 | (288,0,334) | 3.3 | PASS |
| reach-forward | 0,70,−95,25,0,0 | (365,0,170) | 3.3 | PASS |
| reach-up | 0,0,−65,65,0,0 | (216,0,336) | 3.3 | PASS |
| reach-down | 0,70,−5,−65,0,0 | (237,0,42) | 3.3 | PASS |
| wrist-fully-flexed | 0,45,−45,70,70,0 | (193,100,110) | 3.3 | **w_j4_cradle × w_link5 3.4 mm³** |

The compound wrist corner (J4+70 ∧ J5+70) grazes the link5 shell on the
j4 cradle by 3.4 mm³. Each joint individually sweeps its full ±70°
clean — the graze only appears at combined extremes (the MC histogram
below shows it across all sign mixes at high |J4|+|J5|). Matches D6's
own ROM finding (J5 ±70 stops read w_link5×fore_r2 3 mm³ class contacts).

### Corner poses (J2×J3×J4 extremes, J1=J5=J6=0)

| Corner | Result |
|---|---|
| J2−120 J3−180 J4−70 | clean of parts, min z −98.7 (below table) |
| J2−120 J3−180 J4+70 | clean of parts, min z −150.1 (below table) |
| J2−120 J3+30 J4−70 | PASS |
| J2−120 J3+30 J4+70 | **cy2 module × J6/link5** (wrist swings into the J2 actuator zone, ≤4.4 cm³) |
| J2+70 J3−180 J4−70 | PASS |
| J2+70 J3−180 J4+70 | PASS |
| J2+70 J3+30 J4−70 | **arm folded into base/J1** (fore×link1, wrist×base, z −22.9) |
| J2+70 J3+30 J4+70 | same fold family, largest single pair 36.5 cm³ (J1 servo box × J5 servo box) |

### Monte-Carlo — 2200 poses, uniform in limits, grip 0..25 mm

**1062/2200 poses (48%) carry ≥1 undeclared hit; 2457 pair-hits
total** — roughly half of uniform-random joint space is geometrically
blocked (expected for a compact fold arm; the planner/limits are what
keep real motion out of it). Pair histogram (`f2_mc_hist.py`, same
seed → same poses):

| Hits | Pair | Family |
|---|---|---|
| 606 | w_j4_cradle × w_link5 | compound wrist-extreme graze, 1–18 mm³ |
| 368 | base_reinf × yaw_limit | J1 < −152.5 yaw stop sector |
| 194 | vendor_sts3250_j4 × w_link5 | wrist-flex case-edge graze |
| 137+137 | plug_g / vendor_sts3215_g × vendor_sts3215_j5 | wrist-flex grip-body vs J5 case |
| 50 | w_grip_frame × w_link4 | wrist-flex |
| ~200 | base_*/j1_cradle/link1/yaw_limit × wrist parts | deep-fold dives into base |
| rest | fore×link1, j6×j1 servo | deep-fold |

Largest single overlap 27.4 cm³ (`j1_cradle × vendor_sts3215_g` at a
J2+52/J3+16/J4+66 fold) — unreachable poses only. **The wrist-extreme
grazes are the one D6-relevant find**: each wrist joint sweeps its full
±70° clean solo, but at combined |J4|+|J5| extremes (any sign mix) the
link5 shell grazes the cradle ear / J4 case edge — face overlaps of a
few mm³, so the usable wrist envelope is clipped at the compound
corners. Fix would mean reshaping the cradle ear or moving the J5
servo → out of scope, documented per the stage rule.

### Servo-case clearance at home (nearest printed part, KD-tree)

| Servo | Nearest printed | Gap mm |
|---|---|---|
| vendor_sts3250_j1 | j1_cradle | 0.21 |
| vendor_sts3250_j4 | w_j4_cradle | 0.26 |
| vendor_sts3215_j5 | w_link4 | 0.18 |
| vendor_sts3215_j6 | w_link5 | 0.26 |
| vendor_sts3215_g | w_grip_frame | 0.24 |

All five vendor cases seat in their pockets with 0.18–0.26 mm minimum
clearance — tight by design (case-to-pocket fits), no interference.

### Bug found + fixed during this task (honest log)

First run's PoE composition moved each axis by the upstream transform
*and* post-multiplied the rotation — double-transformed axes on any
multi-joint pose (single-joint sweeps were correct). Symptom: phantom
collisions at poses a J3-relative pair could never reach. Fixed to
plain home-axis post-multiplication; a 3-pose FK agreement check
(< 1 mm) is now asserted in-script. Also: plug proxies switched from
an invented padded stub to the sourced `SV_PLUG` box dims, and the
intra-gripper moving/static pair set was added for the stroke sweep.

## Task 3 — MuJoCo + kinematics

### MuJoCo (`final2/mjcf/` — built by `build_mjcf_f2.py`, run by `run_mjcf_f2.py`)

- `nbody 10, njnt 8, nu 7` — J1–J6 hinges + finger_u/d slides coupled
  by an equality joint (one grip actuator), masses from measured
  meshes (grip body 0.099 kg vs gravity model 0.100 kg).
- TCP site at keyframe 0 = **[0.2338, 0, 0.1992]** — exact FK match.
  (Post-settle it reads [0.2332, 0, 0.1935]: −5.7 mm z = the gravity
  droop below, not a frame error.)
- HOLD at home: max joint error **0.0105 rad at J3** (sim stage's D4
  figure: 0.0108) — finite, settles.
- Per-joint sweeps: all 7 actuators reach **both** ctrl-range ends,
  err ≤ 0.0057 rad, finite throughout.

### robot-os checks (merged branch)

- `python3 -m pytest -q` → **66 passed, 0 failed** (12.3 s).
- `python3 -m soma_arm.cli --sim demo` → all 4 waypoints reached
  exactly, gripper stroke sensed ±0.98 rad.
- `wrist2/wrist2_checks.py` re-run on `arm-final2`: every D6 check
  passes; `CHECKS FAIL` only from the known J2 3.28 > 3.0 disc-cap
  line (upstream of the wrist, unchanged).

### IK reachability (2736-target grid, x −0.02..0.38, z 0.05..0.45, pitch −0.6..+0.6)

| | solves | note |
|---|---|---|
| D6 model (w3a=0.0844, w3z=−0.0170) | **752** | |
| D5-scalar model (w3z=0, for comparison) | 748 | |
| gained by D6 | 64 | boundary points, mainly high/low pitch |
| lost vs D5 model | **60 (2.2%)** | all at the workspace boundary |

The dropped TCP (17 mm below the J4 axis) rotates the achievable
pitch–position cone: boundary reshuffle, not a hole — 1924 targets are
unreachable under *both* models. Losses cluster at extreme pitch
(x≈0.05–0.11, z≈0.28–0.44, pitch ±0.6 / near-edge). No interior
singularities appeared; `demo` targets are unaffected.

## Task 4 — torque + payload (`final2/f2_torque_ik.py`, 2780 poses)

J2–J5 gravity torques vs caps (J2 3.0 / J3 2.0 / J4 1.12 / J5 0.70 N·m):

| Joint | Cap N·m | max τ @0.5 kg | verdict | max τ @0.25 kg | verdict |
|---|---|---|---|---|---|
| J2 | 3.00 | **3.341** | **FAIL +11%** | 2.381 | PASS |
| J3 | 2.00 | 1.863 | PASS | 1.210 | PASS |
| J4 | 1.12 | 0.836 | PASS | 0.496 | PASS |
| J5 | 0.70 | 0.565 | PASS | 0.320 | PASS |

Worst J2 pose q ≈ (−162°, −94°, −107°, +12°, +9°, −166°) — far-extended
out-of-plane reach. At the classic AB pose (arm level, J2+90/J3−90):
τ_J2 = 3.249 N·m @0.5 kg — same story as D6's 3.28.

Max payload vs level-tool reach (`final2/payload_vs_reach.png`):

| reach x m | max payload kg | limited by |
|---|---|---|
| 0.09–0.17 | 0.677–0.717 | J3/J4 |
| 0.19–0.27 | ~0.717 | J4 |
| 0.28–0.34 | 0.716→0.545 | J2 takes over |
| 0.35 | 0.491 | J2 |
| 0.36 | 0.459 | J2 |

Workspace-wide worst case (all 2780 poses incl. out-of-plane):
**0.411 kg** (J2). Classic full-reach AB pose: **0.433 kg**.
**Honest rating: 0.5 kg is achievable close-in (≲0.27 m level reach);
derate toward ~0.41–0.43 kg at full extension** — the stage's expected
"~0.5 close, ~0.38 full" behaviour confirmed; computed bounds are a
little kinder than the estimate. robot-os already refuses over-cap
targets (`test_torque_caps`).

## Render review (opened every PNG, honest log)

1. Opened `iso/front/side` — looked plausible, **but a shasum check
   showed all three were byte-identical to the F1 commit**: they were
   stale renders of the old arm2b wrist, never regenerated. Caught it
   before committing.
2. Wrist close-up needed three framings: vertex-crop (caught the
   forearm), re-crop (off-centre), fixed centre (165,0,200) + 170 mm
   span from D6 geometry — correct.
3. Regenerated all views from the current `_tmp` meshes and opened the
   final set:
   - `iso.png` — L-pose; cyclo drums, dogleg, K-KEEL wrist with the
     exposed servo stack + slim shells, grip rails; nothing floating.
   - `front.png` — end-on profile; drums, wrist cluster + rack teeth,
     base plate consistent.
   - `side.png` — L silhouette; J5 fin case over J6 keel case, slim
     grip rails and fingers at the end.
   - `closeup_wrist.png` — J4 flange, link4/5 shells, fin, grip frame
     + racks legible.

## Files changed on `arm-final2` (this stage)

- `final/export_assembly.py` — wrist2 part swap (Task 1).
- `final/out/assembly.stl`, `final/out/assembly.step.gz` — rebuilt.
- `final/renders/{iso,front,side}.png` regenerated for the D6 wrist;
  `final/renders/closeup_wrist.png` added.
- `final/SUMMARY.md`, `final/PRINT_LIST.md`, `final/BOM_FINAL.md` —
  F2 wrist swap, payload rating, print deltas (parts/masses only;
  no price changes — the BOM is vendor-identical).
- `final2/` added: this STATUS, `f2_collision.py`, `f2_mc_hist.py`,
  `f2_torque_ik.py`, `build_mjcf_f2.py`, `run_mjcf_f2.py`,
  `render_wrist.py`, `mjcf/{arm,scene}.xml`, `payload_vs_reach.png`.
- Generated scratch kept untracked: `cad/arm2b/out/` (rebuild),
  `final/renders/_tmp/`, `final2/mjcf/meshes/` (10 MB STLs),
  `final2/f2_collision_log.txt`.

## Mechanical findings (real, not merge regressions)

1. J1 yaw hard stop engages base_reinf below **−152.5°** (designed
   stop; free range −152.5..+180 vs ±180 software).
2. J2 base-plate contact at **+62.5..+70°** (D6 keel ~7.5° earlier
   than D5; moot — wrist is below the table there either way).
3. Compound wrist corner J4+70∧J5+70: cradle×link5 3.4 mm³ graze.
4. Deep-fold corners (J2+70∧J3+30, J2−120∧J3−180) drive the arm into
   the base or below the table — physically unreachable; planner
   keeps clearance anyway. J2+70∧J3+30∧J4+70 puts the J5 servo box
   inside the J1 servo box volume (36.5 cm³) — extreme fold only.
5. J2 torque cap binds payload: 0.5 kg OK close-in, ~0.41 kg at full
   extension (J2 disc cap — documented in D6, unchanged).

None of these can be fixed without moving servos or redesigning parts —
per the stage, reported instead. The D6 wrist itself adds no new
in-reach collisions vs the D5 shell it replaces.

## [U] unverified

- PETG-CF cross-layer strength 25 MPa; 0.6 printed/solid mass factor.
- STS3215 rated 0.98 N·m [U]; real-wire cable bend radii.
- Kt 0.0289, η 0.7, 7 pole pairs — J2/J3 cap currents.
- Plug proxies are sourced dims; real connector+wire sweep [U].
- MuJoCo contact off (`contype 0`) — dynamic self-collision relies on
  the Task-2 mesh sim, not the physics model.

## Open questions

- Should the J1 software limit be pulled to −150° to sit inside the
  hard stop? (stop contact is designed, but homing into it at speed is
  worth avoiding — firmware decision, not geometry.)
- The wrist-fully-flexed 3.4 mm³ graze: leave (extreme corner only)
  or thin the cradle ear? D6 already bounded J5 to ±70 for this class.
- Torque cap vs 0.5 kg rating: keep the 0.5 kg nominal payload with
  pose-dependent refusal (current behaviour) or re-rate the arm?

## Gate lines

- `export_assembly.py` → `parts 72` / `assembly.stl 10.6 MB` /
  `assembly.step 34.1 MB  175 solids` / `DONE` (the concatenated STL
  reads `is_watertight False` — it is a render/collision soup of 72
  disjoint solids; the STEP carries the real B-rep)
- `f2_collision.py` → `HOME … PASS`; per-joint `SWEEP` rows
  (J1/J2 fail at the documented mechanical limits; J3–J6+gripper PASS);
  named poses 5/6 PASS (wrist-fully-flexed graze); `MC … 2457
  undeclared collisions` (uniform-random space, families above);
  `CHECKS FAIL` — the FAIL entries are all documented mechanical
  limits / extreme-fold poses, not merge defects.
- `run_mjcf_f2.py` → `nbody 10 njnt 8 nu 7`; `tcp site @keyframe0
  [0.2338, 0.0, 0.1992]`; `HOLD max joint error 0.0105 rad`; all
  `SWEEP … reached … err <0.006 finite True`; `SWEEP PASS`.
- `python3 -m pytest -q` (software/robot-os) → `66 passed`.
- `python3 -m soma_arm.cli --sim demo` → 4/4 targets reached.
- `wrist2_checks.py` → all D6 checks PASS; `CHECKS FAIL` on the known
  J2 3.28 N·m > 3.0 disc-cap line only.
- `f2_torque_ik.py` → J2 `FAIL 11% over` at 0.5 kg (all else PASS);
  payload-vs-reach table + `WROTE final2/payload_vs_reach.png`.
