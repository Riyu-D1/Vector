# REFINE-LOG — D-series wrist/gripper structural refinement (R1/R2)

Branch: `arm-refine` (worktree `Vector-wt/refine`), based on `arm-toolchg-print` @ 287bb87.
Scope: fix the documented F9 gripper payload limitation in `w_grip_frame` /
`tool_grip`; audit the same defect family across the D6 wrist parts.
All changes live under `refine/`; product files, `main`, and the
tool-changer print pack are untouched. No parts ordered, no physical test.

## 1. Confirmed faults (ranked)

### F9a — Missing mirrored cheek (root cause of F9) — CONFIRMED, FIXED
All four D6 keel-cage generators loop `sg in (1,-1)` with
`poly_ah(sg * CHEEK_B[0], ...)` then extrude the profile +b to the sorted
bounds.  For `sg=-1` the profile face sits on the INNER plane and grows
INTO the servo pocket, which then removes it entirely.
Result (stock builds):

| part            | solids | −b cheek | detached islands            |
|-----------------|--------|----------|-----------------------------|
| w_grip_frame    | 3      | none     | horn plate + 2 slivers      |
| w_link5         | 4      | none     | plate + cleat + slivers     |
| w_link4         | 5      | none     | horn plate + slivers        |
| tool_grip       | 3      | none     | 2 slivers                   |

Single-sided cages concentrate the whole payload wrench in the +b cheek
and the 2 mm keel web — the F9 hotspot (110,±12.5,−52).

### F9b — J6 horn plate knife-edge weld — CONFIRMED, FIXED
`w_grip_frame`: measured volumetric weld between the J6 horn plate and
the cage was **0.32 mm3** (effectively zero — a point contact).  The whole
wrist + payload hangs off that plate through the four M3 horn screws only.
`tool_grip`'s neck→cage junction is the same class of defect.

### F9c — Tangent cheek/web butt faces — CONFIRMED, FIXED
`w_grip_frame` and `w_link5`: cheek bottom edge at h=−52.4 sits exactly on
the keel web top face at −52.4 → measured overlap **0.00 mm3**.
`w_link4`: fin cheek penetrates the fin bottom web only ~0.05 mm
(web↔cheek 9.85 mm3, tailwall↔cheek 5.85 mm3).

### F9d — w_link4 strut self-intersection — CONFIRMED, FIXED
`L4_STRUT` polygon crosses itself at a≈8.8 and again at a≈21 → the rib
builds as disconnected fragments; the J4 horn plate (carries the whole
wrist) is a detached island in stock AND in the first-pass cheek fix.

### F9e — window-2 wedge slivers — CONFIRMED, FIXED
`GF_CAGE` outline dips through the window band at a≈104; the win2 top edge
pinches off a floating ~1.5 mm wedge (stock +b sliver 33.8 mm3, mirrored
after cheek fix 10.8→46.5 mm3).

### Known whole-arm limit (unchanged, previously documented)
J2 torque 3.29 N·m > 3.0 printed-disc cap at the 0.5 kg close-in envelope
check (wrist mass ~unchanged: 0.229 vs 0.234 kg budget).  Not a
regression; the achievable safe payload stays ≈0.41 kg at full reach.

## 2. Fixes implemented (refine/ap7.py + p_wrist7.py + p_toolchg7.py)

R1  Mirrored-cheek fix — profile placed on the lower b-bound and extruded
    to the upper bound (same pattern D5 used).  Applied to `w_link4`
    (`L4_CHEEK_B`), `w_link5` (`L5_CHEEK_B`), `w_grip_frame` (`GF_CHEEK_B`),
    `tool_grip` (same cage, shifted).
R2a `GF_CAGE` back edge 68.8→67.0, −26→−8.5: cheek now overlaps the horn
    plate side bands (~94 mm3 weld) and the back wall (191 mm3).
R2b Cheek bottom edges −52.4→−54.0 (`L5_CAGE`, `GF_CAGE`): cheeks sink
    1.6 mm into the keel webs (321 / 246 mm3 weld per part).
R2c `L4_FIN` bottom −0.1→−1.0: fin cheek sinks ~0.9 mm into the fin web.
R2d `L4_STRUT` re-profiled to a clean 6-pt tapered rib (same envelope
    a5..40 × h−13..38.2 × b−30.65..−26.65): plate↔strut↔ribs↔−b cheek
    chain is now continuous.
R2e `GF_CAGE` front-top corner (115.5,−22)/(104,−14) → −12 flat and win2
    lowered (top −16): eliminates the wedge sliver; rolled radius of the
    new corner ≈16 mm about the J6 axis — clears all statics (a≤64.7).
R2f `w_grip_frame`: side bosses a 66..69 x b +-13.5..14.91 x h −26.5..−8.5
    wrap the J6 horn plate's outer b edge — a second perpendicular weld
    face for the cheek↔plate junction.  a>=66 keeps the J6 roll sweep
    clear of the j5 vendor case (verified: J6 free +-180 deg).

Interfaces unchanged: horn PCD/hole positions, cheek b-band (12.51..14.91),
rack bracket, channels, cleats, windows (except win2 top −2 mm), pocket
volumes, `tool_grip` catch/floor/spigot geometry, J4 bolt pattern.

## 3. Verification results

### Geometry (build123d 0.13.0, cradlefix venv)
    stock:  w_grip_frame 3 solids 16.15 cm3 | w_link5 4/6.48 | w_link4 5/11.42 | tool_grip 3/23.52
    fixed:  w_grip_frame 1 solid  17.51 cm3 | w_link5 1/7.54 | w_link4 1/15.04 | tool_grip 1/24.66
    weld volumes: GF plate↔cheeks 0.32->93.9 | web↔cheeks 0->246.4 | backwall↔cheeks 191.0
                  L5 web↔cheeks 0->321.2 | L4 -b cheek↔ribs 266.3 mm3

### Check suite (refine/wrist7_checks.py, stock thresholds)
    REACH/HOLE/CLEAR/GRIP: all PASS (horn holes err 0.000)
    MASS 0.229 kg <= 0.234 PASS; TORQUE J4 0.830/J5 0.604/J3 1.78 PASS; J2 3.29 FAIL (documented limit)
    STRESS J4 strut hand-check: S=67 mm3 -> 11.9 MPa, SF 2.1 PASS
    WALL probes all PASS; CABLE channels all PASS; OVERHANG all PASS
    ROM: home clear; J4 175 deg, J5 140 deg, J6 360 deg, J3 215 deg, J2 185 deg — all >= required

### FEA (gmsh C3D10 cl=1.5, CalculiX 2.23, E=4000 nu=0.35, rho 7.62e-10)
Case `tool_grip` (D11 verbatim): NFIX catch faces+floor, NLOAD a>=120,
F=(0,0,-5.7) N at TCP (149.4,0,-17):
    stock_tool_grip:  filtered maxVM 28.73 MPa @(110,12.5,-52)  SF 0.87
                      [reproduces the D11 F9 figure exactly]
                      mechanism: ref-node |U| = 2.3e7 mm (detached islands fly free)
    fix_tool_grip:    filtered maxVM  8.08 MPa @(109.4,+-13.2,-12)  SF 3.10
                      max|U| 0.159 mm; TCP ref-node |U| 0.009 mm
Case `grip_frame` (new, [U] horn-face fixity approximated a<=63):
    stock_w_grip_frame: mechanism — raw maxVM 792 MPa (singular-solve garbage),
                      max|U| 5.1e7 mm; the horn-clamp BC exposes the broken
                      load path more severely than the catch-clamp case did.
    fix_w_grip_frame: filtered maxVM 14.13 MPa @(67.3,+-12.5,-25.1)  SF 1.77
                      max|U| 0.413 mm.
                      Linear scaling vs the stated envelope: SF 2.7 at the
                      0.38 kg full-reach load (3.7 N), SF 2.1 at a 0.5 kg
                      full-reach-equivalent wrench (4.9 N).  The residual
                      hotspot is the cheek↔plate weld-root concentration;
                      the real printed part is continuous material there
                      (no weld interface), so the FEA notch is pessimistic.

## 4b. Solver/model caveats
- Stock-model metrics are corrupted by detached islands (free DOFs fly to
  ~1e7-5e7 mm); the 28.73 MPa F9 figure is real near the NFIX-bonded region
  but whole-part displacement metrics on stock are meaningless.
- `filtered` VM excludes elements sharing nodes with NFIX/NLOAD patches
  (project convention).  The 14.13 MPa weld-root value IS adjacent to the
  NFIX patch (a<=63) in runs where the side boss touched the clamp face —
  treat filtered-vs-raw differences there as convention, not new physics.

## 4. Remaining risks / [U]
- PETG-CF cross-layer allowable 25 MPa is unverified [U] (project assumption).
- `grip_frame` case treats the screwed horn flange as full-face fixity —
  optimistic vs screw-only clamp; label [U].
- FEA is linear-static, isotropic; print anisotropy and weld-line strength
  not modelled. Solver limitation: constrained/patch nodes excluded from
  filtered hotspot ranking (same convention as D11).
- Ref-node/TCP displacement in stock models is corrupted by detached
  slivers (free DOFs fly); fixed-model ref-node |U| is the meaningful one.
- Cable routing verified by channel probes only — physical routing/bend
  check is a build-stage test.

## 5. Required build-stage tests
- Print fit check: horn plates to horns (screw stack), cheek cage over
  servo cases (plug clearance), rack/finger free travel over full stroke.
- Payload test to 0.38 kg at full horizontal reach, dwell + creep check
  at the keel welds (cheek/web interface, J6 plate).
- J2 disc torque re-check if the envelope is pushed past 0.41 kg.
