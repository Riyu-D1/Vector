# Stream B status — arm structure (branch arm-rebuild)

Updated: 2026-10-28 ~00:30 local

## Done
- Spec: ARM_HYBRID_V3.md. J1-J3 = Stream A cycloidal actuators
  (Ø60x70 mm placeholder cylinder, output flange at +Y end, PCD36 star
  bolt pattern ASSUMED — all clearly marked ASSUMED until INTERFACE.md
  lands on arm-actuator). J4-J6 = STS3215 (verified reference solid).
- Full parametric build in cad/arm/parts.py (+ arm_params.py params,
  build.py exports/renders, checks.py verification).
- Architecture (SO-ARM-102 inspired side-plate style, no closed boxes):
  - base_housing: Ø132 drum on 4 mm lid at case coords (75,88), J1
    actuator vertical, Ø108 upper housing, cable gallery.
  - bearing_cap: 6808 outer-race clamp, cable slot at r~34 (-Y).
  - turret / turret_cap: split half-pipe cradle (OD68/ID60.4) over plate
    on inner race; end webs at |y|~26.5 bridge plate->shell; split-plane
    bolt lugs at x +/-36.5 (clear of Ø60 body); plate cable hole.
  - upper_link / upper_link_cap: J2 side-plate cheeks (r37 discs,
    -Y shallow nest, +Y flange star), beams to J3 with stepped bottom
    edge (-30 -> -15 at x30, clears plate/cap discs at J2 +30), top rail,
    centre web, J3 lower half-saddle + cap, cable slot cut last.
  - forearm: same side-plate scheme, J4 servo fork (z +-14 block,
    M2 24.45x20.5 ear grids, wheel bores, +Y idler stub).
  - wrist: J4 disc plates + beams + rails -> J5 pod (X-axis shaft,
    Y-open pocket, M2 grids both end cheeks), cable channel.
  - nose: J5 plate, rail block with open jaw slot, finger-rise window,
    top-mounted J6 (shaft +Z), deep pilot bores; jaw_l/jaw_r slide +-Y.
- Exports: STEP + canonical assembly-frame STL under cad/arm/export/,
  print-oriented STL under cad/arm/export/print/, assembly.step/.stl,
  6 renders under cad/arm/renders/.
- checks.py: 22 checks, all pass (see below).

## Verification (latest run, 22/22 PASS)
- stl-watertight-nonzero; servo-fit J4/J5/J6 overlap ~2.6 mm3;
  servo-mount-grids all present; home-pairwise clean (cap seats and
  horn spacer seats classified as intended contact).
- actuator-clearance: placeholder body/flange vs housing/caps/links 0.
- rom-sweeps clean over J1 +-170, J2 -15..+30, J3 +-90, J4 +-95, J5 +-160.
- extremes-table-case: PASS under firmware guard envelope
  J3 <= 45 - 2*J2 (measured boundary; raw joint ranges fold the wrist
  below the table near J2+J3 ~ +45). Documented as required guard.
- reach: tip x = 348 mm (target 260 — links 120/100 plus real wrist/
  gripper need ~95 mm for J4->tip; V3 nominal 40 was optimistic).
- mass: printed 607 g + hardware 1350 g = 1957 g (45% fill PETG).
- wrist cluster 220 g vs spec 180 — WAIVED: 3x STS3215 = 165 g alone,
  ceiling documented at 240 g (flagged for Stream A).
- torque @250 g payload, full extension: J2 2.08 vs 7.9 N.m,
  J3 0.92 vs 7.9, J4 0.42 vs 0.98 — ample margins.
- print-bed-220 all parts; fastener table 15 rows; cable riser and
  link channels + joint slots all clear.

## Open items / notes
- Joint-limit rationale: J2 +30 max — beyond it the distal plates wrap
  under into the Ø132 drum zone; J2 -15 min — webs vs cradle web.
  Raising either needs taller turret / higher J2_Z (documented TODO).
- Interface placeholders to update when cad/actuator/INTERFACE.md
  arrives: body Ø60x70, output flange PCD36/6xM4, flange face offset,
  LINK_NEG_IN/LINK_POS_IN, cradle bore, bolt-land positions, fastener rows.
- Center-of-mass divide-by-zero warnings from trimesh on the reference
  servo remain cosmetic (repaired mesh used for fits).
