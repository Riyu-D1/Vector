# SOMA ← reBot-DevArm B601-DM: risks + STEP adaptation plan (2026-10-28)
Scripts: `/workspace/soma/rebot_stiff.py` (deflection), `/workspace/soma/rebot_torque.py` (torque). Measurements: build123d 0.13 on the box, part STEPs in `/workspace/rebot/hardware/reBot_B601_DM/`.
Prices: steadywin-motor.com products.json, read 2026-10-28 (USD, no shipping). [U] = unverified.

## 1. Risks

### (a) GIM4310 driver variants (SteadyWin pages: steadywin.cn h-pd-10 / h-pd-11, steadywin-motor.com product pages)
| Driver | Voltage | Protocol | 4310-36 price | 4310-10 price | 4310-36 rated/stall | 4310-10 rated/stall |
|---|---|---|---|---|---|---|
| GDS34 | 12–48 V (24 nom.) | CAN, SteadyWin "GIM Motor Driver Protocol Spec" | $169.80 | $151.80 | 7.38 / 20.16 N·m | 2.05 / 5.6 N·m |
| GDZ34 | 12–40 V | CAN + RS485 + Modbus (own protocol) | $169.80 | $146.80 | 6.24 / 25.43 | 1.63 / 7.98 |
| GDK34 | 12–60 V, 20 A max | **MIT protocol**, 16-bit encoder, **pre-order, ~15-day lead** | $146.10 | $126.90 | not published on page [U] | [U] |
- All three accept 12 V. That is the floor, so speed is about half at 12 V: 4310-36 about 2.63 rpm/V × 12 ≈ 32 rpm; 4310-10 about 9.5 × 12 ≈ 114 rpm.
- Our firmware (`kn/fw/gim_proto.*`, cmds 0x91–0x97, 0x83, 0xB3) and the vendor STEP on the Mac (`GIM4310-10-GDS.stp`) are the **GDS34** family. GDK34 = MIT. It needs a different codec (MIT packed p/v/kp/kd/t frames). reBot's own software already drives MIT-mode Damiao motors, but byte compatibility with SteadyWin MIT is [U]. I could not fetch the GDK doc zip (box download blocked).
- **Buy:** GDS34 on both, if the firmware must work unchanged and ship from stock (+$48.60 over GDK, total ≈ $557). Pick GDK34 to stay near $508, accepting a 15-day lead, a codec rewrite, and unknown GDK board thickness (keep the 8 mm plug keep-out). My recommendation is **GDS34**, because it is the lower-risk option for a weak Devin model and needs no new protocol.

### (b) STS3250 (Feetech datasheet ST-3250-C001 2024-01-16, Robonine test)
- 12 V (6–12 V; over-voltage trip >14 V). Rated 16 kg·cm = **1.57 N·m**, stall 50 kg·cm = **4.9 N·m** (measured: 48 peak, **25 kg·cm = 2.45 N·m sustained** before protection). 75 rpm, 4.2 A stall, 1.4 A rated, 74.5 g, 45.2×24.7×35 mm, 12-bit encoder, 25T spline.
- Backlash ≤0.5° (measured 0.43°), which is **≈2.8 mm tip play at 375 mm** on yaw.
- As base yaw: OK for torque, because yaw on a thrust bearing has no gravity load, only inertia. Weak for precision. $43 (C002 12 V, earlier live read).
- reBot's base (01_BASE_Link + 02_Base_Reinforcement_Part) is built around a Ø57 DM motor. **GIM4305-10 (Ø53) drops in with a re-drill; STS3250 needs a new base.** For Devin, GIM4305-10 GDK $105.10 / GDS $127.80 is the easier route (+$62–85).

### (c) Stiffness (`rebot_stiff.py`). Arm horizontal, 0.25 kg at the TCP, link + actuator masses included, joints rigid, E PETG 1.8 GPa / ABS-CF 4.0 GPa [U typical printed]
Measured reBot plates: 03_Link2 (upper, qty 2) is a 3.0 mm C-channel, 57 high × 23 deep × 321 long. 03_Link3_L/R (forearm) is 3.0 mm, 57 × 28.6 × 297.8.
| Plate pair (upper + forearm) | PETG tip | ABS-CF tip | mass |
|---|---|---|---|
| uniform 0.48 (h27.4, t1.44, flange 11) | 3.3 mm | 1.5 mm | 41 g (t below the 1.6 min, FAIL) |
| h27.4 t3 | 1.9 | 0.87 | 80 g |
| **true-size section h57, t4, flat plates** | **0.40** | **0.18** | 141 g |
| h57 t3 with 23 mm flange (reBot shape) | 0.18 | 0.08 | 180 g |
- **Plate thickness: 4 mm, height 57 mm (keep reBot's section), PETG is fine; ABS-CF is better for creep.** Bending is not the problem. The real tip error is joint play: GIM 15 arcmin ×2 ≈ 1.6 + 1.1 mm, STS wrist ≈ 1 mm [U], STS3250 yaw 2.8 mm. Torsion, lateral bending and screw-boss creep are not checked [U]. Use heat-set inserts and ≥6 walls.
- Torque with these plates: J2 2.28–2.39 N·m (margin 2.6× on 6.24, 3.1× on 7.38), J3 1.16–1.19 (1.4× on GDZ 1.63, 1.7× on GDS 2.05), J4 0.48 (2× on STS3215 ≈0.98 [U]). Static only.

### (d) Power
- Worst rated draw: 2 × GIM 2.3 A + STS3250 1.4 A + 4 × STS3215 ≈ 0.9 A [U] ≈ 9.6 A phase/rated. Bus current is lower at holding (J2 ≈ 0.7 A). Stalls: GIM 6.8 A each, STS3250 4.2 A, STS3215 ≈ 2.7 A [U].
- **Recommended:** 12 V ≥ 10 A (120–150 W, e.g. Mean Well LRS-150-12, 12.5 A, [U] price), 8 A slow-blow main fuse, 5 A branch per GIM.
- On the current PCB (8 A supply, 6 A fuse), first motion is OK only with GIM current limits ≤2.5 A each and servo torque limits set (servo bus ≤3 A). Whether the PCB trace/fuse holder takes 8 A is [U].

## 2. STEP adaptation feasibility

### Files to start from (DM version only)
- Assembly reference: `hardware/reBot_B601_DM/reBot_B601_DM_v1.1_20260425.step` (97 products, 358 instances incl. screws). **Do not use `..._20260625.step` in the DM folder.** Its product tree contains RS-version names (2-RSM*, RS06/RS00), so it looks mislabelled.
- Parts: use the `Metal_Parts/0[23]_*.step` (underscore) files. The `03-*` hyphen files are near-duplicates (03-Link1 is 78 vs 84 mm tall); use the underscore set, which the readme references. There are 22 unique metal parts and 19 unique printed parts (`3D_Printed_Parts/01_*`), plus 3 power-box covers.

### Motor interfaces (measured: cylinder faces + hole PCDs)
| Part | Holds | Interface (full size) |
|---|---|---|
| 01_BASE_Link (92×92×63.7, printed) + 02_Base_Reinforcement_Part + 02_Base_Motor_Shim + 02_Arm_Yaw_Limit | J1 DM4340P | pocket Ø54.6–57.8; 5×M3/M4 PCD50; 3×M3 PCD85; thrust brg AXK5578 (Ø78/55); 6707 brg (44/35); rotor 6×M3 PCD27 + 3×Ø4 pins PCD24 |
| 03_Link1 (77×84×84 sheet yoke) | J1 → J2 | 2 × (Ø57 end, Ø14 centre, 12×M3 PCD27) |
| 03_Link2 ×2 (upper-arm plates) | J2 + J3 stators | each end: R28.5 (Ø57) round end, Ø38 pilot, 6×M3 PCD50 |
| 02_Motor_Front_Spacer ×4 | J2–J5 output | Ø34.8 × 4, Ø14 bore, 6×M3 PCD27 + 3×Ø4 PCD24 |
| 02_Motor_Back_Spacer ×3, 02_FLANGE ×3 | J2–J4 back side, 6803 brg | spacer Ø57×5: 5×M3 PCD50 + 4×M3 PCD38; flange Ø34.8: 6×M2.5 (Ø2.7) PCD27, Ø17/19 brg seat |
| 02_Lower_Upper_Link_L/R (5 mm), 03_Link3_L/R (forearm) | J3 output → J4 | Ø45/14: 6×M3 PCD27 + 4×M3 PCD28; J3 end Ø57/38 6×M3 PCD50; J4 end Ø39/14 4×M3 PCD28 |
| 02_Wrist_Bracket, 02_Lower_Wrist_Link_L/R, 01_Motor_Cover | J5 DM4310 | Ø57.2/38, 6×M3 PCD50; 6×M3 PCD27 |
| 03_Link5 | J6 DM4310 | Ø50, 4×M3 PCD72.2 |
| 02_Gripper_Connector_A/B, 02_Gear_Connector, 02_Rack ×2, 02_Slider_*, 01_Rail_Bracket, 01_Finger | J7 gripper DM4310, MGN9-170 rail, m1 16T gear | 4×M3 PCD38 + 3×M3.5 PCD51.8 |
**Key finding:** the DM43 output pattern (M3 on PCD27 + Ø4 pins on PCD24) **matches our GIM4310-36 output** (`kp.py`: 3×M3 PCD27 + 3×Ø4 pins PCD24) and the GIM4310-10 (3×M3 PCD27). Only hole count and angles differ. The back pattern differs: DM 6×M3 PCD50 / pilot 38, while GIM-36 is 6×M3 PCD48 with a Ø40 cap and GIM-10 is 6×M2.5 PCD47.5 with a Ø40 cap. Bodies are Ø55 / Ø53 against the Ø57 envelope, so **J1–J3 joint ends can stay at true size and be re-drilled**.

### Uniform 0.48 scaling: what breaks (essentially everything functional)
- All 3 mm sheet goes to 1.44 mm and 2 mm features to 0.96 mm (<1.6).
- M3 clearance 3.2 goes to 1.54 and taps 2.7 to 1.3.
- Motor envelopes Ø57 go to Ø27 (the GIM won't fit).
- Bearings: 6803 (17/26) goes to 8.2/12.5, 6707 to 16.8/21.1 and AXK5578 to 26.4/37.4, none of them standard.
- The MGN9 rail goes to 4.3, the m1 gear to m0.48, and the 5 mm links to 2.4.
- Only the cosmetic fillers and covers survive, and SOMA drops those.
→ **Uniform scaling is not viable. Use non-uniform scaling: true-size joint modules, shortened link spans.**

### Plan for Devin (build123d, one part per step, gate after each)
1. **Keep unscaled, re-drill only:** 01_BASE_Link, 02_Base_Reinforcement_Part, 02_Base_Motor_Shim, 02_Arm_Yaw_Limit (if J1 = GIM4305-10); 03_Link1; 02_Motor_Front_Spacer; 02_Motor_Back_Spacer; 02_FLANGE (J2/J3 only); 02_Lower_Upper_Link_L/R. Recipe:
   - `import_step`
   - fuse Ø(hole+0.2) plug cylinders into the old holes
   - cut the new GIM holes from `kp.py` numbers (M3_CLEAR 3.4, inserts Ø4.6)
   - change the pilot to Ø40.3 (cap) / Ø37.3 (output)
   - make the body pocket Ø55.3 (-36) or Ø53.3 (-10).
   Thicken any 2–3 mm metal web to ≥4 mm (extrude the largest planar face to 4 mm and re-cut the holes).
2. **Shorten (cut-and-shift) the plates:**
   - 03_Link2 ×2: J2–J3 264 → **126.7 mm**, part length 321 → 183.7.
   - 03_Link3_L/R: J3–J4 242.6 → **116.4 mm**, part length 297.8 → 171.6.
   Method:
   - Cut a slab of width ΔL (137.3 / 126.2 mm) centred mid-span. Keep `plate & Box(left)` and `(plate & Box(right)).moved(Location((-ΔL,0,0)))`, then fuse.
   - First assert that the removed slab contains only straight section; list the holes inside it, which are cover screws and get dropped.
   - Then flatten to a 4 mm flat plate, height 57. All fit the 256 mm bed.
3. **Re-make for STS3215** (no DM4310 equivalent): 02_Wrist_Bracket, 02_Lower_Wrist_Link_L/R, 03_Link5, 02_Gripper_Connector_A/B, 01_Motor_Cover. Use the servo pocket 45.2×24.7×35 + 0.15 slip and the horn 4×M3 PCD14 (`kp.py SV_*`). Keep the J4–J5 offset ≥50 mm (servo length), J5–J6 ≈30 mm.
4. **Gripper:** keep reBot's rack-and-pinion concept, driven by an STS3215. Cut the MGN9 rail to 100 mm and scale finger stroke to about 25 mm. Re-make 02_Gear_Connector for the 25T horn; keep 02_Rack/m1 gear at true size. Print 01_Finger at 0.6 scale (walls stay ≥1.6) [U fit].
5. **Drop:** all fillers and covers (01_*_Fuller/Filler/Cover), cable restraints, 01_Arm_Handle, and the 20260625 file.
6. **Base:** 01_BASE_Plate 200×140 stays as is (fits the bed). Re-make it only if J1 = STS3250.
Expected count: ~10 parts re-drilled, 4 shortened, ~8 re-made, ~15 dropped.
Licence: CERN-OHL-W-2.0. Keep the Seeed credit + a NOTICE listing the changes in the repo.
