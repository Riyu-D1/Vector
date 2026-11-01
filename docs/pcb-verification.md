# Carrier PCB verification — pre-order audit

> **Superseded**: this audit covered the v1.1-era carrier. Carrier
> **v1.3** removed bus B (IO15/12), I2C2 (IO41/42) and the wrist UART
> (IO39/14), and added the MOTOR_EN relay + reverse-polarity FET —
> its own audit is `pcb13/STATUS-pcb13.md` (worktree
> `~/Vector-wt/pcb13`). Kept for history.

Board under audit: `pcb/soma-carrier.kicad_pcb` (135 × 115 mm, 2 layers,
all through-hole, no ICs). Audit run on the emitted file, not the
generator's assumptions, per `VERIFY_GUIDE.md`.

Result legend: **PASS** row verified against a real datasheet/product doc;
**FAIL** mismatch found (listed as a finding); **INFO** verified, note for
assembly.

---

## Phase 1 — pin-by-pin netlist audit

Source of truth for pads: `pcb/audit_pins.py` run on the emitted board —
189 pads / 50 footprints, every pad listed with net + position.

### 1.1 ESP32-S3-DevKitC-1 socket (U1A/U1B, 44 pins)

Physical orientation verified against the Espressif v1.1 user guide J1/J3
tables and the official PCB outline drawing
(`esp32-s3-devkitc-1_v1.1` docs + atomic14 pinout table):
with USB at top, J3 is the left column and J1 the right column, both
numbered pin 22 at the USB end → on our board (USB faces west) J3 = the
bottom socket row (U1A) and J1 = the top row (U1B), each socket pad *n*
mapping to module pin *23−n*. Socket rows are 22.86 mm apart, pin 1 of
each row at the west (USB) end. Not mirrored.

| U1B pad | Module J1 pin | Net on board | Requires | Verdict |
|---|---|---|---|---|
| 1 | 22 = GND | GND | GND | PASS |
| 2 | 21 = 5V | +5V_MCU | 5V | PASS |
| 3 | 20 = IO14 | NC | — | PASS |
| 4 | 19 = IO13 | NC | — | PASS |
| 5 | 18 = IO12 | RXB | any GPIO | PASS |
| 6 | 17 = IO11 | RXA | any GPIO | PASS |
| 7 | 16 = IO10 | VSNS | ADC1 pin | PASS — IO10 = ADC1_CH9 |
| 8 | 15 = IO9 | NC | — | PASS |
| 9 | 14 = IO46 | NC | strapping pin — leave NC | PASS |
| 10 | 13 = IO3 | NC | strapping pin — leave NC | PASS |
| 11 | 12 = IO8 | SDA1 | any GPIO | PASS |
| 12 | 11 = IO18 | SCL1 | any GPIO | PASS |
| 13 | 10 = IO17 | BUSA_DATA | any GPIO | PASS |
| 14 | 9 = IO16 | LEDGPIO | any GPIO | PASS |
| 15 | 8 = IO15 | BUSB_DATA | any GPIO | PASS |
| 16 | 7 = IO7 | BUZ | any GPIO | PASS |
| 17 | 6 = IO6 | TEMP | any GPIO | PASS |
| 18 | 5 = IO5 | IRIN | any GPIO | PASS |
| 19 | 4 = IO4 | NEO | any GPIO | PASS |
| 20 | 3 = EN | NC | module has pull-up + button | PASS |
| 21 | 2 = 3V3 | +3V3 | 3V3 | PASS |
| 22 | 1 = 3V3 | +3V3 | 3V3 | PASS |

Official v1.1 J3 table (Espressif user guide — note J3.14=IO0,
J3.15=IO45, J3.16=IO48, J3.17=IO47, **J3.21=GND**, J3.22=GND; the RGB
LED sits on GPIO38 on v1.1):

| U1A pad | Module J3 pin | Net on board | Requires | Verdict |
|---|---|---|---|---|
| 1 | 22 = GND | GND | GND | PASS |
| 2 | 21 = GND | GND | GND | PASS |
| 3 | 20 = IO19 (USB D−) | NC | leave NC for USB | PASS |
| 4 | 19 = IO20 (USB D+) | NC | leave NC for USB | PASS |
| 5 | 18 = IO21 | ENC_A | any GPIO | PASS |
| 6 | 17 = IO47 | ENC_B | any GPIO | PASS |
| 7 | 16 = IO48 | ENC_SW | any GPIO | PASS |
| 8 | 15 = IO45 | NC | strapping pin — leave NC | PASS |
| 9 | 14 = IO0 | NC | strapping pin — leave NC | PASS |
| 10–12 | 13–11 = IO35/36/37 | NC | flash/PSRAM pins (N16R8) | PASS — all NC |
| 13 | 10 = IO38 | ESTOP | any GPIO | PASS — note: also the v1.1 onboard RGB-LED pin; WS2812 DIN is hi-Z, estop still reads fine |
| 14 | 9 = IO39 | WRX | any GPIO | PASS |
| 15 | 8 = IO40 | WTX | any GPIO | PASS |
| 16 | 7 = IO41 | SCL2 | any GPIO | PASS |
| 17 | 6 = IO42 | SDA2 | any GPIO | PASS |
| 18 | 5 = IO2 | SP1 | any GPIO | PASS |
| 19 | 4 = IO1 | SP2 | any GPIO | PASS |
| 20–21 | 3–2 = IO44/RX0, IO43/TX0 | NC | console UART — leave for debug | PASS |
| 22 | 1 = GND | GND | GND | PASS |

Strapping pins IO0/IO3/IO45/IO46: all NC ✓. USB pins IO19/IO20: both
NC ✓. Flash/PSRAM IO33–37: all NC ✓. Console IO43/IO44: NC ✓.
VSNS on ADC1_CH9 ✓. (An earlier third-party J3 table placing IO48 at
pin 21 was wrong — the official v1.1 table has GND there. The emitted
board matches the official table exactly.)

### 1.2 Servo ports (J4/J5/J6, KK-254)

STS3215 datasheet: 5264-3P pin 1 = GND, 2 = Vcc, 3 = Signal.
HTD-45H (Hiwonder docs): GND, VIN, SIG — same order.

| Ref | pad1 | pad2 | pad3 | Required | Verdict |
|---|---|---|---|---|---|
| J4 | GND | +12V | BUSA_DATA | GND,Vcc,SIG | PASS |
| J5 | GND | +12V | BUSA_DATA | GND,Vcc,SIG | PASS |
| J6 | GND | +12V | BUSB_DATA | GND,VIN,SIG | PASS |

Firmware pins: BUSA_DATA → IO17 (TX), RX via R1 1k → IO11; BUSB_DATA →
IO15, RX via R2 → IO12. Single-wire TTL convention (TX drives bus, RX
listens through resistor) — documented design.

### 1.3 Power connectors

| Ref | Pad map | Required | Verdict |
|---|---|---|---|
| J16 XT60-M | 1=GND (bevelled end), 2=+12V_IN | AMASS: bevelled = − | PASS — verify molded mark on part |
| J1 12V term | 1=+12V_IN, 2=GND | wire: + → pad1 | PASS |
| JP1 | 1=+12V_IN, 2=+12V_SW | shunt/switch bridges | PASS |
| F1 | 1=+12V_SW, 2=+12V | fuse bridges SW→rail | PASS |
| J2 5V term | 1=+5V, 2=GND | wire: + → pad1 | PASS |
| J3 Mini-360 | 1=+12V(IN+), 2=GND(IN−), 3=+5V(OUT+), 4=GND(OUT−) | IN+/IN−/OUT+/OUT− | PASS logical; INFO — module pads are a 2×2 cluster, wire 4 short jumpers, do not plug module directly |

### 1.4 Module headers

| Ref | Pad order (pin 1→n) | Module order | Verdict |
|---|---|---|---|
| J11 OLED | GND,+3V3,SCL1,SDA1 | SSD1306: GND,VCC,SCL,SDA | PASS — direct socket match |
| J12 IMU | +5V,GND,SCL1,SDA1,NC,NC,GND,NC | GY-521: VCC,GND,SCL,SDA,XDA,XCL,AD0,INT | PASS — pad7 GND→AD0 = addr 0x68 |
| J13 jog | +3V3,GND,ENC_B,ENC_A,ENC_SW | EC11 flying lead; KY-040 order is CLK,DT,SW,+,GND (reverse) | PASS — flying lead, order documented on silk (F-doc) |
| J9 estop | ESTOP,GND | button NO contacts | PASS |
| J10 wrist | GND,WTX,WRX,+5V | ESP32 TX(IO40)→wrist RX pin2, wrist TX→WRX pin3 | PASS — crossover at cable |
| J7 SEA | SDA1,+3V3,GND,SCL1 | our SEA board pinout — ours to define | PASS (self-consistent) |
| J8 SEA | +3V3,GND,SDA2,SCL2 | our SEA board pinout | PASS |
| J14 Neo | GND,NEO,+5V | strip: G,DIN,5V | PASS — label on silk |
| J15 spare | +5V,GND,SP1,SP2,+3V3 (pins run x64→74.16) | — | FIXED — silk now "SPARE 5V-G-S1-S2-3V3" matching pin order |
| IR1 socket | IRIN,GND,+3V3 | VS1838B: OUT,GND,VCC | PASS |
| DSG/DST/DSV | GND,TEMP,+3V3 (spread pads) | DS18B20 TO-92: 1=GND,2=DQ,3=VDD | PASS — bend outer leads to 2.54 mm |
| Q1 socket | GND,BZB,BZC = **E,B,C** | PN2222A flat-face = EBC | PASS w/ note — a CBE-marked 2N2222A goes in reversed; silk "E B C" added (F-doc) |
| BZ1 | +5V(+),BZC | active buzzer +/− | PASS — '+' pad marked |
| TP1/TP2 | GND / +12V | test pads | PASS |

### 1.5 Polarised parts

| Ref | Emitted | Required | Verdict |
|---|---|---|---|
| D1 1N5820 | pad1=+5V_MCU (cathode/band side), pad2=+5V | anode +5V → cathode +5V_MCU; band toward pad1 | PASS |
| D4 TVS | pad1=+12V_IN, pad2=GND | unipolar: cathode→pad1; BOM part is P6KE15CA bidirectional → either way OK | PASS — install band to pad1 anyway |
| D2/D3 LED | pad1=GND(cathode), pad2=LED_A via 330R | flat side/cathode → pad1 (square pad) | PASS |
| C1 1000µF | pad1=+12V(+mark), pad2=GND | + → pad1 | PASS |
| C3 220µF | pad1=+5V(+mark), pad2=GND | + → pad1 | PASS |
| BZ1 | pad1(+mark)=+5V, pad2=BZC | + → pad1 | PASS |

### 1.6 Resistors

| Ref | Value | Role | Check |
|---|---|---|---|
| R1/R2 | 1k | bus RX series | PASS |
| R3/R4 | 330R | LED ballast: (5−2)V/330 ≈ 9 mA | PASS |
| R5 | 1k | buzzer base | PASS — base current ~2.6 mA |
| R6 | 4.7k | DS18B20 DQ pull-up to +3V3 | PASS |
| R7/R8 | 30k + 6.8k | VSNS divider | PASS — 12.6 V→2.33 V, 15 V→2.77 V < 3.3 V |

### 1.7 Net isolation

Every named net's pad list was dumped (audit_pins.py). Counts:
+12V 9, +12V_IN 4, +12V_SW 2, +5V 11, +5V_MCU 2, +3V3 10, GND 34,
22 no-net pads (socket spares + 4 mounting-hole pads + J12.5/6/8).
Expected joins only: JP1 (IN↔SW, fuse input side), F1 (SW↔+12V),
J3 (12V↔5V via module), D1 (+5V↔+5V_MCU), U1B (3V3/5V_MCU on one row),
J15 (+3V3/+5V are separate pads of one header — not a short).
No net mixes rails; no unintended joins (U1A.2 = GND is correct —
J3 pin 21 is GND on v1.1).

**Phase 1: 97 PASS, 1 FAIL (F-doc J15 silk order).**

---

## Phase 2 — physical fit / overlap

### 2.1 Courtyard overlap

Scripted pairwise courtyard test on the emitted file: 0 overlaps.
Tightest pairs: D2↔J15 0.02 mm (real bodies ~0.7 mm — LED dome vs header
plastic, OK), D1↔D4 0.20, J3↔J4 0.46, D1↔R3 0.70, J1↔J2 0.83,
D3↔U1A 0.86, R7↔R8 1.0, F1↔U1A 1.16, F1↔J1/J2 1.7 mm.

### 2.2 DevKitC module overhang (board 62.74 mm + antenna ≈ 69.6 × 25.4 mm
total, sits ~8.5 mm up on sockets; module edge ≈ 4.7 mm beyond pin 22/1
each end → module shadow ≈ x 17.4–80.2, y 27.0–52.4)

| Part | Under module? | Height vs 8.5 mm | Verdict |
|---|---|---|---|
| F1 fuse | **yes — east 1.8 mm of body** | ~11 mm tall → **hits module bottom** | **FAIL — F3 (blocker)** |
| R7,R8,R1,R2,R4 | yes | ~3 mm axial | PASS |
| TP1,TP2 | yes | flat pad | PASS |
| JP1,J1,J2,J16 | no (x<17.4 or y<27) | — | PASS |
| D1,D4,R3,J15,J7 | no (y>52.4) | — | PASS |
| C4 | antenna shadow (x80.5–86) | 5 mm, ~3.4 mm below antenna | PASS w/ RF note |
| USB cable exit | needs ~15 mm west of x≈17.4 at z≈22 mm | J1/J2 terminal tops at ~8.4+12.6=21 mm — cable clears by ~1.5 mm | INFO — tight but clears |

### 2.3 Height vs lid (lid underside at 36 mm; board top at 12.6 mm →
23.4 mm of room; flag anything within 2 mm)

Tallest: C1 1000µF ~16–20 mm → ≥3.4 mm clear; XT60 ~16 → ~7 mm; KK-254
+plug ~14 → ~9 mm; modules on sockets ~12 → ~11 mm; BZ1 ~8. **Nothing
within 2 mm of the lid.** PASS.

### 2.4 Edge / mounting

Copper min distance to edge 1.35 mm (+5V_MCU west lane) ≥ 0.5 ✓.
Mounting holes 3.2 mm, centers 4 mm in from corners ✓. `cad/lib/case.py`
standoffs at the same (4,4)/(131,4)/(4,111)/(131,111) ✓. No non-GND
copper within 3 mm of any hole → M3 head clearance PASS.

### 2.5 Case cutouts (board→case map x+7.5, 122.6−y)

| Connector | Board pos | Case cutout | Verdict |
|---|---|---|---|
| J16 XT60 | (7,17) vertical plug | LEFT @case-y 105.6, z16 | PASS w/ assembly note — plug mates downward; cable bends out the slot |
| J1/J2 terminals | x2–13, y28–51 | LEFT y 74.6/86.6, z14 | PASS — wire-entry faces wall |
| JP1 | (10,58) | LEFT y 64.6 | PASS — wire hole |
| ESP32 USB | module west edge ~x17, y-centre 39.7 | LEFT y 83.1, z24 | PASS |
| J12 IMU | (93,24) mid-board | RIGHT y 98.6 | INFO — vestigial cutout (module sockets on board, nothing exits) |
| IR1 | (128,36) | RIGHT y 86.6, z16 | INFO — dome centre ~z23 vs window top z19.75; bend dome toward wall |
| J14 | (128,48) | RIGHT y 74.6 | PASS |
| J10 wrist | (86,95) | FRONT x 93.5, z18 | PASS |
| J9 estop | (30,95) | FRONT x 37.5 ø16 | PASS |
| J13 jog | (14,95) | FRONT x 21.5 | PASS |
| BZ1 | (66–76,95) | FRONT x 77.5 grille | PASS |
| J11 OLED | **(64,10) north edge** | bezel FRONT x 57.5 | **FAIL — F4: socket is 90 mm from its bezel; move J11 to south row** |

### 2.6 Silkscreen

Post-fix DRC on the regenerated board: 85 silk_overlap + 4
silk_over_copper + 2 silk_edge_clearance — all free-text/reference
placement, no electrical issue. The dominant collision was the single
'BUS-A x2 (STS3215)' label inside C1's silk circle (~80 items); plus
'PWR'/'ENC-J3' texts on pads and D2/D3/H1/H2 reference fields.
**FAIL — F5.** Fixes applied: REF_FIX now writes both axes (a bug left
dy ignored), VAL_FIX added, BUS-A label moved north of the bus headers,
ENC-J3 moved west of J8, PWR east of D2's pads, SPARE text corrected
to the real pin order and centered on the row, J13/J11/J10/J9 labels
centered on their actual (east-running) pin spans, H3/H4 refs added.

### 2.7 Assembly order

All parts are top-side THT; bottom pad access unobstructed. Order:
resistors → diodes → disc caps → headers/sockets → fuse/caps → terminals
→ module sockets → DevKitC/modules last. Low parts (R1/R2/R4/R7/R8/TPx)
sit under the module shadow — install before plugging the module.
PASS (documented).

**Phase 2: 9 checks PASS, 3 FAIL (F3 fuse under module — blocker,
F4 J11 placement, F5 silk).**

---

## Phase 3 — electrical & fabrication

### 3.1 Track current (IPC-2221, 1 oz outer, I = 0.048·ΔT^0.44·A^0.725)

| Net | routed width | capacity @10 °C | @20 °C | worst current | verdict |
|---|---|---|---|---|---|
| +12V_IN | 2.5 mm | 4.6 A | 6.2 A | 6 A fuse | PASS @20 °C; note @10 °C is 4.6 A < 6 A — acceptable: fuse is a fault protector, steady-state draw is ~3–4 A |
| +12V_SW | 2.5 mm | 4.6 | 6.2 | 6 A | PASS (same note) |
| +12V | 2.5 mm | 4.6 | 6.2 | 6 A trunk / ~3 A per port | PASS |
| +5V | 1.5 mm | 3.2 | 4.3 | ~2 A | PASS |
| +5V_MCU | 1.0 mm | 2.3 | 3.1 | ~0.5 A | PASS |
| +3V3 | 0.6 mm | 1.6 | 2.2 | ~0.15 A | PASS |
| signals | 0.25 mm | — | — | mA | PASS |

Per-port pin limit: KK-254 contacts ~2.5–4 A — the trunk dives end-on
to each servo Vcc pin (no pin-corridor threading at 2.5 mm — the dives
are short necks from the north lane, see route notes).
GND return: full pour both layers — effectively unlimited.

### 3.2 Holes / drills / annular

| Footprint | drill | pad | annular | lead | verdict |
|---|---|---|---|---|---|
| PinHeader 1xN | 1.0 | 1.7 sq | 0.35 | 0.64 sq | PASS (snug diag) |
| KK-254 | 1.19 | 1.7×2.2 | ≥0.26 | 0.64 | PASS |
| MKDS terminal | 1.3 | 2.6 | 0.65 | ~1.0 | PASS |
| XT60 | 4.5 | 6.0 | 0.75 | ~3.9 blade | PASS |
| DO-201 | 1.3 | 2.6 | 0.65 | ~1.2 | INFO — snug, guide prefers +0.2 |
| 0207 resistor | 0.8 | 1.6 | 0.40 | 0.5–0.6 | PASS |
| CP caps | 1.0 | 2.0 | 0.50 | ~0.6–0.8 | PASS |
| C disc | 0.8 | 1.6 | 0.40 | ~0.5 | PASS |
| Buzzer | 1.0 | 1.7 | 0.35 | ~0.7 | PASS |
| Fuse blade | 3.5 | 5.5×3.8 | 1.0 / 0.15 | 2.8×0.8 tab | INFO — narrow-side annular <0.25 but manufacturable + huge x pad |
| Test pad | 0.7 | 1.5 | 0.40 | — | PASS |
| M3 hole | 3.2 | — | — | M3 | PASS — 4 mm from corners |
| Via | 0.3 | 0.7 | 0.20 | — | PASS — meets JLCPCB min |

Min track 0.25 mm / spacing 0.2 mm — within JLCPCB capability.

### 3.3 GND pour

Zones on F.Cu + B.Cu, 0.5 mm clearance, 0.3 min thickness.
**`connect_pads thru_hole_only`** — thermal reliefs on all PTH pads
(F7 fix), `thermal_gap 0.5` / `thermal_bridge_width 0.65`. First fill
with 0.4 mm spokes flagged 6 `starved_thermal` (C3.2, TP1.1, J8.2,
J10.1, J11.1 + B.Cu); spokes widened to 0.65 mm and re-checked.
Islands: `island_removal_mode 1` + post-fill `(island yes)` strip in
fill_zones.py — dead copper removed (F8).

### 3.4 Gerbers

Existing `pcb/gerbers/` has all layers (F/B.Cu, Mask, Silk, Edge.Cuts,
Fab, Courtyard, Paste, Adhesive, Margin, drill, job). Regenerate after
fixes via `fab.sh`, verify outline 135×115, zip to
`soma-carrier-gerbers.zip`, re-render.

### 3.5 BOM match

Every footprint↔part match verified against `docs/BOM.md` +
`pcb/README.md` tables (XT60-M, MKDS 5.08, KK-254, 1xN 2.54 headers,
DO-201, 0207, D10/D8 electrolytics, 5 mm discs, mini blade fuse,
12 mm buzzer, 3 mm LEDs, M3, test pads). CSV emitted post-fix as
`docs/bom-from-board.csv`.

---

## Findings

| # | Sev | Finding | Fix |
|---|---|---|---|
| F3 | blocker | F1 mini blade fuse (~11 mm) under DevKitC module overhang (8.5 mm gap) — module can't seat | FIXED — F1 → south pocket (17,64) |
| F4 | should-fix | J11 OLED socket on north edge; bezel is on the front rim → 90 mm lead | FIXED — J11 → (44,95) south row |
| F5 | should-fix | 85 silk overlaps + 4 silk-over-copper + 2 edge-clearance; 'SPARE' label order wrong | FIXED — REF_FIX dy bug repaired (it only wrote x), VAL_FIX added, BUS-A/ENC-J3/PWR/SPARE labels repositioned, H3/H4 refs added |
| F6 | blocker | +12V_IN/+12V_SW/+12V trunk = 1.5 mm → ~3.2 A @10 °C, under the ~2.5 mm bar for 6 A | FIXED — +12V family 2.5 mm, +5V 1.5, +5V_MCU 1.0, +3V3 0.6 |
| F7 | should-fix | GND zones `connect_pads yes` (solid) — no thermal relief, hard hand-soldering | FIXED — `thru_hole_only` + bridge width 0.65 |
| F8 | cosmetic | isolated pour islands | FIXED — `(island yes)` strip post-fill (34 removed) |
| F9 | blocker | Post-F6 DRC: 27 `shorting_items` + 18 `clearance` — real overlapping copper (+5V↔SDA1/SCL2, NEO↔+5V, BZC↔+5V, via↔track). Root cause: track-mark halos reserve space only for nets still to come in route `order`; a fat rail re-routed late by the rip-up pass squeezed through signal-width halos and laid overlapping copper | FIXED — router now enforces a per-search hard floor `cuobs`: every foreign copper cell + via expanded by the querying net's true half-width + CLR, checked in `free()` and in the chord-repair pass |
| F10 | blocker | Post-cuobs run unrouted `['+5V_MCU','+3V3']`: two latent defects exposed — (a) +12V's R7.1→(22.5,13) leg exits the west door then hugs U1B's north row edge at y≈25, so its 2.4 mm mark halo seals +5V_MCU's dive channel at (24.7,25.4); (b) the +5V_MCU descent waypoint (81.3,30) sits *inside* C4.1's keepout (edge x80.47) and only ever worked via goal-annulus leniency | FIXED — +12V forced back out the door and up the west side (19,34)/(18.5,22)/(19,14) before J3.1; +5V_MCU descent moved east of C4 into the x86–91 corridor (87.5,34)/(87.5,26) |
| F11 | blocker | GND-stitch vias landed on foreign copper: `_stub_ok` checked foreign tracks only on the stub's layer, but a via is through-hole — SDA1 shorted at (83.8,31.8), +3V3 at (44,96.9), +12V grazed to 0.12 mm | FIXED — via site now checked against foreign copper on BOTH layers; starved-thermal pads stitch on the layer their violation flags |
| F12 | blocker | Dead-copper cleanup: the +5V_MCU east-lane detour was a redundant dead branch (dangling via at 87.12,26.92) whose DRC-driven unwind also cut D1.1's service leg (the pad had tapped off the dead copper); a generic leaf-pruner removed 335 good atoms and had to be replaced | FIXED — pruner is now strictly DRC-driven (only removes atoms KiCad itself flags, loops until clean); D1.1 re-linked to the B.Cu staircase; pcbnew `Save()` adds `(capping)/(covering)` fields — via regexes made field-order tolerant |
| F13 | should-fix | 5 track-vs-pad clearance slivers (0.146–0.189 mm vs 0.2 rule): SCL1↔U1B.2, ENC_A↔J13.5, ENC_SW↔J9.1, BUZ↔J10.3/J10.4 — grid-quantized routing leaves sub-margin gaps | FIXED — `nudge_pad_grazes()` DRC-driven pass: pushes the offending vertex run radially out of the keepout (multi-pad projection solver so runs threading two pads don't oscillate); ENC-J3 label re-sited under J8 |

Classified non-blockers: 12 `lib_footprint_mismatch` warnings = the
generated footprints embed REF_FIX/silk tweaks so the board copy differs
from the stock library part — expected, review-only.

Assembly notes (non-blocking): Mini-360 needs 4 wire jumpers into J3;
XT60 pigtail plugs down, exits through the case slot; IR1 dome bends
toward the wall window; J13 order is +,G,B,A,SW (flying lead — label
on silk); Q1 pad order is E,B,C — PN2222A direct, CBE-variant
2N2222A reversed; J12 IMU cutout vestigial; USB cable grazes J1/J2
terminal tops ~1.5 mm; C4 sits under the antenna shadow (ceramic,
~3.4 mm clear — fine); DO-201 drill snug at +0.1 mm over the 1.2 mm
lead; onboard RGB LED (v1.1, GPIO38) shares the ESTOP pin — it reads
fine as an input, the LED may just echo stray data.

**Total: 6 blockers found + fixed (F3, F6, F9, F10, F11, F12),
4 should-fix fixed (F4, F5, F7, F13), 1 cosmetic fixed (F8).**

## Final verification state

Pipeline: `check_pads → route (cuobs) → fill_zones (nudge → fill →
fixup-stitch → DRC-prune → island-strip) → kicad-cli DRC → gerbers →
render`.

- `check_pads`: **OK — 151 file pads all match internal map, all
  on-board**
- `kicad-cli pcb drc` (authoritative): **0 unconnected items, 0 shorts,
  0 clearance, 0 via/track-dangling, 0 starved-thermal, 0
  isolated-copper, 0 hole-to-hole, 0 silk violations** — only the 12
  expected `lib_footprint_mismatch` warnings
- Gerbers regenerated to `pcb/gerbers/` (16 plots + Excellon drill:
  274 holes, 0.3 mm vias, 3.2 mm NPTH mounts) — outline 135 × 115 mm
- 3D renders (top/bottom) inspected — populate cleanly, silk legible

**Board is orderable.**
