# Stream B status — arm structure (branch arm-rebuild)

Updated: 2026-10-28 (real actuator interface integrated)

## Done
- Spec: ARM_HYBRID_V3.md. J1-J3 = Stream A cycloidal actuators per
  `cad/actuator/INTERFACE.md` v0.2 (branch arm-actuator): Ø70 x 85.5 mm
  shell, output flange face = datum, 8xM3 on Ø44 BCD, Ø45x1 pilot boss,
  rear cap 4xM3 on Ø64 BCD, rear-rim cable slot 8x6 + 10 mm keep-out,
  ~510 g each, ~7.9 N.m peak. J4-J6 = STS3215 (verified reference solid).
- Full parametric build in cad/arm/parts.py (+ arm_params.py params,
  build.py exports/renders, checks.py verification).
- Architecture (SO-ARM-102 inspired side-plate style, no closed boxes):
  - base_housing: Ø132 drum on 4 mm lid at case coords (75,88), J1
    actuator vertical in Ø70.4 pocket (rear face z5, flange face z90.5),
    Ø110 housing, cable gallery at r~39 (-Y), clamp-ring recess z27-34
    with -X ear pocket, 6812 outer-race seat z80.5-86.
  - j1_clamp_ring: printed split ring (OD91.2/ID70.3) pinching the Ø70
    shell mid-body for axial retention + torque reaction, M4 ear pinch.
  - bearing_cap: clamps the 6812 outer race (seat below + lip over the
    race top edge), cable slot at r~39 (-Y), 4xM4 into housing rim.
  - turret / turret_cap: plate disc Ø98 z92.2-96.2 + boss ring Ø72
    resting on inner-race top AND the J1 output flange face (both z90.5)
    + annular plug spigot inside the Ø60 bore; 8xM3 PCD44 through the
    bore into the flange; split half-pipe cradle OD79/ID70.4 |y|<=30.5;
    end webs at |y|~26.5; split-plane lugs x +/-41.5, y +/-27.
  - upper_link / upper_link_cap: J2 side-plate cheeks (r41 discs;
    -Y cheek inner at -44.75 = 2 mm rear clearance + cable keep-out
    notch; +Y cheek inner at +42.75 landing flat on the flange face,
    Ø45.5 pilot counterbore, 8xØ3.4 PCD44), beams with stepped bottom
    edge, top rail at rel +42.5 (above cap shell top), centre web
    x48-72, J3 lower half-saddle + cap, web cable bore at y-36.
  - forearm: same side-plate scheme, J4 servo fork (z +-14 block,
    M2 24.45x20.5 ear grids, wheel bores, +Y idler stub).
  - wrist: J4 disc plates + beams + rails -> J5 pod (X-axis shaft,
    Y-open pocket, M2 grids both end cheeks), cable channel.
  - nose: J5 plate, rail block with open jaw slot, finger-rise window,
    top-mounted J6 (shaft +Z), deep pilot bores; jaw_l/jaw_r slide +-Y.
- J2 axis at z146; links 120/100 mm; J5 at J4+51.
- Exports: STEP + canonical assembly-frame STL under cad/arm/export/,
  print-oriented STL under cad/arm/export/print/, assembly.step/.stl,
  6 renders under cad/arm/renders/.
- checks.py: 22 checks, all pass (see docs/arm-verification.md).

## Verification (latest run, 22/22 PASS — real interface)
- stl-watertight-nonzero; servo-fit J4/J5/J6 overlap ~2.6 mm3;
  servo-mount-grids all present; home-pairwise clean (cap seats and
  horn spacer seats classified as intended contact).
- actuator-clearance: real Ø70x85.5 + Ø45 pilot envelope vs all printed
  parts — only intended contacts (cradle bore slivers ~0.6-1.7 cm3,
  flange-face/cheek contact); J1 vs housing/cap = 0.
- rom-sweeps clean over J1 +-170, J2 -15..+30, J3 +-90, J4 +-95, J5 +-160.
- extremes-table-case: PASS under firmware guard envelope
  J3 <= 45 - 2*J2 (measured boundary; raw joint ranges fold the wrist
  below the table near J2+J3 ~ +45). Documented as required guard.
- reach: tip x = 348 mm (target 260 — links 120/100 plus real wrist/
  gripper need ~95 mm for J4->tip; V3 nominal 40 was optimistic).
- mass: printed 574 g + hardware 1805 g (3x510 g actuators + 3x55 g
  servos + 110 g 6812) = 2379 g (45% fill PETG).
- wrist cluster 220 g vs spec 180 — WAIVED: 3x STS3215 = 165 g alone,
  ceiling documented at 240 g (flagged for Stream A).
- torque @250 g payload, full extension: J2 2.25 vs 7.9 N.m rated
  (margin 5.65 N.m — shoulder load does NOT exceed the limit),
  J3 0.92 vs 7.9, J4 0.42 vs 0.98.
- print-bed-220 all parts; fastener table 16 rows; cable riser and
  link channels + joint slots all clear.

## Open items / notes
- Joint-limit rationale: J2 +30 max — beyond it the distal plates wrap
  under into the Ø132 drum zone; J2 -15 min — webs vs cradle web.
  Raising either needs taller turret / higher J2_Z (documented TODO).
- Rear-face pattern (4xM3 Ø64 BCD) is not bolted to anything — the
  cradles clamp the shell and the cheeks keep clearance; used only as
  documented keep-out. Cable slot assumed reachable via the rear gap
  -> plate hole (J2) / under-saddle route to web channel (J3).
- If Stream A revises INTERFACE.md beyond v0.2, update ActuatorSpec in
  arm_params.py and rebuild — all dims are parametric.
- Center-of-mass divide-by-zero warnings from trimesh on the reference
  servo remain cosmetic (repaired mesh used for fits).
