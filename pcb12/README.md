# SOMA Base Carrier v1.1

2-layer, all-through-hole, **zero ICs** carrier board for the base electronics.
Replaces the off-the-shelf servo bus hub + the ratsnest of Dupont wires: the
ESP32-S3-DevKitC-1 drops into pin sockets, every servo gets a keyed KK-254
connector, power is fused + distributed on-board, and the useful little
peripherals (display, IMU, jog dial, buzzer, IR, temp, voltage sense,
addressable-LED port) are soldered or socketed directly on the board.

Board: 135 x 115 mm, 2 layers (F.Cu + B.Cu GND pours both sides + stitching
vias), all THT — hand-solderable with an iron, no stencil, no SMD. Everything
that plugs in uses standard 2.54 mm pin sockets, so modules stay removable.

Generated parametrically by `gen_pcb.py` (same approach as `cad/`): parts are
placed by coordinate, nets by name, and a grid A* router lays the copper
(3-D search — signals hop layers through vias where the plane is congested).

## Power flow

```
12V brick -> J16 XT60 plug  ==OR==  J1 screw terminal
          -> JP1 shunt (power switch; or wire a panel rocker here)
          -> D4 15 V TVS -> F1 (6 A mini blade fuse) -> +12V rail
          -> J4/J5 (STS3215 bus A x2), J6 (HTD-45H bus B), J3 (buck in)
J3 Mini-360 buck (optional) -> +5V rail  ==OR==  J2 external 5V terminal
+5V -> D1 (1N5820 Schottky) -> +5V_MCU -> U1B.2 (ESP32 5V pin)
```

The Schottky means USB programming and board power can both be connected
at once — the diode drops board 5 V to ~4.8 V at the 5 V pin so neither
supply fights the other. **D1 orientation: cathode band toward pin 1**
(the +5V_MCU side). D4 (TVS) is non-polar if you fit a bidirectional
part (P6KE15CA); band toward pin 1 (+12V_IN) for a unipolar one.

## Connectors

| Ref | What | Pins |
|---|---|---|
| J16 | 12 V input — XT60-M vertical plug | 1=GND, 2=+12V_IN |
| J1 | 12 V input — screw terminal (parallel w/ J16) | 1=+12V_IN, 2=GND |
| JP1 | power-enable shunt (or panel switch) | 1=+12V_IN, 2=+12V_SW |
| J2 | ext 5 V input (skip if Mini-360 fitted) | 1=+5V, 2=GND |
| J3 | Mini-360 buck module (optional) | 1=+12V, 2=GND, 3=+5V, 4=GND |
| J4, J5 | servo bus A (STS3215) | 1=GND, 2=+12V, 3=BUSA_DATA |
| J6 | servo bus B (HTD-45H) | 1=GND, 2=+12V, 3=BUSB_DATA |
| U1A/U1B | ESP32-S3-DevKitC-1 socket (2x 1x22 pin sockets) | USB faces LEFT |
| J7 | SEA encoder J2 (I2C) | 1=SDA1, 2=+3V3, 3=GND, 4=SCL1 |
| J8 | SEA encoder J3 (I2C) | 1=+3V3, 2=GND, 3=SDA2, 4=SCL2 |
| J9 | emergency stop | 1=ESTOP, 2=GND |
| J10 | wrist node | 1=GND, 2=WTX, 3=WRX, 4=+5V |
| J11 | SSD1306 OLED socket (I2C-1) | 1=GND, 2=+3V3, 3=SCL1, 4=SDA1 |
| J12 | GY-521/MPU6050 IMU socket (I2C-1) | 1=+5V, 2=GND, 3=SCL1, 4=SDA1, 7=GND |
| J13 | jog dial port (EC11 encoder) | 1=+3V3, 2=GND, 3=ENC_B, 4=ENC_A, 5=ENC_SW |
| J14 | WS2812 / NeoPixel port | 1=GND, 2=NEO(data), 3=+5V |
| J15 | spare header | 1=+5V, 2=GND, 3=SP1, 4=SP2, 5=+3V3 |

Servo-bus coupling is passive: ESP32 TX drives DATA directly, RX listens
through R1/R2 (1k). Firmware ignores its own echo — the usual trick for
single-wire TTL buses without a transceiver IC.

## On-board parts (solder-in)

| Ref | Part | Purpose |
|---|---|---|
| D4 | 15 V TVS (DO-201) | input transient clamp |
| F1 | 6 A mini blade fuse | rail protection |
| C1 | 1000 µF | 12 V bulk |
| C3 | 220 µF | 5 V bulk |
| C2, C4 | 100 nF | decoupling (12 V / 5 V) |
| D1 | 1N5820 Schottky | USB/board 5 V OR-ing |
| R1, R2 | 1k | servo-bus RX coupling |
| R7, R8 | 30k + 6.8k | 12 V divider -> VSNS ADC (≈0.185 x Vin) |
| BZ1 | 5 V active buzzer | fault/estop beeps |
| Q1 | 2N2222A (leads spread to 0.1") | buzzer low-side switch |
| R5 | 1k | buzzer base resistor |
| IR1 | VS1838B IR receiver | IR remote estop/home |
| DS1 | DS18B20 temp sensor (leads spread) | board ambient/overtemp |
| R6 | 4.7k | DS18B20 pull-up |
| D2 + R3 | LED + 330R | power LED |
| D3 + R4 | LED + 330R | status LED (GPIO) |
| TP1/TP2 | test pads | GND / +12V |
| H1–H4 | M3 | mounting |

TO-92 parts (Q1, DS1) solder onto 2.54 mm pads — spread the outer leads.
The true 1.27 mm TO-92 inline pitch can't pass a track to the middle pin,
so the board doesn't use it.

## ESP32 pin map used (socket positions, real DevKitC-1 v1.1 pinout)

The DevKitC-1 is a 2x22 module; sockets are 1x22. Socket position N maps to
the module pin at that position — pin 1 of each row is at the USB (west) end.

Top row U1B (module J1 side): 1=GND, 2=+5V_MCU, 5=RXB(IO12), 6=RXA(IO11),
7=VSNS(IO10-ADC1), 11=SDA1(IO8), 12=SCL1(IO18), 13=BUSA_DATA(IO17),
14=LEDGPIO(IO16), 15=BUSB_DATA(IO15), 16=BUZ(IO7), 17=TEMP(IO6),
18=IRIN(IO5), 19=NEO(IO4), 21=+3V3, 22=+3V3.

Bottom row U1A (module J3 side): 1=GND, 2=GND, 5=ENC_A(IO21), 6=ENC_B(IO47),
7=ENC_SW(IO48), 13=ESTOP(IO38), 14=WRX(IO39), 15=WTX(IO40), 16=SCL2(IO41),
17=SDA2(IO42), 18=SP1(IO2), 19=SP2(IO1), 22=GND.

Unconnected by design: strapping pins IO0/IO3/IO45/IO46, USB pins
IO19/IO20, console UART0 IO43/IO44, and flash/PSRAM pins IO26-37 on
N16R8 modules. VSNS uses IO10 (ADC1 only — ADC2 conflicts with Wi-Fi).
**Verify the module's silkscreen pin order on assembly** — Espressif has
revised this board.

## Regenerating

    python3 gen_pcb.py            # ~15-25 min: builds + autoroutes the board
    python3 fill_zones.py         # bakes the GND pours into the file
    kicad-cli pcb drc --format json --output drc.json \
        soma-carrier-v12.kicad_pcb

`fill_zones.py` uses KiCad's bundled pcbnew `ZONE_FILLER` when present
(exact engine — needed because headless refill ignores the generator's
K9-style zone sexpr unless the rule-area flag is cleared), else falls
back to `pour.py` (build123d booleans emitting `filled_polygon` data).
In the GUI, `B` re-fills interactively.

Routing notes for future edits: J13 pad3/4 dive north on staggered
columns; pad5 (ENC_SW) dives south via the deep lane reached from the
EAST (x36-38 descent) — the J9 pad+stub marks wall x29-35,y76-83. The
merged R3/R6 keepouts (x48-66,y50-58) force SDA1/SCL1 transit to y46-48
and parallel lanes at y35.8/37.6 under C4/over TP2. WTX uses the far
east x87-88 descent + deep lane; WRX uses the x60 slot + field dive.
J13 pad 1 is +3V3 (fed from the west). Keep dive waypoints ~1.6 mm
below pad centres.

Gerbers + drill in `gerbers/` — upload the folder to JLCPCB/OSH Park as-is.
2 layers, 1.6 mm, HASL, any colour. ~$5-10 for 5 boards.

Last verified DRC: 0 clearance / 0 track / 0 via electrical violations,
0 non-GND unconnected; 2 GND pads (J15.2, TP1.1) sit in pour-starved
pockets — acceptable, or add a stitched via nearby. Remaining report
items are silkscreen cosmetics and generated-library footprint diffs.
