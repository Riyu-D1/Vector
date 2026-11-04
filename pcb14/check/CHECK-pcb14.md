# CHECK-pcb14 — Full per-connection spec audit of SOMA carrier PCB v1.4

Read-only audit. No product files were changed. Everything below was produced
from `soma-carrier-v14.kicad_pcb` @ `595f229` (branch `pcb-v14`), `bom.csv`,
the in-tree verification scripts, KiCad 10 DRC, and manufacturer datasheets
cited per row.

Board under test: `pcb14/soma-carrier-v14.kicad_pcb` — 2-layer, 135×115 mm,
1.6 mm, THT except U2 (SOIC-8). 59 footprints, 177 pads, 27 routed nets,
67 vias (all 0.7 mm pad / 0.3 mm drill), ~3077 mm of track.

## 0. Tool runs (real output)

### KiCad DRC (re-run this audit, all severities)

```
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb drc \
  --severity-all --format json -o check/drc-p5.json soma-carrier-v14.kicad_pcb
```

Result: **27 violations, 0 unconnected nets, 0 shorted nets.**
Breakdown: 16 × `silk_overlap` (silkscreen clearance — cosmetic),
11 × `lib_footprint_mismatch` (locally-edited footprints differ from
library copy — informational; the edits are the deliberate drill/pad
changes documented in STATUS-pcb13/14).

### verify_nets.py

```
RESULT: PASS  — all 7 new v1.3/v1.4 nets verified:
+12V_RP, RP_GATE, +12V_MOT, RLY_LOW, RLY_SW, Q3_B, MOTOR_EN
```

### audit_pins.py (independent netlist dump)

```
177 emitted pads, 27 routed nets, 40 GND pads, 29 NC/zero-net pads.
Every net's pad set matches STATUS-pcb13 + STATUS-pcb12 tables exactly.
```

### check_pads.py (place-only pad diff, run against a stubbed-heal copy of
### gen_pcb.py under check/, per STATUS-pcb14 fallback)

```
OK — 177 pads match between place-only dump and routed board;
all pads on-board, none missing, none extra.
```

(The stub copy `check/gen_pcb_dump.py` + its outputs `check/paddump.txt`,
`check/soma-carrier-v14.placeonly.kicad_pcb` are audit artifacts only;
the product generator was not modified.)

## 1. Summary

| Metric | Count |
| --- | --- |
| Check rows audited (parts + nets + logic + physical) | 68 |
| PASS | 41 |
| FAIL rows | 17 → grouped into **6 distinct issues** (F1–F6) |
| [U] rows (unverifiable / needs bench confirmation) | 10 |

**Headline result: DO NOT FABRICATE AS-IS.** One `blocks-power-on`
defect (F1: ESP32-DevKitC socket mirror — accounts for 11 of the 17
FAIL rows) plus five further issues (F2–F6); exact fixes are in
`proposed_fixes.md`. The copper itself passes DRC and the netlist
verifier — the defect is the *assumed module orientation*, which no
DRC can see.

## 2. Part inventory (59 footprints; BOM rows cross-checked)

| Ref | Value | Footprint | Pads |
| --- | --- | --- | --- |
| Q2 | IRF4905 | TO-220-3_Vertical | 3 |
| Q1, Q3 | 2N2222A | PinHeader_1x03_P2.54 | 3 ea |
| U2 | TJA1051T/3 | SOIC-8_3.9x4.9_P1.27 | 8 |
| U1A / U1B | DevKitC-J3 / DevKitC-J1 | PinHeader_1x22_P2.54 | 22 ea |
| K1 | SRD-12V | Relay_SPST_SANYOU_SRD_Series_Form_A | 4 (1,2,3,5) |
| D1 | 1N5820 | D_DO-201_P12.70 | 2 |
| D4 | TVS15 | D_DO-201_P12.70 | 2 |
| D5 | 1N4007 | D_DO-41_P10.16 | 2 |
| D2 / D3 | PWR / STAT LED | LED_D3.0mm | 2 ea |
| F1 | 10A | Fuse_Blade_Mini_directSolder | 2 (oval 3.5×2 drill) |
| BZ1 | BUZZ5V | Buzzer_12x9.5RM7.6 | 2 |
| J1, J18, J20, J2 | 12V_IN / 12V_MOT / 5V_IN | MKDS-1,5-2-5.08 | 2 ea (drill 1.3) |
| J16 | XT60 | AMASS_XT60-M_P7.20 | 2 (drill 4.5) |
| J3 | MINI360 | PinHeader_1x04 | 4 |
| J4, J5, J17 | BUS_A / CAN | Molex_KK-254_6410-03A | 3 (drill 1.19) |
| J9, J19, JP1, JP2 | ESTOP / ESTOP-NC / PWR-ON / CAN-TERM | PinHeader_1x02 | 2 ea |
| J11 | OLED | PinHeader_1x04 | 4 |
| J12 | IMU | PinHeader_1x08 | 8 |
| J13 | JOG | PinHeader_1x05 | 5 |
| J14 | NEOPIX | PinHeader_1x03 | 3 |
| J15 | SPARE | PinHeader_1x05 | 5 |
| IR1 | VS1838B | PinHeader_1x03 | 3 |
| DSG/DST/DSV | DS18B20 G/DQ/V | TestPoint_THTPad_D1.5_D0.7 | 1 ea |
| TP1, TP2 | GND / +12V | TestPoint | 1 ea |
| R1,R5,R11 | 1k | R_Axial_DIN0207_P7.62 | 2 ea |
| R3,R4 | 330 | same | 2 ea |
| R6 | 4.7k | same | 2 |
| R7 / R8 | 30k / 6.8k | same | 2 ea |
| R9 | 120 | same | 2 |
| R10, R12 | 10k | same | 2 ea |
| C1 | 1000uF | CP_Radial_D10_P5.00 | 2 |
| C3 | 220uF | CP_Radial_D8_P3.50 | 2 |
| C2,C4,C5,C6 | 100nF | C_Disc_D5_P2.50 | 2 ea |
| H1–H4 | M3 | MountingHole_3.2mm | 1 ea |

## 3. Per-part / per-connection spec check

Assumptions: 1 oz copper, IPC-2221 external-layer formula
`I = k·ΔT^0.44·A^0.725`, k = 0.048, A = cross-section in mil²
(1 oz = 1.378 mil thick). Load context: two STS3215 (≈2.7 A stall each)
on the servo bus plus user loads on J18/J20 — the entire +12 V rail is
fused at 10 A by F1.

| # | Item | What was checked | Spec (quoted) | Source | Result |
| --- | --- | --- | --- | --- | --- |
| 1 | U1A+U1B socket orientation | pad↔module-pin mapping vs official DevKitC-1 pinout | Official pinout numbers J1/J3 pin 1 **at the USB end** (J1-1=3V3, J3-1=GND, J1-22=GND). gen_pcb.py L258: "socket pin N maps to module J-position (23-N)… position 21/22 (5V, GND) land on pins 2/1 at the USB (west) end" — the design needs pin 1 at the *far* end | https://dl.espressif.com/dl/schematics/SCH_ESP32-S3-DevKitC-1_V1.1_20221130.pdf ; gen_pcb.py:258-262 | **FAIL — blocks-power-on** |
| 2 | U1B.1 (GND) → J1-1 | 3V3 vs GND | J1-1 = 3V3 (module's regulated 3V3 output) | same | **FAIL** — 3V3 shorted to GND |
| 3 | U1B.22 (+3V3) → J1-22 | rail vs GND | J1-22 = GND | same | **FAIL** — second hard 3V3→GND short |
| 4 | U1B.21 (+3V3) → J1-21 | rail voltage | J1-21 = 5V → 5 V driven onto the +3V3 rail (feeds DS18B20 pull-up, IR RX, encoder VCC pin, OLED VCC) | same | **FAIL** — overvoltage on 3V3 rail |
| 5 | U1B.2 (+5V_MCU) → J1-2 | rail vs 3V3 | J1-2 = 3V3 → +5V_MCU fights the module's 3V3 output | same | **FAIL** — rail contention |
| 6 | U1A.2 (GND) → J3-2 | GPIO drive | J3-2 = IO43 (U0TXD, idles/drives high) → continuous output short to GND | same | **FAIL** — GPIO shorted to GND |
| 7 | U1A.15 MOTOR_EN → J3-15 | strapping pin | J3-15 = IO45, a strapping pin (VDD_SPI select); pulled low via R11+BE | esp32-s3 datasheet §Boot Config | **FAIL** (part of #1) |
| 8 | U1B.13 BUSA_DATA → J1-13 | strapping pin | J1-13 = IO3 (strapping); servo bus idles high → forces strap high | same | **FAIL** (part of #1) |
| 9 | U1B.14 LEDGPIO → J1-14 | strapping pin | J1-14 = IO46 (strapping) | same | **FAIL** (part of #1) |
| 10 | U1A.19 CAN_RX → J3-19 | USB D+ conflict | J3-19 = IO20 = USB D+; CAN_RX line would load/fight USB enumeration | same | **FAIL** (part of #1) |
| 11 | All 17 remaining U1A/U1B signal pads | net↔GPIO | every signal lands on the mirrored GPIO (pad N ⇒ J-N, not J-(23−N)); full table in §4 | same | **FAIL** (part of #1) |
| 12 | U2 TJA1051T/3 pinout | 1 TXD,2 GND,3 VCC,4 RXD,5 VIO,6 CANL,7 CANH,8 S vs board 1=CAN_TX,2=GND,3=+5V_MCU,4=CAN_RX,5=+3V3,6=CANL,7=CANH,8=GND | NXP datasheet pinning: identical; "S: LOW = normal mode, HIGH = silent/standby"; VCC 4.5–5.5 V, VIO 2.8–5.5 V | https://www.nxp.com/docs/en/data-sheet/TJA1051.pdf | PASS (S→GND = normal mode; VIO=3V3 in range) |
| 13 | U2 VCC = +5V_MCU | rail level | +5V_MCU ≈ +5V − Vf(1N5820) ≈ 4.6–4.8 V vs VCC min 4.5 V — inside range but ≤0.3 V margin; rises to 5.0 V on USB power | NXP ds + onsemi 1N5820 Vf 0.475 V @3 A | PASS (marginal — see §5 note) |
| 14 | Q2 IRF4905 pin order | pad1=G,2=D(+12V_SW),3=S(+12V_RP) | Infineon TO-220: "1 Gate, 2 Drain, 3 Source; tab = Drain" | https://www.infineon.com/assets/row/public/documents/24/49/infineon-irf4905-datasheet-en.pdf | PASS |
| 15 | Q2 reverse-polarity topology | D toward input, S toward F1/rail, G pulled to GND via R10 | P-ch body diode anode=D, cathode=S: correct input → diode conducts, Vgs ≈ −11.3 V, FET enhances on; reversed input → diode off, Vgs ≈ 0 → protected | IRF4905 ds (VGS ±20 V, RDS(on) 0.02 Ω @ VGS=−10 V) | PASS |
| 16 | Q2 VGS at 12 V input | | −12 V vs ±20 V limit | same | PASS (input must stay ≤20 V; D4 clamps ~15–17 V) |
| 17 | Q2 dissipation | I²·RDS(on) | at 5 A → 0.5 W; at 10 A (fuse) → 2.0 W — needs airflow/heatsink above ~5 A continuous | same | PASS w/ note |
| 18 | K1 SRD-12VDC-SL-A | coil on +12V → RLY_LOW; contacts +12V→+12V_MOT | Songle: coil 12 V ≈400 Ω (30 mA); contacts "10 A 250VAC / 10 A 30VDC, max switching 15 A"; Form A | https://www.alldatasheet.com/html-pdf/1131797/SONGLERELAY/SRD-12VDC-SL-A/1713/2/SRD-12VDC-SL-A.html | PASS (contact rating = fuse rating — see §5) |
| 19 | K1 footprint pads 1,2,3,5 | SRD bottom-view numbering | footprint `Relay_SPST_SANYOU_SRD_Series_Form_A` = KiCad SRD library part; pad4(NC) absent as designed; assumed 1/2=coil, 3=COM, 5=NO | KiCad lib + Songle ds | [U] — datasheet gives bottom-view drawing without printed pad numbers; verify 3=COM/5=NO with a DMM on the real relay before soldering |
| 20 | Q1/Q3 2N2222A pin order | pads 1=E,2=B,3=C (silk "Q1 EBC") | PN2222A (onsemi/fairchild TO-92) = E-B-C ✓; P2N2222A (onsemi) = C-B-E ✗ | https://www.onsemi.com/pdf/datasheet/p2n2222a-d.pdf | [U] — pinout is vendor-specific; build only with an E-B-C part (PN2222A, BC547-style orientation) or leads will land B↔E swapped |
| 21 | Q3 base drive | MOTOR_EN→R11 1k→base, R12 10k pull-down, coil load 30 mA | 3.3 V drive ⇒ Ib≈2.5 mA ⇒ Ic≫30 mA at β≥30 | 2N2222A ds | PASS |
| 22 | Q1 buzzer switch | BUZ→R5 1k→base; BZ1 between +5V and collector | same drive math; load = 5 V active buzzer (~30 mA typ) | — | PASS |
| 23 | D1 1N5820 | cathode(pad1)=+5V_MCU, anode=+5V → diode-ORs buck output into MCU rail | onsemi: Io=3 A, VRRM=20 V, Vf≈0.475 V@3 A (≈0.35 V at the ~0.3–0.6 A load) | https://www.onsemi.com/pdf/datasheet/1n5820-d.pdf | PASS (orientation correct per KiCad D_DO-201 pad1=cathode convention + README "band toward pin1") |
| 24 | D4 TVS15 on +12V_IN | clamp vs rail | P6KE15-class: Vrwm≈12.8–15 V, Vclamp≈21–24 V @Ipp; protects Q2/rail from transients | littelfuse P6KE ds | [U] — BOM says "TVS15" only; uni- vs bidirectional changes reversed-input behaviour (uni clamps −0.7 V, bi clamps −15 V; Q2 protects either way) |
| 25 | D5 1N4007 flyback | cathode→+12V, anode→RLY_LOW (across K1 coil) | 1N4007: 1 A, VRRM 1000 V — vastly oversized for a 30 mA coil | chipdatasheet.com/1n4007 | PASS |
| 26 | D2 power LED + R3 330 | 5 V → (5−2)/330 ≈ 9 mA | standard 3 mm LED | — | PASS |
| 27 | D3 stat LED + R4 330 | LEDGPIO(3.3 V) → ~4 mA | same | — | PASS |
| 28 | F1 10 A mini-blade | rating vs circuit | board/silk = 10 A; STATUS-pcb12 documents deliberate 6 A→10 A change; pcb14/README still says 6 A (stale doc) | STATUS-pcb12 §F1 | PASS (electrical) + doc-drift FAIL (cosmetic) — see FAIL F5 |
| 29 | J16 XT60-M | 12 V input connector, 7.2 mm pitch, 4.5 mm drill | XT60 rated 30 A cont / 60 A peak; PCB-mount pins ≈3.5 mm Ø | AMASS XT60 spec | PASS |
| 30 | J1/J18/J20/J2 MKDS 1,5/2-5,08 | screw terminals, 5.08 pitch, 1.3 drill | Phoenix 1715721: "nominal current 17.5 A, rated voltage 250–400 V, pin 0.9×0.9 mm, hole Ø 1.3 mm" | https://www.farnell.com/datasheets/3630632.pdf | PASS — drill exactly matches datasheet |
| 31 | J3 MINI360 header | 1=+12V(IN+),2=GND(IN−),3=+5V(OUT+),4=GND(OUT−) | Mini-360 (MP2307): VIN 4.75–23 V, Iout 1.8 A cont / 3 A surge; pads are 4 corner pads — order **varies between clone boards**; module is wire-hooked to J3 | https://components101.com/modules/mini360-dc-dc-buck-converter-module | [U] — user must map clone pad labels to J3 silk + set VOUT=5.0 V before connecting (§5) |
| 32 | J2 5V_IN vs J3 | wired-OR of two 5 V sources onto +5V | no OR-ing diode — connecting both ties buck output to external 5 V | — | [U]/note — use one source only (README says either/or; mark on bench) |
| 33 | J4/J5 KK-254 servo conn | 1=GND,2=+12V,3=BUSA_DATA | Feetech STS3215 lead = GND/VCC/DATA on a 2.54 mm 3-pin latching plug; KK-254 (6410-03A) is the compatible keyed header | Molex 6410 + Feetech cable | PASS ([U] minor: verify plug keying/latch on the exact servo cable) |
| 34 | KK-254 current | 2.7 A stall per servo on pin 2 | KK-254 contacts rated ~4 A @ 250 V | Molex KK-254 ds | PASS (margin thin if both stall simultaneously — shared +12V track carries sum) |
| 35 | STS3215 supply = +12V | servo voltage | "ST3215 12 V: operating 4–14 V, stall ≈2.7 A" | https://docs.waveshare.com/ST3215_Servo | PASS |
| 36 | BUSA_DATA 5 V TTL into ESP32 pin | signal level into U1B | Feetech bus is TTL half-duplex; servo TX high level ≈5 V-class on HV variants; ESP32-S3 GPIO max = VDD+0.3 ≈ 3.6 V | Feetech docs + esp32-s3 ds | [U] — measure servo TX idle level; R1 1k limits injection ≈1.5 mA (probably survivable but out-of-spec); see FAIL F4 fix |
| 37 | R1 1k series on servo data | protects both ends on a shared TX/RX node | — | — | PASS |
| 38 | J17 CAN + JP2 + R9 | 1=GND,2=CANH,3=CANL; 120 Ω across CANH–CANL when JP2 fitted | ISO 11898 wants 120 Ω bus termination; single end populated is correct for a node at cable end | TJA1051 ds | PASS |
| 39 | J19 ESTOP-NC loop | RLY_LOW→J19→RLY_SW→Q3: open loop ⇒ coil never energised ⇒ +12V_MOT dead | fail-safe by design; silk "FIT JUMPER OR NC E-STOP" | — | PASS |
| 40 | J9 ESTOP sense | 1=ESTOP(U1A.13/IO38), 2=GND | switch-to-GND input needs pull-up → enable ESP32 internal PU (IO38 is RTC GPIO, has PU) | esp32-s3 ds | PASS (firmware note) |
| 41 | J11 OLED | 1=GND,2=+3V3,3=SCL1,4=SDA1 vs module order | common SSD1306 4-pin order GND,VCC,SCL,SDA — exact match; "not all OLEDs use the same pin order — check" (some are VCC,GND,SCL,SDA) | https://pinoutdb.org/en/component/ssd1306-0-96-oled | PASS + [U] minor (check bought module's pin order) |
| 42 | J12 GY-521 | 1=+5V,2=GND,3=SCL,4=SDA,7=GND(AD0),5/6/8 NC | GY-521 order VCC,GND,SCL,SDA,XDA,XCL,AD0,INT — match; AD0 tied GND ⇒ addr 0x68; module LDO accepts 3.3–5 V; onboard I2C pull-ups to module 3V3 | https://github.com/RobTillaart/GY521 | PASS |
| 43 | J13 JOG/encoder | 1=+3V3,2=GND,3=ENC_B,4=ENC_A,5=ENC_SW | KY-040 module order is **GND,VCC,SW,DT,CLK** — plugging a KY-040 straight in powers it backwards (module VCC→board GND, GND→+3V3) and lands all signals wrong; bare EC11 wired per silk works | https://docs.wokwi.com/parts/wokwi-ky-040 | **FAIL — will-not-work** (direct plug of the part named in the brief; silk order itself is self-consistent) |
| 44 | IR1 VS1838B | 1=IRIN,2=GND,3=+3V3 | VS1838B: pin1=OUT,2=GND,3=VCC, 2.7–5.5 V, active-low out | https://componentindex.net/components/ir-receiver/ | PASS (+3V3 in range; enable internal PU or confirm module has onboard PU) |
| 45 | J14 NEOPIX | 1=GND,2=NEO,3=+5V; data driven at 3.3 V | WS2812B: VIH = 0.7×VDD = **3.5 V min at 5 V**; a 3.3 V data line does not meet spec | https://www.digikey.com/htmldatasheets/production/2371852/0/0/1/ws2812b-led.html | **FAIL — will-not-work** (marginal; often limps at room temp, fails when warm/aging) |
| 46 | DS18B20 pads (DSG/DST/DSV) | GND,TEMP(+R6 4.7k→+3V3),+3V3 | DS18B20 TO-92: 1=GND,2=DQ,3=VDD (flat face), 3.0–5.5 V; needs 4.7k pull-up — R6 provides it | https://www.analog.com/media/en/technical-documentation/data-sheets/ds18b20.pdf | PASS (probe wiring order documented on silk "TEMP") |
| 47 | R7/R8 divider | 30k/6.8k on +12V → VSNS = 2.22 V @12 V; 2.77 V @15 V; 3.70 V @20 V | vs IO abs-max ≈3.6 V → exceeds only during a >19.5 V transient (D4 clamps ~21–24 V for µs) | esp32-s3 ds | PASS w/ note (thin transient margin) |
| 48 | BZ1 BUZZ5V | buzzer between +5V and Q1 collector | 5 V active buzzer ~30 mA — Q1 fine; **no flyback diode across buzzer** | — | [U] — magnetic buzzers can spike; add 1N4148 or use piezo (bench) |
| 49 | C1 1000 µF on +12V | voltage rating | BOM has no voltage; rail = 12 V, TVS clamps ~21–24 V transient → need ≥25 V (20 % margin rule wants >14.4 V, but transients push to ~24 V → 25 V part mandatory, 35 V preferred) | IPC/derating rule from stage | [U] — BOM incomplete; buy 25 V+ |
| 50 | C3 220 µF on +5V | voltage rating | need ≥10 V (5×1.2=6 V min) | same | [U] — buy 10 V+ |
| 51 | C2/C4/C5/C6 100 nF | ratings | C2 sits on +12V → ≥25 V; C4/C5 on +5V → ≥10 V; C6 on +3V3 → ≥6.3 V (std 50 V discs all pass) | same | [U] — BOM has no ratings |
| 52 | Decoupling placement | C5 at U2 VCC, C6 at U1B 3V3, C4 at +5V | all adjacent to the loads they serve | layout | PASS |
| 53 | +12V* rail tracks (2.5 mm) | IPC-2221 @1 oz, 20 °C rise | 2.5 mm ≈ 98 mil → ~6.3 A; @10 °C ≈4.6 A; @30 °C ≈7.5 A — vs **10 A fuse** | ipc-2221 formula | **FAIL — will-not-work at fuse rating** (track is the weakest link before the fuse; see §4/F3) |
| 54 | +12V_IN single via | 0.3 mm drill via in series with entire input | one 0.3 mm plated via ≈1–2 A sensible; at 10 A ≈40–60 °C rise | via current rule-of-thumb + JLCPCB | **FAIL** (same root cause class — under-engineered input path; fix = parallel vias, §proposed_fixes) |
| 55 | +12V_MOT path | relay COM→NO→J18/J20, 2.5 mm track | carries combined motor current ≤ fuse 10 A > ~6.3 A track guidance | same | FAIL (covered by F3) |
| 56 | +5V track 0.8 mm | 20 °C → ~2.8 A | Mini-360 cont 1.8 A max; loads <1 A typ | IPC-2221 | PASS |
| 57 | +5V_MCU 1.0 mm | → ~3.2 A | feeds module 5V pin + U2 + C5 — <1 A | same | PASS |
| 58 | +3V3 0.6 mm | → ~2.2 A | module-internal reg; rail loads tiny | same | PASS |
| 59 | Signal tracks 0.25 mm | → ~1.2 A | µA–mA signals | same | PASS |
| 60 | GND net | 40 pads, dual GND pours both layers, 3×0.5 mm tracks | DRC: 0 unconnected → fully stitched | DRC run | PASS |
| 61 | Two drivers on one net | scan all nets | +5V wired-OR (J2 vs J3) is the only contention — covered #32; no logic outputs tied together | netlist | PASS |
| 62 | Unconnected power pins | scan | U2.8→GND intentional (normal mode); module EN/IO0/USB pins not landed on socket — module's own pulls handle EN; IO0 = BOOT button on module | — | PASS ([U] note: no RST/BOOT access from carrier — use module buttons) |
| 63 | Floating inputs | scan | RP_GATE→R10 10k GND ✓; Q3_B→R12 10k ✓; ESTOP needs internal PU (firmware); encoder needs PUs (internal for EC11 / module PUs for KY-040); TEMP has R6 ✓; IRIN idle-high ✓; CAN_RX inputs biased by U2 ✓ | — | PASS |
| 64 | ESP32 strapping pins IO0/3/45/46 | intended map | intended: all NC (README L102); **actual (mirrored): IO3←BUSA_DATA, IO46←LEDGPIO, IO45←MOTOR_EN** — boot-state corruption on top of everything else | esp32-s3 ds §boot config | **FAIL** (part of #1) |
| 65 | ESP32 5 V tolerance | any 5 V signal → GPIO | intended map: none — all GPIO nets are 3.3 V or open-collector-to-GND; only question is servo TX level (#36) | esp32-s3 ds | PASS (intended) / [U] (servo level) |
| 66 | I2C pull-ups | SDA1/SCL1 | not on carrier — supplied by GY-521 onboard PUs (to its 3V3) and/or OLED module PUs; two modules in parallel ≈2–5 kΩ effective | module schematics | PASS ([U] minor: confirm effective PU with both modules fitted) |
| 67 | EN pin | module-internal RC + button | DevKitC-1 handles EN on-module | DevKitC schematic | PASS |
| 68 | USB pins IO19/20 | intended NC | intended unconnected ✓ (mirrored: IO20 gets CAN_RX — covered #10) | — | PASS (intended) |

## 4. The headline FAIL — ESP32-DevKitC-1 socket mirror (detail)

Design intent (README L93–100, gen_pcb.py L258): socket pad N should meet
module J-position (23−N); the comments assume header pin 1 sits at the
far (non-USB) end. On the real ESP32-S3-DevKitC-1 **both header rows are
numbered from the USB/antenna end** — so with the module plugged in as
silkscreen instructs ("DevKitC-1 USB->W", "TOP=J1 BOT=J3"), pad N meets
J-position N, and every intended connection lands mirrored:

| Socket pad | Board net | Intended module pin | Actual module pin | Consequence |
| --- | --- | --- | --- | --- |
| U1B.1 | GND | J1-22 GND | **J1-1 3V3** | module 3V3 → GND short |
| U1B.2 | +5V_MCU | J1-21 5V | **J1-2 3V3** | 5V rail into 3V3 output |
| U1B.21 | +3V3 | J1-2 3V3 | **J1-21 5V** | 5V onto +3V3 rail |
| U1B.22 | +3V3 | J1-1 3V3 | **J1-22 GND** | +3V3 rail → GND short |
| U1B.6 | RXA | J1-17 IO11 | J1-6 IO6 | wrong GPIO |
| U1B.7 | VSNS | J1-16 IO10 | J1-7 IO7 | wrong GPIO (ADC gone) |
| U1B.11 | SDA1 | J1-12 IO8 | J1-11 IO18 | I2C swapped |
| U1B.12 | SCL1 | J1-11 IO18 | J1-12 IO8 | I2C swapped |
| U1B.13 | BUSA_DATA | J1-10 IO17 | **J1-13 IO3 (strap)** | bus on strapping pin |
| U1B.14 | LEDGPIO | J1-9 IO16 | **J1-14 IO46 (strap)** | LED drive on strapping pin |
| U1B.16 | BUZ | J1-7 IO7 | J1-16 IO10 | wrong GPIO |
| U1B.17 | TEMP | J1-6 IO6 | J1-17 IO11 | wrong GPIO |
| U1B.18 | IRIN | J1-5 IO5 | J1-18 IO12 | wrong GPIO |
| U1B.19 | NEO | J1-4 IO4 | J1-19 IO13 | wrong GPIO |
| U1A.2 | GND | J3-21 GND | **J3-2 IO43/U0TXD** | UART TX output shorted to GND |
| U1A.5 | ENC_A | J3-18 IO21 | J3-5 IO2 | wrong GPIO |
| U1A.6 | ENC_B | J3-17 IO47 | J3-6 IO42 | wrong GPIO |
| U1A.7 | ENC_SW | J3-16 IO48 | J3-7 IO41 | wrong GPIO |
| U1A.13 | ESTOP | J3-10 IO38 | **J3-13 IO35** | IO35 absent on octal-PSRAM modules (N16R8/N8R8) → floating ESTOP |
| U1A.15 | MOTOR_EN | J3-8 IO40 | **J3-15 IO45 (strap)** | motor enable on VDD_SPI strap |
| U1A.18 | CAN_TX | J3-5 IO2 | J3-18 IO21 | wrong GPIO |
| U1A.19 | CAN_RX | J3-4 IO1 | **J3-19 IO20 = USB D+** | CAN loads USB data line |

Net effect of powering up as silkscreened: module 3V3 output shorted to
board GND at TWO pads, 5 V forced onto the +3V3 rail, a GPIO shorted to
GND, and every signal net on the wrong pin — with BUSA_DATA, LEDGPIO and
MOTOR_EN additionally corrupting boot strapping. **Severity:
blocks-power-on.** Copper and DRC are clean; this is purely the
pad↔pin orientation model being wrong by 180°.

Exact correction: keep the documented USB-west mounting and swap each
live socket pad's net to the net of its mirror pad (new_net(p) =
old_net(23−p)); equivalently, in `gen_pcb.py` the socket map should map
pad N → module J-position N. Full corrected pad tables are in
`proposed_fixes.md` §F1.

## 5. Remaining FAILs

- **F2 — J14 NeoPixel data level (will-not-work / out-of-spec).**
  WS2812B datasheet: `VIH = 0.7 VDD` → 3.5 V minimum at 5 V supply; the
  board drives DIN straight from a 3.3 V GPIO. Margin −0.2 V below spec.
  Fix options (proposed_fixes §F2): 74AHCT125-level shift, series-diode
  strip supply ≈4.3 V, or sacrificial first pixel; also add the
  customary ~330–470 Ω DIN resistor + bulk cap.

- **F3 — +12 V path ampacity vs 10 A fuse (will-not-work at rated
  fuse).** 2.5 mm 1 oz tracks ≈6.3 A @20 °C rise; one 0.3 mm-drill via
  carries the whole input on +12V_IN; the fuse only opens >10 A.
  Between ~6.5–10 A continuous the copper overheats before protection.
  Fix: ≥4 paralleled vias + widen/pour the +12V* nets (≥4.5 mm for
  10 A @20 °C), or fit a fuse matched to real motor draw (STATUS-pcb12
  shows 6 A was the original intent — a 6 A fuse roughly matches the
  copper, but two stalled STS3215 ≈5.4 A would sit on the edge).

- **F4 — [U]→advisory: servo bus level.** Feetech TTL bus on the 12 V
  STS3215 may idle ≈5 V on its DATA line into the ESP32 pin through R1
  1k. Out-of-spec for a 3.3 V GPIO if the servo really drives 5 V
  (measure on bench; if so, add divider/zener — proposed_fixes §F4).

- **F5 — fuse-rating doc drift (cosmetic).** Board + silk + pcb12 status
  say 10 A; `pcb14/README.md` still documents 6 A. Doc-only fix.

- **F6 — J13 vs KY-040 order (will-not-work when plugged directly).**
  Board order VCC,GND,B,A,SW vs KY-040 GND,VCC,SW,DT,CLK. A bare EC11
  wired to silk works; a KY-040 module does not plug straight in.
  Fix: re-order header or document a mapped cable (proposed_fixes §F6).

## 6. [U] bench checklist

| Item | What to verify |
| --- | --- |
| K1 relay pads | confirm COM=pad3, NO=pad5 on the actual SRD relay body (DMM continuity, coil across 1–2) |
| Q1/Q3 transistor | use an E-B-C TO-92 (PN2222A). If only C-B-E (P2N2222A) stock exists, mount leads crossed/reversed to keep E on pad 1 |
| D4 TVS | identify uni- vs bidirectional "TVS15"; install band toward +12V_IN pad if unidirectional |
| Mini-360 | read clone pad labels; wire IN+/IN−/OUT+/OUT− per silk; **set VOUT to 5.0 V before connecting to J3** — a mis-set pot (>5.5 V) endangers TJA1051 (max ~7 V abs) and NeoPixel (max 5.3 V) |
| Servo DATA level | scope/DMM the STS3215 TX idle level on the bench; expect ≤3.6 V — if ≈5 V apply F4 fix |
| OLED module pin order | most are GND,VCC,SCL,SDA (matches); some clones are VCC,GND,SCL,SDA — check before plugging |
| Servo plug keying | confirm the Feetech cable latches into the KK-254 header in the right orientation |
| Buzzer type | confirm BZ1 is a self-driven 5 V active unit; consider adding a flyback diode if magnetic |
| Cap voltage ratings | C1 ≥25 V (transients), C3 ≥10 V, ceramics ≥ their rail ×1.2 |
| IRF4905 mounting | tab = Drain; silk should face tab toward +12V_SW side — confirm lead order G-D-S lands pads 1-2-3 (tab orientation marking is minimal) |
| Fuseholder | F1 is direct-solder mini-blade — replacement means desoldering; acceptable for a carrier but note it |
| IR receiver PU | VS1838B output idles high; enable ESP32 internal pull-up to be safe |
| +5V wired-OR | never power J2 and the Mini-360 simultaneously |

## 7. Independent netlist vs documentation

`audit_pins.py` dump (177 pads, 27 nets) was compared net-by-net to
`STATUS-pcb13.md`'s net table and the pcb12 doc trail:

- All 7 new nets from v1.3/v1.4 (+12V_RP, RP_GATE, +12V_MOT, RLY_LOW,
  RLY_SW, Q3_B, MOTOR_EN) match their documented pad sets exactly.
- GND: all 40 expected pads present.
- Mismatches found:
  1. `STATUS-pcb14.md` claims the ESP32 socket map was "verified" — the
     claim is wrong; see §4. The verification compared the generator's
     own assumption to itself.
  2. `pcb14/README.md` fuse text (6 A) vs board/silk/pcb12 (10 A) — F5.
  3. `STATUS-pcb14.md` "5V logic vs 3V3" note does not list the NeoPixel
     VIH violation — F2.
  4. README lists intended pads U1B.5=RXB(IO12), U1B.15=BUSB_DATA(IO15),
     U1A.14=WRX(IO39), U1A.16=SCL2(IO41), U1A.17=SDA2(IO42) — all are NC
     in the routed board (intentional spares; documentation only).

## 8. Physical / fabrication checks

| Check | Board | JLCPCB 2-layer min | Result |
| --- | --- | --- | --- |
| Min track | 0.25 mm | 0.10–0.127 mm (1 oz) | PASS |
| Min spacing | 0.5 mm zone clearance; ≥0.25 mm copper | 0.10–0.127 mm | PASS |
| Via pad/drill | 0.7 / 0.3 mm | ≥0.45–0.6 mm pad / ≥0.3 mm drill | PASS |
| Annular ring (via) | (0.7−0.3)/2 = 0.20 mm | ≥0.18 mm rec. | PASS |
| Annular ring (PTH) | e.g. header pads 1.7 mm / drill 1.0 → 0.35 mm | ≥0.18 mm | PASS |
| Min drill | 0.7 mm (test points) | 0.3 mm PTH | PASS |
| Max drill | 4.5 mm (XT60), 3.5×2 oval (F1), 3.2 mm NPTH (H1–4) | 6.3 mm | PASS |
| Copper→edge | GND pour inset 0.5 mm | 0.2 mm | PASS |
| MKDS drill | 1.3 mm vs pin 0.9×0.9 | datasheet hole Ø1.3 | exact |
| Header pitch | 2.54 / 5.08 / 7.20 / 1.19 mm drills | matches real parts | PASS |
| Relay pitch | SRD 4-pad grid per KiCad lib | — | [U] (see §6) |
| TO-220 | 2.54 pitch, 1.1 mm drill vs ~0.8 mm leads | fits | PASS |
| Silk text | all connector pin orders printed (JOG, OLED, NEO, CAN, Q1 EBC, USB->W, TOP=J1 BOT=J3, ESTOP-NC note, fuse 10 A) | min 1.0 mm height (silk here 0.8–1.0 mm, borderline on some) | PASS w/ note |
| 16× silk_overlap DRC | silk over pad edges — cosmetic only | — | cosmetic |

## 9. Safety notes

- **12 V high current:** XT60/Phoenix inputs can deliver tens of amps
  from a LiPo — F1 (10 A) is the only protection and it sits ABOVE the
  copper's comfortable capacity (F3). Size the fuse to the real load.
- **Fuse context:** the stage brief says 6 A; the board is marked and
  valued 10 A — STATUS-pcb12 records this as a deliberate v1.2 change.
  It is consistent, not a build error — but see F3.
- **Relay switches motor power:** K1 breaks +12V_MOT for J18/J20 and
  is itself gated by the NC e-stop loop through J19 — with no jumper/NC
  switch fitted the motors can never energise (fail-safe ✓).
- **LiPo/battery:** 12 V input only; no charge circuitry; observe
  polarity (Q2 protects the board but a reversed battery still dumps
  through D4 — check the TVS after any polarity event).
- **No mains anywhere.** Peak rail ≈24 V transient on clamp.
- **Before first power-on:** confirm the socket-map fix (§4) has been
  applied. Note +5V_MCU is fed by the module's 5 V pin on USB power,
  which feeds U2 VCC and C5 regardless of fuse F1.

## 10. Verdict

Fabrication as-is is not recommended. Every FAIL has an exact, verified
correction in `pcb14/check/proposed_fixes.md`; none require schematic
re-think beyond the socket re-map. Once F1 (socket mirror) is corrected
and F2/F3 mitigations are applied, the remaining items are bench-confirm
[U]s and cosmetic clean-ups.
