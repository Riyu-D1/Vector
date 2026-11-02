# PRINT OR CUT LIST — cyclo4

Everything prints on the Bambu A1. Nothing is cut/bought beyond the existing
BOM dowels. Source STLs: `cyclo4/out/*.stl` (STEP alongside).

## Print (PETG-CF, dry 8 h @ 80 C; 0.4 nozzle, 0.12 layer, 6 walls, 100% infill, no supports)

- `disc1.stl`, `disc2.stl` — the redesigned parts. Print flat, lobes in XY
  (along-layer). The flank offset is nominal -0.01 mm; DO NOT apply
  horizontal-expansion compensation on the disc profile.
- `hub.stl`, `carrier.stl`, `out_flange.stl` — same spec as discs.
- `housing.stl`, `pin_ring.stl`, `front_ring.stl`, `mag_puck.stl` — PETG,
  0.2 layer, 6 walls, 40% gyroid, no supports (unchanged from BOM).

## Assembly fit procedure (new — the redesign depends on it)

1. Fit-check the Ø3 ring-pin holes and the 6808 seat first (print housing
   front 12 mm only).
2. Grease all 41 ring pins + both disc flanks (PTFE or lithium).
3. Assemble; hand-cycle 5-10 min — the near-zero profile is designed to
   run-in; it should free up smoothly, not ratchet.
4. If a quadrant binds: swap those pins for the loosest of the spare dowels
   (selective fit) rather than sanding the flank.
5. Backlash check: rotate output +/- and feel for lost motion; a unit that
   lands loose (effective clearance ~0.05+) is outside the verified SF 2
   envelope — flag it, don't run at design torque.

## DXF reference drawings (`cyclo4/dxf/`)

`disc1.dxf`, `disc2.dxf`, `output_pin_plate.dxf` — 2D profile reference only
(discs are printed; kept in case a cutting service is ever wanted).
