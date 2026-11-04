# STATUS — SOMA carrier PCB v1.4 (pcb14/)

Copy of `pcb13/` (v1.3) with every routed net re-laid by hand to look
hand-routed: fewer vias, 0°/45°/90° copper only, tidy bundles, strict
layer discipline. All v1.3 product files are untouched; everything lives
under `pcb14/`. Placement, footprints, netlist and the GND pours are
unchanged — only the copper between the pads is new.

## Part A — v1.3 audit findings (real numbers)

`kicad-cli pcb drc --severity-all` on soma-carrier-v13.kicad_pcb:

- 27 violations, all benign/inherited: 16 `silk_overlap`,
  11 `lib_footprint_mismatch`. 0 shorting, 0 clearance, 0 unconnected
  (zones filled). GND "unconnected" only appears on an unfilled copy.
- `verify_nets.py`: PASS — every checked net one copper island.
- `audit_pins.py`: 27 routed nets, 40 GND pads, 29 NC pads; rail joins
  J15(+3V3/+5V), U2(+3V3/+5V_MCU), D1(+5V/+5V_MCU), J3(+12V/+5V),
  U1B(+3V3/+5V_MCU), JP1(+12V_IN/+12V_SW).
- `check_pads.py`: OK — 177 emitted pads match the generator map.

Routing review (why it looked autorouted):

| net | mm | vias | non-45° segs |
|-----|-----|------|--------------|
| +12V | ~300 | many | 16 dead-end stubs |
| totals | 2625.5 | 165 (24 GND stitch) | 412 |

- 165 vias total, 1843 segments, 412 diagonal segments off 0°/45°/90°.
- 39 dead-end stubs (+12V alone had 16), 11 acute-angle corners
  (worst 9.7° on +12V_IN), max detour ratio 2.42.
- No via-within-1 mm-of-pad or track-within-0.3 mm-of-edge violations.
- Widths were already correct: +12V* 2.5 mm, +5V/+5V_MCU/+3V3 0.6–1.0,
  signals 0.25.

Electrical sanity (vs STATUS-pcb13 intent): Q2 IRF4905 orientation
correct (source→F1.1, drain→JP1.2, gate→R10), K1 coil/COM/NO and D5
flyback polarity correct, Q3 pinout (1=E GND, 2=B Q3_B, 3=C RLY_SW)
correct, MOTOR_EN path U1A.15→R11.1→Q3_B verified, VSNS on ADC1 pin,
U2 = TJA1051T/3 CAN transceiver wired correctly (TXD/RXD/VIO/S). No
real bugs found; nothing needed fixing in v1.4 beyond the re-route.

## Part B — the re-route

Placement untouched (0 nudges — the brief's 1–2 mm allowance unused).
All 27 nets were re-laid by a handwritten route table
(`routes_v14.py`, ~113 legs) emitted by `reroute.py`, a leg/chamfer
engine that validates against real pad geometry before writing:

- exit checks (every leg lands on its pads), pad-vs-track and
  track-vs-track clearance at real width, dangling-endpoint and
  missed-pad detection, via dedup at layer junctions.
- It reported `legs 113, segments 359-363, vias 65, warnings: 0`
  before every write.

Style achieved:

- F.Cu = horizontal lanes, B.Cu = vertical descents (visible in
  render-top/bottom.png and the copper maps).
- Every corner is a 45° chamfer pair; 0 non-45° diagonals at >0.06 mm
  asymmetry (v1.3 had 412).
- Bundles: ENC_A/ENC_B/ENC_SW nested descents into J13, SDA1/SCL1 pair,
  CANH/CANL pair to U2/J17, +3V3/U2 feeds as parallel lanes.
- Wide short power: +12V* 2.5 mm, +5V 0.8/1.0, +3V3 0.6, signals 0.25.
- 15 explicit GND stitch vias + 2 added by the zone healer.

## Part C — proof

| metric | v1.3 | v1.4 |
|--------|------|------|
| vias | 165 | 67 (−59 %) |
| segments | 1843 | ~413 |
| track length | 2625.5 mm | 3077.5 mm |
| non-45° segments | 412 | 0 |
| dead-end stubs | 39 | 0 |
| acute corners | 11 | 0 |

- `kicad-cli pcb drc --severity-all` after fill_zones: **27 violations,
  all inherited cosmetic** (16 silk_overlap + 11 lib_footprint_mismatch
  — the same classes v1.3 carried). **0 unconnected items** (GND pours
  filled + stitched), 0 shorting, 0 clearance, 0 dangling.
- `verify_nets.py` (KiCad python): **PASS** — every net one copper
  island; netlist equivalence to v1.3 holds (same pad sets per net as
  the `audit_pins.py` table above).
- `check_pads.py`: **OK — 177 file pads all match internal map, all
  on-board.** (Generated with `PLACE_ONLY=1 PAD_DUMP=1`; the run must
  stub out gen_pcb.py's module-level `heal_unconnected()` call or it
  burns ~15 min of A* on an unrouted place-only board.)
- Renders: `render-top.png`, `render-bottom.png`,
  `render-copper.svg` in `pcb14/`.
- Fab: `gerbers/` — 17 gerbers + `soma-carrier-v14.drl` + `bom.csv` +
  `soma-carrier-v14-jlcpcb.zip` (JLCPCB-ready).
- Board silk title updated `SOMA BASE CARRIER v1.3` → `v1.4`
  (file + generator label).

Route-level geometry decisions worth logging (the "nudge" list —
tracks, not parts):

- +5V west riser on B.Cu moved x19.9 → x20.5, then jogged east at y55
  to descend x24.9: F1.1's real pad box is x14.25–19.75 and D4.1's is
  x20.70–23.30, so the only w0.8 corridor is a dogleg between them
  (validator caught the DRC short at x19.9 first).
- CANH's R9.2 branch extended to (82.9, 88.8) — the first emission
  left a 0.1 mm dangling end at R9.2's pad edge.
- BUZ exits U1B on F at y46 and descends far east x121.7 into R5.1 —
  avoids the entire U2/C5/C6/R11/CAN knot.
- ENC_SW approaches J13.5 on F.Cu at y96.3 from the east — the B.Cu
  lane stack into J13's pins was unresolvable below the pad row.
- BZB column x120.9, BUZ/BZB pair kept concentric on the east edge.

## Build notes

- `reroute.py` + `routes_v14.py` are the routing authority for v1.4;
  `gen_pcb.py` remains the placement/footprint authority. Re-routing:
  `python3 reroute.py` (validates, then writes), then KiCad-python
  `fill_zones.py soma-carrier-v14.kicad_pcb`, then `bash fab.sh`.
- `fill_zones.py` prunes ~45 unfilled island fragments per fill — its
  "SPLIT nets" report lists pour fragments with 0 pads, not real nets.
- `fab.sh` uses KiCad's bundled python (the `/Users/.../soma/.venv`
  path from the v1.3 script does not exist on this machine).
- `verify_nets.py`, `audit_pins.py`, `check_pads.py` updated to the
  v14 file names (v13 copies untouched).

## UNVERIFIED [U]

- [U] Same hardware caveats as v1.3: K1 pad mapping vs the SRD-12VDC-
  SL-A datasheet, IRF4905 dissipation near 10 A, relay contact rating
  vs motor stall, no precharge on +12V_MOT.
- [U] 16 silk_overlap items are cosmetic but print as fab warnings;
  check silkscreen legibility on the gerbers before ordering.
- [U] Zone fills are baked into the file; if the board is re-edited by
  hand in KiCad, press `B` to refill before fab.
- [U] LiPo/battery wiring, the e-stop loop through J19, and motor
  wiring are the user's responsibility to check before powering. No
  mains on this board.
