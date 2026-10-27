# SOMA arm: ACTUATOR UPDATE v2 (supersedes ARM_REBUILD_GUIDE.md sections 1 and 2, and any earlier ARM_ACTUATOR_UPDATE)

The user does NOT want springs, belts or pulleys. All joints are DIRECT DRIVE on the servo output. The arm is made SMALLER so that standard Feetech servos have enough rated torque with no gravity spring, no belt reduction and no printed SEA cartridges. The HTD-45H is dropped. Every servo is a Feetech STS on the same protocol. Target: all standard AliExpress parts, about $500.

| Joint | Servo | Notes |
|---|---|---|
| J1 waist yaw | STS3215 12 V | direct, on the 6808 bearing turntable |
| J2 shoulder | TWO Feetech STS3250 (12 V, rated about 1.57 N-m each) on ONE shoulder axis | One servo each side of the upper-arm fork, both horns bolted to the same shaft or to the arm's two cheeks, wired as two bus IDs and commanded together (mirrored direction). This is the same approach as the PingTi-Arm shoulder (https://github.com/nomorewzx/PingTi-Arm), so reuse its idea. STS3250 holes UNVERIFIED, so use slotted holes or an adapter plate |
| J3 elbow | ONE STS3250 | direct |
| J4 wrist pitch | STS3215 12 V | direct |
| J5 wrist roll | STS3215 12 V | direct |
| Gripper | STS3215 12 V | direct |

Size and loads (my numbers; you must recompute from the real CAD masses):
- Reach about 260 mm from the J2 axis horizontally to the gripper tip (upper arm about 120 mm, forearm about 110 mm, wrist and gripper about 70 mm from the elbow-side stage; refine to match the SO-ARM-102 parts). Do NOT make it longer than 280 mm.
- Wrist, camera and gripper cluster at most 180 g. Use the lightest gripper from the reference design. Drop the second eye display, and keep the camera only if the weight budget allows it.
- Design payload 500 g at full stretch, 300 g rated minimum.
- Expected loads at 260 mm, no spring, wrist 180 g: J2 about 2.06 N-m at 500 g (pair of STS3250 rated 3.14 N-m, margin about 1.5x) and J3 about 0.93 N-m (one STS3250, margin about 1.7x). Margins are on RATED torque, not stall. Report what your real CAD masses give, and say plainly if any margin is under 1.5x at 500 g.
- No springs. Remove every spring anchor, the SEA spring discs and the belt/pulley hardware from earlier guidance. Optional: leave a small AS5600 magnet boss on the J2 and J3 output so an encoder can be added later, but do not design around it.

Other requirements still apply from ARM_REBUILD_GUIDE.md: every check in section 5, cable channels, the 132 mm base recess on the case, the 6808 bearing turntable, branch arm-rebuild only, /usr/bin/git, no inventing dimensions.
BOM: update docs/BOM.md actuation lines: 3x STS3250 (about $43 each, WowRobo, checked 2026-10-27), 3x STS3215 (J1, J4/J5... recount: J1, J4, J5, gripper = 4x STS3215 at about $16 to $22), remove the HTD-45H and the extension spring lines. Note the second UART was built for 115200 baud, and 1 Mbps there is UNVERIFIED, so servo baud may need lowering.
