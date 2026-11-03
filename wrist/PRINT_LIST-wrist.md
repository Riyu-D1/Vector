# D5 wrist print list (replaces the wrist rows of final/PRINT_LIST.md)

PETG-CF, Bambu A1 (256 mm bed), 0.2 mm layers, 6 walls / 40% gyroid infill —
same print conventions as the existing list.  Mass = solid-equivalent g at
rho 1.27 g/cm3 (ap2.RHO_PETG); effective mass at 40% infill is ~0.6x.
STLs/STEPs: `wrist/out/`.  Vendor parts, racks, fingers: unchanged, print the
existing `cad/arm2b` STLs.

| Part | STL | Mass g | Bbox mm | Orientation | Supp. | Walls/Infill |
|---|---|---|---|---|---|---|
| w_j4_cradle | wrist | 22 | 49.6×52.5×29.0 | bolt plate on bed, sleeve mouth up | Yes — under sleeve +b rim [U] | 6 / 40% |
| w_link4 | wrist | 22 | 66.7×61.7×69.1 | horn-plate down (-b on bed) | Yes — horn counterbores, plug-tunnel roof, window ledges [U] | 6 / 40% |
| w_link5 | wrist | 13 | 41.7×29.0×51.9 | -a end cap on bed, bore open up | Yes — cheek-window top edges may droop [U] | 6 / 40% |
| w_grip_frame | wrist | 25 | 56.4×64.0×59.7 | rack channel opening up | Yes — channel roof (as before) + window ledges | 6 / 40% |
| finger_u, finger_d, vendor_rack_u/d | arm2b (unchanged) | 2 / 3 each | — | as before | — | — |

Structural printed mass: 63.1 cm3 / 80 g solid-equiv (was 90.6 cm3 / 118 g) -> -30%.
Wrist+gripper printed total incl. racks+fingers: ~72 cm3 (was 98).

Fasteners: unchanged — 4x M3x10 ISO 7380 fore_r -> w_j4_cradle pilots (same
centres, same pilot d2.5 x 8+ deep); horn screws unchanged.  BOM delta: none.
