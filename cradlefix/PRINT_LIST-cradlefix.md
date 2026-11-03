# D7 cradlefix print-list update — changed rows only (parts/masses)

Replaces the two wrist2/PRINT_LIST-wrist2.md rows for the re-shaped parts.
All other rows, orientations, support notes, fasteners and BOM unchanged.

PETG-CF, Bambu A1, 0.2 mm layers, 6 walls / 40% gyroid — same conventions.
Mass = solid-equivalent g at rho 1.27 g/cm3; effective ~0.6x at 40% infill.
STLs/STEPs: `cradlefix/out/`.

| Part | STL | Mass g | Bbox mm | Orientation | Supp. | Walls/Infill |
|---|---|---|---|---|---|---|
| w_link5 | cradlefix | 8 | 50.2×33.8×52.3 | -a end on bed, keel fins up | Yes — cheek-window top edges may droop [U] | 6 / 40% |
| w_grip_frame | cradlefix | 20 | 62.4×64.0×59.8 | keel bottom on bed, rack channel opening up (-h up) | Yes — channel roof (as before) + window ledges | 6 / 40% |

Structural printed mass now: 51.0 cm3 / 65 g solid-equiv (D6: 51.6 cm3 /
66 g). w_link5 -372 mm3, w_grip_frame -140 mm3 vs D6 — both mass deltas are
removals, no additions.
