# SOMA ARM v3 — build instructions

One arm: printed cycloidal actuators J1–J3, STS3215 wrist, ESP32-S3 base
node on a fabbed carrier, all on a printed case. Everything below is the
integrated state of `arm-integrated`; items the CAD/tests could not prove
are in the UNVERIFIED table at the end — measure them on the bench.

Verification status: CAD suite 22/22, host tests 41/41, firmware UNBUILT
(no toolchain here — syntax-checked only). Nothing has touched hardware.

---

## 1. Parts list (order these)

### 1.1 Electronics

| qty | part | notes |
|---|---|---|
| 3 | MAD Components 5010 EEE V2.0 110 KV motor (Ø56×32.7, 162 g) | J1–J3; 12N14P |
| 3 | ST B-G431B-ESC1 driver | one per actuator |
| 3 | AS5600 encoder module + 6×3 mm diametric magnet | output-shaft feedback |
| 3 | Feetech STS3215 **12 V** (ST-3215-C047 / Waveshare ST3215) | J4/J5/J6 — order the 12 V variant, not 7.4 V |
| 1 | ESP32-S3-DevKitC-1 (N16R8 or N8) | base node; verify silkscreen pin order |
| 1 | SOMA carrier PCB v1.1 | fab from `pcb/gerbers/` (JLCPCB/OSH Park, 2-layer 1.6 mm) |
| 1 | SN65HVD230 CAN transceiver module (3.3 V) | plugs J15; **do not feed it +5 V** |
| 1 | Mini-360 buck module (optional) | 12 V→5 V on J3; else feed J2 ext 5 V |
| 1 | 12 V / 8 A PSU brick + XT60 lead | single rail feeds everything |
| 1 | Ø16 panel estop button, **NC** | front rim cutout → J9 |
| 1 | EC11 jog encoder (optional) | J13 |
| 1 | SSD1306 0.96" OLED, I2C (optional) | J11 + front bezel pocket |
| 1 | Orange Pi (host) + USB cable | runs `software/robot-os` |
| 2 | 120 Ω axial resistors | CAN bus ends — only if the boards lack them |

### 1.2 Carrier passives (solder-in — see `pcb/README.md` for refs)

6 A mini blade fuse (F1), 15 V TVS (D4), 1N5820 (D1), 2N2222A (Q1),
5 V active buzzer, VS1838B IR rx, DS18B20, 1000 µF + 220 µF + 2×100 nF
caps, 1 k×3 + 4.7 k + 330 Ω×2 + 30 k + 6.8 k resistors, LEDs ×2,
pin-socket strips, KK-254/JST pigtails, XT60-M plug, screw terminals,
M3 board screws.

### 1.3 Bearings & shaft hardware

| qty | part | where |
|---|---|---|
| 1 | 6812 bearing (60×78×10) | J1 turntable race, base drum top |
| 6 | 6809ZZ (45×58×7) | 2 per actuator, stacked output hub |
| 6 | 6701-2RS (12×18×4) | 2 per actuator, input journals |
| 39 | MR106-2RS (6×10×3) | 13 per actuator: 12 output rollers + 1 pilot |
| 48 | Ø6 mm dowel pin ×~16 mm | 16 per actuator (ring pins) — cut to suit `UNVERIFIED` |
| 3 | M4×12 hex standoff | input-shaft tip support, per actuator |

### 1.4 Fasteners (arm structure — from `checks.py` fastener table)

| qty | part | where |
|---|---|---|
| 5 | M4×16 csk self-tap | drum → lid posts |
| 4 | M4×10 | bearing cap → housing rim (into inserts) |
| 8 | M3×12 | turret plate → J1 flange PCD44 |
| 2 | M3×16 | J1 clamp-ring ear pinch |
| 4 | M4×10 | turret_cap clamp |
| 4 | M4×10 | upper_link_cap clamp |
| 8 | M3×10 | J2 flange → upper cheek PCD44 |
| 8 | M3×10 | J3 flange → forearm cheek PCD44 |
| 4 | M4×8 | J4 wrist idler stub socket (into inserts) |
| 8 | M2×8 self-tap | J4 servo end faces |
| 8 | M2×8 self-tap | J5 servo end faces |
| 4 | M2×8 self-tap | J6 servo bottom ears |
| 4 | M3×8 | J4 wheel → wrist cheek |
| 4 | M3×8 | J5 wheel → nose plate |
| 20 | M4 heat-set inserts | housing rim ×4, cradle caps ×8, bearing cap ×4, J4 idler ×4 |
| ~4+4 | M3/M2.5 self-tap | case-lid corners + PCB standoffs `UNVERIFIED` (pilot holes Ø1.15/Ø1.1) |

### 1.5 Fasteners (per actuator — ×3)

| qty each | total | part |
|---|---|---|
| 4 | 12 | M3×55 socket-head (housing clamp bolts) |
| 6 | 18 | M3×25 + washers (output-roller retention) |
| 4 | 12 | M3×6 (motor stator → shell lands) |
| 6 | 18 | M3×8 (driven link → output flange PCD44) |
| 4 | 12 | M2×6 (AS5600 board → end cap) |
| 4 | 12 | M2.5×6 (ESC → end cap posts) |
| 24 | 72 | M3×4×5 heat-set inserts |
| 4 | 12 | M2×3×3.5 heat-set inserts |

---

## 2. Print list

PETG recommended (mass model assumes 45 % effective fill,
perimeter-heavy), 0.4 nozzle, 220×220 bed minimum — all parts pass
`print-bed-220`. PLA acceptable for a proto fit-check.

### 2.1 Case — `cad/export/` (print as-modelled, flat)

| part | orientation | supports |
|---|---|---|
| case_tray | flat on floor | no (recesses face up) |
| case_lid | flat, top down | no |

### 2.2 Arm structure — `cad/arm/export/` (14 parts)

Files in `export/print/` are already rotated for the bed; the rest
print in assembly orientation.

| part | orientation | supports |
|---|---|---|
| base_housing | as-modelled, drum up | `UNVERIFIED` — has >60° overhang faces (drum lip, recess); try none first, add brim |
| bearing_cap | as-modelled | likely none |
| j1_clamp_ring | as-modelled | no |
| turret | as-modelled, plate down | `UNVERIFIED` — cradle is a split half-pipe, prints cup-up |
| turret_cap | as-modelled | no |
| upper_link | `export/print/` (back face down) | `UNVERIFIED` |
| upper_link_cap | as-modelled | no |
| forearm | `export/print/` (side face down) | `UNVERIFIED` |
| horn_ext_j4 | as-modelled | no |
| wrist | `export/print/` (side face down) | `UNVERIFIED` |
| horn_ext_j5 | as-modelled | no |
| nose | `export/print/` (flat face down) | `UNVERIFIED` |
| jaw_l, jaw_r | as-modelled | no |

(`ref_sts3215.stl` and `assembly.stl` are reference — do not print.)

### 2.3 Actuators — `cad/actuator/export/` (7 parts ×3, from §6 of `actuator-verification.md`)

| part | orientation | supports |
|---|---|---|
| housing ×3 | flange up | none (axial grooves, bridged shelves) |
| cycloidal_disc_x2 ×3 | flat | none |
| input_shaft ×3 | upright on tip face | none (0.8 mm ledges) |
| output_shaft ×3 | flange down | none |
| motor_shell ×3 | as-modelled, open top | none |
| end_cap ×3 | face down | none |
| motor_shaft ×3 | flat | none |

Total: 2 case + 14 arm + 21 actuator = **37 printed parts**.

---

## 3. Assembly order

### 3.1 Actuators ×3 (`cad/actuator/README.md` — verified)

1. Heat-set inserts into all pockets (24×M3, 4×M2 per actuator).
2. Seat the 16 ring pins in the housing grooves.
3. Input shaft in from the top; press 6701 + disc1 on journal 1, then
   6701 + disc2 rotated 180°.
4. Drop the 6809 pair into their seat pockets.
5. Output shaft in from the top — pins thread both disc holes.
6. Motor from below: stator to shell lands, puck on rotor bolts, square
   drive mates the shaft.
7. ESC + AS5600 onto end-cap posts (magnet gap ~1–3 mm `UNVERIFIED`);
   end cap closes; 4×M3×55 clamp the stack.

### 3.2 Base + arm (`docs/STATUS-structure.md` assembly map)

1. Bolt the carrier PCB onto the case-tray standoffs; wire the panel
   parts (estop button → J9 **NC loop**, jog → J13, OLED → J11).
2. Set the case lid: arm drum drops into the recess at (75, 88); 5×M4×16
   csk hold the drum to the tray posts.
3. Base: seat J1 actuator in the Ø70.4 pocket (rear face down), close
   `j1_clamp_ring` ears (2×M3×16), drop the 6812 race, bolt
   `bearing_cap` (4×M4 into inserts).
4. Turret: plate on J1 flange (8×M3×12 PCD44), `turret_cap` clamp (4×M4).
5. J2 actuator → `upper_link` cheeks (8×M3×10 PCD44), `upper_link_cap`
   (4×M4). Route the J2 cable through the cheek keep-out.
6. J3 actuator → `forearm` cheeks (8×M3×10), cable through the saddle
   web bore into the link channel.
7. Wrist: J4 servo into the forearm fork (M2 grids, idler stub on the
   +Y side), `horn_ext_j4` + `wrist` cheeks (4×M3×8 wheel bolts),
   J5 servo + `horn_ext_j5`, `nose` (4×M3×8).
8. J6 servo top-mounts the nose; `jaw_l`/`jaw_r` slide ±Y on the rail.
9. Dress cables: riser at r~39 (−Y) in the base, link channels, joint
   slots — all verified clear by CAD checks; use spiral wrap, leave
   service loops at joints.

### 3.3 Wiring

- **CAN bus (J1–J3 drivers):** SN65HVD230 module on carrier **J15**:
  pin 3 (SP1=IO2) → module TXD/CTX, pin 4 (SP2=IO1) → module RXD/CRX,
  pin 5 → 3V3, pin 2 → GND. **Never pin 1 — that is +5 V and the
  module is 3.3 V.** Twisted pair CANH/CANL to each ESC1's CAN port
  (PA11 RX / PB9 TX on the MCU). **120 Ω termination at BOTH ends** —
  set `CAN_TERM_LAST=true` only on the last node's build (onboard
  PC14 termination), fit a 120 Ω resistor at the carrier end if the
  module has none (`UNVERIFIED` — check your module).
- **Servo bus:** J4 or J5 header (daisy-chain the three STS3215, ids
  4/5/6): pin1 GND, pin2 +12 V, pin3 BUSA_DATA (IO17). TTL
  single-wire — keep leads < ~50 cm, twist with GND.
- **Power:** XT60 → J16 (or screw terminal J1), JP1 shunt as the
  switch, buck on J3 for 5 V (or feed J2).
- **Actuator wiring per unit:** 3 motor phases → ESC pads, CAN pair,
  AS5600 on I2C1 (PB6 SCL/PB7 SDA, J8 connector `UNVERIFIED` pin
  order), 12 V.
- **Estop:** button NC loop → J9 pin1↔pin2. Open = estop, always wire
  before motor power.
- Common ground between carrier and all three ESC boards is mandatory.

---

## 4. First power-up

Follow **`docs/bringup.md`** — it is the staged checklist (stage 0
carrier-only → stage 4 assembled arm). The short version:

1. Carrier only, USB to host: `python -m soma_arm.cli --port
   /dev/ttyUSB* ping` → PONG. Prove the estop line and the 500 ms
   watchdog **before any motor is attached**.
2. CAN: one driver at a time, `NMT CALIBRATE` with the rotor free, then
   enable + small moves. Set per-joint caps J1 3 A / J2,J3 5 A (the
   base node pushes them every boot anyway).
3. Servos one at a time on bus A; drop `FT_BAUD` to 500 k if 1 Mbps is
   flaky (`UNVERIFIED` on this wiring).
4. Assembled arm: `enable`, jog each joint slowly, then `demo` at
   `--speed 0.2`, hand on the estop. Payload last, to 250 g.

---

## 5. UNVERIFIED — check before/while building

| item | where it bites | what to do |
|---|---|---|
| 5010 pole pairs = 7 | `joint_driver.ino` POLE_PAIRS; actuator-verification says "14 pole pairs" — likely means 14 poles = 7 pp | count rotor magnets |
| AS5600 on J8 PB6/PB7 | encoder dead → no FOC | check UM2516 J8 pin order; alt PB7/PB8 |
| Feetech bus at 1 Mbps | servos silent | scope or drop to 500 k both ends |
| SN65HVD230 120 Ω | CAN errors | module-dependent; fit resistor if absent |
| Motor shaft stub Ø6 mm + rotor bolt circle | shaft won't mate | measure on arrival (BHL assumed) |
| Output-pin BCD 33 mm / roller stack | discs won't assemble | arithmetic + thumbnail only |
| ESC hole pitch ~33 mm, encoder 25.4/20 mm | boards won't seat on posts | measure on arrival |
| Dowel pin length ~16 mm | pins short/long | cut to suit |
| Case-lid + PCB screw sizes | pilots are Ø1.15/Ø1.1 | try M3 self-tap, verify bite |
| >60° overhangs on several arm parts | droop/stringing | orient per `export/print/`; supports if needed |
| All firmware | never compiled here | install PlatformIO/STM32duino on the build machine, flash, then run `docs/bringup.md` |
| J6 gripper jaw↔shaft mapping | stroke/servo direction | jog on bench, flip sign if reversed |
