# BUILD_GUIDE — SOMA hybrid arm assembly + bring-up

Order-of-work for a first build. Cross-references: `docs/bringup.md`
(normative power-up), `cad/act2/BOM.md` (module), `cad3/PRINT_LIST.md`
(parts), `order/PCB_ORDER.md` (board), `order/BOM_FINAL.md` (parts).

Print time budget: largest part ~200 mm; all parts fit A1 256³.

## 0. Print order (do this first, ~3-4 days of printing)

Structural parts (PETG-CF, 0.2 layer, 6 walls, 40% gyroid): housings,
mid_plates, rings, link plates, fore_l2/fore_r2, j4_cradle, link4,
link5, grip_frame, fingers, base parts, spacers, flanges, rack pair.
Small loaded parts (PETG-CF, 0.12 layer, **6 walls, 100% infill**):
cycloid discs ×4, hubs ×2, carriers ×2, out_flanges ×2, mag_pucks ×2.

Print-sanity first run: housing front 12 mm test slice — verify the
52.1 mm 6808 seat and Ø3.05 pin holes BEFORE committing the full parts.

## 1. Post-processing

- Deburr all pin holes with a 3.0 mm reamer/bit — pins must press, not
  wedge. Sharp-tool hazard: cut away from hands, parts in a vice.
- Chase all M3 pilot holes with an M3 tap **or** the screw itself once;
  thread-forming screws split thin walls if driven dry first.
- Fit-test: 6808 into its seat (slip-press), 6702s into hubs, 685 into
  carrier, AS5600 board into the back pocket, Ø6 magnet into puck.
- Press the heat-set inserts (soldering iron ~220 °C, insert press tip,
  keep them square): 3× per actuator carrier flange, 4× J4 cradle
  pilots (replaces thread-forming — see STRESS_SANITY #6).

## 2. Actuator assembly (×2, J2 then J3)

1. Press 41× Ø3×10 ring pins into housing grooves (they stand on the
   blind floors); a drop of 603 if any pin is finger-loose.
2. Motor: 3× M3×6 ISO7380 stator → housing back plate, Loctite 243.
   Phase wires out through the wire channel/notch.
3. mag_puck + Ø6×2.5 magnet on shaft end: M3×4 button screw (243).
4. Hub: rotor adapter clamps the bell top — 2× M3×5 ISO7380 (243;
   the kit's M3×11.3 are too long, do NOT use them).
5. 6702 on each cam, discs 1&2 in phase (pin holes 180° apart —
   mark before assembly), 685 + carrier + out_flange stack, 3× M3
   into the carrier inserts.
6. 6× Ø3×12 output pins pressed 3.6 mm into the carrier; 3× Ø4×8
   locating dowels — **firm fit mandatory (603 if loose) — they carry
   output torque shear** (STRESS_SANITY #2).
7. Grease ring pins + disc flanks (PTFE/lithium). Spin-test the
   output by hand: ~40 turns in = 1 turn out, smooth, no catch.
8. AS5600 board in the back pocket, wires through the groove; check
   magnet–chip gap ~1 mm (0.5–3 spec).

## 3. Springs (J2 + J3)

- 471671 stock legs are 70 mm: cut/form on the bench into the pocket
  notches (one LH + one RH helix — see BOM note [U]).
- Target ~0.55 N·m/rad; at +70° expect ~0.67 N·m assist. Bench-verify
  with a spring scale at the arm radius BEFORE closing the joint.
- **Pinch hazard**: a wound torsion spring snaps; hold the coil with a
  gloved hand + lever with a bar, never fingers inside the pocket.

## 4. Arm mechanical build

- J1: STS3250 + metal horn in j1_cradle; AXK5578 + 2 washers + 6707
  stack; yaw_limit on 4× M3×8.
- J2/J3: modules between flanges; 6× M3 link bolts each — **torque
  evenly, all 6 engaged (single-pilot carry fails)**; 3× M3×14 (J2)
  / 3× M3×16 (J3) flange bolts + the 12× M3×10 csk back screws.
- J4: STS3250 in j4_cradle, 4× M3×10 into the **heat-set inserts**.
- Wrist: link4 → J5, link5 → J6, grip_frame + fingers; servo horns
  4× M3 on PCD14 each — set horns at mid-count (2048) before bolting
  to avoid a hard-stop fold at first power.
- Gripper: m1 16T gear on the horn (4× M3 csk), printed racks glued
  into the finger tabs.

## 5. Wiring harness

| Run | Wire | Notes |
|---|---|---|
| PSU → XT60 → carrier | 18 AWG silicone | fuse F1 6A on board; strain-relief both ends |
| J18/J20 → ESC ×2 | 18 AWG, ≤300 mm | twisted pair, +12V_MOT switched |
| ESC → motor phases | motor's own leads | keep phase bundle off the encoder magnet |
| Servo bus A (J4,J5 → servos 1,4,5,6,7) | Feetech 3-pin daisy | GND/+12V/DATA, 200–300 mm links |
| CAN carrier↔ESC2↔ESC3 | 22 AWG twisted pair | 120 Ω at BOTH ends; CANH/CANL/GND |
| J7/J8 AS5600 I2C | 22 AWG | SDA/SCL/3V3/GND per README pin table |
| J19 e-stop loop | 22 AWG | NC loop; jumper for bench, button for use |

12 V / 6 A: 18 AWG minimum on motor rail; CAN/encoders 22 AWG fine.

## 6. PCB soldering (v1.3-fixed)

- Solder low→tall: resistors → D5/D1 diodes → sockets → Q3 → Phoenix
  blocks → XT60 → K1 → Q2. Verify K1 pads against `pcb13_fix/` map:
  **pad1=COM(+12V), pads 2/5=coil (+12V & RLY_LOW), pad3=NO(+12V_MOT)**.
- Continuity checks BEFORE power: J18.1→K1.3; K1.5→+12V; K1.2→J19.1;
  J19.2→Q3.3; no shorts +12V↔GND (DMM beep).
- Socket the ESP32 (2×22) and Q3 (machined 1×03). Fit Mini-360 if
  used; otherwise J2 is the 5 V input.

## 7. Firmware flash

Environment: PlatformIO (`.venv-pio` per `docs/firmware-verification.md`;
the stm32duino core is pinned 2.12.0 — do NOT "upgrade" it).

```
cd firmware/base-node && pio run                 # build carrier fw
pio run -t upload                                # USB-C to DevKit UART port
cd firmware/joint-driver && pio run              # build ESC fw
pio run -t upload                                # ST-LINK onto each B-G431B
```

Set CAN node IDs before install: node 2 = J2 ESC, node 3 = J3 ESC.
Set Feetech IDs on the bench, one at a time: J1=1, J4=4, J5=5, J6=6,
gripper=7; bus 1 Mbaud nominal — **unverified on this wiring** (drop
FT_BAUD to 500000 both ends if the bus is deaf).

## 8. Power-up sequence (from docs/bringup.md — follow it verbatim)

1. **Bench supply, current limit 1 A** for every first step. 12 V
   high current: ring off, no loose wires, fuse in.
2. Stage 0: carrier only, J19 **jumper fitted**, motors off.
   `ping` → PONG fw 0x000200; `sense` flags MOTOR_EN=0/ARMED=0/
   ESTOP=0. J18/J20 must read **0 V** with 12 V applied.
3. Open the J19 jumper → STATE shows ESTOP. Close → `clear-estop`,
   `arm-motors` → relay clicks, J18/J20 = 12 V, then ~1.5 s
   `MOTOR_EN_OFF reason=6` (esc-boot-timeout) — that cycle IS the
   safety proof. E-stop press mid-window kills the rail instantly.
4. Stage 1: ESC node 2 on J18 + CAN; `arm-motors` → heartbeat within
   1.5 s, `can_ok_mask` bit0. Then both ESCs.
5. Stage 2: `mode 2 2` CALIBRATE (rotor free), `mode 2 3` HOME —
   hand on the e-stop, homing current/offset [U]. `enable`, ±0.1 rad
   moves, 60 s hold temp check. Repeat J3.
6. Stage 3: servos on bus A one at a time. Stage 4: full arm, `demo`
   at `--speed 0.2`, hand on e-stop, then payload ramp.

## 9. Safety summary

- **12 V 6 A**: enough to weld a ring or burn a servo — fuse never
  bypassed, current limit on first runs.
- **Mains PSU**: RS-100-12 is 230 VAC — earthed case, sleeved mains
  leads, no exposed live metal; LiPo swap only if you accept charge/
  fire management (3S max, no cutoff on board).
- **Pinch/crush**: spring pockets, cycloidal mesh, gear rack — keep
  fingers out when powered; spring forming is the highest injury-risk
  step.
- **Hot surfaces**: nozzle during insert pressing (~220 °C), motor
  bells and ESC after stalls, IRF4905 under sustained ~10 A.
- **Sharp tools**: reamers/knives during post-processing.
- **Magnet warnings**: N35 pucks snap together and shatter; keep off
  the AS5600 chip face until final assembly.

## 10. Printable checklist (one page)

```
[ ] All prints done, pin holes reamed, seats fit-tested
[ ] Inserts pressed (3/actuator + 4 J4 cradle)
[ ] J2 module: pins pressed, discs phased 180°, spins smooth
[ ] J3 module: same
[ ] Springs formed + rate-checked; seated in pockets
[ ] Dowels firm (603 where loose); horn screws 243
[ ] J1/J4 servos in cradles; horns preset to 2048
[ ] PCB: K1 pin map = fixed board; DMM continuity pass
[ ] J19 jumper fitted; F1 6A; PSU current limit 1A
[ ] base-node flashed, ping PONG 0x000200
[ ] Relay cycle proven (close -> timeout drop -> estop kill)
[ ] ESC node2 heartbeat -> can_ok_mask bit0; node3 both bits
[ ] J2 calibrate+home on bench -> homed; ±0.1 rad both ways
[ ] J3 same. 60 s hold temps OK
[ ] Servos 1,4,5,6,7 respond on bus A
[ ] Full arm: demo at 0.2 speed, e-stop in hand
[ ] Payload ramp only after clean demo
```
