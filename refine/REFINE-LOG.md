# REFINE-LOG — D-series wrist/gripper structural refinement (R1/R2/R3)

Branch: `arm-refine` (worktree `Vector-wt/refine`), based on `arm-toolchg-print` @ 287bb87.
Scope: fix the documented F9 gripper payload limitation in `w_grip_frame` /
`tool_grip`; audit the same defect family across the D6 wrist parts.
All changes live under `refine/`; product files, `main`, and the
tool-changer print pack are untouched. No parts ordered, no physical test.

**Status (R3 pass, this commit):** geometry R1/R2 as logged below PLUS the
R3 horn-mount investigation — realistic screw/horn FEA found the w_link4
J4 horn-mount load path was soft and notched (fixed: widened strut,
10x stiffer, ~93->15 MPa); PETG-CF allowables are now source-backed
(25 MPa in-layer / 12.5 MPa cross-layer); assembled-load sweep bounds the
payload envelope (0.38 kg anywhere unsprung; 0.5 kg only in the documented
close-in/forward envelope with the J2 spring). NOT hardware-verified — see
sections 6-9.

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

---

# R3 PASS — horn-mount realism, material basis, assembled loads (2026-11-07)

## 6. Material allowables — sourced (replaces the [U] 25 MPa "cross-layer")

The prior label "25 MPa cross-layer" was wrong: 25 MPa is the repo's
**in-layer** design allowable; the **cross-layer** (through-layer / Z)
allowable is **12.5 MPa** (`order/STRESS_SANITY.md`, 2026-11-01, same
convention). Sources (accessed 2026-11-07):

| source | values used | URL |
|---|---|---|
| Bambu PETG-CF TDS via official filament guide (rev 250123) | tensile 35 MPa XY / **29 MPa Z** (ISO 527 printed 100% infill); E 2460/1340; Tg 68 C; Charpy-Z 10.7 kJ/m2 | https://cdn1.bambulab.com/filament/filament-guide/250123/filament-guide-en.pdf |
| Bambu store guidance | open-frame printing + overcooling WEAKEN Z adhesion (A1 is open-frame) | https://uk.store.bambulab.com/products/petg-cf |
| Li et al., J. Mater. Sci. (ORNL), Jul 2023 | printed CF-PETG composites: creep service time in Z ~175x lower than X at 60 C for the same creep strain; inter-layer adhesion is the weak axis | https://doi.org/10.1007/s10853-023-08709-8 |

Derivation (cross-layer): 29 MPa Z tensile x ~0.43 = **12.5 MPa** allowable —
covers TDS-specimen vs real-part gap (100% infill, lab cooling vs open-frame
A1), print scatter (+-4 MPa band), long-term creep on the weak axis (ORNL),
and residual uncertainty. In-layer: 35 MPa x ~0.71 = **25 MPa**.
Datasheet strength is a short-term lab value; these are DESIGN allowables,
not measured on this part — physical validation still required (section 9).

Layer-orientation audit (print up-directions from the overhang probes):
w_grip_frame up=h, w_link5 up=a, w_link4/w_j4_cradle up=b.

## 7. R3 horn-mount FEA — realistic screw/horn load path

`fea/msh2_r3.py` replaces the [U] full-face horn fixity with bounded BC
models per part (face / horn annulus+pilot / 4xM3 shank band / shank+pilot /
screws+annulus+pilot / 2-screw fault bound). Loads: ~0.5 kg-class wrench
(payload + carried stack, moment-matched at each servo pocket floor,
stated in the deck headers). gmsh C3D10, ccx, E=4000 nu=0.35, isotropic
linear-static — does NOT model print anisotropy or weld lines.

Results (cl=1.5, filtered VM, wrench class ~0.5 kg):

| part | BC-insensitive | max filtered VM | layer split at hotspot | max\|U\| |
|---|---|---|---|---|
| w_grip_frame | yes (12.4-13.0 all 6 BCs) | 13.0 MPa | sig_n(z) **-12.0 COMPRESSION**, in-layer 5.3 | 0.45 mm |
| w_link5 (old geom) | magnitude varies | 31.2 (scrann) / 38.3 (scr2) | sig_n ~0, **in-layer 25-30** | 0.72 mm |
| w_link4 (old geom) | magnitude varies | **92.9 (scrann) / 93.3 (scr2)** | sig_n +13, **in-layer ~96** | **6.33 mm** |
| w_link4 R3-fixed | yes (~14.9 all BCs) | 14.9 MPa | sig_n(y) +15.0 tension (tail T-notch) | **0.63 mm** |

Mesh convergence (scrann case, cl 3.0 / 1.5 / 0.8):
- gf: 9.2 / 12.9 / 16.9 MPa — still rising = junction notch, but the stress
  is layer-normal COMPRESSION (does not drive delamination); U converged
  (0.44/0.45/0.45 mm). PASS.
- l5: 29.7 / 31.2 / 46.6 MPa — notch-dominated, not converged. U converged
  (0.69/0.70/0.72 mm). Conditional feature, see section 8.
- l4 old: 80.0 / 92.9 / 104.5 MPa — not converged (sharp re-entrant notch
  where the strut exits the horn plate edge); U converged (6.18/6.33/6.39
  mm) — the **converged deflection is the robust finding**: the R1/R2
  strut was the ONLY horn->fin load path (single 4 mm wall at -b),
  J4-axis compliance ~5.5 deg under the wrench. JOINT FAIL.
- l4 R3: see fix below; converged 0.63 mm, ~15 MPa BC-insensitive.

Singularities excluded: elements sharing nodes with the NFIX/NLOAD patches
(project convention) — reported alongside raw values. The junction hotspots
themselves are REAL sharp re-entrant CAD corners (no fillet), i.e. physical
notches whose numerical peak is mesh-dependent — quoted as indications, not
converged strengths.

### R3 geometry fix — w_link4 strut (ap7.py L4_STRUT / L4_STRUT_B)
- Plate-edge weld h -4..+4 -> **-11..+13** (exits moved into the plate's
  r5 corner-radius region, opening the notch angle).
- Rib widened b -30.65..-26.65 -> **-30.65..-22.65** (8 mm; 2.65 mm clear
  of the cradle -b end at -20; b-separated from the J4 case +-12.36).
- Result: 1 solid, 17.1 cm3 (was 15.0); mass 0.231 kg wrist (<= 0.234 PASS).
- FEA: |U| 6.33 -> **0.63 mm** (10x stiffer); VM ~93 -> **14.9 MPa** and
  now insensitive to which horn BC is modelled (face/scrann/scr2 agree) —
  the horn mount is no longer the weak link. Hand check: min strut
  S=101 mm3 -> 7.9 MPa, SF 3.1 PASS.

## 8. Assembled loads — `refine/asm_loads.py` (includes self-weight)

FK-exact per-joint gravity torques (upgrade1 gravity model: real masses &
centroids incl. 0.231 kg refined wrist) over **29,653 poses** (27,648
pitch-grid + 2,000 MC + 5 named), linear payload interpolation, J2 spring
ON/OFF. Caps = firmware torque caps (J2 3.0 / J3 2.0 / J4 1.12 / J5 0.70 /
J6 0.70 N.m); caps are protections, not structural proof. Actual output in
`refine/checks/asm_loads_out.txt`.

UNSPRUNG (no spring credit):
- 0.25 kg: worst J2 2.50 J3 1.26 J4 0.49 J5 0.31 — all under caps. PASS.
- 0.38 kg: worst J2 3.00 J3 1.60 J4 0.66 J5 0.44 — at J2 cap. PASS (bound).
- 0.50 kg: worst J2 **3.46 OVER** at q deg [0,-90,-114,20,0,0] (backward
  flop, spring cannot engage at q2<0); J3 1.91 J4 0.825 J5 0.56 OK.
- Workspace-wide bound: **0.380 kg** (J2-limited).
- Close-in (Q_CLOSE +30/-150/+90): bound **0.788 kg** (J4-limited) —
  0.5 kg close-in is FINE (J2 only 1.46 there). The prior "0.5 kg close-in
  exceeds the J2 cap" was a REACH case mislabeled close-in: at AB-level /
  arm-horizontal the check reads J2 3.29-3.35 > 3.0 — correct and kept.
- Level-tool reach table: 0.5 kg OK to ~0.30-0.34 m; bound 0.432 @ 0.36 m.

SPRUNG (J2 spring k=0.55 N.m/rad, q2>0, vendor_spring_j2 in BOM):
- Forward poses (q2>0): spring relieves ~0.6-0.86 -> forward-horizontal
  J2 net ~2.4-2.5 -> bound improves to J3-limited ~0.58 kg.
- Backward flop (q2<0): NO assist -> workspace bound stays 0.380 kg.

Reconciliation of prior claims (same model, heavier refined wrist):
- final2 "0.41 kg workspace" -> 0.380 (wrist +0.06 kg, caps accounting).
- "0.46 kg close-in / 0.36 m level" -> 0.432-0.465 consistent.
- upgrade1 "0.501 kg @ Q_WORST" was J3-limited under servo deratings;
  under printed-disc caps it is 0.430 (J2) unsprung at that pose.

**Defensible payload rating (statics, paper):**
- **0.25 kg: anywhere in the workspace — passes all caps unsprung.**
- **0.38 kg: anywhere in the workspace — at the J2 cap, worst-case bound.**
- **0.5 kg: close-in envelope (level reach <= ~0.30 m) unsprung; forward
  poses (q2>0) incl. horizontal reach WITH the J2 spring [U bench-cal].
  NOT achievable in the backward-flop region at any spring state.**
- J2 disc SF vs cyclo4 bounds (3.65/3.64 N.m at SF2 nominal): at cap 3.0
  nominal SF ~2.4; at the 0.5 kg unsprung worst 3.46 nominal SF ~2.1 —
  the cap exists to keep tolerance-scatter margin, not to meet SF2 exactly.
- Recommendation (not implemented, product code): restrict under-payload
  J2 travel to q2>=0 via the existing torque_ok gate; then the sprung
  bound ~0.58 kg governs the forward workspace.

## 8b. Main links / joint mounts / bearing supports — evidence audit

This pass focused on the wrist; the rest of the arm is covered by prior
stage evidence (read, not re-run):
- cyclo4: J2/J3 printed-disc pin contact, Hertz solver — p0 33-38 MPa,
  equiv 20-23 vs 50 bearing allowable -> SF 2.21/2.56 at design torque;
  SF-2 bounds J2 3.65 / J3 3.64 N.m nominal (tol scatter SF ~1.0-2.2).
  Caps J2 3.0 / J3 2.0 chosen for enforcement margin.
- cad3: housing + bolt-hole FEA ran (pipeline cad3/fea/); 6803 bearing
  cavity in back_spacer; J2/J3 joint hand checks incl. single-bolt worst
  case (needs >=2 pilots engaged — build torque check).
- lighten: every lightened main-link variant FAILED the SF>=2 +
  deflection-growth gate -> 0.0 g adopted. The main links are already at
  their evidenced safe mass — no further lightening is justified.
- final2: full-assembly collision/ROM gates PASS (with documented
  collision-family exceptions unchanged by this pass).
- order/STRESS_SANITY.md: housing->base bolts, out-flange M3+dowel and
  ring-pin conformal-contact hand checks; actions carried to the
  build-stage list (torque all 6 pilots evenly; dowels are load-carrying).

No evidence-backed stiffness/weight change is available for the main
links beyond what stages D2-D13 already applied — the new finding this
pass is on the wrist side (w_link4 J4 mount, section 7), now fixed.

## 9. Remaining risks + build-stage tests (updated)

Still [U] / unverified:
- PETG-CF allowables are TDS-derived design values, not measured on this
  part/printer; ORNL creep data is at elevated T (60-80 C) — room-T creep
  derate is embedded in the 0.43 factor, not separately measured.
- w_link5 plate/cage junction: in-layer ~25-30 MPa at the 0.5 kg wrench
  (notch, mesh-dependent; 46.6 at cl=0.8 still rising). Cannot be filleted
  inside (J6 case pocket is 0.15 mm away). ~~Conditional limit + epoxy/CA
  fillet recommendation~~ — FIXED IN R4 (section 10/11): widened plate,
  buried cheek flat, external longerons -> filtered 9.27 MPa in-layer at
  the 0.5 kg wrench, SF ~2.7. Residual ring-edge sigma_n bounded ~1.5 SF,
  see R1 in section 11.
- w_link4 fin-tailwall top corner: sig_n +15.0 MPa layer-normal TENSION vs
  12.5 allowable at the 0.5 kg wrench (same T-notch class, unloaded tail;
  ~7.5 MPa at 0.25 kg). ~~Epoxy-fillet recommendation~~ — FIXED IN R4:
  the 0.13 mm membrane is deleted; an external lap collar carries the
  tail (tail-region sigma_n +3.2 max, SF ~3.9).
- J2 spring torque curve unverified (bench cal required); sprung payload
  numbers are conditional on it.
- FEA: linear-static isotropic; no anisotropy/weld-line/contact; RB load
  patches spread load (patch stress is a lower bound on local bearing).
- Solver: ccx 2.23 small-strain; singular re-entrant corners reported as
  indications only.
- tool_grip part: inherits the gf cage fix; prior fixed-model FEA stands
  (filtered 8.08 MPa, SF 3.1, |U| 0.159 mm).

Build-stage tests (required before the rating above is claimed on hardware):
1. Horn screw-stack fit: all four horn plates to horns; torque evenly;
   confirm >=2 pilots/screws bite per order/STRESS_SANITY.
2. w_link4 J4 mount droop test: arm-horizontal, 0.38 kg, measure fin-tip
   sag vs the 0.63 mm model prediction (large deviation -> investigate).
3. Payload dwell: 0.38 kg full horizontal reach 24 h; creep marks at the
   cheek/web welds, J6 plate, l5 plate junction, l4 tailwall.
4. J2 spring bench calibration: measure assist torque vs q2; re-run
   asm_loads.py with the measured curve before claiming the sprung 0.5 kg
   forward-envelope rating.
5. Cycloidal run-in + pin/disc inspection per cyclo4 protocol; re-torque
   after 10 h.
6. Torque-cap verification: robot-os refuses over-cap waypoints in both
   directions of J2 (incl. backward flop q2<0).
7. Cable bend/fit physical check at J4/J5/J6/g; re-verify the J6 sublimit
   behaviour when J5<0.
8. ~~Epoxy fillets on the l5 plate-cheek and l4 tailwall T-junctions~~ —
   SUPERSEDED by R4: both junctions are now printable geometry (section
   10+); no adhesive reinforcement is part of the accepted design.

---

# R4 PASS — printable-geometry repair of the two R3 open junctions (2026-11-07)

R3 left two wrist junctions relying on a recommended epoxy/CA fillet:
the w_link5 plate↔cheek T-junction (31.2 -> 46.6 MPa, rising with mesh)
and the w_link4 fin↔tailwall corner (+15.0 MPa layer-NORMAL tension vs
the 12.5 MPa assumed cross-layer allowable).  R4 replaces both with
printed geometry; no adhesive is load-carrying in the accepted design.

## 10. R4 root causes + geometry changes

Probed the built solids at the R3 hotspot coordinates:

- w_link5 (36.2, +-12.5, -6.2): the cheek band (b 12.51..14.91) met the
  plate over only ~1 mm in b (plate edge +-13.5) with a ~0.25 mm ligament
  under the pocket roof - a ~1 mm-wide T-junction with a re-entrant
  inside corner.  The J6 pocket wall sits flush at b=12.51, so NO
  internal fillet could ever fit there; the fix had to be external.
- w_link4 (65.9, -11.8, 24.0): the tailwall survived the J5 pocket cut
  only as a ~0.13 mm membrane at a 65.87..66.0 - a b-normal butt T-notch
  at its top corner.  Anything between the cheeks at a<65.87 is pocketed
  away, so the membrane could not be thickened either.

w_link5 (print up-direction = a; changes in ap7.py L5_* / p_wrist7.py):
- Plate widened b +-13.5 -> +-16.41 (full cheek width + a 1.5 mm ledge
  per side) and extended a 37.6 -> 41.5.
- Cheek top edge runs flat at h=-3.0 for a 28..40 (0.85 mm below the
  plate top): the cheek welds into the plate over an ~11 x 2.4 mm
  volumetric band per side (~5x the old footprint), and every polygon
  vertex in the weld zone is buried in plate material.
- External longeron ribs (L5_GUSSET trapezoid a 28..46 x h -3..-13,
  b band 12.3..16.41) merge into the cheek outer faces AND the plate
  ledges - a second, external load path: plate -> ledge -> longeron ->
  cheek outer face, capping the cheek edge where it exits the plate.
- Front relief cuts widened to |b| 10..17 so the cradle-sweep clearance
  is unchanged by the wider plate.
- Iteration note: the first R4 mesh pass caught the flat's exposed end
  vertex at (40,+-12.5,-2.15) reading +19..+24 MPa layer-normal (a)
  tension (weld-end + vertex notch, converged ~22).  v2 lowers the flat
  to -3.0 under the plate and buries that vertex; all numbers below are
  the v2 solids.

w_link4 (print up-direction = b):
- L4_TAILWALL deleted - it could only ever build as the 0.13 mm membrane.
- External tail COLLAR: two side plates (L4_COLSIDE) lapping the cheek
  outer faces through their full thickness, plus a back plate
  (L4_COLBACK a 66.0..66.7, b +-16.41, h 4..27) closing the tail and
  tying both cheek tips.  Lap/shear transfer replaces the b-normal butt;
  no b-normal T-junction remains on the cheek inner faces.
- Mid rib enlarged and reshaped (a,h) box (16,32,12,17.8) -> tapered
  polygon L4_RIBMID reaching a~4 in the plate's interior: buries the
  strut silhouette's (14,12) vertex and the old rib weld-end (~26,11)
  and moves the rib's own -a end off the plate-face edge zone (the
  square end still read ~12.4 MPa in-layer at cl0.8 - the tapered tip
  sits in the low-stress plate interior).

Interfaces unchanged: horn PCD/holes, servo pockets, cheek b bands,
cable channels, ROM stops, rack/finger geometry, J5-yaw gap >=0.75 mm,
roll-tube clearance a>61.  Printability unchanged: all features are
a-h or b-plate profiles in the same build orientations; overhang scan
all PASS (Bambu A1, PETG-CF).

## 11. R4 FEA - before/after (fea/run_r4fea.py; same deck convention as R3)

Rebuilt decks on the R4 solids: 6 horn BCs (face / ann+pilot / screws /
screw+pilot / screws+ann+pilot / 2-screw fault bound), payload-scaled
wrenches _p25/_p38/_p50 (payload force + fixed carried stack ~0.11/0.20/
0.23 kg, moment-matched at the pocket floor), mesh convergence at cl
3.0/1.5/0.8, self-weight included via deck density.  Analyzer reports
raw max, filtered (excludes patch-adjacent), patch-region max, |U|,
layer-normal sigma_n, in-layer VM.  Actual outputs: fea/*_r4.txt.

w_link5 (layer axis = a):

| BC case | filtered VM | sigma_n(a) | in-layer VM | max|U| |
|---|---|---|---|---|
| face    | 5.51  | +5.0        | 1.8   | 0.17 mm |
| ann     | 9.40  | +0.2        | 9.4   | 0.35 mm |
| screw   | 13.10 | +9.1        | 10.1  | 0.41 mm |
| scpilot | 13.07 | +9.1        | 10.1  | 0.41 mm |
| scrann  | 9.27  | +0.2        | 9.2   | 0.34 mm |
| scr2    | 18.64 | -19.9 compr | 12.9  | 0.63 mm |

scrann payload sweep (filtered): 0.25 kg -> 5.96 | 0.38 kg -> 7.69 |
0.50 kg -> 9.27 MPa.  scrann convergence: 8.41 / 9.27 / 11.33 MPa at
cl 3.0/1.5/0.8 - saturating, not a runaway notch.

w_link4 (layer axis = b):

| BC case | filtered VM | sigma_n(b) | in-layer VM | max|U| |
|---|---|---|---|---|
| face    | 6.40 (tail collar zone, sigma_n +3.25) | | 0.21 mm |
| ann     | 8.11  | -0.8        | 8.4   | 0.37 mm |
| screw   | 8.12  | -0.8        | 8.4   | 0.39 mm |
| scpilot | 8.12  | -0.8        | 8.4   | 0.38 mm |
| scrann  | 8.11  | -0.8        | 8.4   | 0.36 mm |
| scr2    | 8.13  | -0.8        | 8.5   | 0.46 mm |

scrann payload sweep (filtered): 0.25 kg -> 5.34 | 0.38 kg -> 6.78 |
0.50 kg -> 8.11 MPa.  scrann convergence: 6.25 / 8.11 / 9.98 MPa at
cl 3.0/1.5/0.8 - saturating (deltas +1.9,+1.9, bounded ~11-12); the
cl0.8 peak sits on the fin cheek face (in-layer 10.3), NOT on a weld
line - the junction features are no longer the controlling corners.

Before -> after at the two R3 open junctions (design BC = scrann,
0.5 kg-equivalent wrench):

| junction | R3 result | R4 result | margin |
|---|---|---|---|
| l5 plate-cheek (36.2,+-12.5,-6.2) | 31.2 MPa VM cl1.5 (in-layer 25.3); 46.6 at cl0.8 still rising | filtered 9.27, in-layer 9.2, sigma_n +0.2 | in-layer SF ~2.7 vs 25 MPa |
| l4 fin-tailwall (65.9,-11.8,24.0) | sigma_n(b) +14.98 tension | collar lap path: tail-region sigma_n +3.25 max | cross-layer SF ~3.8 vs 12.5 MPa |

Safety-factor accounting (design allowables from section 6 - NOT
datasheet strength): in-layer SF2 needs filtered in-layer <= 12.5 MPa;
cross-layer SF2 needs tensile sigma_n <= 6.25 MPa at the worst node.
- w_link5: in-layer max ~9.4-10.1 (all BCs except the scr2 fault bound)
  -> SF ~2.5-2.7 PASS.  sigma_n <= ~9 MPa -> see residual R1 below.
- w_link4: in-layer max ~8.4-10.5 (all BCs, incl. cl0.8) -> SF ~2.4-3.0
  PASS.  sigma_n <= +3.3 tensile -> cross-layer SF ~3.8 PASS.
- No double-counted deratings: allowables 25/12.5 are the design values;
  SF is quoted against them directly.  Datasheet 35/29 MPa would give
  higher nominal margins but is a lab-specimen value, not part
  validation (section 9 [U] stands).

Residuals + honest bounds:
- R1 (l5): the worst layer-normal reading is at the rigid annulus BC
  boundary (r~10 about the horn, plate top fibre): sigma_n(a) +8.4 MPa
  at the 0.5 kg wrench (cl0.8), ~+5-6 at 0.38, ~+4 at 0.25.  This is
  plate bending tension at the idealised clamp edge - a real horn's
  compliant flange spreads it - but treating it as real: cross-layer SF
  ~1.5 at 0.5 kg-equivalent, >=2 below ~0.30 kg-equivalent.  Mitigation
  is a build setting (solid infill + full perimeters in the plate band
  lifts local inter-layer strength well above the generic 12.5 MPa
  assumption) + droop test 2 below.  Disclosed, not silently passed.
- R2 (l5): scr2 2-screw fault bound reads filtered 18.6 / in-layer 12.9
  / sigma_n -19.9 (bearing COMPRESSION at the surviving screw pair) -
  fault bound only, disclosed.
- R3 (both): patch-region maxima sit inside the constraint/load sets by
  construction; raw vs filtered deltas are convention, not new physics.
- |U|: l5 0.34 mm, l4 0.36 mm at the 0.5 kg wrench (converged) - stiffer
  than R3 (0.70 / 0.63); the max-|U| nodes are the cage tip / collar top
  corner, not the junctions.

## 12. Mass + assembled loads after R4

R4 volumes: w_link4 19.8 cm3 (was 17.1), w_link5 8.6 cm3 (was 7.54).
Measured mass at the project convention (rho x 0.6): wrist+gripper
0.234 kg (gate 0.234 PASS, ~1 g margin).  gravity_up1.py wrist plastic
masses updated to the measured values (wrist4 22.7->28.1 g, wrist5
8.5->6.6 g, grip 15.9->13.4 g); centroids unchanged (D6 parts_AB,
sub-mm drift, <0.005 N.m effect).  asm_loads.py re-run on the new
masses - checks/asm_loads_out.txt:

- Unsprung: 0.25 kg all joints OK; 0.38 kg J2 3.00 fractionally OVER
  the 3.0 cap (+0.2 g on the wrist4 mass tipped it); 0.50 kg J2 3.46
  OVER (backward flop); workspace-wide bound 0.380 kg
  (J2-limited) - identical to R3 within report precision.
- Named poses: Q_WORST 0.430 unsprung / 0.581 sprung (J3); close-in
  0.790 (J4); AB-level 0.406 unsprung / 0.581 sprung; stow 0.587/0.740.
- Level-tool reach table: 0.5 kg OK to ~0.30-0.34 m; 0.432 at 0.36 m.
- The wrist structural results above are INDEPENDENT of these caps:
  torque-cap compliance is not structural proof, and vice versa.

## 13. R4 status of the [U] items + build-stage tests

- Epoxy/CA fillet reliance: REMOVED from the accepted design (was test
  #8 and the two section-9 bullets).  Both junctions now carry load
  through printed lap/shear geometry, verified by the decks above.
- Still [U]: PETG-CF allowables are TDS-derived design values (not
  measured on this part/printer); the residual R1 ring-edge sigma_n is
  a model-boundary reading bounded at ~1.5 SF - the honest claim is
  "junction fixed; ring-edge residual bounded and mitigated by print
  density, pending the droop test".
- J2 spring torque curve still unverified -> all spring-assisted
  payload numbers remain conditional on bench calibration.
- FEA caveats unchanged: linear-static isotropic, no anisotropy/weld
  lines/contact; re-entrant corners reported as indications.

Build-stage tests (updated):
1-7. Unchanged from section 9 (screw stacks, droop test now vs the
   0.36 mm l4 prediction, 24 h 0.38 kg dwell incl. the new collar/longeron
   zones, spring bench cal, cyclo4 run-in, torque caps, cable check).
8. Print-density mitigation for residual R1: print the l5 plate band
   (a 20..45) at 100% infill / full perimeters and note the observed
   ring-edge region in the dwell inspection.
9. Junction visual + pull check on the first printed set: l4 collar lap
   faces and l5 longeron/ledge welds free of print voids (the welds are
   the load path; voids there defeat the fix).
