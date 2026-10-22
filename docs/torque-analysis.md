# SOMA — Joint Torque & Mass Budget

Worst-case static analysis used to size actuators and define the rated payload.
All numbers are conservative estimates to be re-verified against the final CAD
mass properties.

## Geometry & assumed masses

| Segment | Length / position | Assumed mass |
|---|---|---|
| Upper arm link (J2→J3) | 180 mm | ~220 g (printed PETG, 30% infill) |
| Forearm link (J3→wrist) | 160 mm | ~150 g |
| Elbow joint (J3 servo at joint) | at 180 mm | ~110 g |
| Wrist/face/gripper cluster (J4, J5 servos, eyes, camera, gripper, pads) | at ~340 mm | ~280 g |
| Payload | at flange, ~400 mm | **300 g rated** |

Total moving mass ≈ 1.06 kg + payload. If CAD comes in heavier, payload
derates first (see margin table).

## Worst-case static torques (arm fully extended horizontal)

τ = Σ m·g·r with g = 9.81.

### J2 — shoulder

| Load source | m (kg) | r (m) | τ (N·m) |
|---|---|---|---|
| Upper arm link | 0.22 | 0.09 | 0.19 |
| J3 servo | 0.11 | 0.18 | 0.19 |
| Forearm link | 0.15 | 0.26 | 0.38 |
| Wrist/face cluster | 0.28 | 0.34 | 0.93 |
| Payload | 0.30 | 0.40 | 1.18 |
| **Total** | | | **≈ 2.9 N·m** |

**Actuator: Hiwonder HTD-45H** → stall ≈ 4.4 N·m (45 kg·cm @11.1 V), real
price $25–30 vs. $79–165 for the SM60CL it replaces. Continuous rating is not
published; ~15 kg·cm ≈ 1.5 N·m is the working estimate.

**The gravity-assist spring is now required hardware, not a mitigation.** A
~1–1.5 N·m assist at full extension drops the servo's share of the worst case
to ~1–1.5 N·m — inside its realistic envelope. The SEA encoder reports true
output torque, so the servo not having a load register costs nothing: firmware
duty-limits on *measured* torque, which is more accurate than motor-current
inference anyway.

Premium swap if bench tests fail: SM60CL (60 kg·cm stall, real 20 kg·cm rated
spec, +$50–135) — `SERVO_XL` in params.py adjusts the mount envelope.

Additional margin levers, unchanged:
- Derate payload to 200 g → worst case ≈ 2.5 N·m.
- Reduce reach to 350 mm → worst case ≈ 2.4 N·m.
- CyberGear drop-in at J2 (4 N·m continuous, native torque telemetry).

### J3 — elbow (load distal to J3 only)

| Load source | m (kg) | r (m) | τ (N·m) |
|---|---|---|---|
| Forearm link | 0.15 | 0.08 | 0.12 |
| Wrist/face cluster | 0.28 | 0.16 | 0.44 |
| Payload | 0.30 | 0.22 | 0.65 |
| **Total** | | | **≈ 1.2 N·m** |

**Actuator: STS3215-12V** → stall ≈ 2.9 N·m (30 kg·cm @12 V), ~$21 vs. $55–100
for the SM40BL it replaces. Stall margin 2.4× over worst case; usable
continuous ~0.9 N·m vs. ~0.8 N·m sustained need — duty-managed via its own SEA
like J2. Bonus: same TTL bus + same protocol library as J1/J4/J5/grip — J3 is
no longer a second servo family. ✓

### J1 — waist

Yaw axis: gravity does not load it; loads are inertial + friction.
STS3215 is ample. ✓

### J4/J5 — wrist

Distal cluster only: ≈ 0.28 kg at ~50–80 mm + payload moments ≈ **0.2–0.5 N·m**
worst case. STS3215-12V (stall ≈ 2.9 N·m) — now ~6× margin vs. the 19.5 kg·cm
7.4 V variant originally assumed. ✓

### Gripper tendon

Tendon-driven underactuated fingers; STS3215 → tendon tension for ~10–15 N
fingertip force achievable with ~20–30 mm tendon lever arms. Exceeds the ~5 N
per-finger need for desk objects. ✓

## SEA spring sizing (J2, J3)

Series-elastic cartridge = printed spiral/straight torsion spring between servo
output and link; AS5600 reads output-side angle. Torque = k·Δθ.

| Joint | Max working torque | Target max deflection | Spring rate target | Torque resolution (12-bit enc) |
|---|---|---|---|---|
| J2 | ~2.9 N·m | ~7° (0.12 rad) | ~24 N·m/rad | ~0.037 N·m/count |
| J3 | ~1.2 N·m | ~7° (0.12 rad) | ~10 N·m/rad | ~0.015 N·m/count |

Notes:
- Printed springs creep/hysteresis — prefer PETG or nylon over PLA, or
  laser-cut acetal/polycarbonate disc springs. Print 2–3 candidate geometries.
- **Calibration rig**: clamp the link, hang known masses at a known radius,
  record encoder deflection → fit k and the hysteresis curve. Document the
  calibration table in the repo.
- Side benefit: output-side encoders bypass servo gear backlash — the arm's
  *reported* position is the true link position, fixing the classic
  cheap-servo drift problem.

## Torque limits (software safety)

Per-joint `torque_limit` register caps every servo in software; nominal cap =
static worst case + 30%. J2/J3 additionally trip a yield-admit if measured SEA
torque exceeds the cap.
