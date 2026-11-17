# SOMA printed actuator study (2026-10-28, Europe/London)
Maths: `printed_act_calc.py`. Prices in USD, read 28 Oct 2026 unless marked; [U] = unverified, [P] = from an earlier note (27 Oct).

## 1. Candidates (read from repo or page today)
| Design | Type, ratio | Motor | Size, mass | Torque | Backlash | Licence, files |
|---|---|---|---|---|---|---|
| **Dongil Choi V2** [hackaday.io/project/167688](https://hackaday.io/project/167688) | cycloid 40:1, e = 0.5 mm | Tarot 4008 330KV | **OD 60 mm**, length [U], mass [U] | not published | not published | licence [U]; STL zip (44.7 MB, 2019), no STEP |
| **SwannSchilling** [github.com/SwannSchilling/Cycloidal-Drive](https://github.com/SwannSchilling/Cycloidal-Drive) | cycloid 40:1 | Tarot 4108 + AMT102 | [U] | [U] | [U] | no licence on GitHub; Printables 53681 |
| Berkeley Humanoid Lite [MakerWorld 1279205](https://makerworld.com/en/models/1279205-5010-cycloidal-gear-actuator) | cycloid 15:1 | 5010 | 70 × 85.5 mm, 509 g [P] | Kt 0.1176 [P] | "slight growth" after 60 h [P] | licence [U], Onshape CAD. **Too fat** |
| TipTapMotor [github](https://github.com/DarrenLevine/TipTapMotor) | planetary 8:1 | GBM3506H-130T | 47 × 47 × 47 mm | [U], too low a ratio for J2 | [U] | MIT, STL |
| Caden Kraft QDD [github](https://github.com/CKraft11/Ironless-QDD-Actuator) | cycloidal-tooth planetary 7:1 | wound 10010 | 728 g | 29.4 N·m at 50 A | "no perceptible" | credit requested. **Too big**, but its lobe-profile gears (pygeartrain) are the best low-backlash printed tooth idea |

Cycloid designs carry the load on many lobes at once and tolerate print error. Printed spur planetaries are weaker and have more backlash.

## 2. Shoulder and elbow sizing
- **Motor: Tarot TL2955 4008 330KV.** 44.5 mm OD, 22 mm tall, 85 g, 0.145 Ω [U, xcopterCalc], 4 mm shaft (not hollow). Price $45.99 at Foxtech. AliExpress 4008 listings run about $25–29 [U].
- Kt = 8.27/KV = 0.0251 N·m/A. At 40:1 and 75 % efficiency that is **0.75 N·m per phase amp** (0.70 at 70 %, 0.80 at 80 %).
- **J2 (40:1):** 2.3 N·m static needs 3.1 A. 1.5× (3.45 N·m) needs 4.6 A. With a **5 A limit it gives 3.5–4.0 N·m** and about 2.3 W of copper loss, which is fine.
- **J3 (same module):** 1.8 N·m needs 2.4 A, so a 3 A limit gives 2.25 N·m. One module design for both joints.
- Speed at 12 V is about 99 rpm at the output (ideal, no load). At 24 V it is about 198 rpm, but the STS servos are 12 V only, so stay at 12 V.
- **Rejected:** GM4108H-120T (11.1 Ω, hollow shaft). It is limited to about 1.25 A at 12 V and gives only about 8 rpm at 40:1.
- **Envelope:** reBot's joint ends are Ø57 (R28.5, 6×M3 PCD50 back, PCD27 output). The plan is a **Ø56–57 × about 50–55 mm** housing [estimate]: motor 22 mm + two cycloid discs + a 6808 (40×52×7) output bearing, as in the Dongil design, + an ESC1 (30×41 mm, diagonal 50.8 mm) behind the motor. That is about GIM4310 size. Mass [U].

## 3. Driver and encoder
- **ST B-G431B-ESC1:** $39.26 at the ST eStore (Berkeley's paper listed $19). 30 × 41 mm, 9.2 g, up to 6S, 40 A peak. CAN has an onboard transceiver (UM2516 search snippet [U]). It runs the Berkeley Humanoid Lite CAN firmware or SimpleFOC.
- Encoder: AS5600 or AS5047P/MT6701 on the motor shaft (about $3–5 [U]). At 40:1 the output is multi-turn, so **homing is needed** (end-stop, or a second output-side AS5600).
- Host: ESP32-S3 TWAI + SN65HVD230 board, $4.69 [P].
- **Rejected:** MKS XDrive Mini ($40.99, 63×58×32 mm, too big). SimpleFOC Mini has no CAN.

## 4. Other joints
- J4–J6 and the gripper: STS3215, $74.95 for a 5-pack [P]. J4 needs 0.5 N·m against about 0.98 N·m rated [U], so 2×.
- J1 yaw: STS3250, $43 [P], which needs a new base. Or reuse the printed module later (+about $98).

## 5. Cost vs $500
| Item | USD |
|---|---|
| 2 × (Tarot 4008 45.99 + ESC1 39.26 + encoder ~5 [U] + bearings ~8 [U]) | 196.50 |
| STS3250 (J1) | 43.00 |
| STS3215 ×5 | 74.95 |
| CAN board | 4.69 |
| Rest (PCB electronics, screws, filament), from the $557 plan | ~117 [U] |
| **Total** | **≈ $436** (≈ $395 with $25 AliExpress motors) |

## 6. Risks
- Printed cycloid backlash is unmeasured. 0.5° = 3.3 mm at the tip.
- Wear and creep: use PETG/PA-CF, steel pins, grease.
- Firmware bring-up on ESC1: CAN protocol and calibration are new code.
- Homing is needed.
- The ESC may not fit inside Ø57.
- The 4 mm shaft has no hollow bore, so wires route in the link channel.

## 7. Recommendation
Base the gearbox on the **Dongil Choi 40:1 cycloid (Tarot 4008, OD 60)** concept and re-model it to **Ø56–57**. Use reBot's interface (6×M3 PCD50 / PCD27), the same module at J2 and J3, a 5 A / 3 A current limit, and a 6808 output bearing.

Prototype one module first and measure torque and backlash.

Fallback if it's weak: a 50:1 cycloid (same size, +25 % torque, −20 % speed). After that, buy a GIM4310-36 GDK34 for J2 only ($146.10 [P]).
