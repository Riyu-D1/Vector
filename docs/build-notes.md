# Build notes

> **Superseded pin map**: this file documents the pre-v1.3 carrier
> (bus B IO15/12, I2C2 IO41/42, wrist UART IO39/14). Those nets were
> REMOVED in carrier v1.3 — the current map is in
> `docs/STATUS-fw2.md` and `firmware/base-node/README.md`. Kept for
> history.

Order of operations that minimizes rework. Print everything first (days),
order parts while prints run, then assemble bottom-up.

## 1. Print the arm

- **Material**: PETG or ABS/ASA for structural parts (joints, links, case).
  PLA only for cosmetic shells — it creeps under constant joint load.
- **Layer**: 0.2 mm, 4+ walls/perimeters, 40–60% gyroid infill on
  load-bearing parts (yokes, brackets, links). 20% is fine for covers.
- **Orientation**: every part is designed to print flat on its largest face —
  no support material anywhere in `cad/export/`.
- SEA springs (`j2_sea_spring`, `j3_sea_spring`): 100% infill, print lying
  flat. These are the parts that define arm feel — print two spares.
- Expected filament: ~1.4 kg total. Expected time: ~3–4 days on a Bambu-class
  printer.

## 2. Assemble the electronics plinth (`cad/export/case_*.stl`)

1. **Tray**: drop the carrier PCB onto the four Ø6.4 mm standoffs; screw down
   with M3×8 (self-tap into the 2.2 mm pilot holes — pre-thread once by hand).
2. **Panel wiring** (short keyed leads, ≤120 mm):
   - EC11 jog → J13 (1=+3V3, 2=GND, 3=ENC_B, 4=ENC_A, 5=ENC_SW)
   - E-stop button → J9 (1=ESTOP, 2=GND)
   - OLED module → J11 (1=GND, 2=+3V3, 3=SCL1, 4=SDA1)
   - Passive buzzer → BZ1 pads (front grille bay)
3. Cable tails exit up through the rear channel before the lid goes on.
4. **Lid**: M3×10 into the four corner bosses; the drum lands in the Ø134
   recess. Five M4×16 hold-down screws thread through the lid into the
   tray posts under the seat ring.
5. The whole plinth is your arm's counterweight — the drum bolts to it and
   the PCB mass + footprint (150×160) resists tip-over at full reach.

## 3. Carrier board (see `pcb/README.md` for the pinout table)

- Socket everything: DevKitC, buck module, OLED, IMU — nothing solders
  directly except passives, headers and the XT60.
- Power-enable shunt: leave it OFF until smoke-test.
- Smoke test order: rails unpowered-continuity → 12 V on with no modules →
  +5 V rail measured → then plug modules → then servos.
- Firmware GPIO map (DevKitC-1 v1.1, assigned by destination proximity;
  strapping/USB/UART0/flash-PSRAM pins avoided):

| Signal | GPIO | Signal | GPIO |
|---|---|---|---|
| BUSA_DATA | IO17 | BUSB_DATA | IO15 |
| RXA | IO11 | RXB | IO12 |
| SDA1 | IO8 | SCL1 | IO18 |
| SDA2 | IO42 | SCL2 | IO41 |
| WTX | IO40 | WRX | IO39 |
| VSNS | IO10 (ADC1) | ESTOP | IO38 |
| ENC_A | IO21 | ENC_B | IO47 |
| ENC_SW | IO48 | NEO | IO4 |
| IRIN | IO5 | TEMP | IO6 |
| BUZ | IO7 | LEDGPIO | IO16 |
| SP1 | IO2 | SP2 | IO1 |

## 4. Arm stack-up

1. J1 drum bolts onto the plinth seat ring (M4 pattern in the lid).
2. J2 (HTD-45H + SEA) → upper link → J3 (STS3215 + SEA) → fore link →
   wrist module (J4/J5) → face plate + gripper.
3. Route the servo loom *inside* the links as you stack them — retrofitting
   the bus through assembled joints is the worst part of the build.
4. SEA encoder discs are glued to the output hubs dead-center before the
   cartridge caps go on — a 0.3 mm offset is ~1° of angle error.

## 5. First power

- IMU must show tilt ~0° on a flat desk — the base uses it for tip-over
  estop.
- Jog dial: click to select joint, rotate to move — verify each joint's
  direction matches the encoder sign before enabling torque.
