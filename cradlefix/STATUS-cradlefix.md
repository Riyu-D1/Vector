# D7 cradlefix — wrist-corner graze fix (w_j4_cradle x w_link5 family)

Worktree `~/Vector-wt/cradlefix`, branch `arm-cradlefix` off `arm-final2`
79394a1. Goal: zero undeclared collisions in the wrist-pair family across the
full combined J4xJ5 envelope at <=2.5-deg steps incl. J6 and gripper strokes,
keeping all servo positions, horn faces, bolt patterns, joint axes, ranges,
walls >= 1.8 mm, cable channels, J4 stress SF >= 2, mass <= D6, no BOM change.

## What actually collided (baseline, seed 20261103 / 2.5-deg grids)

The D6 single-pose graze (3.4 mm3 at J4+70/J5+70) was only the tip. Full
envelope probing (`cf_probe.py`, same f2_collision machinery):

- J4xJ5 grid 2.5 deg (3249 poses, J6=grip=0):
  `w_j4_cradle x w_link5` **908 hits** (worst 34.6 mm3 @ -70/+70),
  `vendor_sts3250_j4 x w_link5` **278 hits** (worst 13.2 mm3).
- J5xJ6 grid 2.5 deg (8265 poses/J4 sample, J4 in {-70..+70}):
  `w_grip_frame x w_link4` **230 hits** (worst 2.0 mm3 @ J5+25/J6+122.5);
  `plug_g x vendor_sts3215_j5` and `vendor_sts3215_g x vendor_sts3215_j5`
  **504 hits each** (worst 11.1 mm3 @ J5-17.5/J6+160).
- J6 x gripper-stroke grid: clean for printed parts.

Swept-intersection footprints (`cf_footprint*.py`, union in each part's home
frame) localized the offenders:

- link5 side: a wedge on the **dorsal cheek top-front corner** a 21.0..30.1 x
  h -10.4..-2.15, |b| 12.5..14.9 (plus the horn plate's rounded front-outer
  corner at |b|->13.5, a<27.6 grazing by ~0.7 mm). Under J5 yaw the corner
  orbits inside the cradle b-band, then J4 pitch drops it onto the sleeve's
  rounded front-top/bottom edge and the J4 servo case's rounded front edge.
- link4 side: the J6 horn plate's rolled silhouette (D6 clip r16.2 -> top
  h -0.8) enters the fin **bottom web** h -1.4..-0.05 at a 59..61 whenever
  |J6|>~110 — the clip cleared the fin face but not the web thickness.
- vendor side: the g-servo cable plug lump (a 66.8..79, b +-9, h -39..-28)
  rolls up at |J6|>~110 and meets the **j5 vendor case** rear-bottom edge
  (a 64.6..65.7, h 0.1..6.8). Both bodies are vendor parts — see Residual.

## Fix (geometry edits, cradlefix/ copies of ap6.py + p_wrist6.py)

Only printed shell corners trimmed; the cradle ear itself keeps its full
servo wrap (cutting it would open the J4 case pocket for ~0 gain).

1. `ap6.py L5_CAGE` — cheek top-front corner reshaped:
   `(37.6,-2.15) -> (21.0,-2.15)` becomes `(37.6,-2.15) -> (33.0,-2.15) ->
   (21.0,-15.5)`, i.e. a chamfer running ~2 mm under the measured collision
   footprint everywhere.
2. `p_wrist6.py w_link5()` — horn plate front b-corner reliefs:
   `|b| > 10.0` removed for a < 28.2 over the plate thickness (keeps >= 1.95 mm
   ligament to the M3 counterbores at |b| = 8.05).
3. `ap6.py GF_PLATE` — J6 horn plate re-clipped to r 15.0 about the roll axis
   (was r 16.2): rolled silhouette top h -2.0 vs fin-web bottom -1.4.

Servo positions, horn faces, bolt patterns, joint axes, ranges: untouched.
Kinematics: `J4->J5 30.6`, J6 roll line -17.0, TCP 137.4 all identical.

## Gate outputs (real numbers)

### Collision envelope after fix — `cf_probe.py`, `CF_WRIST_DIR=cradlefix/out`

- GRID A J4xJ5 2.5 deg, J6=grip=0, 3249 poses: **CLEAN - no undeclared hits**.
- GRID B J5xJ6 2.5 deg at J4 = -70,-35,0,+35,+70 upstream x grip: **CLEAN**.
- GRID B wrist4/5 x grip (J4=0): only
  `plug_g x vendor_sts3215_j5` / `vendor_sts3215_g x vendor_sts3215_j5`,
  **504 hits each**, worst 11.1 mm3 @ J5-17.5/J6+160 — vendor-pair residual.
- GRID C J6 x stroke {0,4,8,12.5} at J5 -70/0/+70: **CLEAN**.

### Monte-Carlo before/after (seed 20261103, 2200 poses, same stream)

| pair                                   | before | after |
|----------------------------------------|-------:|------:|
| w_j4_cradle x w_link5                  |    606 |   **0** |
| vendor_sts3250_j4 x w_link5            |    194 |   **0** |
| w_grip_frame x w_link4                 |     50 |   **0** |
| plug_g x vendor_sts3215_j5             |    137 |    137 |
| vendor_sts3215_g x vendor_sts3215_j5   |    137 |    137 |
| hit poses / total pair-hits            | 1062/2457 | 546/1606 |

All remaining wrist-internal hits are the vendor plug-vs-vendor-case pair.

### Minimum clearance (cf_clearance.py, vertex->surface, 0.5-deg refine)

- `w_link5 x w_j4_cradle`:        **0.66 mm** @ J4+47.5/J5-70 (plate relief step corner)
- `w_link5 x vendor_sts3250_j4`:  **1.26 mm** @ J4-57.5/J5-70
- `w_grip_frame x w_link4`:       **0.60 mm** @ J5-27.5/J6+129.25

All >= 0.3 mm target.

### cradle_checks.py (wrist2_checks equivalent, build123d 0.13.0)

- REACH: J4->J5 30.6 PASS, J5 horn z +3.0 PASS, J6 line -17.00 PASS,
  J4->TCP 137.4 PASS, J2->TCP 380.5 (375 +- 10) PASS.
- HOLE: 4x d3.4 PCD14 horn holes all three plates PASS; cradle pilots PASS.
- CLEAR (home pose, all case pockets): 0.00 mm3 x4 PASS.
- GRIP open 25.0 mm: racks in channels PASS.
- MASS: cradle 17.0 / link4 11.4 / link5 **6.5** / grip 16.2 cm3;
  wrist+gripper 0.225 kg <= 0.234 PASS (link5 -372 mm3, grip -140 mm3 vs D6).
- TORQUE: J4 0.827 PASS, J5 0.603 PASS, J3 1.77 PASS;
  **J2 3.28 N.m > cap 3.0 FAIL — inherited D6 limitation** (printed cyclo-disc
  load cap, unchanged by D7; documented in wrist2/STATUS-wrist2.md).
- STRESS J4: min strut section S 67 mm3 at h 16 -> 11.9 MPa, **SF 2.1** vs
  [U] 25 MPa — >= 2 PASS (hand-calc line from checks).
- WALL: all 11 probes PASS, min 1.85 mm (link5 plate).
- ROM: J4 -90..+85 (175 >= 140) PASS, J5 +-70 (140) PASS, J6 +-180 (360) PASS.
- CABLE: 12/12 plug-channel probes empty PASS.
- OVERHANG: all PASS (worst droop 1.00).

### software/robot-os

`python3 -m pytest -q` -> **66 passed** (kinematics/firmware unchanged).

### Full assembly (cf_export_assembly.py = final/export_assembly.py pattern)

`cradlefix/out_asm/assembly.stl` 10.6 MB, `assembly.step` 34.2 MB, 175 solids,
72 parts / 212,204 tris — same structure as D6 (10.6 MB / 34.1 MB / 175).

### Renders (cradlefix/renders/, Blender workbench)

- `cf_{before,after}_*.png` — cradle + link5 + posed J4 servo close-up.
  Inspected: side view shows the cheek top-front chamfer and the shortened
  plate ledge; cradle ear/servo wrap unchanged. No visual collisions.
- `asm_*.png` — full arm iso: wrist reads as D6 (slim fin + keel + grip
  train), no anomalies.

## Residual collision — honest report

`plug_g` / `vendor_sts3215_g` x `vendor_sts3215_j5`: **504 grid poses / 137 MC
poses remain** (worst 11.1 mm3). Both bodies are vendor-servo proxies; the
contact is the g servo cable-plug lump rolling into the J5 case rear-bottom
edge at |J6| > ~110 deg with J5 ~ -40..0. Eliminating it needs a moved servo,
a reshaped vendor part, or a reduced J6 range — all forbidden by the stage's
invariants ("keep ALL servo positions ... joint axes and ranges"). So: **not
fixable by printed geometry; reported as the stage's "if impossible, say so"
case.** Real mitigations outside this stage's scope: dress the g cable so the
connector body doesn't stand 11 mm off the case in -a (the lump is the
vendor-frame plug box), or a J6 software sublimit ~ +-110 deg for poses with
J5 < 0 (firmware owns range; hardware stops are unchanged).

## Files changed (all inside cradlefix/)

- `ap6.py` — L5_CAGE corner (2 points -> 3), GF_PLATE re-clip r16.2 -> r15.0.
- `p_wrist6.py` — w_link5 horn-plate front b-corner reliefs.
- `build_wrist6.py`, `p_wrist6.py` base, `cradle_checks.py`, `render_blend.py`
  — verbatim copies of the wrist2 tools (wrist2 originals untouched).
- New probes: `cf_probe.py`, `cf_footprint.py`, `cf_footprint2.py`,
  `cf_clearance.py`, `cf_mc_hist.py` (seed preserved), `cf_export_assembly.py`.
- `PRINT_LIST-cradlefix.md`, this status.
- `out/` (13 parts stl+step), `out_asm/`, `renders/_tmp/` — generated, not
  committed.

## [U] unverified / fallbacks

- Documented CAD venv `~/soma/.venv` does not exist on this machine —
  fallback: created worktree-local `.venv` with **build123d 0.13.0** (the
  spec'd version) + trimesh/manifold3d; system `python3` used for the sim and
  pytest per rules. `.venv` not committed.
- `cad/arm2b/out/` scratch built with the same venv (needed by the sim); not
  committed.
- PETG-CF cross-layer 25 MPa, 0.6 mass factor, STS3215 0.98 N.m rating, plug
  dims: inherited [U]s from D5/D6, unchanged.
- Vendor plug lump = servo-frame box dims (SV_PLUG_*); real cable is flexible —
  the residual above is a worst-case rigid-lump model.

## Open questions

- Real g-cable dressing: if the connector can route under/behind the J6 horn
  plate (D5-style interleave already used for the case), the residual family
  may disappear in hardware even though the rigid-lump model still flags it.
- J2 torque cap 3.0 N.m exceeded (3.28) at 0.5 kg payload — pre-existing D6
  finding, out of D7 scope.
