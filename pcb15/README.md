# SOMA Base Carrier v1.5

2-layer, all-through-hole carrier board for the base electronics.
Replaces the off-the-shelf servo bus hub + the ratsnest of Dupont wires: the
ESP32-S3-DevKitC-1 drops into pin sockets, every servo gets a keyed KK-254
connector, power is fused + distributed on-board, and the useful little
peripherals (display, IMU, jog dial, buzzer, IR, temp, voltage sense,
CAN transceiver, NeoPixel port) are soldered or socketed directly on the board.

Board: 135 x 115 mm, 2 layers (F.Cu + B.Cu GND pours both sides + stitching
vias), all THT — hand-solderable with an iron, no stencil, no SMD (U2 CAN
transceiver is the one SOIC-8 exception). Everything that plugs in uses
standard 2.54 mm pin sockets, so modules stay removable.

v1.5 fixes the CHECK-pcb14 audit findings: the ESP32 socket was mirrored
180° (F1 — power shorts + wrong GPIO), the NeoPixel port lacked a 5 V
level shifter (F2), the 12 V rails were undersized for 10 A (F3), the
servo-bus RX had no clamp footprint (F4), the fuse was documented as
6 A (F5), and J13's pin order didn't match a stock KY-040 (F6).

## Power flow

```
12V brick -> J16 XT60 plug  ==OR==  J1 screw terminal
          -> JP1 shunt (power switch; or wire a panel rocker here)
          -> D4 15 V TVS -> F1 (10 A mini blade fuse) -> +12V rail
          -> J4/J5 (STS3215 bus A x2), J3 (buck in), K1 relay (motor feed)
J3 Mini-360 buck (optional) -> +5V rail  ==OR==  J2 external 5V terminal
+5V -> D1 (1N5820 Schottky) -> +5V_MCU -> U1B.21 (ESP32 5V pin)
```

**Use ONE 5 V source only** — fit either the Mini-360 buck on J3 *or* feed
external 5 V into J2, never both. (Silkscreen reminder is on the board.)

The Schottky means USB programming and board power can both be connected
at once — the diode drops board 5 V to ~4.8 V at the 5 V pin so neither
supply fights the other. **D1 orientation: cathode band toward pin 1**
(the +5V_MCU side). D4 (TVS) is non-polar if you fit a bidirectional
part (P6KE15CA); band toward pin 1 (+12V_IN) for a unipolar one.

**F1 is a 10 A mini blade fuse** (v1.4 doc said 6 A — wrong). The +12V
motor feed passes through K1 (SRD-12V, contacts rated 10 A) so firmware
can cut motor power on estop/fault; the servo rails are unfused past F1
by design — the fuse is the only overcurrent device on the 12 V path.

## Connectors

| Ref | What | Pins |
|---|---|---|
| J16 | 12 V input — XT60-M vertical plug | 1=GND, 2=+12V_IN |
| J1 | 12 V input — screw terminal (parallel w/ J16) | 1=+12V_IN, 2=GND |
| JP1 | power-enable shunt (or panel switch) | 1=+12V_IN, 2=+12V_SW |
| J2 | ext 5 V input (skip if Mini-360 fitted) | 1=+5V, 2=GND |
| J3 | Mini-360 buck module (optional) | 1=+12V, 2=GND, 3=+5V, 4=GND |
| J4, J5 | servo bus A (STS3215) | 1=GND, 2=+12V, 3=BUSA_DATA |
| U1A/U1B | ESP32-S3-DevKitC-1 socket (2x 1x22 pin sockets) | USB faces LEFT |
| J9 | emergency stop button | 1=ESTOP, 2=GND |
| J11 | SSD1306 OLED socket (I2C-1) | 1=GND, 2=+3V3, 3=SCL1, 4=SDA1 |
| J12 | GY-521/MPU6050 IMU socket (I2C-1) | 1=+5V, 2=GND, 3=SCL1, 4=SDA1, 7=GND |
| J13 | jog dial port — **direct KY-040 fit** | 1=GND, 2=+3V3, 3=SW, 4=DT, 5=CLK |
| J14 | WS2812 / NeoPixel port | 1=GND, 2=NEO5V(data, shifted), 3=+5V |
| J15 | spare header | 1=+5V, 2=GND, 3/4=NC, 5=+3V3 |
| J17 | CAN bus | 1=GND, 2=CANH, 3=CANL |
| J18, J20 | 12 V motor feed (K1-switched) | 1=+12V_MOT, 2=GND |
| J19 | estop loop NC jumper | 1=RLY_LOW, 2=RLY_SW |
| JP2 | CAN termination jumper | 1=CAN_TERM, 2=CANL |

J13 was re-pinned in v1.5 so a stock KY-040 encoder module plugs straight
on: GND, 3V3, SW, DT(=ENC_B), CLK(=ENC_A). No adapter needed.

## On-board parts (solder-in)

| Ref | Part | Purpose |
|---|---|---|
| D4 | 15 V TVS (DO-201) | input transient clamp |
| F1 | **10 A** mini blade fuse | rail protection |
| C1 | 1000 µF | 12 V bulk |
| C3 | 220 µF | 5 V bulk |
| C2, C4 | 100 nF | decoupling (12 V / 5 V) |
| D1 | 1N5820 Schottky | USB/board 5 V OR-ing |
| R1 | 1k | servo-bus RX coupling (kept) |
| D6 | 3V6 zener (footprint only, optional) | RXA clamp — see F4 note |
| R7, R8 | 30k + 6.8k | 12 V divider -> VSNS ADC (≈0.185 x Vin) |
| U3 | **74AHCT125** (DIP-14 socket) | NEO 3V3 -> 5V level shifter |
| R13 | **330R** | NeoPixel DIN series resistor |
| C7 | **470–1000 µF** | strip supply bulk at J14 |
| C8 | 100 nF | U3 decoupling |
| BZ1 | 5 V active buzzer | fault/estop beeps |
| D7 | 1N4148 | buzzer flyback (inductive load) |
| Q1 | 2N2222A (leads spread to 0.1") | buzzer low-side switch |
| R5 | 1k | buzzer base resistor |
| IR1 | VS1838B IR receiver | IR remote estop/home |
| DS1 | DS18B20 temp sensor (leads spread) | board ambient/overtemp |
| R6 | 4.7k | DS18B20 pull-up |
| D2 + R3 | LED + 330R | power LED |
| D3 + R4 | LED + 330R | status LED (GPIO) |
| U2 | TJA1051T/3 (SOIC-8) | CAN transceiver |
| C5, C6 | 100 nF | U2 VCC/VIO decoupling |
| R9 | 120R | CAN termination (via JP2 jumper) |
| K1 | SRD-12V (contacts 10 A) | motor-power relay, estop chain |
| D5 | 1N4007 | relay-coil flyback |
| Q3 | 2N2222A | relay driver |
| R11, R12 | 1k + 10k | Q3 base resistors |
| Q2 | IRF4905 | reverse-polarity protection (tab = drain) |
| R10 | 10k | Q2 gate pull-down |
| TP1/TP2 | test pads | GND / +12V |
| H1–H4 | M3 | mounting |

TO-92 parts (Q1, Q3, DS1) solder onto 2.54 mm pads — spread the outer
leads. The true 1.27 mm TO-92 inline pitch can't pass a track to the
middle pin, so the board doesn't use it.

## NeoPixel level shifting (F2)

IO4 drives NEO at 3.3 V logic; WS2812 DIN wants ~0.7xVDD ≈ 3.5 V — marginal.
U3 (74AHCT125, powered from +5V) level-shifts it to a real 5 V swing:
`U1B.4 -> U3.2 (1A) -> U3.3 (1Y) -> R13 330R -> J14.2`. All four /OE
pins are grounded (always enabled; 3 spare drivers). C7 sits at the
strip supply pins — fit 470–1000 µF there per the strip length, and R13
330R in series damps the data edge.

## Bus clamp footprint (F4)

R1 (1k) stays as the RX coupling. D6 is a 3V6 zener footprint on RXA,
**unpopulated by default** — fit it only if bench measurement of the
bus high level exceeds ~3.6 V at the ESP32 pin (long-cable reflections
on the STS3215 bus can overshoot).

## ESP32 pin map used (socket positions, real DevKitC-1 v1.1 pinout)

The DevKitC-1 is a 2x22 module; sockets are 1x22. **Socket position N maps
to module pin N — pin 1 of each row is at the USB (west) end.** (v1.4 had
this backwards — the socket was mirrored; v1.5 fixes it per the official
Espressif user-guide pin layout.)

Top row U1B (module J1 side): 1=+3V3, 2=+3V3, 3=RST/EN, 4=NEO(IO4),
5=IRIN(IO5), 6=TEMP(IO6), 7=BUZ(IO7), 9=LEDGPIO(IO16), 10=BUSA_DATA(IO17),
11=SCL1(IO18), 12=SDA1(IO8), 16=VSNS(IO10-ADC1), 17=RXA(IO11),
21=+5V_MCU, 22=GND.

Bottom row U1A (module J3 side): 1=GND, 4=CAN_RX(IO1), 5=CAN_TX(IO2),
8=MOTOR_EN(IO40), 10=ESTOP(IO38), 16=ENC_SW(IO48), 17=ENC_B(IO47),
18=ENC_A(IO21), 21=GND, 22=GND.

Unconnected by design: strapping pins IO0/IO3/IO45/IO46, USB pins
IO19/IO20, console UART0 IO43/IO44, and flash/PSRAM pins IO26-37 on
N16R8 modules. VSNS uses IO10 (ADC1 only — ADC2 conflicts with Wi-Fi).
**Verify the module's silkscreen pin order on assembly** — Espressif has
revised this board.

## Regenerating

    python3 gen_pcb.py            # placement + board skeleton (~minutes)
    python3 reroute.py            # replaces all copper from routes_v15.py
    python3 fill_zones.py         # bakes the GND pours into the file
    ./fab.sh                      # fill + DRC + gerbers + drill

`gen_pcb.py` is the placement/footprint/pad-net authority;
`routes_v15.py` + `reroute.py` are the routing authority (hand-routed
0/45/90 legs with chamfered corners — no autorouter).
`fill_zones.py` uses KiCad's bundled pcbnew `ZONE_FILLER` when present
(exact engine), else falls back to `pour.py`. In the GUI, `B` re-fills
interactively.

Verify with `check_pads.py` (placement probe), `reroute.py --check`
(route rules), `verify_nets.py`, `audit_pins.py`, and `net_stats.py`.

Gerbers + drill in `gerbers/` — upload the folder (or the packaged
`soma-carrier-v15-jlcpcb.zip`) to JLCPCB/OSH Park as-is.
2 layers, 1.6 mm, HASL, any colour. ~$5-10 for 5 boards.

## Safety

- 12 V, 10 A fuse on the input — the board can source real current;
  shorted 12 V tracks will bite. Fuse first, power second.
- The SRD-12V relay switches *motor* power only (10 A contacts); the
  servo bus rails are direct from F1.
- Battery/PSU handling: XT60 polarity is marked; the IRF4905 reverse-
  polarity FET protects the board but not a reversed servo.
- No mains anywhere on this board — 12 V SELV only.
