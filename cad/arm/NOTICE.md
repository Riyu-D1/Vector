# Notices — cad/arm

This arm structure adapts geometry and interface dimensions from the
following open hardware projects:

- **SO-ARM-102** — https://github.com/roboninecom/SO-ARM-102
  Hardware licence: CERN-OHL-P-2.0 (see LICENSES/ upstream).
  Used for: STS3215 servo body model (extracted from the follower
  assembly STEP), servo mounting hole grids (24.45x20.5 / 20.7x20.5, M2),
  horn/idler boss dimensions, joint range-of-motion limits, and the
  rack-and-pinion gripper concept.
- **SO-ARM100 / SO-101** — https://github.com/TheRobotStudio/SO-ARM100
  Apache-2.0. Servo-joint architecture reference.
- **PingTi-Arm** — https://github.com/nomorewzx/PingTi-Arm
  Dual-servo-on-one-axis shoulder concept reference.
- **Berkeley Humanoid Lite 5010 cycloidal actuator** —
  https://berkeley-humanoid-lite.gitbook.io/docs
  The J1-J3 joint actuators are Stream A's reimplementation; see
  cad/actuator/ (branch arm-actuator) for its licence and credits.

All original work in this directory is licensed CERN-OHL-P-2.0, matching
the primary base.
