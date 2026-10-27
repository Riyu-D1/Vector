# SOMA arm rebuild: a printable, fully working arm around the chosen servos

You (Devin) are bad at inventing 3D models from scratch, so do NOT invent the arm. Start from a proven open-source arm, adapt it to SOMA's parts, and prove the result with automated checks. The previous model in `cad/` was a hand-made parametric sketch that was never fit-checked: its servo hole pattern was wrong, links did not touch the joints, and the gripper did not match the wrist. Leave `cad/` untouched. Build the new arm in `cad/arm/`.

Rules for this session:
- Use `/usr/bin/git` only. Homebrew git is broken. Install nothing with brew.
- Work on a branch called `arm-rebuild`. Push there often. Never merge to main or push to main. The user decides on merging.
- Keep disk use small: no big scratch folders, delete temp files, push work to GitHub instead of keeping copies.
- If you get stuck on one thing for more than 20 minutes or 3 attempts, write down what you tried and take the simpler design. Do not run endless experiments.
- Never invent a dimension. If a number is not in a cited source or measured from a STEP file, mark it UNVERIFIED in the docs and make that feature adjustable (slotted holes, a printed adapter plate).

## 1. What the arm must be (the chosen components, do not swap them)

| Joint | Part | Notes |
|---|---|---|
| J1 waist yaw (Z axis) | Feetech STS3215 12 V (45.2 x 24.7 x 35 mm, 55 g, 30 kg-cm, TTL, 25T spline) | Turns the arm on a 6808 bearing (40 x 52 x 7 mm) |
| J2 shoulder pitch | Hiwonder HTD-45H (body 40 x 20.14 x 40 mm, 64 g, 45 kg-cm, TTL, 9 to 12.6 V) | With a gravity-assist spring, about 1.5 N-m at full reach. 51.1 mm is the length along the shaft, not the body width |
| J3 elbow pitch | STS3215 12 V | Rated payload 200 g until bench-tested. Make the mount parametric so an STS3250 (same footprint, but UNVERIFIED) can drop in |
| J4 wrist pitch | STS3215 12 V | |
| J5 wrist roll | STS3215 12 V | |
| Gripper | STS3215 12 V | Two fingers. Use whatever gripper the reference arm has (a direct-drive jaw is fine). The old Dyneema tendon and force sensor are dropped for v1 |

- Reach about 400 mm or more from the J2 axis, all printed in PETG. TPU only for finger pads.
- The arm base sits in the electronics case recess: a drum of diameter 132 mm (recess), centred at case (75, 88), on top of the 4 mm lid. The case is `cad/lib/case.py` and is correct, so keep it and mate to it. The carrier PCB is 135 x 115 mm inside that case. Do not touch `pcb/`.
- Electronics wiring goes through the arm: one 12 V pair plus the TTL data lines for the servo chain. HTD-45H is on its own UART, the STS3215 servos are on the other (see `docs/architecture.md`). Leave cable channels (at least 8 x 6 mm in each link, and a slip path through the J1 bearing centre big enough for a 6-wire harness).

## 2. Verified facts you must use (from the research, with sources)

- STS3215 mounting: the holes are 1.6 mm diameter for M2 self-tapping screws, on a 24.45 x 20.5 mm pattern. Source: Waveshare drawing https://files.waveshare.com/upload/0/08/ST3215-2D.zip (DXF and PDF). The old `cad/params.py` had 2.8 mm holes on 30 x 40, which is wrong. Take the real shape from the STS3215 STEP in the reference repos below, and check it against that drawing.
- The old BOM said C047 is the 12 V part, the research says C018 is. Do not argue it: write a line in `docs/BOM.md` saying "verify the 12 V variant part number on the listing before ordering (research says C018 = 12 V / 30 kg-cm; C001, C044, C046 are the 7.4 V ones)". Do not decide which to buy.
- HTD-45H: body 40 x 20.14 x 40 mm. Source: https://www.hiwonder.com/products/htd-45h (dimension drawing). Its mounting hole pattern and spline are UNVERIFIED, so make an adapter plate with slotted holes and flag it. It turns only 240 degrees.
- Torque (worst case, arm horizontal, 300 g at the tip): J2 about 2.88 N-m (the rated STS3215 is 0.98 N-m, so it needs the HTD-45H plus spring). J3 about 1.20 N-m. Recompute these from your real CAD masses and write them in `docs/arm-verification.md`.
- Printed series-elastic spring cartridges at J2 and J3 (24 N-m/rad) are too soft: the shoulder would wobble at about 2.5 Hz and the tip could move about 48 mm. DROP them for v1. Use direct drive. Keep an optional AS5600 magnet boss on the J2 and J3 output so encoders can be added later.
- The gravity spring must be a zero-length or Anglepoise-style design (extension spring plus a lever/pulley), because a plain extension spring can't cancel the load at every angle. Design anchors for it. Say which spring (wire diameter, free length, rate) and show the torque-vs-angle curve it gives against the arm's gravity torque.

## 3. Reference designs (fork these, don't redraw)

Clone with `/usr/bin/git`. Primary base: **SO-ARM-102** (https://github.com/roboninecom/SO-ARM-102), 12 V STS32xx on one bus, 483 mm reach, 300 g payload. Hardware licence CERN-OHL-P-2.0, so keep the attribution in `cad/arm/NOTICE.md`. Its STL files are git-LFS placeholders in a plain clone (and `/usr/bin/git` has no LFS). Get the real files from `https://media.githubusercontent.com/media/roboninecom/SO-ARM-102/main/<path>`, and check each file is more than a few hundred bytes. Prefer the STEP files for editing.
Fallback and cross-check: **SO-101** (https://github.com/TheRobotStudio/SO-ARM100, Apache-2.0, has STEP, STL, a URDF and MJCF in `Simulation/SO101`). Parts sources only: PingTi-Arm (https://github.com/nomorewzx/PingTi-Arm) and ElRobot (https://github.com/norma-core/norma-core/tree/main/hardware/elrobot).
Known problem: some SO-102 STLs are not watertight (bottom servo holder, upper arm left, wrist holder). Re-export these from the STEP or repair them, and check watertightness for every final STL.

Tooling: build123d is already used in `cad/`. Use it to import STEP, modify and export. If a tool is missing, use pip in a venv inside `cad/arm/` only if really needed. Use trimesh (already present in `~/soma/.venv`) for mesh checks.

## 4. What to build (in `cad/arm/`)

1. `arm_params.py`: one source of truth with the servo specs above, link lengths, joint limits, bearing sizes.
2. Imported reference parts, adapted so that: J2 takes the HTD-45H (with the adapter plate and the spring anchors), the base is a rotating turntable on the 6808 bearing that sits in the 132 mm recess, and every link spans exactly from one joint to the next with no gaps or floating parts.
3. A SOMA base: a fixed housing that bolts to the case lid, the 6808 bearing seat, a rotating turret that carries the J2 bracket, and a J1 servo mount. Work out how J1's spline turns the turret (horn bolted to the turret, servo fixed in the housing) and show it in a section view.
4. Parts exported one-by-one as STEP and STL to `cad/arm/export/`, in print orientation, plus the full assembly STEP and STL.
5. A script `cad/arm/build.py` that regenerates everything, and `cad/arm/checks.py` that runs all checks below and prints PASS or FAIL for each.

## 5. Proof it works (all of this is required; nothing counts as done without the output)

`checks.py` must show real output for:
- Every STL is watertight and has no zero-volume pieces.
- Servo fit: every servo envelope sits inside its pocket with at least 0.3 mm clearance and the mounting hole centres line up with the real hole pattern.
- Assembly interference: pairwise overlap volume of all parts that are not meant to touch (use boolean intersection or trimesh). Fasteners and bearings press-fit tolerances listed separately. Zero unexplained overlaps.
- Range of motion: sweep every joint through its full limits (and the combined extremes of J2, J3, J4) and report any collision with another part, a cable bundle zone, the case, or the table. Show the limit angles that result.
- Reach and workspace: horizontal reach and the maximum height from the J2 axis (target at least 400 mm).
- Mass and torque: real mass of the whole arm from CAD volumes (PETG 1.27 g/cm3 x infill assumption) plus servo masses, then static torque at J2, J3 and J4 at full stretch with 200 g and 300 g, compared to the rated and the stall torque. State plainly whether J3 is OK at 300 g.
- Printability: minimum wall of at least 1.6 mm, no overhangs above 60 degrees unsupported in the chosen orientation (list the ones that need support), every part fits on a 220 x 220 mm bed. List the print orientation and estimated filament per part.
- Fasteners: a table of every screw and insert with count, size, length, and where it goes. Use M3 heat-set inserts. No mystery screws.
- The cable path: show the route for the 12 V and data cable from the case through J1, up each link to the gripper, with the bend radius.

## 6. Reporting

- Write `docs/arm-verification.md` with the check outputs, the UNVERIFIED list (HTD-45H holes and spline, STS3250 holes) and what the user has to measure with calipers when the parts arrive.
- Render images with matplotlib or trimesh to `cad/arm/renders/`: front, side, top, an isometric view in the home pose, one in the reach-out pose, and a section view of the base. Look at them yourself and fix anything floating, intersecting or touching wrongly before saying done. The user's assistant will review the renders independently.
- Update `README.md` and `docs/BOM.md` (the fastener list, the corrected servo note). Commit and push the branch `arm-rebuild` with clear messages, then stop and send a 10-line summary: what you based it on, what changed from the old model, the check results, the open UNVERIFIED items.
