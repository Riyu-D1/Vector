# cad3/BOM_delta.md — Stage D2 bill-of-materials delta

Delta vs the current arm2b BOMs (`cad/arm2/BOM.md` + `cad/arm2b/BOM.md`).
Prices real where cited; [U] = unverified. Dates checked 1 Nov 2026.

## Added

| Qty | Item | Source / price | Notes |
|---|---|---|---|
| +1 | **Feetech STS3250** (ST-3250-C001) 12 V TTL servo, 50 kg·cm stall, 74.5 g | eBay UK flyfuntech2014 ≈ **£15.31 + £4.48 p&p** (ships Shenzhen) [S, 1 Nov 2026]; US retail $64.99 BABSCO [S] | J4 replacement. Same 45.22×24.72×35 mm case, 25T spline, same bus — drops into the existing J4 pocket. |
| +2 | **Springmasters 471671** metric torsion spring, stainless: wire Ø2.0, OD 22, suggested mandrel Ø14.8, leg 70 mm, ends figure B | springmasters.com/shop/471671 — **£4.708 ea** (1–11 qty band), £4.002 @12–24 [S, 1 Nov 2026] | J2 + J3 balance springs. Stock legs are 70 mm — cut/form to the printed notches on the bench [D]; achieved rate k≈0.55 N·m/rad target is **[U]** (shim on bench, see D1 docs). Order 1× LH + 1× RH helix [U handedness variants exist]. |

## Removed

| Qty | Item | Notes |
|---|---|---|
| −1 | Feetech STS3215 servo (J4 position) | Moves to spares; J5/J6/gripper keep their STS3215s (3 remain). |
| −2 | 6803ZZ bearing 17×26×5 (J2, J3 back) | Seat cavity reclaimed as the spring coil pocket; the spring mandrel now centres the J2/J3 back side. Joint stiffness re-verified by the spring sweep + interference checks. |

## Unchanged-count hardware (still needed)

- All M3 fasteners as `cad/arm2/BOM.md` lines 21–25 and `cad/arm2b/BOM.md`
  lines 13–15 — the spring features are printed (notches/mandrel/recess), no
  new screws.
- act2 module hardware (dowels, bearings, motor, encoder) unchanged.

## Mass delta (carried by the arm)

| Item | Δ mass |
|---|---|
| STS3250 @J4 vs STS3215 | +19.5 g [S Feetech datasheet 74.5 g vs 55 g] |
| 2× 471671 springs | +~40 g [U — Ø22 coil, ~9.5 mm wound length; proxy used 20 g ea] |
| −2× 6803ZZ | −14 g (7 g each [U typical]) |
| Printed feature changes (mandrel turn-down vs bore/seat cuts) | ≈ −2 g |
| **Net** | **≈ +43 g [U]** |

The D1 gravity model already used 74.5 g for J4 and passed max-payload at
0.5 kg; the +40 g of springs sits at the J2/J3 axes (near-zero torque arm at
J2, small at J3) — worst-case recheck in `cad3/STATUS-cad3.md`.

## Open sourcing questions

1. **J1 servo**: upstream `cad/arm2` already pockets/names an STS3250 at J1
   (BOM line 18, flagged [U case = STS3215 case]). D2 does not change J1 —
   confirm the physical J1 unit is also an STS3250 when ordering (consistent
   74.5 g in PARTS already used for it upstream).
2. 471671 leg form: stock figure-B legs at 70 mm need bench cutting/bending
   into the pocket notches; if the formed spring can't hold rate, the fallback
   is 471672 (OD 27 — does **not** fit the Ø23.2 pocket, would need a bigger
   pocket → rejected for envelope growth) or a custom wind [U].
