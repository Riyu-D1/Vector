# BOM-prototype.md — hardware kit for the D13 print pack (qty 1 set)

Prototype-only kit: master + plate + **passive pen tool**. No servo, no
rack, no 12 V wiring in this pack.

| # | item | qty | where in CAD | source / price | status |
|---|---|---|---|---|---|
| 1 | M4 ball plunger (commercial), e.g. M4×10 | 1 | radial detent bore Ø4.2 at a74/ph110 | UK sources checked in D12 **2026-11-05**: Good Hand K0316 M4×10 ~£2.50 (45 in stock), WDS 823 M4×10 ~£6.23 (stock<10), Ross Handling M4 ~£6.72 | `[U bench fit]` — commercial plungers carry a Ø2.5 ball vs the CAD Ø4 ball / Ø3.0 dimple; dimple still engages ~0.35 mm. Bore mouth needs an M4 thread (heat-set insert or printed thread). |
| 1a | — or DIY: steel ball Ø4 + compression spring ~Ø3.2 × 8 + M4 grub | 1 set | same bore | generic hardware `[U]` | fallback if no plunger |
| 2 | M3 × ~8 ISO 7380 button-head screws | 4 | horn holes Ø3.4 PCD14 (as stock w_grip_frame) | generic `[U]` — reuse the stock horn screws/spares | `[U length]` — plate 6 mm + ~4 mm into the horn; reuse stock length on hand |
| 3 | horn centre screw | 1 | master centre bore Ø7.2 access | reuse the stock J6 horn hardware | — |
| 4 | M3 grub/set screw ~M3×4–6 | 2 | pen pilots Ø3.0 at a136, ph 30/210 — self-tap, **not** heat-set inserts (an insert would need ~Ø4.3) | generic `[U]` | `[U]` |
| 5 | Pogo pins ~Ø1.5 barrel, ~0.6–0.8 mm working travel | 5 | floor bores Ø1.8 (GND, +12 V, DATA, SP1, SP2) | sourced UK **2026-11-05**: P75-series spring test probes (barrel ~Ø1.36, head Ø1.5) — Amazon UK 100-pc mixed P75/P50 £4.99–£10.99 in stock; PicClick UK P75-E3 100-pc £7.81 | `[U fit]` — barrel ~Ø1.36 in Ø1.8 bore needs a sleeve/CA or a tighter ream; **pen tool is passive — pogos optional for this pack** |
| 6 | PETG-CF filament | ~27 cm³ (~35 g) | all three parts | user stock | see PRINT.md |

Not needed here (later packs): STS3215 servo + wiring, rack fasteners,
M3 heat-set inserts, 12 V bus wiring.
