# ACTUATOR INTERFACE — SOMA arm J1/J2/J3 (v0.1, 2026-10-27)

For Stream B (arm structure). One identical actuator module at J1, J2, J3.
Re-implementation of the Berkeley Humanoid Lite 5010 cycloidal actuator
(CC BY-SA 4.0). Numbers in **bold** are frozen; others may still move a few mm
(track this file on branch `arm-actuator`).

## Envelope

| | |
|---|---|
| **Outer diameter** | **70 mm** (cylindrical shell) |
| **Overall length** | **74 mm** nominal (rear cap face -> output flange face) |
| Mass target | ~0.35 kg printed + hardware (motor alone 162 g) |
| Ratio | **15:1** cycloidal |
| Peak torque | ~7.9 N.m (110 KV motor @12 V, ~5 A phase — see torque-analysis) |

Datum: **output-flange face = Z0**, axis = actuator axis. Shell extends
toward **-Z** (motor + driver at the back).

## Rotating OUTPUT interface (front face, Z0)

- Output flange OD: **50 mm**
- **8 x M3 threaded holes on 44 mm BCD**, useful depth 6 mm — this is where
  the driven link bolts on. Use M3x8 screws.
- Centre pilot boss **OD 45 mm x 1 mm proud** (the 6809 bearing inner journal
  is 45 mm; pilot boss is for centring only).
- Flange face must stay clear: keep the driven link's mating pocket >= 51 mm
  dia, depth per link design.

## FIXED input interface (rear face, -74 mm)

- Rear cap face has **4 x M3 on 64 mm BCD** (the M3x55 housing through-bolt
  heads). The fixed link can either:
  - bolt a flange to these 4 holes (M3x10 into the cap), or
  - clamp the 70 mm shell in a split ring/cheeks (recommended for J2/J3
    yokes: shell is plain cylinder 70 OD).
- A 2 mm register lip at OD 70.0/69.8 is present on both shell ends.

## Cable exit

- **Radial slot at the shell rear rim**: 8 mm wide x 12 mm, centred 6 mm
  from the rear face. Carries motor phase wires (16 AWG x3), CAN (30 AWG x2),
  encoder I2C (30 AWG x4) — bundle ~8 mm.
- Keep a 10 mm keep-out sector around the slot on the fixed link side.

## Internals (for reference, driven by `cad/actuator/params.py`)

- 16 x 6 mm ring pins on R29, disc 15 lobes, e = 1.5 mm, 2 discs 180 deg.
- Bearings: 2x 6809ZZ (output), 2x 6701-2RS (eccentric), 13x MR106-2RS
  (12 output-pin rollers + 1 pilot).
- Motor MAD 5010 EEE 110 KV (OD 56 x 32.7, mounts M3 @ 25/30 mm BCD).
- ESC B-G431B-ESC1 + AS5600 encoder in the rear bay.
- CAN: SN65HVD230 module -> carrier J15 (SP1=GPIO2, SP2=GPIO1, +5 V, +3V3,
  GND) — 12 V enters on the same loom.

## Coordinate convention for the arm

J1: actuator axis = +Z (yaw), output flange up.
J2: axis horizontal, output flange toward the upper link.
J3: axis horizontal, output flange toward the forearm.
