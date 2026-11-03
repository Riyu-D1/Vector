# D6 wrist2 print list (replaces the wrist rows of final/PRINT_LIST.md and wrist/PRINT_LIST-wrist.md)

PETG-CF, Bambu A1 (256 mm bed), 0.2 mm layers, 6 walls / 40% gyroid infill —
same print conventions as the existing list.  Mass = solid-equivalent g at
rho 1.27 g/cm3 (ap2.RHO_PETG); effective mass at 40% infill is ~0.6x.
STLs/STEPs: `wrist2/out/`.  Fingers and racks print from `wrist2/out/` too —
same geometry as `cad/arm2b`, shifted +5.6 mm in a (kept here so the posed
vendor proxies stay consistent with the D6 train).

| Part | STL | Mass g | Bbox mm | Orientation | Supp. | Walls/Infill |
|---|---|---|---|---|---|---|
| w_j4_cradle | wrist2 | 22 | 49.6×52.5×29.0 | bolt plate on bed, sleeve mouth up (-b up) | Yes — under sleeve +b rim [U] | 6 / 40% |
| w_link4 | wrist2 | 15 | 81.0×45.6×52.8 | horn plate down (-b on bed) | Yes — horn counterbores, plug tunnel roof [U] | 6 / 40% |
| w_link5 | wrist2 | 9 | 50.2×33.8×52.2 | -a end on bed, keel fins up | Yes — cheek-window top edges may droop [U] | 6 / 40% |
| w_grip_frame | wrist2 | 21 | 62.4×64.0×59.8 | keel bottom on bed, rack channel opening up (-h up) | Yes — channel roof (as before) + window ledges | 6 / 40% |
| finger_u, finger_d, vendor_rack_u/d | wrist2 (same geometry as arm2b, +5.6 mm a) | 2 / 3 each | — | as before | — | — |

Structural printed mass: 51.6 cm3 / 66 g solid-equiv (D5 63.1 cm3 / 80 g;
arm2b 90.6 cm3 / 118 g) -> −18% vs D5, −43% vs arm2b.
Modelled wrist+gripper mass incl. vendor parts at 40% infill: **0.225 kg**
(D5 modelled 0.234).

Fasteners: unchanged — 4x M3x10 ISO 7380 fore_r2 -> w_j4_cradle pilots (same
centres, same pilot d2.5 x 8+ deep); 12x M3x8 horn screws unchanged.
BOM delta: none — same vendor parts (J4 STS3250 from cad3; J5/J6/gripper
STS3215; existing racks, gear, fingers).
