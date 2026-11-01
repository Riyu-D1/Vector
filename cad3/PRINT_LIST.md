# cad3/PRINT_LIST.md — Stage D2 print-readiness table

Arm assembly = `cad/arm2b` (arm-arm2b lineage, D2 changes applied) + 2× `cad/act2`
40:1 cycloid actuator modules (J2, J3). Volumes/bboxes measured from the
exported STLs by `cad3/checks/print_audit.py` (trimesh 5.1.1); mass shown is the
solid-equivalent at PETG-CF bulk density 1.31 g/cm³ (Bambu PETG-CF datasheet
density ~1.31 [S bambulab.com PETG-CF TDS, checked 1 Nov 2026]).
Printer target: **Bambu A1, bed 256×256×256 mm** — every part fits (largest
single dimension 200 mm, base_plate X).

## Filament recommendation (A1-compatible)

**PAHT-CF is NOT suitable** on the A1 (open frame, needs enclosure + dry box +
hardened nozzle; per stage brief). Recommend PETG-CF — the same material the
repo's FEA used (E = 4000 MPa, ρ = 1.31 g/cm³, parts_AB.json convention):

| Option | UK shop | Price/kg (inc VAT) | Checked |
|---|---|---|---|
| **Bambu PETG-CF** (1 kg, with spool) | uk.store.bambulab.com — carbon-fibre collection | £32.99 list (£17.39 on bulk sale) | 1 Nov 2026 [S] |
| | additive-x.com (alternative listing) | £32.99 | 1 Nov 2026 [S] |
| **eSUN ePETG-CF** (1 kg) | 3djake.uk | £26.50 | 1 Nov 2026 [S] |
| | amazon.co.uk (eSUN store) | £27.06 | 1 Nov 2026 [S] |

Both need a **hardened-steel hotend** (Bambu's own compatibility table:
PETG-CF → hardened steel *required*, 0.4 mm nozzle OK on the A1
[S uk.store.bambulab.com/products/bambu-hotend-a1-a2, checked 1 Nov 2026]):
- Bambu Hotend A1-series 0.4 mm hardened steel: **£9.99** uk.store.bambulab.com
  (£10.98 inc VAT at additive-x.com) [S, 1 Nov 2026]. Add the hardened extruder
  gear too if not already fitted — "Hardened Steel Upgrade Combo" £42.38
  (uk.store.bambulab.com, P1/A1) [S, 1 Nov 2026].
- Dry PETG-CF before printing (Bambu lists "Recommended to dry out before use").

## Per-part table — arm structure (qty 1 unless noted)

STLs are in `cad/arm2b/out/` (unchanged parts) and `cad3/out/` (D2-changed
parts — marked **D2**). Settings follow the repo convention (act2 BOM):
structural parts 0.2 mm layer / 6 walls / 40% gyroid, small loaded parts
0.12 mm / 100% infill, no supports where geometry allows.

| Part | Qty | STL | Vol cm³ | Mass g | Bbox X×Y×Z mm | Orientation (layer ⊥ load) | Supp. | Walls/Infill |
|---|---|---|---|---|---|---|---|---|
| base_plate | 1 | arm2b/out | 385.5 | 505 | 140.0×200.0×14.0 | Flat on plate face; layers ⊥ g-load | No | 6 / 40% |
| base_link | 1 | arm2b/out | 243.4 | 319 | 92.0×92.0×63.7 | Upright (print as-built); servo walls load in-plane | No | 6 / 40% |
| j1_cradle | 1 | arm2b/out | 103.8 | 136 | 57.5×57.3×54.5 | Open cup up; hoop layers around servo pocket | No | 6 / 40% |
| base_reinf | 1 | arm2b/out | 27.3 | 36 | 92.0×92.0×6.9 | Flat | No | 6 / 40% |
| yaw_limit | 1 | arm2b/out | 13.2 | 17 | 77.0×77.0×7.1 | Flat; horn-bolt counterbores up | No | 6 / 100% |
| link1 | 1 | arm2b/out | 42.6 | 56 | 83.7×77.2×84.0 | Flat face down; layers ⊥ J2 bolt PCD shear | No | 6 / 40% |
| front_spacer_j2 | 1 | arm2b/out | 2.8 | 4 | 34.8×4.0×34.7 | Flat disc face down (layers ⊥ bolt clamp) | No | 6 / 100% |
| flange_j2 **D2** | 1 | cad3/out | 4.7 | 6 | 34.8×11.6×34.8 | Disc face down, hub up; mandrel + free-leg notch print clean | No | 6 / 100% |
| back_spacer_j2 **D2** | 1 | cad3/out | 9.7 | 13 | 57.0×4.7×56.8 | Flat ring face down; spring bore + anchor notch in-plane | No | 6 / 100% |
| upper_out | 1 | arm2b/out | 18.9 | 25 | 61.0×7.0×187.5 | Flat side down (61×187.5 face); layers ⊥ link bending | No | 6 / 40% |
| upper_back | 1 | arm2b/out | 27.6 | 36 | 61.0×4.0×187.5 | Flat side down; countersink side up | No | 6 / 40% |
| front_spacer_j3 | 1 | arm2b/out | 3.5 | 5 | 34.8×5.0×34.7 | Flat disc face down | No | 6 / 100% |
| flange_j3 **D2** | 1 | cad3/out | 5.6 | 7 | 34.8×12.6×34.8 | Disc face down, hub up (thickened disc, extra +1 mm) | No | 6 / 100% |
| back_spacer_j3 **D2** | 1 | cad3/out | 9.7 | 13 | 57.0×4.7×56.8 | Flat ring face down | No | 6 / 100% |
| dogleg_l | 1 | arm2b/out | 19.4 | 25 | 76.1×5.0×99.0 | Flat cheek face down; layers ⊥ J3 shear | No | 6 / 40% |
| dogleg_r | 1 | arm2b/out | 19.4 | 25 | 76.1×5.0×99.0 | Flat cheek face down | No | 6 / 40% |
| fore_l2 | 1 | arm2b/out | 23.9 | 31 | 171.6×4.0×57.0 | Flat plate face down; layers ⊥ forearm bending | No | 6 / 40% |
| fore_r2 | 1 | arm2b/out | 23.8 | 31 | 171.6×4.0×57.0 | Flat plate face down | No | 6 / 40% |
| j4_cradle | 1 | arm2b/out | 28.7 | 38 | 38.0×52.5×30.0 | Servo pocket opening up; layers ⊥ J4 bolt shear | Yes — servo plug overhang slot | 6 / 40% |
| link4 | 1 | arm2b/out | 29.8 | 40 | 66.6×60.6×69.0 | Horn-plate face down; J5 pocket open up | Yes — horn counterbores | 6 / 40% |
| link5 | 1 | arm2b/out | 11.2 | 15 | 38.1×30.0×34.6 | J6 case face down | No | 6 / 40% |
| grip_frame | 1 | arm2b/out | 20.9 | 27 | 56.4×64.0×52.4 | Rack channel opening up | Yes — rack guide channel | 6 / 40% |
| vendor_rack_u | 1 | arm2b/out | 2.4 | 3 | 6.0×36.0×12.0 | Flat flank down; teeth in-plane | No | 6 / 100% |
| vendor_rack_d | 1 | arm2b/out | 2.4 | 3 | 6.0×36.0×12.0 | Flat flank down | No | 6 / 100% |
| finger_u | 1 | arm2b/out | 1.3 | 2 | 14.4×4.0×25.2 | Flat side down | No | 6 / 100% |
| finger_d | 1 | arm2b/out | 1.3 | 2 | 14.4×4.0×25.2 | Flat side down | No | 6 / 100% |
| **Arm subtotal** | | | **1083** | **1419** | | | | |

(vendor_rack_u/d are reBot 02_Rack_U/D solids — printed parts despite the
vendor_ name prefix; they carry rack teeth and must be printed.)

## Per-module table — act2 actuator (qty **2** modules: J2 + J3)

STLs in `cad/act2/out/`. Settings verbatim from `cad/act2/BOM.md`.

| Part | Qty/arm | STL | Vol cm³ ea | Mass g ea | Bbox mm | Orientation | Supp. | Walls/Infill |
|---|---|---|---|---|---|---|---|---|
| housing | 2 | act2/out | 55.6 | 73 | 57.0×57.0×54.4 | Back plate down; pin-bore land prints as bored | No | 6 / 40% gyroid |
| front_ring | 2 | act2/out | 0.9 | 1 | 52.0×52.0×2.0 | Flat | No | 6 / 40% |
| pin_ring | 2 | act2/out | 1.0 | 1 | 51.9×51.9×1.9 | Flat | No | 6 / 40% |
| disc1 | 2 | act2/out | 4.3 | 6 | 44.4×44.4×4.0 | Flat cycloid face down | No | 6 / **100%** (0.12 lyr) |
| disc2 | 2 | act2/out | 4.3 | 6 | 44.5×44.5×4.0 | Flat | No | 6 / 100% |
| carrier | 2 | act2/out | 12.1 | 16 | 43.0×43.0×10.0 | Flat | No | 6 / 100% |
| out_flange | 2 | act2/out | 3.8 | 5 | 44.0×44.0×2.6 | Flat | No | 6 / 100% |
| hub | 2 | act2/out | 4.9 | 6 | 20.0×44.0×18.0 | Flange face down | No | 6 / 100% |
| mag_puck | 2 | act2/out | 0.5 | 1 | 12.0×12.0×6.0 | Flat | No | 6 / 100% |
| **Module subtotal** | | | **87.4 ×2** | **114 ×2** | | | | |

act2 BOM notes: discs/hub/carrier/out_flange ideally PA-CF (dry 8 h @ 80 °C) —
on the open A1 keep **PETG-CF** and accept lower wear margin; grease ring pins
and discs with PTFE or lithium grease; fit-test the 6808 seat and Ø3 pin holes
first (print only the housing front 12 mm as a test coupon).

## Vendor (not printed) — for completeness

`vendor_sts3250_j1`, `vendor_sts3250_j4` (STS3250 servos), `vendor_sts3215_j5`,
`vendor_sts3215_j6`, `vendor_sts3215_g` (STS3215), `vendor_spring_j2/j3`
(Springmasters 471671 stock spring — see BOM_delta), `vendor_gear_grip`,
`vendor_act_j2/j3` + `vendor_actout_j2/j3` (actuator proxies — real module is
the act2 build above), module hardware per `cad/act2/BOM.md`
(bearings/dowels/motor/encoder).

## Totals

- Solid-equivalent volume: 1083 + 175 = **1258 cm³** → **1647 g** at 100%
  density (upper bound; real extruded mass ≈ solid vol × fill fraction).
- Estimated print mass at recommended settings (mostly 40% gyroid + walls):
  **~0.8–0.9 kg [U]** — fits on a single 1 kg spool.
- Filament cost: ~**£24–33** (one 1 kg spool of eSUN or Bambu PETG-CF) +
  **~£10** hardened hotend if not fitted.
- Longest part 200 mm (base_plate) — all parts fit the 256³ bed with margin.
