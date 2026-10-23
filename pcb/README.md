# SOMA Base Carrier v1

2-layer, all-through-hole, **zero ICs** carrier board for the base electronics.
Replaces the off-the-shelf servo bus hub + the ratsnest of Dupont wires: the
ESP32-S3-DevKitC-1 drops into pin sockets, every servo gets a keyed KK-254
connector, and power is fused + distributed on-board.

Board: 90 x 70 mm, 2 layers (F.Cu + B.Cu GND pour), all THT — hand-solderable
with an iron, no stencil, no SMD.

Generated parametrically by `gen_pcb.py` (same approach as `cad/`): parts are
placed by coordinate, nets by name, and a grid A* router lays the copper.

## Power flow

```
12V brick -> J1.1(+12V_IN) -> F1 (6A blade fuse) -> +12V rail
           -> J4/J5 (STS3215 bus A x2), J6 (HTD-45H bus B), J3 (buck in)
J3 Mini-360 buck (optional) -> +5V rail  ==OR==  J2 external 5V terminal
+5V -> D1 (1N5820 Schottky) -> +5V_MCU -> U1B.1 (ESP32 5V pin)
```

The Schottky means USB programming and board power can both be connected
at once — the diode drops board 5V to ~4.8V at the 5V pin so neither supply
fights the other. **D1 orientation: cathode band toward pin 1** (upper pad,
toward the +5V_MCU side).

## Connectors

| Ref | What | Pins |
|---|---|---|
| J1 | 12 V input | 1=+12V_IN, 2=GND |
| J2 | ext 5 V input (skip if Mini-360 fitted) | 1=+5V, 2=GND |
| J3 | Mini-360 buck module (optional) | 1=+12V, 2=GND-in, 3=+5V, 4=GND-out |
| J4, J5 | servo bus A (STS3215) | 1=GND, 2=+12V, 3=BUSA_DATA |
| J6 | servo bus B (HTD-45H) | 1=GND, 2=+12V, 3=BUSB_DATA |
| U1A/U1B | ESP32-S3-DevKitC-1 socket (2x 1x19 pin sockets) | USB faces LEFT |
| J7 | SEA encoder J2 (I2C) | 1=+3V3, 2=GND, 3=SDA1, 4=SCL1 |
| J8 | SEA encoder J3 (I2C) | 1=+3V3, 2=GND, 3=SDA2, 4=SCL2 |
| J9 | emergency stop | 1=ESTOP (GPIO), 2=GND |
| J10 | wrist node | 1=+5V, 2=GND, 3=WTX, 4=WRX |

Servo-bus coupling is passive: ESP32 TX drives DATA directly, RX listens
through R1/R2 (1k). Firmware ignores its own echo — the usual trick for
single-wire TTL buses without a transceiver IC.

LEDs: D2 = power (always on), D3 = status (GPIO-driven via U1B.18/IO47).
Test points: TP1 = GND, TP2 = +12V. Mounting: 4x M3.

## ESP32 pin map used

Bus A: TX=U1A.9 (IO17), RX=U1A.10 (IO18)
Bus B: TX=U1A.7 (IO15), RX=U1A.8 (IO16)
I2C-1: SDA=U1A.11 (IO8), SCL=U1A.14 (IO3)
I2C-2: SDA=U1A.16 (IO9), SCL=U1A.15 (IO46)
Wrist UART: TX=U1B.3 (TX0), RX=U1B.4 (RX0)
ESTOP: U1A.3 (IO4). Status LED: U1B.18 (IO47)

## Regenerating

    python3 gen_pcb.py            # ~20 min: builds + autoroutes the board
    kicad-cli pcb drc --refill-zones --format json --output drc.json \
        soma-carrier.kicad_pcb

Current DRC: **0 shorts, 0 unconnected, 0 clearance/hole violations.**
Remaining warnings are cosmetic silkscreen overlaps only (ref labels on a
dense THT board — fab house prints what fits).

Gerbers + drill in `gerbers/` — upload the folder to JLCPCB/OSH Park as-is.
2 layers, 1.6 mm, HASL, any colour. ~$5-10 for 5 boards.
