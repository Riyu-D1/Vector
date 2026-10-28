# NOTICE — cad/arm2 (Stage A2a, J1–J3 chain)

This directory contains a modified version of the **reBot-DevArm** hardware design by
**Seeed Technology Co., Ltd.** (https://github.com/Seeed-Projects/reBot-DevArm, commit `13bebbf`),
licensed under the **CERN Open Hardware Licence Version 2 – Weakly Reciprocal (CERN-OHL-W-2.0)**.
The modified files are distributed under the same licence. Source location of the original:
`reBot_B601_DM_v1.1_20260425.step`, `Metal_Parts/02_*`, `Metal_Parts/03_*`, `3D_Printed_Parts/01_*`.

`rebot_src/*.step` are reBot parts re-exported **unchanged** in the position they have in
`reBot_B601_DM_v1.1_20260425.step` (folded rest pose). The 20260625 assembly was not used.

## Changes (2026-10, Riyansh Diwan / SOMA arm)
- Arm scaled in **span only** (joint ends full size): upper arm J2→J3 264 → 126.7 mm, forearm J3→J4 242.6 → 116.4 mm.
- J2/J3: Damiao DM-J4340P replaced by a printed cycloidal actuator (Ø57 × 55, cad/act2). J1: DM-J4340P replaced by a Feetech STS3250 servo.
- `03_Link2` C-channel replaced by two flat 4 mm printed plates (`upper_out`, `upper_back`), R30.5 ends (reBot R28.5 + ring wall), R12 lightening slot; the output-side plate grips the actuator housing in a Ø57.15 ring.
- `03_Link3_L/_R` replaced by flat 4 mm plates (`fore_l`, `fore_r`) cut from the reBot sheets: J3-end piece moved −137.3 mm in X, J4-end piece moved −11.1 mm, joined by a 32 mm band; inner web removed; moved 1.0 mm outboard.
- `02_Motor_Front_Spacer` (J2, J3): all holes plugged, re-drilled to the actuator output (3× Ø3.2 PCD27 at 0/120/240°, 3× Ø4.1 PCD24 at 60/180/300°); J3 spacer thickened 4 → 5 mm.
- `02_Motor_Back_Spacer` replaced by a 4.7 mm spacer with 6× Ø3.4 on PCD50 (actuator back pilots) and the reBot 6803 seat.
- `02_FLANGE` (J2, J3): Ø14 bore plugged and re-drilled Ø8; J3 flange disc thickened 1.0 mm.
- `02_Lower_Upper_Link_L/_R` moved 1.0 / 2.0 mm outboard and 137.3 mm toward J2 (geometry unchanged).
- `01_BASE_Link`: DM4340 pocket cut for the STS3250 body (+0.15/side) and its plug; reBot overlap with `02_Base_Reinforcement_Part` cut away. New printed `j1_cradle` fills the old motor pocket.
- `02_Arm_Yaw_Limit`: Ø14 centre plugged; 4× Ø3.2 on PCD14 (servo horn) with Ø6.2 × 2.0 counterbores and a Ø7 × 2.2 horn-screw recess.
- All metal reBot parts are printed in PETG in this version.
- Not included (A2b): wrist (J4–J6), gripper, covers, handle.
