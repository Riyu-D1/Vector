# wrist/RESEARCH.md — D5: how small desk arms build the wrist around the gripper

Brief survey of comparable 3D-printed / kit arms (checked 3 Nov 2026). The
question answered: *what structural language makes a servo-chain wrist look
slim and intentional instead of a stack of boxes?*

## 1. TheRobotStudio SO-100 / SO-101 — gripper-led single shell

- The wrist is literally **built around the gripper**: the part called
  `Wrist_Roll_Follower_SO101` *is* the gripper body — one printed piece that
  encloses 100% of the gripper STS3215, carries the horn recess (stepped
  r10/r12/r13.24 pocket), the jaw attachment and the wrist-roll mounting
  face, all in one. There is no separate "wrist link" + "gripper frame".
- Servo retention is by small self-tapping M2 screws through the servo case
  tabs into thin printed walls — the case itself is the visual mass; the
  printed part is a 2–3 mm clamshell hugging it.
- Moving jaw is a single slim lever driven straight off the horn — the
  envelope starts at the jaws and everything else tucks behind.
- Sources: github.com/TheRobotStudio/SO-ARM100 (STL/SO101 + assembly STEP);
  deepwiki.com/TheRobotStudio/SO-ARM100 "Grippers and End Effectors";
  kitsmith.dev SO-101 assembly guide ("gripper body encloses servo 6").

## 2. reBot-DevArm (Seeed, our base CAD) — thin brackets + dedicated cable clips

- The production B601 wrist uses thin formed brackets (`02_Wrist_Bracket`,
  `03_Link5`, `02_Gripper_Connector`) plus a compact rail block
  (`01_Rail_Bracket`) hugging an MGN9 rail and the rack/pinion — the gripper
  mechanism sets the envelope, brackets only touch it where needed.
- Cable management is designed, not improvised: dedicated printed restraint
  parts (`01_Joint5_Cable_Restraint`, `01_Joint6_7_Cable_Restraint_A/_B`)
  clip the motor harnesses to the link surfaces.
- Source: github.com/Seeed-Projects/reBot-DevArm (hardware/reBot_B601_DM,
  commit 13bebbf; parts list in readme_zh.md).

## 3. Koch v1.1 / low_cost_robot — servo-as-structure

- Minimal connector plates bolt straight into the servo case tabs; each
  joint reads as *a servo with two slim cheeks*, nothing more. No part is
  bigger than the servo it holds.
- Trade-off we keep: our pockets wrap the case for hidden screws (the V5
  "nothing visible" rule); the takeaway is proportion — wall thickness and
  outline should follow the servo silhouette, not a bounding box.
- Sources: github.com/jess-moss/koch-v1-1; github.com/AlexanderKoch-Koch/
  low_cost_robot.

## 4. Gripper mechanism precedent — pinion + dual racks

- Our rack-and-pinion parallel jaw (reBot `02_Rack` pair, m1 16T pinion on
  the servo horn) is the same scheme used by SO-101-class gripper tools:
  e.g. a documented SO-101 tool-changer gripper drives "two racks with the
  jaws on them in opposite directions" from one spur pinion. Compact,
  self-guiding, one servo — keep it, slim only its housing.
- Source: chasebonfiglio.com/so101-toolchanger (design notes).

## Approach chosen

**"Servo-shell clamshell" (SO-101 style), translated to our hidden-screw
language.** The gripper (4th STS3215 + gear + racks + fingers) keeps its
exact proven envelope — every functional dimension is unchanged. Each wrist
part is rebuilt as a thin (≈2 mm wall) contoured shell that follows the
servo case profile:

- `w_j4_cradle` — rounded-rect sleeve hugging the J4 servo case (ap2b
  pocket) + bolt plate carried on 4 pillars (was a 28.7 cm³ block).
- `w_link4` — J4 horn plate + a silhouette spine rib + open-mouth J5
  servo ring cage (was a 29.8 cm³ block with lightening window).
- `w_link5` — J5 horn plate + U-channel cage along the J6 case (was a
  solid box 11.2 cm³).
- `w_grip_frame` — J6 horn plate + two contoured cheeks + bottom web around
  the gripper servo; the rack-slot cage keeps its exact section, outer
  corners rounded, lips chamfered for support-free printing (was 20.9 cm³).
- Cable clips/channels are designed features (cleats + grooves on the
  link surfaces), per the reBot restraint-part idea.

All joint axes, horn faces, servo placements, TCP and the rack/gear/finger
solids are identical to A2b — kinematics and `software/robot-os` config are
untouched.
