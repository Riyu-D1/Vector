# STATUS — order-ready stage (D3), branch arm-ord

Date: 2026-11-01. Worktree `~/Vector-wt/ord`, base `arm-cad3@11ad11e`.
All work is under `order/`; no product files touched; no carts, no buys.

## Plain summary

The arm is orderable with caveats. The big-ticket parts all have real UK
prices today except the STS3250 pair (genuine-UK source unresolved).
The carrier PCB needed a real fix: **K1's pin map in v1.3 was wrong on
all three nets** (stage wording assumed 1/2=coil, 3=COM, 5=NO; the actual
Sanyou/Songle SRD Form A is 1=COM, 2+5=coil, 3=NO, 4=NC). A surgically
patched board lives in `order/pcb13_fix/` with gerbers, DRC 27 benign
violations / 0 unconnected, and `verify_nets.py` PASS. Hand stress calcs
show the FEA was optimistic but the joints pass once dowels/inserts are
treated as load parts; two marginal bounds are documented with fixes.

## Deliverables

| File | Contents |
|---|---|
| `STRESS_SANITY.md` | 7 hand checks vs 25/12.5 MPa printed limits |
| `BOM_FINAL_GBP.csv` / `BOM_FINAL.md` | 50-line UK BOM, verified vs [U] |
| `PCB_ORDER.md` | K1 evidence + fix, DRC, JLCPCB options/files |
| `BUILD_GUIDE.md` | print->power-up sequence, wiring table, checklist |
| `pcb13_fix/` | corrected `.kicad_pcb`, refilled zones, gerbers+drill, `drc_fix.json`, `refill.py`, patched `gen_pcb.py` (records intended map) |

## Money

- **Verified total: £367.89**
- **Total incl. [U] estimates: £593.64** (eBay STS3250 case)
- Worst-case with verified-but-pricey Amazon STS3250s: **£826.36**

## [U] table

| Item | Why unverified |
|---|---|
| STS3250 x2 | Only UK-priced line is a suspicious ~£15 eBay/Shenzhen listing; genuine disty ~£61-136 — flag & test-first-buy |
| 12V PSU JLCPCB quote | no live quote pulled; ~£18 landed est. |
| AS5578 washers, 6707 | page not re-verified today |
| Dowel 3x12/4x8 prices | same-band assumption |
| SRD-12VDC-SL-A UK stock | Switch Electronics OOS; LCSC alt |
| IRF4905, TJA1051T, passives | [U] smalls pricing |
| Spring 471671 handedness | 1 LH + 1 RH needed; SKU question open |
| Servo cables, wire, crimps, connectors, inserts, Loctite, grease, OLED/IMU/EC11, heatsinks, USB | small-part estimates |
| Motor dims/mass/winding R | vendor numbers unverified from D2 |
| Homing current/stop offset, FT_BAUD 1 Mbps | bench-verify at bring-up |
| ESC inrush on relay close | no precharge on +12V_MOT |
| IRF4905 dissipation near 10 A | flagged from pcb13 STATUS |

## Order blockers (must resolve before clicking buy)

1. **STS3250 source** — decide cheap-test-first (eBay) vs verified-
   distributor (Amazon/OpenELAB/BABSCO); both in BOM CSV.
2. **JLCPCB real quote** — upload `order/pcb13_fix/gerbers/` zip at
   checkout; confirm landed price.
3. **Relay part on the FIXED board** — order SRD-12VDC-SL-A (LCSC
   C93716 fine); confirm the pcb13_fix map at soldering time.
4. Spring handedness SKU check at Springmasters.
5. Gear m1 16T bore machining [U] (or accept [U] price).

## Stress sanity — bottom line

FEA spiders spread reactions => patch stresses are 2-4x optimistic.
Worst-case-single-element bounds fail SF<2 at: out-flange M3-only (if
dowels loose), single-link-pilot carry, cycloidal single-lobe bend, J4
cradle pilot ligament. All resolve to SF>2 with documented assembly
actions (firm dowels + inserts + even pilot torque + wear monitoring) —
no geometry change needed, no CAD edit made.
