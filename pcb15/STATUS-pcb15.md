# STATUS — SOMA carrier PCB v1.5 (pcb15/)

Copy of `pcb14/` (v1.4) re-spun to fix the findings in
`pcb14/check/CHECK-pcb14.md`. All v1.4 product files are untouched;
everything lives under `pcb15/`. `routes_v15.py` is the hand-route
authority; `gen_pcb.py` remains the placement/footprint/netlist
authority. Same pipeline: `PLACE_ONLY=1 PAD_DUMP=1 python3 gen_pcb.py`
→ `python3 reroute.py` → KiCad-python `fill_zones.py` → `bash fab.sh`.

## Part A — findings fixed (from CHECK-pcb14.md)

| # | finding | fix applied |
|---|---------|-------------|
| F1 | **ESP32-S3-DevKitC-1 socket mirrored 180°** — U1A/U1B pads mapped to module pins `23−N`, so J1/J3 met the headers swapped: pad U1B.1 (22.14 mm W end) carried GND onto module J1-1 (3V3 out) → dead short, and every GPIO landed on the wrong pin. Verified independently against the official Espressif user guide v1.1 (J1: 1=3V3 … 21=5V 22=GND; J3: 1=GND, 2=IO43/TX, 3=IO44/RX, 19=IO20, 20=IO19, 21-22=GND; pin 1 at the USB end — silk already says "USB->W, TOP=J1 BOT=J3"). | Remapped U1A/U1B pad→net tables 1:1 with physical pad N ↔ module header position N. Every GPIO function re-landed on its intended IO (verified by audit_pins vs the proposed_fixes table). |
| F2 | **NeoPixel data driven at 3.3 V logic into 5 V pixels** — marginal high-level margin. | New parts: U3 = 74AHCT125 (DIP-14_W7.62mm_Socket) level shifter at (109,46) rot 90°, R13 = 330R series resistor at (108,50.5), C8 = 100 nF supply cap. Chain: U1B.4 (NEO, IO48) → U3.2 (1A) → U3.3 (1Y=NEO_A) → R13.2 → R13.1 → J14.2 (NEO5V) → pin. U3.14 on +5V, all unused inputs + /OE pins (1,4,5,9,10,12,13) tied to GND, unused outputs (6,8,11) float. |
| F3 | **12 V copper too thin / single-via layer transitions** for a 10 A rail. | +12V_IN / +12V / +12V_SW / +12V_MOT widened to **4.5 mm** trunks (2.5 mm necks only where pad throats force it, e.g. Q2's 2.54 mm-pitch gate window), parallel via pairs on every layer change plus extra stitching vias: +12V_IN (24.0,78.5), +12V (86.2,12.8) and (116.8,20), GND (87.5,79.5). |
| F4 | **No protection on the RS-485/UART RX line.** | Optional RX protection added: D6 = 3V6 zener (OPT footprint, silk "D6 OPT 3V6") clamps the RXA node; D7 = 1N4148 documented in BOM. Fit-or-jump per assembly. |
| F5 | **Fuse behavior undocumented.** | README now states F1 = 10 A inline on +12V_IN, what it protects and what it does not, plus the single-5V-source rule. |
| F6 | **Jog encoder connector order wrong.** | J13 repinned so the silk `JOG G-3V-SW-B-A` reads in connector order: 1=GND, 2=+3V3, 3=ENC_SW(IO48), 4=ENC_B(IO47), 5=ENC_A(IO21). |

Cosmetic: silk title → `SOMA BASE CARRIER v1.5`, all text ≥1.0 mm,
label positions re-spaced to clear the new parts (7 silk overlaps
remain, down from v1.4's 16), "ONE 5V SRC ONLY", "Q2 TAB=D",
"74AHCT125", "NEO G-D-5V" labels added.

## Part B — verification numbers

**FAIL rows re-checked: 17 FAIL rows grouped into 6 issues (F1–F6) —
all now PASS** (socket table below, pin/power audits, route/DRC runs).
Via count before/after: **v1.4 = 67 vias / 413 segments →
v1.5 = 88 vias / 426 segments** (86 in the hand-route table + 2 GND
stitches added by `fill_zones.py`; the +21 buys the 4.5 mm 12 V
parallel-via transitions and the new U3/GND stitching).

Independent socket check — every U1A/U1B pad vs the official
Espressif J1/J3 table (KiCad python on the final file):

| pad | net | module pin | pad | net | module pin |
|-----|-----|------------|-----|-----|------------|
| U1B.1/2 | +3V3 | J1-1/2 3V3 | U1A.1 | GND | J3-1 GND |
| U1B.3 | NC | J1-3 RST/EN | U1A.2/3 | NC | J3-2/3 IO43/IO44 |
| U1B.4 | NEO | J1-4 IO4 | U1A.4/5 | CAN_RX/CAN_TX | J3-4/5 IO1/IO2 |
| U1B.5-7 | IRIN/TEMP/BUZ | J1-5/6/7 | U1A.8 | MOTOR_EN | J3-8 IO40 |
| U1B.9 | LEDGPIO | J1-9 IO16 | U1A.10 | ESTOP | J3-10 IO38 |
| U1B.10 | BUSA_DATA | J1-10 IO17 | U1A.16/17/18 | ENC_SW/ENC_B/ENC_A | J3-16/17/18 IO48/IO47/IO21 |
| U1B.11/12 | SCL1/SDA1 | J1-11/12 IO18/IO8 | U1A.21/22 | GND | J3-21/22 GND |
| U1B.16/17 | VSNS/RXA | J1-16/17 IO10/IO11 | | | |
| U1B.21 | +5V_MCU | J1-21 5V | U1B.22 | GND | J1-22 GND |

(omitted pads = NC spares). Scripted check: **no GND net lands on a
non-GND module pin, no +3V3/+5V net lands on a GND pin or GPIO, 5V
and 3V3 pins carry their true rails.** The three v1.4 hard shorts
(3V3→GND ×2, 5V→3V3) cannot exist anymore.

- `check_pads.py`: **OK — 201 file pads all match internal map, all
  on-board.** (Place-only gen must skip `heal_unconnected()` — now
  gated behind `PLACE_ONLY`; it used to burn ~15 min of A* writing
  throwaway legs.)
- `reroute.py --check`: **legs 159, segments 400, vias 86, total
  track 3479.5 mm, warnings: 0** (pad/track/via clearance 0.22 mm,
  edge, exits, dangling, unrouted — all clean).
- `verify_nets.py` (KiCad python): **PASS** — every routed net one
  copper island.
- `audit_pins.py` vs Espressif pinout: U1B.1/2 = +3V3 (J1-1/2),
  U1B.3 = RST (J1-3), U1B.21 = +5V_MCU (J1-21 5V), U1B.22 = GND
  (J1-22); U1A.1/21/22 = GND (J3-1/21/22), U1A.2 = IO43 TX,
  U1A.3 = IO44 RX — the mirror is gone.
- U3 pin audit: 1,4,5,7,9,10,12,13 = GND; 14 = +5V; 2 = NEO;
  3 = NEO_A; R13.1 = NEO5V → J14.2; C8.2 = +5V.
- `fill_zones.py`: bridged 24 micro-gaps, stitched 2 orphan GND pads,
  pruned dead fragments; both GND pours carry `(net "GND")` and one
  connectivity island.
- `kicad-cli pcb drc --severity-all`: **21 violations, 0 unconnected
  items** — 13 `lib_footprint_mismatch` (inherited class + the new
  DIP-14/DO-35/CP_Radial library copies), 7 `silk_overlap`,
  1 `silk_over_copper` (D6's (K) mark clipped by R1.2's mask opening —
  fab auto-clips; accepted rather than move D6 into R4's courtyard).
  No shorting/clearance/hole/courtyard/dangling violations. v1.4
  baseline was 27 of the same warning classes.
- Renders: `soma-carrier-v15-top.png`, `soma-carrier-v15-bottom.png`,
  `soma-carrier-v15-copper.svg` — LOOK checked: socket USB→W,
  TOP=J1/BOT=J3 silk on the pad rows, 74AHCT125 socket sits clear of
  K1's courtyard, v1.5 title visible.
- Fab: `gerbers/` — 17 gerbers + `soma-carrier-v15.drl` +
  `soma-carrier-v15-jlcpcb.zip` rebuilt from this run's exports
  (JLCPCB set: F/B Cu, Mask, Silk, Paste, Edge.Cuts, drill) +
  `bom.csv` (U3/R13/C7/C8/D6/D7 added).

## Part C — geometry decisions worth logging

- **K1's courtyard is huge** (x98.45–118.55, y54.05–69.95): the
  74AHCT125 could not sit where the check suggested. U3 went to
  (109,46) rotated 90° north of K1; R13 to (108,50.5); C8 (112,34.5);
  C7 (102,30).
- The +12V_MOT descent moved west of the U3 block (x99.5/107.3 on B,
  under everything at y52.9); K1.1's F stub extended east along y60.8
  straight into K1.3, deleting a B descent that crossed it.
- BUZ's whole path rerouted: U1B.7 exits B at y71.9, F transit to
  x104.3, B hop y76.5→80.5 under the +3V3 lane, F on to R5.1.
- BZC transits the mid-board on F at y57.7 (single B hop through the
  +3V3 spine at (80.3,58.6)→(76.4,62.5) is blocked by a via bubble),
  hops the K1.5 notch, ascends B at x125.5 east of TEMP.
- U2.8 (MCP2551 RS pin, SMD → F.Cu only) was a GND island inside the
  +3V3 pocket: explicit F stub to a GND via at (87.5,79.5) bridges it.
- NEO_A kept to one B.Cu leg (U3.3 → R13.2): an earlier multi-segment
  version lost a 0.58 mm sub-segment to chamfer degeneracy and got
  pruned → dangling stubs.
- The route validator's `net_of` originally parsed only `(net N)` /
  `(net "name")`; the board writes `(net 2 "+12V_IN")` so every pad
  read as net 0 → ~340 false warnings. Fixed to prefer the name —
  this is why the early warning count looked catastrophic.

## Build notes / gotchas

- **KiCad 10 SaveBoard turns zones into rule areas**: any
  `pcbnew.SaveBoard` call (e.g. inside `fill_zones.py`'s
  pad-graze nudge pass) silently writes zones back as rule areas —
  they lose `(net N)`, the pour becomes dead copper, and DRC explodes
  (we saw 226 violations / 50 unconnected GND pads). `fill_zones.py`
  now calls `SetIsRuleArea(False)` before **every** save. Verify with
  `grep -c '(net "GND")' board.kicad_pcb` after any pcbnew save.
- Presence of `pts` polygons in a zone is not proof of connectivity —
  check `(net …)` and `island yes/no`, then trust the DRC
  unconnected-items count.
- `fab.sh` keeps `|| true` on the DRC step so warning-level classes
  don't block gerber export; read `drc_report.txt` for the real count.
- The v1.4 `gerbers/soma-carrier-v15-jlcpcb.zip` shipped with the
  copy contained v14-named gerbers; the zip must be rebuilt after any
  gerber re-export (done — see Part B).

## Safety notes

- 12 V battery input, fused at **F1 = 10 A** — fuse is the first
  element in the +12V_IN path, upstream of the 4.5 mm trunk. It
  protects wiring/tracks from downstream shorts; it does NOT protect
  the ESP32, servos' electronics, or a stalled motor below 10 A.
- K1's contacts switch motor power (+12V_MOT → J18/J20). D5 is the
  flyback across the coil; the contact side has no suppression —
  motor wiring should be short and away from the CAN/signal bundle.
- Battery handling: no reverse-polarity protection upstream of F1 —
  check XT60 polarity before first power; "ONE 5V SRC ONLY" — never
  feed the Mini-360 5V and USB at the same time.
- Low-voltage DC only; no mains on this board.

## UNVERIFIED [U]

- [U] Same hardware caveats as v1.3/v1.4: K1 relay pin mapping vs the
  SRD-12VDC-SL-A datasheet, IRF4905 dissipation near 10 A, relay
  contact rating vs motor stall, no precharge on +12V_MOT.
- [U] Q3 2N2222A pin order: footprint assumes a TO-92 **E-B-C**
  (pin1=E GND, pin2=B Q3_B, pin3=C RLY_SW) — some 2N2222A variants
  are P2N2222A-style reversed; confirm the part in hand or fit a
  PN2222A.
- [U] Mini-360 pad order on J3/module footprint assumed GND/… per
  module silk — verify against the buck module in hand before first
  power-up (module pinout varies by clone).
- [U] Electrolytic ratings on the 12 V rail (C1/C3 reservoir caps)
  assumed ≥25 V — confirm before stuffing; 16 V parts would be
  marginal.
- [U] TVS type on the 12 V input (D4) assumed unidirectional
  ≥18 V standoff / <30 V clamp — verify fitted part.
- [U] 74AHCT125 pinout assumed standard (1=/1OE, 2=1A, 3=1Y …
  14=VCC, 7=GND, /OE active-low → tied to GND). Socketed DIP — verify
  orientation and the level-shift chain on the bench with a single
  pixel before a panel.
- [U] D6 zener value (3V6) chosen for a 3.3 V RXA clamp; confirm vs
  the actual bus transceiver's absolute max before fitting — the
  footprint/silk are marked OPT.
- [U] 4.5 mm 12 V trunks assume ≥1 oz copper; check the fab's outer
  copper weight option at order time.
- [U] 9 silk_overlap + 1 silk_over_copper items are cosmetic but
  print as fab warnings; check silkscreen legibility on the gerbers
  before ordering.
- [U] The board is verified electrically by geometry + net audits
  only — no ERC (no schematic), no prototype bring-up yet.
