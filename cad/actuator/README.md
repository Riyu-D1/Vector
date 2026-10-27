# SOMA actuator — 15:1 printed cycloidal direct-drive (J1/J2/J3)

Parametric `build123d` re-implementation of the **Berkeley Humanoid Lite 5010
cycloidal actuator**, adapted to the SOMA arm envelope (70 mm OD x 85.5 mm).
Credit: UC Berkeley Humanoid Lite project, CC BY-SA 4.0 —
https://lite.berkeley-humanoid.org .  This derivative CAD is likewise CC BY-SA
4.0.

## Files

| file | purpose |
|---|---|
| `params.py` | every dimension, single source of truth |
| `cycloid.py` | cycloidal disc profile generator (pin-mesh envelope) |
| `parts.py` | the 7 printed parts + standard-part models |
| `assembly.py` | full assembly builder; exports STL + STEP to `export/` |
| `check.py` | verification suite -> `docs/actuator-verification.md` |
| `INTERFACE.md` | frozen interface for Stream B |

Run: `python3 assembly.py` (exports), `python3 check.py` (verification,
`--fast` for a quicker sweep).

## Printed parts (PETG recommended, PLA ok for proto)

housing, cycloidal_disc_x2, input_shaft, output_shaft, motor_shell,
end_cap, motor_shaft — all exported in `export/`; all print without supports
(orientations in verification doc §6).

## BOM (per actuator)

| qty | part | source |
|---|---|---|
| 1 | MAD Components 5010 EEE V2.0 110 KV motor (OD 56 x 32.7 mm, 162 g) | datasheet values |
| 2 | 6809ZZ bearing 45 x 58 x 7 mm | BHL BOM |
| 2 | 6701-2RS bearing 12 x 18 x 4 mm | BHL BOM |
| 13 | MR106-2RS bearing 6 x 10 x 3 mm (12 output rollers + 1 pilot) | BHL BOM |
| 16 | 6 mm dowel pin x ~16 mm (ring pins) | BHL BOM |
| 1 | ST B-G431B-ESC1 motor driver | BHL BOM |
| 1 | AS5600 encoder module + 6x3 mm diametric magnet | BHL BOM |
| 1 | M4 x 12 hex standoff (input-shaft tip support) | BHL BOM |

### M3 fastener table

| qty | part | where |
|---|---|---|
| 4 | M3 x 55 socket-head | housing clamp bolts (end_cap -> motor_shell -> housing, 64 mm BCD) |
| 6 | M3 x 25 + washers | output-pin roller retention (into M3x4x5 insert in pin tip or through-nut) |
| 4 | M3 x 6 (approx) | motor stator -> motor_shell floor lands (25 + 30 mm BCD) |
| 6 | M3 x 8 | driven link -> output flange face (8 holes, 44 mm BCD) |
| 4 | M2 x 6 | AS5600 board -> end_cap posts |
| 4 | M2.5 x 6 | B-G431B-ESC1 -> end_cap posts |
| 24 | M3 x 4 x 5 mm heat-set inserts | shell-bolt pockets, stator lands, pin tips, ESC posts (per BHL BOM) |
| 4 | M2 x 3 x 3.5 heat-set inserts | encoder posts (per BHL BOM) |

## Design notes / deviations vs BHL

- **Both 6809ZZ output bearings are a stacked pair on the top hub**
  (z = 71–78 + 78–85).  The BHL BOM lists 2x 6809 "between output shaft and
  housing"; a lower spigot cannot pass the pin/disc zone, so the model puts
  them stacked — stiffer against moment loads anyway.  Documented in
  `parts.py` header.
- Disc flank offset uses a **true polygon buffer offset** (shapely) — the
  naive normal offset self-intersects at lobe tips; the manufactured profile
  keeps +0.15 mm pin clearance everywhere (verification §2–§3).
- FDM clearance is parametric: `P.gear.clearance` (mesh flank, 0.15 mm) and
  `P.fd_clearance` (seats/grooves, 0.2 mm).

## UNVERIFIED (measure on arrival)

- Output-pin BCD 33 mm / roller stack (arithmetic + thumbnail only).
- ESC hole pitch ~33 mm square; encoder module 25.4 mm/20 mm pitch.
- Motor shaft stub diameter (6 mm assumed) and rotor bolt circle detail.
- Exact overall length vs BHL original (BHL value not published; ours is
  85.5 mm including retainer rim).
- Pin/dowel length 16 mm assumed (BOM lists "6 mm dowel"; cut to suit).

See `../../docs/actuator-verification.md` for the full check log.
