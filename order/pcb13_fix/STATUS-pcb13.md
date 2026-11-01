# STATUS — SOMA carrier PCB v1.3 (pcb13/)

Copy of `pcb12/` (v1.2) extended with reverse-polarity protection and a
hardware e-stop relay that switches the motor +12V rail. All v1.2 files
are untouched; everything lives under `pcb13/`. Board outline unchanged:
135 x 115 mm, F.Cu + B.Cu, all through-hole.

## Removed parts (step 1)

- J6, R2 — BUSB_DATA / RXB gone; U1B.15, U1B.5 left unconnected
- J7, J8 — SDA2 / SCL2 gone; U1A.16, U1A.17 left unconnected
- J10 — WRX gone; U1A.14 left unconnected
- Net WTX renamed MOTOR_EN, stays on U1A.15 (IO40)
- J9 (ESTOP sense input) kept as is

## New circuitry

### Reverse-polarity protection (step 2)

- Q2 IRF4905 P-FET, TO-220-3 vertical at (12, 74), rot 90 — between
  JP1 (+12V_SW in) and F1. Wrong-way input leaves gate at source
  potential; FET stays off.
- Q2.2 drain = +12V_SW (JP1.2 -> Q2.2); Q2.3 source = +12V_RP (Q2.3 ->
  F1.1; F1.1 moved +12V_SW -> +12V_RP); Q2.1 gate = RP_GATE.
- R10 10k, RP_GATE -> GND, at (10, 82).

### Hardware e-stop relay (step 3)

- K1 Songle SRD-12VDC-SL-A (SANYOU SRD Form A footprint) at (100, 62).
  Pads 1/2 = coil, 3 = COM, 5 = NO (pad 4 absent = NC).
  Coil: K1.1 +12V, K1.2 RLY_LOW -> J19 -> Q3.
  Contact: K1.3 COM +12V -> K1.5 NO +12V_MOT.
- D5 1N4007 flyback across coil at (86, 70): pad1 cathode +12V, pad2
  anode RLY_LOW.
- J19 ESTOP-NC header at (92, 74): pin1 RLY_LOW, pin2 RLY_SW — external
  NC e-stop loop ties the coil-low leg to Q3.3 only while closed.
- Q3 2N2222A (machined-pin 1x03 socket) at (96, 82): pin1 GND emitter,
  pin2 Q3_B base, pin3 RLY_SW collector.
- R11 1k at (88, 96): MOTOR_EN -> Q3_B. R12 10k at (98, 96): Q3_B -> GND.
- J18 relabeled +12V_MOT; J20 added, same Phoenix 2-pin footprint at
  (115, 105). Both = switched motor 12V outputs.

## Firmware

```
MOTOR_EN = IO40 (high = motors powered)
```

(high lets Q3 sink RLY_LOW through the closed J19 loop -> relay energises
-> +12V_MOT live. E-stop opening the J19 loop drops the relay regardless
of firmware.)

## New net table

| net       | pads |
|-----------|------|
| +12V_RP   | Q2.3, F1.1 |
| RP_GATE   | Q2.1, R10.1 (R10.2 -> GND) |
| +12V_MOT  | K1.5, J18.1, J20.1 |
| RLY_LOW   | K1.2, D5.2, J19.1 |
| RLY_SW    | J19.2, Q3.3 |
| Q3_B      | Q3.2, R11.2, R12.1 |
| MOTOR_EN  | U1A.15, R11.1 |
| +12V_SW   | JP1.2, Q2.2 (F1.1 moved off) |
| +12V taps | K1.1 (coil), K1.3 (COM), D5.1 (flyback) |

## DRC (`kicad-cli pcb drc --severity-all`, after `fill_zones.py`)

- **27 violations**, all benign / inherited categories:
  - 16 `silk_overlap` (silk labels over pads — cosmetic; v1.2 shipped
    with the same category)
  - 11 `lib_footprint_mismatch` (pre-existing library deltas; v1.2
    had 12)
- **0 `shorting_items`, 0 `clearance`, 0 `track_dangling`,
  0 `via_dangling`, 0 `hole_to_hole`.**
- **0 unconnected items** (not even GND — zones filled and stitched).
- Pass criteria met: `pcb13/verify_nets.py` prints each new net's pads
  and confirms one copper island per net (KiCad 10 connectivity model):
  +12V_RP, RP_GATE, +12V_MOT, RLY_LOW, RLY_SW, Q3_B, MOTOR_EN all PASS.
- All `+12V*` tracks = 2.5 mm (`+12V` 86, `+12V_IN` 74, `+12V_MOT` 20,
  `+12V_SW` 6, `+12V_RP` 1 segment; no thin +12V* copper anywhere).

## Build notes

- 2 generator runs; run 2 split +5V into a top/east trunk plus a 0.6 mm
  low-current south tail through the west-mid corridor, which kept +5V
  off CAN_TERM's blocker list (run 1 was destroyed by that rip-up).
- Post-route surgical fixes (pcbnew, then re-fill + re-DRC):
  +12V_MOT K1.5 -> outputs bridge through the x104/x105.8 F.Cu corridor
  (dodges the +12V y62 lane, K1.2, and R12.2), +12V_SW JP1.2 -> Q2.2
  hop via (9.4, 71.5), +12V_RP F1.1 -> Q2.3 widened 0.25 -> 2.5 mm,
  one NEO vertex nudged off J12.2, one duplicate GND via removed.

## UNVERIFIED

- K1 pad mapping (1,2 coil; 3 COM; 5 NO) must be checked against the
  Songle SRD-12VDC-SL-A datasheet — footprint is generic Form A.
- IRF4905 runs warm near 10 A; check dissipation if motors share it.
- Relay contact rating (10 A nominal) vs motor stall current.
- ESC inrush when the relay closes — no precharge on +12V_MOT.
- Zones need `B` in KiCad if the board is edited by hand later.
