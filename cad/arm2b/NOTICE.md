# NOTICE — cad/arm2b (Stage A2b, wrist J4–J6 + gripper)

This directory contains a modified version of the **reBot-DevArm** hardware design by
**Seeed Technology Co., Ltd.** (https://github.com/Seeed-Projects/reBot-DevArm, commit `13bebbf`),
licensed under the **CERN Open Hardware Licence Version 2 – Weakly Reciprocal (CERN-OHL-W-2.0)**.
The modified files are distributed under the same licence. It builds on cad/arm2 (A2a), whose NOTICE.md also applies.
Source of the original: `reBot_B601_DM_v1.1_20260425.step` (wrist, gripper and `02_Rack` bodies).

`rebot_src/02_Rack_U.step`, `rebot_src/02_Rack_D.step` are the two reBot gripper racks re-exported **unchanged**
in the position they have in `reBot_B601_DM_v1.1_20260425.step` (folded rest pose).

## Changes (2026-10, Riyansh Diwan / SOMA arm)
- Wrist re-made for three **Feetech STS3215** servos instead of 3× Damiao DM4310, keeping the reBot wrist layout
  (J4 pitch on the forearm, J5 yaw on top, J6 roll on the tool axis) and its exposed, minimal links.
  Spans scaled 0.48: J4→J5 78.3 → 37.6 mm, J5→J6 40 → 19.2 mm, J6→TCP 75.0 mm.
- `03_Link3_L/_R` J4 ends (A2a `fore_l`/`fore_r`): Ø38 DM4310 pilot plugged; `fore_r2` gets 4× Ø3.4 for a new printed J4 servo cradle.
- `02_Wrist_Bracket` + `02_Lower_Wrist_Link_L/_R` replaced by one printed `link4` (J4 horn plate + J5 servo pocket).
- `03_Link5` replaced by a printed `link5` (J5 horn plate + J6 servo pocket).
- `02_Gripper_Connector` + `01_Rail_Bracket` + gripper motor mount replaced by one printed `grip_frame`
  (J6 horn plate, gripper STS3215 pocket, rack channels). The MGN9 rail is replaced by printed channels.
- Gripper keeps the reBot rack-and-pinion concept: the reBot `02_Rack` bodies cut to 36 mm, m1 16T gear on the
  gripper servo horn; reBot `01_Finger` replaced by flat 4 mm printed fingers (`finger_u`, `finger_d`), stroke 25 mm.
- Not included: covers, handle, camera mount, cable guides.
