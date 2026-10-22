# SOMA — Bill of Materials

Target: full-functionality all-servo build with **verified sourcing** (prices from
real listings — AliExpress/Waveshare/Hiwonder/Seeed/DFRobot, Oct 2025).

Build cost: **~$440 with onboard brain**, **~$355 headless** — either way well
under the Level 4 cap ($1000); headless also fits Level 3 ($400) after reserve.

## What the research changed (vs. first draft)

- **STS3215-12V exists** — same servo, 30 kg·cm @12 V (not just the 19.5 kg 7.4 V
  version), ~$20. This collapses the design: J3 doesn't need an SM servo, and
  *every* servo runs on one 12 V rail over TTL. No RS485 transceiver, no 7.4 V
  buck, one protocol for five joints.
- **SM60CL costs $79–165 real** (not ~$40) — replaced by Hiwonder HTD-45H at
  $25–30 for J2, with the gravity-assist spring becoming *required* hardware
  instead of a mitigation. The SEA output encoder measures true joint torque,
  so losing the servo's internal load register costs no sensing capability.
- **SM40BL costs $55–100 real** — replaced by STS3215-12V for J3 (2.5× stall
  margin at J3's 12 kg·cm worst case).
- **Waveshare ESP32-S3-LCD-1.28** ($16) is the wrist/face node — it *includes* a
  GC9A01 round display (eye #1) and a QMI8658 IMU, so those two line items drop.

## Actuation

| Qty | Part | Unit | Sub | Verified source / notes |
|---|---|---|---|---|
| 1 | Hiwonder HTD-45H serial bus servo — 45 kg·cm stall @11.1 V, TTL, 9–12.6 V, 51.1×20.1×40 mm, 64 g (J2 shoulder) | $28 | $28 | hiwonder.com $24.99 / RobotShop $29.99. Feedback: position/temp/voltage (torque comes from SEA). 0–240° range ✓. **Verify spline type on arrival** |
| 5 | Feetech STS3215 **12 V variant** (ST-3215-C047 / Waveshare ST3215) — 30 kg·cm @12 V, TTL, 45.2×24.7×35 mm, 55 g (J1, J3, J4, J5, gripper) | $21 | $105 | Waveshare $21.99 / DFRobot $19.90 / AliExpress ~$15–18. **Order the 12 V version, not 7.4 V** — same bus family as SO-101, same library |
| 1 | Metal servo horns/spline hardware | $8 | $8 | Bundled with most listings — verify 25T |
| 1 | J2 gravity-assist extension spring (~1–1.5 N·m assist at full reach) | $8 | $8 | **Required, not optional** — derates HTD-45H continuous load to ~1 N·m. Extension spring + printed anchor, tuned on bench |

### Why HTD-45H and not SM60CL at J2

| | HTD-45H | SM60CL |
|---|---|---|
| Real price | $25–30 | $79–165 |
| Stall torque | 45 kg·cm (4.4 N·m) | 60 kg·cm (5.9 N·m) |
| Rated/continuous | ~15 kg·cm est. | 20 kg·cm (real spec) |
| Feedback | pos/temp/volt | pos/load/current/temp |
| Case | plastic, 64 g | aluminum, 180 g |

J2 worst-case statics are ~2.9 N·m; with the assist spring the servo's share is
~1–1.5 N·m — inside HTD-45H's realistic envelope. The SEA encoder reports true
output torque regardless, so firmware duty-limiting is identical either way.
SM60CL remains the documented premium swap (param `SERVO_XL` adjusts the mount).

### J3 selection

STS3215-12V: 30 kg·cm stall vs. 12 kg·cm worst-case → 2.5× stall margin,
~0.9 N·m usable continuous vs. ~0.8 N·m need — plus its own SEA tells us the
real number. Saves $35–80 vs. SM40BL and keeps J3 on the same TTL bus and
protocol library as the other four servos.

## Sensing

| Qty | Part | Unit | Sub | Verified source / notes |
|---|---|---|---|---|
| 3 | AS5600 magnetic encoder breakout + 6×3 mm diametric magnet | $4 | $12 | Adafruit $5.95 / AliExpress ~$2–4. 2× SEA outputs (J2, J3), 1× tendon idler. Fixed addr 0x36 → split across I2C buses (see architecture.md) |
| 2 | BMP390 pressure breakout | $4.5 | $9 | AliExpress ~$3–4. Potted in Ecoflex fingertip pads |
| 0 | IMU | — | $0 | QMI8658 already on the ESP32-S3-LCD wrist board |
| 1 | Music-wire assortment 0.8–1.5 mm (SEA + idler springs) | $8 | $8 | Bench-characterized per torque-analysis.md |
| 1 | Ecoflex 00-30 silicone kit | $15 | $15 | Fingertip pad potting + grip skins |

## Compute & interaction

| Qty | Part | Unit | Sub | Verified source / notes |
|---|---|---|---|---|
| 1 | **Orange Pi 5B 4 GB** (recommended brain) | $75 | $75 | AliExpress ~$75 — RK3588S, 6 TOPS NPU, onboard WiFi + eMMC. Best perf/$ in class (RPi5 4GB ~$60–110 has no NPU; OPi5 non-B ~$90–140). **Optional** — see headless below |
| 1 | ESP32-S3-DevKitC-1 (base brainstem) | $10 | $10 | Two UARTs = two servo buses; I2C sensors; watchdog |
| 1 | Waveshare ESP32-S3-LCD-1.28 (wrist/face node) | $16 | $16 | ESP32-S3 + GC9A01 round LCD (eye #1) + QMI8658 IMU onboard — replaces 3 line items |
| 1 | GC9A01 1.28" round LCD, bare (eye #2) | $7 | $7 | Shared SPI bus, second CS |
| 1 | ESP32-CAM (OV2640) — wrist camera | $8 | $8 | Streams MJPEG to agent over WiFi; upgrade path OV5640 +$5 |
| 1 | INMP441 I2S mic | $3 | $3 | Voice in |
| 1 | MAX98357A I2S amp + 8Ω speaker | $7 | $7 | Voice out |
| 1 | microSD 64 GB (if Pi installed) | $8 | $8 | |

## Power & interconnect

| Qty | Part | Unit | Sub | Notes |
|---|---|---|---|---|
| 1 | 12 V / 8 A PSU, barrel out | $20 | $20 | One rail feeds **all** servos (HTD-45H: 9–12.6 V; STS3215-12V: 6–12.6 V ✓) |
| 1 | Buck 12 V→5 V, ≥5 A | $8 | $8 | Logic + Pi + displays |
| 1 | Servo bus hub/board (TTL daisy chain) | $8 | $8 | SO-101 motor-control board (~$11) works |
| 1 | Wiring kit: JST-XH, silicone wire, ferrules, in-arm 4-wire harness | $15 | $15 | |
| 1 | Connectors/heatshrink/cable chain, fuse + switch | $10 | $10 | |

~~7.4 V buck~~ and ~~RS485 transceiver~~ deleted — not needed with the revised
servo set. Total power budget: 6 servos ≈ 20–25 W typical, 70 W transient worst.

## Mechanical

| Qty | Part | Unit | Sub | Notes |
|---|---|---|---|---|
| ~1.5 kg | PETG + TPU filament | $25 | $25 | PETG structure, TPU shell/grip skins |
| 1 | Bearing assortment: 6808 (base) + 6804 + 6704 thin-section | $10 | $10 | |
| 1 | M2–M4 fasteners + heat-set inserts | $12 | $12 | Inserts everywhere — no self-tappers |
| 1 | Dyneema/PE braid tendon line + ferrules | $6 | $6 | ~0.5 mm, ~40 kg test |
| 1 | Shafting/dowel pins, epoxy, threadlocker | $8 | $8 | |

## Totals

| | |
|---|---|
| Actuation | ~$149 |
| Sensing | ~$44 |
| Compute & interaction | ~$134 |
| Power & interconnect | ~$61 |
| Mechanical | ~$51 |
| **Subtotal** | **~$439** |
| Reserve (spares, reprints, shipping) | ~$45 |
| **Funded ask (with Orange Pi 5B)** | **~$485** |
| **Funded ask (headless, no Pi)** | **~$400** |

## Variants

- **Recommended (this BOM):** $485 ask — onboard NPU brain, works untethered.
- **Headless:** drop Pi + microSD (−$83) → ~$400 ask, agent runs on your
  computer over USB-C. Same sensing, same compliance, loses "untethered demo."
- **Premium J2:** swap HTD-45H → SM60CL (+$50–135): aluminum case, real rated
  torque spec, RS485 (needs MAX3485 +$3). Do it only if bench tests show the
  assist spring can't keep HTD-45H in duty range.

## Staged purchase plan (de-risks before full spend)

1. **Stage 1 — SEA rig (~$55):** 1× STS3215-12V, 1× AS5600 + magnet, music-wire
   kit, filament. Print 2–3 J3 SEA discs, characterize spring rate + hysteresis.
   Everything else is mechanical work that costs nothing but time.
2. **Stage 2 — skeleton (~$180):** remaining 5 servos, ESP32-S3 pair, bus hub,
   PSU, bearings, fasteners. Whole arm moves under control.
3. **Stage 3 — senses & face (~$120):** encoders, BMP390s, displays, ESP32-CAM,
   audio, silicone. Compliance + expression online.
4. **Stage 4 — brain (~$85):** Pi 5B + microSD (optional — headless saves it).

## Already-owned / excluded

- 3D printer & filament time — assumed available.
- Agent compute (your computer) — excluded per Fabricate rules.
- Optional CyberGear drop-in at J2 (~$165 CN) — J2 mount stays parametric so a
  QDD upgrade replaces the cartridge, not the arm.

## Risks / substitutions

- **HTD-45H is the value bet:** stall torque is real, continuous spec is not
  published. Mitigations: assist spring (required), SEA duty management, and
  SM60CL as documented premium swap. This is the one part to bench-test first
  in Stage 2 — hold 1.5 N·m for 60 s, log temperature.
- **STS3215-12V vs 7.4V:** order carefully — the part numbers differ (C047 vs
  C018). Same price, wrong voltage kills the servo.
- **AS5600 address conflict:** all AS5600s share 0x36 — SEA encoders on the
  base node's two I2C buses; tendon idler on the wrist node's bus.
- **Spline verification:** HTD-45H uses Hiwonder's spline, STS3215 uses 25T —
  horn adapters in CAD are parametric; print-fit on arrival before locking.
- **AliExpress lead times:** 2–4 weeks — order Stage 1 immediately.
