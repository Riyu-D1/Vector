# BOM_FINAL — SOMA hybrid arm, UK procurement list

Machine CSV: `BOM_FINAL_GBP.csv`. All prices GBP inc VAT where the
listing is a UK retail page; date checked 2026-11-01. `[U]` = unverified
— never ordered blind. Nothing bought, no carts checked out.

## Totals

- **Verified-lines total: £367.89** (every line with a live UK price
  confirmed today).
- **Total including [U] estimates: £593.64** — with the flagged cheap
  eBay STS3250s. If STS3250 must be a verified UK line instead, swap in
  Amazon UK B0FLJ6289C @ £136.15 ea: **£826.36**.
- Postage is extra where noted (DigiKey free >£33; Search4Parts £3.95
  <£60; WDS/Frasar small-order p&p [U]).

## Open sourcing items (stage-required resolutions)

1. **STS3250 genuine UK source — UNRESOLVED [U].** Cheapest real listing
   is eBay UK `flyfuntech2014` ~£15.31 + £4.48 p&p, ships Shenzhen —
   suspiciously under every other channel (US $64.99, EU ~€72, Amazon UK
   £136.15). The D2 BOM already flagged it. Risk: clone/remarked unit.
   Recommendation: order 1 first, run the Feetech FD debug tool to check
   firmware ID + stall torque, then order the second. If authenticity
   matters more than money, BABSCO (US, $64.99 + ship) or OpenELAB
   (€72.40) are established distributors. Budget line uses eBay price.
2. **Tarot TL2955 — RESOLVED.** FlyingTech UK £34.90 inc VAT in stock;
   3DXR £34.95 second source. Genuine Tarot, UK stock.
3. **B-G431B-ESC1 — RESOLVED.** DigiKey UK £30.06+VAT = £36.07, 2,277 in
   stock today (99-week factory lead time bypassed by disty stock).
   Farnell also lists UK stock (912 pcs, price not shown in GBP page).
4. **AS5600 breakout — RESOLVED.** 38-3D UK £4.04; Pi Hut Grove variant
   £6.30 as second source. Board is 23x23 mm class — ENC_W pocket fits.
5. **Rack/gears — RESOLVED.** Gear racks (reBot 02_Rack) are **printed**
   parts on the A1 (`vendor_rack_u/d` in the D2 print list) — no
   purchase. The m1 16T spur gear is bought steel (Technobots
   SS10/16B £6.16) and needs its bore/hub machined to the horn PCD —
   machining is a [U] service cost; alternative Kramp MOD116 £1.46 +
   £4.80 delivery via Blueperry.
6. **Springmasters 471671 — VERIFIED price £4.708** (D2). Handedness:
   catalogue sells one helix direction; J2 and J3 want opposite winds —
   [U] whether the counter-wind unit is a separate SKU; bench workaround
   is to mount one spring mirrored.

## Notes / hazards

- Mains PSU (RS-100-12) — 230 VAC wiring: qualified person, earthed
  metal case, fuse the IEC inlet. LiPo alternative NOT recommended
  for bench (12 V 3S pack ok if used — charging/fire hazard flagged).
- Relay SRD-12VDC-SL-A: **K1 pin mapping on v1.3 was WRONG** — see
  `PCB_ORDER.md` and `pcb13_fix/`. Order the corrected board.
- Heat-set inserts need a soldering-iron press tool (~£3 tip adapter,
  in the crimp-kit allowance).
- Prices with "ships Shenzhen" attract 20% import VAT + ~£8 courier
  handling over £135 (under £135 VAT usually collected at checkout).
- Spares column: +1 on cheap mechanicals, +1 servo, no spare ESC/motor
  (budget); increase to +1 each if downtime matters (+£70.97).

## Grouped spend (verified+est, eBay servo case)

| Group | £ |
|---|---|
| Actuators (motors+ESC+encoders+bearings+pins) | ~244 |
| Servos (2x STS3250 eBay + 4x STS3215) | ~130 |
| Carrier PCB + electronics + PSU + e-stop | ~120 |
| Filament + nozzle + springs + gear | ~58 |
| Fasteners, wire, adhesives, tooling | ~42 |
