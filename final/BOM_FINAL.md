# BOM_FINAL — SOMA arm, UK procurement list (F1 refresh)

Machine CSV: `final/BOM_FINAL_GBP.csv`. Prices GBP inc VAT where the
listing is a UK retail page. `[U]` = unverified — never order blind.
Nothing bought, no carts checked out.

## What changed vs `order/BOM_FINAL*` (D3)

- **STS3250 sourcing decided**: the user chose the verified seller —
  **Amazon UK B0FLJ6289C, £136.15 each** (rechecked **2026-11-02**:
  still £136.15, in stock, "usually dispatched within 4–5 days",
  free UK delivery). The suspicious ~£15 eBay/Shenzhen line is dropped.
- **D4 BOM delta applied**: `cyclo4/BOM_delta.md` — **zero purchased
  items**. The cycloidal discs stay printed PETG-CF (4.25 mm, near-zero
  flank); ring pins unchanged (41× ISO 8734 Ø3×10 + spares already in
  the dowel line).
- **Added**: metric feeler-gauge set (~£6 [U]) — required for the
  `final/out/coupon.stl` clearance check before printing the discs.
- **Added (R9)**: 1× ISO 8734 Ø3×18 dowel — the wrist's second J4
  bearing pin. Price TBC (same WDS precision-dowel family as the
  3×12/4×8 lines); totals unchanged.
- D4's flagged firmware change is now **done**: phase-current caps
  J2 3.71 A / J3 2.47 A + 75 ms soft-stop ramp (see
  `final/BUILD_GUIDE.md` §7).
- **F2 BOM delta applied**: `wrist2/out` D6 wrist replaces the arm2b
  printed wrist — **zero purchased items** (same J4 STS3250, same 3×
  STS3215 for J5/J6/gripper, same racks/gear/fingers shifted +5.6 mm).
  Printed wrist structure drops 90.6 → 51.6 cm³ (−39 cm³ ≈ −51 g of
  PETG-CF at solid equivalent).

## Totals (computed from the CSV)

- **Verified + resolved lines: £674.07** — includes the two Amazon
  STS3250s at £272.30.
- **Total including [U] estimates: £825.16**.
- For reference, D3's headline numbers were £367.89 verified / £593.64
  all-in *with the cheap eBay servos and a slightly different counting
  rule* (ESP32 counted as unpriced); the Amazon servo decision alone
  adds +£232.72 over that case.
- Postage extra where noted (DigiKey free >£33; Search4Parts £3.95
  <£60; WDS/Frasar small-order p&p [U]).

## Open sourcing items

1. **STS3250 — RESOLVED (F1).** Amazon UK verified seller per user
   decision — see above. Still bench-verify both units on arrival
   (Feetech FD debug tool: firmware ID + stall torque) — £136/each
   buys genuine but grey-channel stock.
2. **Tarot TL2955 — RESOLVED.** FlyingTech UK £34.90 inc VAT in stock;
   3DXR £34.95 second source.
3. **B-G431B-ESC1 — RESOLVED.** DigiKey UK £36.07, 2,277 in stock on
   1 Nov (factory lead-time bypassed by disty stock).
4. **AS5600 breakout — RESOLVED.** 38-3D UK £4.04; Pi Hut Grove £6.30
   second source. 23×23 mm class — ENC_W pocket fits.
5. **Rack/gears — RESOLVED.** Racks printed on the A1; m1 16T spur
   bought steel (Technobots £6.16) + bore machining [U] service cost.
6. **Springmasters 471671 — VERIFIED £4.708.** Handedness [U]:
   catalogue sells one helix; J2/J3 want opposite winds — bench
   workaround = mount one spring mirrored.
7. **Songle SRD-12VDC-SL-A relay — [U] out of stock at Switch
   Electronics on 1 Nov; alt LCSC C93716.** Any SRD-12VDC-SL-A works —
   the pcb13_fix pad map assumes the Songle pinout.

## Notes / hazards

- Mains PSU (RS-100-12) — 230 VAC wiring: qualified person, earthed
  metal case, fuse the IEC inlet. LiPo alternative NOT recommended
  for bench.
- Relay K1 pin mapping on v1.3 was wrong — order the corrected board
  (`order/PCB_ORDER.md`, `order/pcb13_fix/`).
- Heat-set inserts need a soldering-iron press tool (~£3, in the
  crimp-kit allowance).
- Prices "ships Shenzhen" attract 20% import VAT + ~£8 courier
  handling over £135 (under £135 VAT usually collected at checkout).
- Selective pin fit needs dowel variety: the 2×50 ISO 8734 boxes give
  ~18 spares after the 82 ring pins — enough spread for the F1
  pin-fit procedure (`final/PRINT_LIST.md`).
- Spares: +1 on cheap mechanicals, +1 servo already counted; no spare
  ESC/motor (budget) — +£70.97 if downtime matters.

## Grouped spend (all-in estimate, Amazon servo case)

| Group | £ |
|---|---|
| Actuators (motors+ESC+encoders+bearings+pins) | ~244 |
| Servos (2× STS3250 Amazon + 4× STS3215) | ~363 |
| Carrier PCB + electronics + PSU + e-stop | ~120 |
| Filament + nozzle + springs + gear | ~58 |
| Fasteners, wire, adhesives, tooling, gauges | ~48 |
