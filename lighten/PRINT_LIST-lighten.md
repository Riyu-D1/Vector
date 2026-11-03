# PRINT_LIST-lighten.md — Stage D9 print list

**No D9 prints.** Every lightened plate variant failed the D9 FEM gate
(see `STATUS-lighten.md` Task 3): the adopted arm structure is unchanged
from final2/D7.

Print the six candidate parts exactly as listed in
`final/PRINT_LIST.md` (Bambu A1, PETG-CF, 6 walls / 40 % infill, no
supports — all flat, ≤45° overhangs by design):

| Part | Source STL | Mass g | Orientation | Status |
|---|---|---|---|---|
| upper_out | `cad/arm2b/out/upper_out.stl` | 25 | flat side down | stock (D9 verified: do not lighten) |
| upper_back | `cad/arm2b/out/upper_back.stl` | 36 | flat side down | stock (same) |
| dogleg_l | `cad/arm2b/out/dogleg_l.stl` | 25 | flat cheek down | stock (skip: free volume is the J3→J4 load web) |
| dogleg_r | `cad/arm2b/out/dogleg_r.stl` | 25 | flat cheek down | stock (same) |
| fore_l2 | `cad/arm2b/out/fore_l2.stl` | 31 | flat plate down | stock (skip: ~10 % free, all load path) |
| fore_r2 | `cad/arm2b/out/fore_r2.stl` | 31 | flat plate down | stock (same) |

Evaluated-but-rejected variants remain under `lighten/out/` locally
(`*_l`, `*_lp`, `*_l2` STL+STEP, uncommitted): `_l` −3.3 g/plate at
+81 % deflection, `_lp` −5.6 g/plate at +224 % / SF 1.5 — do not print.

Firmware note: no hardware action, but the deployed robot-os now carries
`config.J6_SUBLIM_J5_NEG` — J6 clamps to ±110° whenever J5 < 0
(crash-side plug graze fix; full ±180° otherwise).
