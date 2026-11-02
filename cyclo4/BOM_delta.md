# BOM delta — cyclo4 vs cad/act2 module

User brief: PETG-CF printed discs only. Steel dowel ring pins already in BOM
stay — no new bought parts. **Delta vs `cyclo4/BOM.md`: zero purchased items.**

| change | detail | cost |
|---|---|---|
| Discs 1/2, thickness | 4.0 -> 4.25 mm, PETG-CF (was already listed "PA-CF or PETG" — now pinned to PETG-CF per brief) | +~1 g filament |
| Disc flank profile | clearance offset 0.15 -> 0.01 mm + run-in/selective pin fit | — |
| Out-pin holes | radial clearance 0.15 -> 0.12 mm (CLR_OUT, separate param) | — |
| Ring pins | unchanged: 41 x ISO 8734 Ø3x10 hardened dowel | — |
| Output pins | unchanged: 6 x Ø3x12 dowel | — |
| Everything else | unchanged | — |

## Firmware change required (flagged, owner = arm firmware)

`firmware/base-node/src/config.h` `PHASE_CURRENT_LIMIT_A = {5.0, 5.0}`:
cap output torque inside the verified envelope —
**J2 -> ~3.7 A (3.0 N·m), J3 -> ~2.5 A (2.0 N·m)** at
T_out = I x Kt 0.0289 x 40 x eta 0.7, plus a soft E-stop current ramp
(~50-100 ms to zero). Existing product file — not touched here.
