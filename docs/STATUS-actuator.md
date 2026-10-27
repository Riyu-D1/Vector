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
  - Licence: CC BY-SA 4.0 (credits will be in README).
- `cad/actuator/params.py` — parametric spec written.
- `cad/actuator/INTERFACE.md` — published for Stream B (OD 70, len ~74,
  8xM3 @44 BCD output, 4xM3 @64 BCD rear, cable slot).
- CAN GPIO confirmed from pcb/gen_pcb.py: J15 pin3 SP1=IO2, pin4 SP2=IO1
  (TWAI TX/RX for Stream C).

## In progress
- build123d module: gear profile, parts, assembly.

## Blocked
- Onshape STEP export needs an account -> parametric re-implementation per
  spec (allowed fallback). Tessellation/mass API endpoints are
  authenticated; thumbnails + DXF were anonymous.

## UNVERIFIED so far
- Output-pin BCD / roller choice (BOM arithmetic gives 6 pins + MR106
  rollers, BCD ~33; thumbnail confirms 6 pins).
- ESC mounting hole pattern (~33 mm square), encoder module footprint.
- Exact overall length (~74 mm est; BHL value not published).
