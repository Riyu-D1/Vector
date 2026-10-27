# Arm structure verification (Stream B, branch arm-rebuild)

All checks live in `cad/arm/checks.py`. Run:

    /Users/deepakdiwan/soma/.venv/bin/python cad/arm/checks.py

(needs build123d + trimesh + manifold3d; exports must be regenerated
first with `build.export_all()`).

Latest result: **22/22 PASS** against the real Stream A actuator
interface (`cad/actuator/INTERFACE.md` v0.2: Ø70 x 85.5, 8xM3 PCD44,
Ø45x1 pilot, rear 4xM3 PCD64, 8x6 rear cable slot, ~510 g, 7.9 N.m).

## What is verified

| check | result |
|---|---|
| stl-watertight-nonzero | PASS — all 14 exported STLs watertight |
| servo-fit-clearance | PASS — J4/J5/J6 reference solid overlap ~2.6 mm3 |
| servo-mount-grids | PASS — M2 24.45x20.5 grids probe-clear at J4/J5/J6 |
| home-pairwise-interference | PASS — only documented seats (cap saddles, horn spacers) |
| actuator-clearance | PASS — Ø70x85.5+pilot vs housing/cap/links: intended contacts only |
| rom-sweeps | PASS — J1 ±170, J2 −70..+35, J3 ±90, J4 ±95, J5 ±160 |
| extremes-table-case | PASS under guard `J3 <= 45 − 2·J2` |
| reach | PASS — tip x=348 mm (V3 target 260; see note) |
| mass-total | printed 574 g + hw 1805 g = 2379 g |
| wrist-cluster | 220 g (spec 180 waived — 3×STS3215 = 165 g minimum) |
| torque-J2 | 2.25 N.m vs 7.9 rated — margin 5.65 N.m |
| torque-J3 | 0.92 N.m vs 7.9 |
| torque-J4-servo | 0.418 N.m vs 0.98 rated |
| payload-verdict | 250 g at 348 mm OK |
| print-bed-220 | PASS |
| fastener-table | 16 rows |
| cable-riser / channels / joint slots | PASS |

## Notes

- STL exports in `export/` are canonical assembly-frame; print
  orientations live in `export/print/`.
- The guard envelope is required firmware behaviour: raw folds past
  J3 <= 45 − 2·J2 pitch the wrist below the table. It is enforced in
  the base node (`arm_clamp_q`) and the host (`config.guard_clamp`).
- J2 range was widened on `arm-integrated` (2026-10): measured clean
  sweep −72..+36 vs the documented −15..+30; adopted −70..+35 with
  margin. +90 down is architecturally impossible — the J3 actuator
  folds into the Ø110 housing; clearing it needs J2_Z ≈ +110 mm. See
  `docs/INTEGRATION-REPORT.md`.
- c7 samples poses inside the guard envelope plus its boundary; fixed
  folds are clipped to `J3 <= 45 − 2·J2` first (a firmware-reachable
  sample must be legal). Wrist-down J4 poses near the boundary can
  still touch the table — documented limitation, not a guard bug.
- Reach overshoot (348 vs 260) is driven by the real wrist/gripper
  stack (J4->tip = 128 mm measured); links stay at the planned
  120/100 mm.
- Actuator contact volumes (~0.6–1.7 cm3) are intended: cradle bore
  clamp surface + flange-face landing. Deep embeds (>3 cm3) would fail.
