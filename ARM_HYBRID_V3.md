# SOMA ARM v3: HYBRID PRINTED-ACTUATOR ARM (supersedes ARM_ACTUATOR_UPDATE.md v2)

DEADLINE: ALL DESIGN, CAD, FIRMWARE AND SOFTWARE MUST BE COMMITTED AND PUSHED BY 31 OCT 2026. Riyansh prints and assembles himself. Prioritise a complete, buildable, documented result over polish. Three Devin windows work in parallel, each on its own branch and git worktree (see STREAMS). Never merge to main. Use /usr/bin/git only. Do not install large packages (disk is tight). Mark any dimension or spec you could not source as UNVERIFIED. 20 minutes or 3 attempts per problem, then pick the simplest fallback and note it.

## Design
- 6-DOF desk arm, about 260 mm reach, styled like Oleksandr Stepanenko's compact precision arm: chunky cylindrical modular joints, clean 3D-printed shells. Fully 3D printed (PLA/PETG, FDM) apart from standard parts.
- NO springs, belts or pulleys. Direct drive everywhere (the gearbox is the printed cycloidal reducer).
- J1 base yaw, J2 shoulder, J3 elbow: identical printed cycloidal actuators, based on the Berkeley Humanoid Lite 5010 actuator (docs https://berkeley-humanoid-lite.gitbook.io/docs , paper https://arxiv.org/html/2504.17249v1). 5010 motor, 15:1 cycloidal, AS5600 encoder, ST B-G431B-ESC1 driver, CAN 2.0 at 1 Mbps. Reimplement the actuator as parametric build123d code in this repo if the original STL/STEP can't be downloaded; check licence and credit it in the README.
- J4 wrist pitch, J5 wrist roll, J6 gripper: Feetech STS3215 12 V (45.2x24.7x35 mm, 25T spline, M2 holes on 24.45x20.5 mm pattern). Wrist cluster mass 180 g or less (keep weight off the end).
- Link lengths: shoulder to elbow 120 mm, elbow to wrist 100 mm, wrist to tool point 40 mm. Payload target 250 g at full stretch. Static model target: shoulder about 1.7 N.m needed vs about 7.9 N.m available.
- Power: 12 V / 8 A supply, 6 A fuse on the carrier. Set driver phase-current limits low (about 5 A phase max, lower for J1) so sudden moves do not blow the fuse.
- Bus plan: CAN for J1-J3 via an SN65HVD230 transceiver module wired to the SPARE header J15 (pin 3 = SP1 = ESP32-S3 GPIO connected to U1A pad 18, pin 4 = SP2 = pad 19; 5 V, GND and 3V3 also on J15). NO PCB change. Confirm the real GPIO numbers from pcb/gen_pcb.py and docs/architecture.md and state them. Feetech servos stay on the existing UART bus (BUS_A / BUS_B, check baud, 1 Mbps is UNVERIFIED there).
- Carrier PCB (pcb/) is final: do not modify it. The case recess is 132 mm; the base must fit the existing case/turntable design from ARM_REBUILD_GUIDE.md.

## STREAMS (each in its own window, branch and worktree)
Create worktrees with: cd ~/Vector && /usr/bin/git worktree add ~/Vector-wt/NAME -b BRANCH arm-rebuild  (the existing arm-rebuild window keeps ~/Vector).

### Stream A: actuator CAD (worktree ~/Vector-wt/actuator, branch arm-actuator)
Parametric build123d module cad/actuator/: housing, cycloidal disc(s) with proper eccentricity and pin/roller geometry (lobe count N = 15+1 for 15:1, tolerances for FDM, e.g. 0.2 mm clearances parameterised), eccentric input shaft on the 5010 motor, output flange, bearing seats (list the exact standard bearings, with sizes), AS5600 magnet and PCB mount, ESC mount, M3 fastener table, connector/cable exit. Export STL for every part to cad/actuator/export/ and a STEP assembly. CHECKS (real output in docs/actuator-verification.md): watertight STLs, interference check of the assembled gearbox through a full rotation, disc geometry check (no undercut, pin contact), mass estimate, print orientation and support notes, 5010 motor dimensions and mounting pattern from a sourced datasheet (else UNVERIFIED). Publish the mounting interface early (first 2-3 hours): put cad/actuator/INTERFACE.md on the branch with the outer diameter, length, mounting bolt pattern on both faces, cable exit, and push it so Stream B can use it.

### Stream B: arm structure (existing window, ~/Vector, branch arm-rebuild)
Continue the arm structure: base on the 6808 bearing turntable with J1 actuator, shoulder, upper link, elbow, forearm, STS3215 wrist pitch/roll, gripper, cable routing. Use Stream A's INTERFACE.md (git fetch from the other worktree branch arm-actuator; until it exists, use a placeholder cylinder of 60 mm OD x 70 mm with a clearly marked interface). Replace the STS3250 shoulder/elbow plan with the actuators. Keep what you already built for the wrist and gripper. CHECKS as in ARM_REBUILD_GUIDE.md: watertight STLs, servo fit, pairwise interference, range-of-motion sweeps, reach, mass and torque, printability, fastener table, cable path. Report in docs/arm-verification.md and renders in cad/arm/renders/.

### Stream C: firmware and software (worktree ~/Vector-wt/firmware, branch arm-firmware)
1. ESP32-S3 firmware (PlatformIO or ESP-IDF; do not install heavy toolchains unless already present; if the toolchain is missing, write the code and a build README anyway and mark it UNBUILT): TWAI CAN driver at 1 Mbps, CAN protocol for the three brushless joints (position/velocity/torque command, state feedback, current limit, enable, e-stop), Feetech STS servo bus driver for J4-J6, and a serial/USB or UART link to the Orange Pi (simple framed protocol). Use the real pin map from the PCB (pcb/gen_pcb.py). Honour the ESTOP input.
2. Driver firmware for the ST B-G431B-ESC1 (STM32G431): base it on the Berkeley Humanoid Lite open firmware (check licence) or SimpleFOC with CAN; include calibration (encoder offset, pole pairs for the 5010), current limit config for 12 V and a 5 A phase cap, and a flashing README.
3. Orange Pi side (Python): kinematics (forward and inverse for the 6-DOF geometry above), trajectory planner with joint limits and a speed limit, a CLI, and a simple simulator or dry-run mode so it can be tested without hardware.
4. Tests: pytest for kinematics (round trip FK/IK on many random poses), the CAN frame encoders/decoders (loopback test), and the Feetech packet checksums. Run them and put the real output in docs/firmware-verification.md.
5. Write docs/bringup.md: step-by-step first power-up checklist (no motors attached, then one joint, then all), with safety notes (12 V 8 A, fuse, e-stop, LiPo/battery warnings if any).

## Always
- Commit often with small commits and push your branch to origin (github.com/Riyu-D1/Vector) at least every hour. Report status in a file docs/STATUS-<stream>.md (done / in progress / blocked) updated every push so Riyansh and Grok Bot can read it without disturbing you.
- Final deliverables per stream: code, STL/STEP or firmware, tests with real output, a README with a bill of any extra parts, and a list of UNVERIFIED items.
- Be honest: if something does not work or was not tested, say so in the status file.
