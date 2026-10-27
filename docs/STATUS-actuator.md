# Stream A — actuator CAD status

Branch `arm-actuator`, worktree `~/Vector-wt/actuator`. Deadline 31 Oct 2026.

## Done
- Research on Berkeley Humanoid Lite 5010 actuator (the reference design):
  - BOM extracted (official Google sheet, tab "5010 Actuator"):
    bearings MR106-2RS x13, 6701-2RS x2, 6809ZZ x2; M3x55 x4, M3x25 x6,
    M2x3x3.5 inserts x4, M3x4x5 inserts x24, M4x12 hex standoff x1;
    motor MAD 5010 110KV, ESC B-G431B-ESC1, AS5600 encoder.
  - Cycloidal profile recovered from the public Onshape doc blob
    `5010_profile.dxf` (document 192ab9c484f00d0dd33b8f01). It is a classic
    pin-mesh disc: 16 ring pins r=3.0 mm on Rp=29.0 mm, eccentricity e=1.5 mm,
    15 lobes -> 15:1. My parametric generator reproduces the DXF to
    0.007 mm RMS.
  - Part-set confirmed via Onshape thumbnails: housing w/ internal pin slots,
    2 discs, output shaft w/ 6 pins, input shaft, motor shaft puck,
    motor shell, end cap (ESC tray), hex standoff.
  - Motor datasheet: MAD 5010 EEE V2.0 = OD 56 x 32.7 mm, stator mount M3 on
    25 + 30 mm BCD, rotor mount M3 on 12 + 18 mm BCD, 14 pole pairs, 162 g.
  - Licence: CC BY-SA 4.0 (credited in `cad/actuator/README.md`).
- `cad/actuator/` complete: params.py, cycloid.py, parts.py, assembly.py,
  check.py, INTERFACE.md, README.md (BOM + M3 table + UNVERIFIED).
- `cad/actuator/INTERFACE.md` v0.2 — OD 70, length 85.5, 8xM3 @44 BCD output,
  4xM3 @64 BCD rear, cable slot. Stream B can consume.
- All 7 printed parts + bearings/pins/boards in assembly; STL per part +
  assembly STEP exported to `cad/actuator/export/`.
- **Verification green** (`docs/actuator-verification.md`, auto-generated):
  - 7/7 STLs watertight.
  - Interference sweep 48 samples/rev: 0.0000 mm3 on every pair
    (ring-pins, output pins, housing, eccentric shaft, pilot).
    BREP boolean spot-check agrees: 0.000 mm3.
  - Disc profile: 15 lobes, star-shaped (no undercut), flank contact = touch
    (design), manufactured profile keeps +0.15 mm pin clearance.
  - Mass estimate 509 g all-in.
  - Profile vs Onshape DXF: 0.0070 mm RMS / 0.014 mm max.
- Bugs found & fixed during verification:
  - second cycloidal disc now phased 180 deg (odd lobe count needs it);
  - `Polygon` -> `Polyline`: build123d Polygon interpolates a smooth wire
    that bulged ~0.4 mm at lobe tips into the pins;
  - naive curve offset -> shapely buffer (true envelope, no spikes);
  - disc pin-holes cut at wrong z (Pos*Cylinder centre vs cz());
  - input-shaft cam stack reworked (collars + retainer lips inside disc bore).
- CAN GPIO confirmed from pcb/gen_pcb.py: J15 pin3 SP1=IO2, pin4 SP2=IO1
  (TWAI TX/RX for Stream C).

## In progress
- Sanity render of final assembly; minor cosmetics.

## Blocked
- Onshape STEP export needs an account -> parametric re-implementation per
  spec (allowed fallback). Tessellation/mass API endpoints are
  authenticated; thumbnails + DXF were anonymous.

## UNVERIFIED so far
- Output-pin BCD / roller choice (BOM arithmetic gives 6 pins + MR106
  rollers, BCD ~33; thumbnail confirms 6 pins).
- ESC mounting hole pattern (~33 mm square), encoder module footprint.
- Motor shaft stub OD (6 mm assumed).
