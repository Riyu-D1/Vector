# SOMA — Bill of Materials

Target: full-functionality all-servo build. Build cost for the funding request:
**~$460** including reserve (~$414 in parts). Fits the Level 4 cap ($1000) with
headroom; exceeds Level 3 ($400), so this is submitted as a Level 4 project.

> If you decide to run headless (agent's computer as the only brain), drop the
> Orange Pi 5 — total lands ~$375 and fits **under the Level 3 cap**.

## Actuation

| Qty | Part | Unit est. | Sub | Source / notes |
|---|---|---|---|---|
| 1 | Feetech SM60CL-class serial servo, ~60 kg·cm @12 V, RS485 (J2 shoulder) | $40 | $40 | AliExpress — RS485 bus, steel gears, brushless |
| 1 | Feetech SM40BL, 40 kg·cm @12 V, RS485 (J3 elbow) — 46.5×28.5×34 mm, 100 g | $32 | $32 | AliExpress — RS485, 9–24 V input |
| 4 | Feetech STS3215, 19.5 kg·cm @7.4 V, TTL (J1, J4, J5, gripper) — 45.2×24.7×35 mm, 55 g | $16 | $64 | AliExpress/Waveshare |
| 1 | RS485 transceiver module (MAX3485/SN65) | $3 | $3 | SM servos are RS485, not TTL — second bus off ESP32 UART2 |
| 1 | Metal servo horns/spline hardware | $8 | $8 | Usually bundled — verify 25T spline |

**⚠ Datasheet correction vs. earlier drafts:** STS3215 stall is **19.5 kg·cm
(1.9 N·m)** at 7.4 V — not 30. J2 needs ~2.9 N·m worst-case, so the big joints
move to SM-class servos (RS485, 12 V). Consequence: **two servo buses** (TTL
for the smalls, RS485 for the bigs — one ESP32-S3 runs both) and **two rails**
(12 V main, bucked to 7.4 V for the STS3215s — they die at 12 V).

Alternative if a single bus is preferred: all-SM lineup (SM-class small servos
exist but cost ~$25 each and are overkill at the wrist) or swap STS3215s for a
~35 kg·cm TTL servo (Hiwonder HTS-35H-class) and drop J2 to a spring-assisted
45 kg TTL unit — documented fallback, adds procurement risk.

## Sensing

| Qty | Part | Unit est. | Sub | Source / notes |
|---|---|---|---|---|
| 3 | AS5600 magnetic encoder breakout + 6×3 mm diametric magnet | $4 | $12 | AliExpress — 2× on SEA outputs (J2, J3), 1× on tendon idler. AS5600 has a fixed I2C addr — split across the ESP32's two I2C buses (see architecture.md) |
| 2 | BMP390 pressure sensor breakout | $4.5 | $9 | AliExpress/LCSC — potted in silicone fingertip pads (Ecoflex below) |
| 1 | IMU (MPU6050 or LSM6DS3) | $5 | $5 | Any generic breakout |
| 1 | Torsion spring wire/kit assortment (music wire 0.8–1.5 mm) | $8 | $8 | For SEA cartridges + tendon idler return spring |
| 1 | Ecoflex 00-30 / 00-50 silicone (small kit) | $15 | $15 | Fingertip pad potting + gripper pads |

## Compute & interaction

| Qty | Part | Unit est. | Sub | Source / notes |
|---|---|---|---|---|
| 1 | Orange Pi 5, 4 GB | $85 | $85 | Official store/AliExpress — 6 TOPS NPU for onboard vision. **Alternate:** Raspberry Pi 5 4 GB ($60) — easier software, no NPU |
| 1 | ESP32-S3 dev board (base node) | $8 | $8 | Drives servo bus, SEA encoders, IMU, watchdog |
| 1 | ESP32-S3-MINI or ESP32-C3 mini board (wrist/face node) | $6 | $6 | Drives eyes + fingertip I2C + tendon encoder |
| 2 | GC9A01 1.28" round LCD module (SPI) | $7 | $14 | "Robot eyes" standard part |
| 1 | USB micro camera (wide angle) | $13 | $13 | Mounted in wrist/face module; **alternate:** ESP32-CAM $8 over WiFi (worse image, zero wiring) |
| 1 | INMP441 I2S mic + MAX98357A amp + 8Ω mini speaker | $13 | $13 | Voice presence |
| 1 | microSD 64 GB | $8 | $8 | Pi boot |

## Power & interconnect

| Qty | Part | Unit est. | Sub | Source / notes |
|---|---|---|---|---|
| 1 | 12 V / 6–8 A PSU, barrel output | $20 | $20 | Main rail — feeds SM servos directly |
| 1 | Buck 12 V→7.4 V, ≥3 A (STS3215 rail) | $7 | $7 | STS3215 max is 8.4 V — keep the buck at ≤8 V |
| 1 | Buck 12 V→5 V, ≥4 A (logic + Pi rail) | $8 | $8 | |
| 1 | Servo bus hub / breakout (3-pin TTL, daisy chain) | $8 | $8 | The SO-101 motor-control board works ($11 on Amazon) |
| 1 | Wiring kit: JST/XH + silicone wire + ferrules + 4-wire harness through arm | $15 | $15 | |
| 1 | misc connectors, heatshrink, cable spiral/chain | $10 | $10 | |

## Mechanical

| Qty | Part | Unit est. | Sub | Source / notes |
|---|---|---|---|---|
| ~1.5 kg | PETG + TPU filament | $25 | $25 | PETG structure, TPU soft shell/fingertip skins |
| 1 | Bearing assortment (6704/6804 thin-section + 608) | $10 | $10 | Joint support bearings |
| 1 | M2–M5 fastener assortment + heat-set inserts | $12 | $12 | Heat-set inserts everywhere — no self-tappers |
| 1 | Springs/steel wire + tendon line (Dyneema/PE braid fishing line) | $6 | $6 | Tendon-driven gripper |
| 1 | Shafting/dowel pins, epoxy, threadlocker | $8 | $8 | |

## Totals

| | |
|---|---|
| Actuation | ~$147 |
| Sensing | ~$49 |
| Compute & interaction | ~$139 |
| Power & interconnect | ~$68 |
| Mechanical | ~$61 |
| **Subtotal** | **~$464** |
| Reserve (broken part, re-print, shipping variance) | ~$45 |
| **Funded ask** | **~$470–490** |

Headless variant (no Orange Pi, agent on your computer over USB): ~$385 —
still Level 4-able, or trim mechanical reserve to scrape under the $400 L3 cap.

## Already-owned / excluded

- 3D printer & filament time — assumed available.
- Agent compute (your computer) — excluded, per Fabricate rules (no funding for
  owned gear).
- Optional CyberGear drop-in at J2 later (~$165) — the shoulder mount should be
  designed so a QDD upgrade only replaces the cartridge, not the arm.

## Risks / substitutions

- **Serial servo availability**: if 60 kg·cm bus servos are out of stock, 2×
  STS3215 ganged on J2 is the documented fallback (SO-100 family does similar
  doubling on the shoulder).
- **AS5600 I2C address conflict**: all AS5600s share 0x36 — put SEA encoders on
  I2C bus 0 of the base node and the tendon idler on the wrist node's bus.
- **Spring tuning**: SEA springs are characterized on a bench rig with known
  masses (see torque-analysis.md); print 2–3 geometries and calibrate.
