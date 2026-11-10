# BUILD_GUIDE — SOMA arm assembly + bring-up (F1 final)

Order-of-work for a first build. Cross-references: `docs/bringup.md`
(normative power-up), `cyclo4/` (D4 actuator), `final/PRINT_LIST.md`
(parts + tolerance plan), `order/PCB_ORDER.md` (board),
`final/BOM_FINAL.md` (parts).

Print time budget: largest part 200 mm; all parts fit A1 256³.

## 0. Print order (~3–4 days)

0. **CALIBRATION COUPON FIRST** — `final/out/coupon.stl`, ~20 min.
   Measure the 4 stations per `final/PRINT_LIST.md` §coupon: pass = a
   station reading ≥0.00 and ≤0.05 actual gap. If the printer runs
   oversize, add XY compensation and re-coupon BEFORE printing discs.
1. Structural parts (PETG-CF, 0.2 layer, 6 walls, 40% gyroid): housing,
   rings, link plates, fore_l2/fore_r2, j4_cradle, link4, link5,
   grip_frame, fingers, base parts, spacers, flanges, rack pair.
2. Small loaded parts (0.12 layer, 100% infill or ≥6 walls, no
   supports, ironing OFF): **cycloid discs ×4 (one plate, one go)**,
   hubs ×2, carriers ×2, out_flanges ×2, mag_pucks ×2.
3. Housing front-12 mm test slice first if unsure — verify the 52.1 mm
   6808 seat and Ø3.05 pin holes before the full housing.

## 1. Post-processing

- Deburr all pin holes with a 3.0 mm reamer/bit — pins must press, not
  wedge. Sharp-tool hazard: cut away from hands, parts in a vice.
- **Disc flanks**: scrape the first-layer edge, 400→800 grit ONE/TWO
  passes on the lobe tips only. Ream the 6 out-pin holes to a running
  fit (~Ø4.0) — do NOT ream ring-pin bores.
- Chase all M3 pilot holes with an M3 tap or the screw itself once.
- Fit-test: 6808 in seat (slip-press), 6702s into hubs, 685 into
  carrier, AS5600 board into the back pocket, Ø6 magnet into puck.
- Heat-set inserts (iron ~220 °C, press tip, keep square): 3× per
  carrier flange, 4× J4 cradle pilots.

## 2. Actuator assembly (×2, J2 then J3) — D4 selective-fit build

1. **Selective pin fit** (procedure in `final/PRINT_LIST.md`): seat all
   41 ring pins dry, number the stations, rock the input against each
   disc — swap tight pins for spares until the rock is uniform through
   a full crank turn. A drop of 603 only on a pin that is finger-loose.
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
   output torque shear**.
7. **Run-in**: grease ring pins + disc flanks (PTFE/lithium), hand-cycle
   ~200 input revs both ways (or a slow drill <200 rpm, 10 min). Mesh
   starts notchy, frees up. Still notchy → pull 2–3 tight pins, fit
   looser spares, repeat. Pass = ≤~1° backlash rock-test, one-finger
   spin 10 revs, no white powder inside.
8. AS5600 board in the back pocket, wires through the groove; check
   magnet–chip gap ~1 mm (0.5–3 spec).

## 3. Springs (J2 + J3)

- 471671 stock legs 70 mm: cut/form into the pocket notches (one LH +
  one RH helix — see BOM note [U]).
- Target ~0.55 N·m/rad; at +70° expect ~0.67 N·m assist. Bench-verify
  with a spring scale at the arm radius BEFORE closing the joint —
  see §7 checklist.
- **Pinch hazard**: a wound torsion spring snaps; gloved hand + bar,
  never fingers inside the pocket.

## 4. Arm mechanical build

- J1: STS3250 + metal horn in j1_cradle; AXK5578 + 2 washers + 6707
  stack; yaw_limit on 4× M3×8.
- J2/J3: modules between flanges; 6× M3 link bolts each — **torque
  evenly, all 6 engaged**; 3× M3×14 (J2) / 3× M3×16 (J3) flange bolts
  + the 12× M3×10 csk back screws.
- J4: STS3250 in j4_cradle, 4× M3×10 into the **heat-set inserts**.
- Wrist: link4 → J5, link5 → J6, grip_frame + fingers; servo horns
  4× M3 on PCD14 each — preset horns to mid-count (2048). **The J4
  horn plate (w_link4) needs M3×14**, not the shorter kit screws —
  R8 added +1.5 mm of plate reach for the rolled-pose margin.
- R9 wrist pin: slip the 1× ISO 8734 Ø3×18 dowel into the cradle pad
  bore Ø3.1 with adhesive (CA/603); the l4 journal bore Ø3.4 must
  slide free. Verify engagement through the full ±80° J4 sweep —
  the pin IS the second J4 bearing.
- Gripper: m1 16T gear on the horn (4× M3 csk), printed racks glued
  into the finger tabs.

## 5. Wiring harness

| Run | Wire | Notes |
|---|---|---|
| PSU → XT60 → carrier | 18 AWG silicone | fuse F1 6A; strain-relief both ends |
| J18/J20 → ESC ×2 | 18 AWG, ≤300 mm | twisted pair, +12V_MOT switched |
| ESC → motor phases | motor's own leads | keep phase bundle off the encoder magnet |
| Servo bus A (J4,J5 → 1,4,5,6,7) | Feetech 3-pin daisy | GND/+12V/DATA, 200–300 mm links |
| CAN carrier↔ESC2↔ESC3 | 22 AWG twisted pair | 120 Ω at BOTH ends; CANH/CANL/GND |
| J7/J8 AS5600 I2C | 22 AWG | SDA/SCL/3V3/GND per README pin table |
| J19 e-stop loop | 22 AWG | NC loop; jumper for bench, button for use |

12 V / 6 A: 18 AWG minimum on motor rail; CAN/encoders 22 AWG fine.

## 6. PCB soldering (v1.3-fixed)

- Low→tall: resistors → D5/D1 → sockets → Q3 → Phoenix → XT60 → K1 →
  Q2. Verify K1 pads against `pcb13_fix/`: **pad1=COM(+12V),
  pads 2/5=coil (+12V & RLY_LOW), pad3=NO(+12V_MOT)**.
- Continuity BEFORE power: J18.1→K1.3; K1.5→+12V; K1.2→J19.1;
  J19.2→Q3.3; no shorts +12V↔GND.
- Socket the ESP32 (2×22) and Q3 (machined 1×03). Fit Mini-360 if
  used; else J2 is the 5 V input.

## 7. Firmware flash + torque envelope (F1)

Environment: PlatformIO (`~/Vector-wt/fw2/.venv-pio` per
`docs/firmware-verification.md`; stm32duino core pinned 2.12.0 — do
NOT "upgrade" it).

```
cd firmware/base-node && pio run                 # build carrier fw
pio run -t upload                                # USB-C to DevKit UART port
cd firmware/joint-driver && pio run              # build ESC fw
pio run -t upload                                # ST-LINK onto each B-G431B
```

**Torque envelope now enforced in three places (F1):**

- **ESC (joint-driver)**: `TQ_CAP_NM` per joint — J2 3.0 N·m →
  **3.71 A**, J3 2.0 N·m → **2.47 A** phase cap via
  `T = I × Kt(0.0289 [U]) × 40 × η(0.7 [U])`. `SDO_CURRENT_LIMIT_A`
  writes and EEPROM values are CLAMPED to that ceiling — the host can
  only ever lower it. Output velocity capped at `VEL_LIMIT_OUT =
  0.5 rad/s` (~29 °/s, slow smooth moves).
- **Base node**: pushes the same caps over SDO at boot and clamps
  J2/J3 jog velocity to 0.5 rad/s.
- **Soft stop**: on NMT_ESTOP, NMT_DISABLE, or CAN heartbeat loss
  (500 ms silence while armed) the ESC ramps phase current to zero
  over **75 ms**, then disables — no torque step through the discs.
  The K1 relay cut is independent and stays instant.
- **Planner (robot-os)**: refuses waypoints whose static gravity torque
  exceeds the caps (`tests/test_torque_caps.py`); the old 80%-of-rated
  derate still applies on top.

Set CAN node IDs before install: node 2 = J2 ESC, node 3 = J3 ESC.
Feetech IDs on the bench one at a time: J1=1, J4=4, J5=5, J6=6,
gripper=7; bus 1 Mbaud nominal — **unverified** (drop FT_BAUD to
500000 both ends if the bus is deaf).

## 8. Power-up sequence (docs/bringup.md verbatim)

1. Bench supply, **current limit 1 A** for every first step.
2. Stage 0: carrier only, J19 jumper, `ping` → PONG 0x000200;
   J18/J20 = 0 V with 12 V applied.
3. J19 open → ESTOP; close → `clear-estop`, `arm-motors` → relay
   clicks, ~1.5 s `MOTOR_EN_OFF reason=6` = the safety proof.
4. Stage 1: ESC node 2 on J18 + CAN → heartbeat, `can_ok_mask` bit0.
   Then both.
5. Stage 2: `mode 2 2` CALIBRATE (rotor free), `mode 2 3` HOME —
   hand on e-stop. `enable`, ±0.1 rad moves, 60 s hold temp check.
   **Watch the first estop**: the arm should SETTLE, not snap (75 ms
   ramp working). Repeat J3.
6. Stage 3: servos on bus A one at a time. Stage 4: full arm, `demo`
   at `--speed 0.2`, hand on e-stop, then payload ramp.

## 9. Bench-verification checklist — every [U] in the drive chain

Do these BEFORE payload. "If fail" = what to change in firmware.

| [U] value | How to measure | Pass criteria | If it fails |
|---|---|---|---|
| Pole pairs 7 | Count rotor magnets by hand (14 magnets → 7 pp); or run `mode 2 2` CALIBRATE and check `SDO_ENCODER_OFFSET` repeats | Count = 14 magnets | Edit `POLE_PAIRS` in `joint_driver.ino`, reflash, re-calibrate |
| Kt 0.0289 N·m/A | Output-stall test: command iq = 1.0 A (torque mode), measure output force on a lever arm r → Kt = T_out/(I×40×η_meas) | 0.024–0.034 N·m/A | Change `KT_MOTOR` in `joint_driver.ino` + `KT_MOTOR`/`KT_MOTOR_NM_A` in `config.py`/`config.h` — all caps rescale automatically |
| Current caps 3.71/2.47 A | `param 0 <node> SDO_CURRENT_LIMIT_A` read-back after boot; then `set-current-limit <joint> 5.0` and read back | Read-back = 3.71/2.47; after the 5.0 write still ≤ cap (ESC clamped) | ESC clamp broken → reflash; if read-back is lower, EEPROM had an older value — save via SDO_SAVE_FLASH |
| Gear efficiency η 0.7 | Same stall test: η = T_meas/(I×Kt_meas×40) | ≥0.55 — caps stay conservative | η lower → output per amp is LESS: discs are safe but payload drops — lower `GEAR_EFF` in all three files and recompute caps (they rise in A; keep T_out caps fixed) |
| Soft-stop ramp 75 ms | Arm under light load, trigger `estop`, watch the joint settle; or scope a phase line if available | Arm settles smoothly, no snap/bounce; drive disables ~75 ms after | If it snaps: `ESTOP_RAMP_MS` increase to 150; if it sags before cutting: decrease to 50 |
| Velocity cap 0.5 rad/s | `move` jog at speed 1.0, time a 30° move ≥1.05 s | No faster than 0.5 rad/s at the output | If it exceeds: `VEL_LIMIT_OUT`/`JOINT_VEL_LIMIT_OUT_RADS` mismatch — check both files |
| Backlash ≤~1° | Output-flange rock test by hand, dial gauge or mark | ≤ ~1° at the output | Re-run selective pin fit; if still loose, check out-pin holes were reamed round not oval |
| Spring rate ~0.55 N·m/rad | Spring scale at known radius at 0°, +35°, +70° | 0.4–0.7 N·m/rad, no bind | Re-form legs/preload; if rate is way off, the gravity margin shrinks — re-run `max_payload` before payload |
| Relay K1 cut | `arm-motors` → J18 live; `estop`/watchdog-drop → J18 dead | Rail dies <50 ms after trigger, independent of any CAN state | Hardware fault — check pcb13_fix pad map (pad1 COM, 2/5 coil, 3 NO); do NOT bypass |
| AS5600 gap ~1 mm | Feeler gauge between magnet face and chip | 0.5–3.0 mm | Shim the puck pocket or re-seat the magnet |
| Homing current 1.0 A | Watch `home` on bench: reaches stop, stalls ~300 ms, zero sets | Stalls at stop without belt/grind noise | `HOME_CURRENT_A` 0.7–1.3 by ear; too high = flank shock, too low = false stall |
| FT bus 1 Mbaud | `sense` servo positions on bus A for 60 s | Zero dropped reads | `FT_BAUD 500000` + set each servo's baud to match |

## 10. Safety summary

- **12 V 6 A**: fuse never bypassed, current limit on first runs.
- **Mains PSU**: RS-100-12 is 230 VAC — earthed case, sleeved leads,
  no exposed live metal; LiPo only with charge/fire management.
- **Pinch/crush**: spring pockets, cycloidal mesh (near-zero clearance
  — it bites harder than it looks), gear rack.
- **Hot surfaces**: nozzle (~220 °C), motor bells/ESC after stalls,
  IRF4905 under sustained ~10 A.
- **Sharp tools**: reamers/knives during post-processing.
- **Magnets**: N35 pucks snap/shatter; keep off the AS5600 until final.

## 11. Printable checklist

```
[ ] Coupon printed; a station reads 0.00-0.05 actual -> printer calibrated
[ ] All prints done; discs = one plate, 100% infill, no ironing
[ ] Disc flanks deburred/sanded; out-pin holes reamed running-fit
[ ] Selective pin fit done; uniform rock both discs; card of swaps written
[ ] Run-in 200 revs greased; backlash <= ~1 deg; no powder
[ ] Inserts pressed (3/actuator + 4 J4 cradle)
[ ] Springs formed + rate-checked 0.4-0.7 N.m/rad; seated in pockets
[ ] Dowels firm (603 where loose); horn screws 243
[ ] J1/J4 servos in cradles; horns preset to 2048; M3x14 at the J4 horn plate
[ ] d3x18 wrist pin glued in the cradle pad; l4 journal slides free on it
[ ] PCB: K1 pin map = fixed board; DMM continuity pass
[ ] J19 jumper fitted; F1 6A; PSU current limit 1A
[ ] base-node flashed, ping PONG 0x000200
[ ] Relay cycle proven (close -> timeout drop -> estop kill)
[ ] ESC node2 heartbeat -> can_ok_mask bit0; node3 both bits
[ ] SDO_CURRENT_LIMIT_A reads 3.71 (J2) / 2.47 (J3)
[ ] J2 calibrate+home; +-0.1 rad both ways; estop settles not snaps
[ ] J3 same. 60 s hold temps OK
[ ] Servos 1,4,5,6,7 respond on bus A (60 s, no drops)
[ ] Full arm: demo at 0.2 speed, e-stop in hand
[ ] Payload ramp only after clean demo (<=0.5 kg per D4 envelope)
```
