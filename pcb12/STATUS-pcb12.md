# STATUS — SOMA carrier PCB v1.2 (pcb12/)

Copy of `pcb/` (v1.1) extended with CAN support for the three printed
brushless actuators. All v1.1 files are untouched; everything lives under
`pcb12/`. Board outline unchanged: 135 x 115 mm (no growth needed).

## New circuitry

- U2 TJA1051T/3 CAN transceiver, SOIC-8 on F.Cu at (87, 82)
  - pin1 TXD -> CAN_TX, pin2 GND, pin3 VCC -> +5V_MCU, pin4 RXD -> CAN_RX,
    pin5 VIO -> +3V3, pin6 CANL, pin7 CANH, pin8 S -> GND
- C5 100 nF +5V_MCU->GND at (84, 77); C6 100 nF +3V3->GND at (89, 89)
- J17 CAN bus port, Molex KK-254 3-pin at (90, 105): pin1 GND, pin2 CANH,
  pin3 CANL
- R9 120 ohm + JP2 termination jumper: CANH -> R9 -> CAN_TERM -> JP2 -> CANL
- J18 fused +12V output, Phoenix 2-pin at (100, 105): pin1 +12V, pin2 GND
- F1 changed 6A -> 10A
- SP1/SP2 removed from U1A.18/U1A.19; J15 keeps +5V/GND/+3V3 only.

## Firmware pin map

```
CAN_TX = IO2   (U1A.18 -> U2.1 TXD)
CAN_RX = IO1   (U1A.19 -> U2.4 RXD)
```

## New net table

| net | pins |
|-----|------|
| CAN_TX | U1A.18, U2.1 |
| CAN_RX | U1A.19, U2.4 |
| CANH   | U2.7, R9.2, J17.2 |
| CANL   | U2.6, JP2.2, J17.3 |
| CAN_TERM | R9.1, JP2.1 |

## DRC (kicad-cli pcb drc --severity-all, 2025-10-29 run)

- 20 violations: 12 `lib_footprint_mismatch` (pre-existing v1.1 library
  deltas), 7 `silk_overlap` (new U2/J17 silk labels), 1 `track_dangling`
- 2 unconnected items — KNOWN FAILURES, board is NOT clean:
  1. `+5V`: PTH pad R3.1 @ (54.0, 56.0) <-> via @ (46.99, 21.082).
     R3.1 has only a short F.Cu stub reaching it; the pad is not tied to
     the main +5V body.
  2. `ESTOP`: F.Cu track @ (51.816, 51.435) <-> B.Cu track @
     (27.178, 81.407). The F.Cu leg ends ~0.9 mm short of U1A.13 and the
     B.Cu fragment is an island; U1A.13 <-> J9.1 continuity is broken.
- The single `track_dangling` is the same ESTOP F.Cu stub.
- 0 `shorting_items`, 0 `clearance`, 0 `hole_to_hole`, 0 `via_dangling`.
- Pass criteria met: all new nets (CAN_TX, CAN_RX, CANH, CANL, CAN_TERM)
  routed with copper to every pad; all `+12V*` tracks = 2.5 mm
  (`+12V_IN` 73 atoms, `+12V_SW` 4, `+12V` 66, all width 2.5).
- Generator self-check additionally reports `+12V_IN` split at XT60 pad
  J16.2 (stricter than KiCad; KiCad connectivity counts it connected —
  copper edge overlaps the 6 mm annulus).

## Failing nets/pads (for the next fix round)

- `+5V` pad R3.1 (54, 56)
- `ESTOP` pads U1A.13 (52.62, 51.16) and J9.1 (30, 95)

Fix hint: bridge R3.1's F.Cu stub to the main +5V body near (51.9, 57.8);
extend the ESTOP F.Cu leg the last ~0.9 mm onto U1A.13, and join the
B.Cu island near via (26.924, 81.661).

## Outputs

- `soma-carrier-v12.kicad_pcb` — routed 2-layer board, GND pours baked
- `gerbers/` — 16 gerber layers + Excellon drill (fab.sh)
- `drc_report.txt`, `soma-carrier-v12-top.png`, `soma-carrier-v12-bottom.png`
- `bom.csv` — new/changed parts only

## P2 — fix ESTOP and +5V continuity (2026-10-29)

Hand-edited `soma-carrier-v12.kicad_pcb` (backup:
`soma-carrier-v12.before-P2.kicad_pcb`). No re-route, no regen. Added
12 segments + 2 vias; removed nothing.

- `+5V` (F.Cu, w=1.5, 4 segments, 0 vias): extended the island tip at
  (93.98,24.892) east, south at x95.5 (west of IRIN's F.Cu run starting
  x97.03), east at y37.5 (between IRIN y35.94 and +12V top y40.1), south
  at x125.5 onto +5V via (125.22,53.21). Joins R3.1's island to the
  southern +5V body (via 46.99,21.08 side).
- `ESTOP` (w=0.25, 8 segments, 2 vias at (32.3,63.9) and (30.7,73.8)):
  F.Cu west at y56 under the U1A row, south at x32.3 through the D1/J7
  gap, via to B.Cu, south past the ENC dive pickets, west to
  (30.7,73.8), via to F.Cu, one 45 deg leg to (27,77.5), south onto the
  island-A F.Cu chain at (27,81.74). U1A.13 <-> J9.1 continuity restored.

DRC after fix (`kicad-cli pcb drc --severity-all`, written to drc.json):
- `unconnected_items`: 0 (was 2)
- `shorting_items`: 0, `clearance`: 0, `track_dangling`: 0 (was 1),
  `via_dangling`: 0, `hole_to_hole`: 0
- remaining violations: 19 = 12 `lib_footprint_mismatch` + 7
  `silk_overlap` (all pre-existing, non-electrical)
- 1 fix round needed.

`gen_pcb.py` ROUTES not ported: the autorouter chooses its own copper
from waypoints, so the hand-placed repair does not map to ROUTES
semantics — **`soma-carrier-v12.kicad_pcb` is the source of truth** for
these two nets. Regenerating the board would lose the fix.

Gerbers re-exported to `gerbers/` via fab.sh (16 layers + Excellon
drill); `soma-carrier-v12-top.png` re-rendered.

## UNVERIFIED

- TJA1051T/3 pin order and the VIO pin — check against the datasheet
  before ordering.
- The motor controller boards (ESCs) are not chosen yet; they must be
  CAN-compatible with 3.3 V logic (VIO is on +3V3).
- 10 A fuse and 2.5 mm tracks vs the real motor peak current — must be
  re-checked once the ESCs are chosen.
- The F.Cu/B.Cu GND pours are baked into the file; if the board is
  re-opened in KiCad, refill with `B` before further edits.
