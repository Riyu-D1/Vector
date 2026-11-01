# PCB_ORDER — SOMA carrier v1.3 manufacturing pack

Board: `soma-carrier-v13` — 135×115 mm, 2-layer, all through-hole,
F.Cu + B.Cu. Source: branch `pcb-v13` `pcb13/` (untouched). **Order the
FIXED board from `order/pcb13_fix/` — see the K1 finding below.**

## K1 relay check — MISMATCH found and fixed

Stage wording assumed SRD-12V pads `1/2 = coil, 3 = COM, 5 = NO`.
Evidence against the real part (Songle SRD-12VDC-SL-A / Sanyou SRD):

- Board footprint = KiCad `Relay_SPST_SANYOU_SRD_Series_Form_A`
  (pad-for-pad identical to the official library): pad 1 @(0,0),
  pad 2 @(1.95,6.05), pad 3 @(14.15,6.05), pad 5 @(1.95,-5.95);
  drills: pads 1,3 = 1.3 mm (contact blades), pads 2,5 = 1.0 mm (coil).
- Sanyou SRD datasheet PCB layout, Form A (bottom view): the coil is
  the two Φ1.0 holes (right column pair); the Φ1.3 offset-mid hole is
  COM; the Φ1.3 bottom-left hole is NO; the omitted fourth position is
  NC. Cross-mapped to KiCad numbering: **pad 1 = COM, pads 2+5 =
  coil, pad 3 = NO, pad 4 = NC (absent)**.
- v1.3 as committed wired K1.1=+12V (treated as coil), K1.3=+12V
  (treated as COM), K1.5=+12V_MOT (treated as NO). Real result would
  have been: coil across COM/NO and +12V_MOT shorted to the coil
  pin — **relay dead and the "switched" rail hard-wired**. MISMATCH,
  confirmed on all three nets.

Fix (copy only, in `order/pcb13_fix/`): pad nets reassigned
`1:+12V(COM) 2:RLY_LOW 3:+12V_MOT(NO) 5:+12V(coil)`; `+12V` route now
feeds K1.5→K1.1→D5.1; `+12V_MOT` leaves K1.3 through the proven
x≈105.8 corridor to J18/J20. Corrected net table:

| net | pads |
|---|---|
| +12V_MOT | K1.3, J18.1, J20.1 |
| +12V (relay taps) | K1.5, K1.1, D5.1 |
| RLY_LOW | K1.2, D5.2, J19.1 |
| RLY_SW | J19.2, Q3.3 |

## DRC

- **Committed v1.3 (pcb-v13 branch), re-run with kicad-cli 10.0.4:
  27 violations, 0 unconnected** — identical to the committed report:
  16 cosmetic `silk_overlap`, 11 inherited `lib_footprint_mismatch`;
  0 shorting/clearance/dangling/hole violations.
- **Fixed copy `order/pcb13_fix/soma-carrier-v13.kicad_pcb`:** produced by
  surgical patch of the committed board (pad-net swap + copper reroute —
  the full A* re-generation was abandoned as unbounded). Then
  pcbnew `ZONE_FILLER` refill + island strip.
  **DRC re-run: 27 violations, 0 unconnected** — identical profile to
  the committed board (16 `silk_overlap`, 11 `lib_footprint_mismatch`,
  all benign/inherited; 0 shorting/clearance/dangling/hole).
  `verify_nets.py` **PASS** — `+12V_MOT` island = {K1.3, J18.1, J20.1};
  `+12V` reaches K1.1/K1.5/D5.1. Evidence: `drc_fix.json` in the dir.

## Files to upload to JLCPCB

From `order/pcb13_fix/gerbers/` (regenerated after fix):

- Layers: `*-F_Cu.gtl`, `*-B_Cu.gbl`, `*-F_Mask.gts`, `*-B_Mask.gbs`,
  `*-F_Silkscreen.gto`, `*-B_Silkscreen.gbo`, `*-Edge_Cuts.gm1`,
  `*-F_Paste.gtp`, `*-B_Paste.gbp` (paste only needed for SMD assembly).
- Drill: `soma-carrier-v13.drl` (PTH, all holes plated).
- `*.gbrjob` is metadata, not required by the fab.
- BOM: `bom.csv` (delta vs v1.2 — full list in `order/BOM_FINAL_GBP.csv`).
- CPL: **none** — board is 100% through-hole; there is no SMD pick
  data. Hand assembly only (see below).

## Recommended order options

- Layers: **2**; Thickness: **1.6 mm**; Finish: **HASL lead-free**;
  Copper: **1 oz** (motor rail is 2.5 mm tracks + pours, 6 A fuse —
  1 oz is adequate at <20 °C rise; 2 oz if offered free).
- Quantity: **5** (JLCPCB minimum; ~2 boards' worth of spares).
- JLCPCB quote: **[U]** — jlcpcb.com was reachable for search but no
  live quote endpoint was used; typical landed cost for 5× this size:
  ~US$5 boards + ~US$15-20 shipping + 20% UK import VAT ≈ **£18 landed**
  (est., get real quote at checkout; upload gerber zip from
  `order/pcb13_fix/gerbers/`).

## Assembly: hand-solder vs JLCPCB/LCSC PCBA

All components are through-hole (Phoenix blocks, XT60, headers, relay,
TO-220, axial passives, socketed ESP32/Q3). JLCPCB assembly cannot
place TH connectors economically — **hand soldering is the correct
route**; every part is beginner-safe with a fine tip. LCSC stocks
SRD-12VDC-SL-A (C93716, ~$0.39@5, 18.5k in stock) — a $0.40 relay,
worth adding to the fab order if placing one anyway.

## [U] list for this board

- Live JLCPCB quote + UK import total.
- `verify_nets.py` + refill + island-strip all completed on the FIXED
  board — PASS (see DRC section above).
- K1 coil polarity is non-polarized (datasheet) — either coil leg high
  is fine; fixed map puts +12V on pad 5, RLY_LOW on pad 2.
