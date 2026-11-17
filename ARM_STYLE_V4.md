# SOMA ARM v4: INDUSTRIAL DESIGN PASS (one Devin window). Deadline 31 Oct 2026.
Rules: /usr/bin/git only, never merge to main, no big installs, UNVERIFIED for anything unsourced, 20 min / 3 attempts per problem. Work in a new worktree: cd ~/Vector && /usr/bin/git worktree add ~/Vector-wt/style -b arm-style arm-integrated. Push arm-style to origin. Keep hybrid design (3 printed cycloidal actuators 70x85.5 mm + 3 STS3215). Keep every existing check passing (22 CAD checks, interference, ROM sweeps, torque) and update docs/arm-verification.md.

## Problem
Riyansh rejected the current renders: the arm is a set of flat-sided blocks (boxy upper link, forearm, wrist, nose, plain plate turret). He expected a sleek, finished-looking arm like Oleksandr Stepanenko's compact precision arm: round joint housings that read as modules, slim tapered links with smooth fillets, continuous surfaces, hidden fasteners, clean panel lines, and deliberate pockets and covers for components.

## Required design changes
1. Visual language: every joint is a cylindrical module (use the 70 mm actuator as a visible round joint housing with a consistent cap, a thin shadow-gap ring and a flush flange ring). Links connect joints with smooth tapered shells (loft or hull between joint circles), min 3 mm outer fillets everywhere, no sharp box edges, no flat rectangular slabs. One consistent radius family (e.g. 3, 6, 12 mm).
2. Two-tone printed look: parts split so each shell can print in a different colour, with a 0.3 mm to 0.5 mm shadow-line gap between shells.
3. Hide hardware: screws sit in counterbores under snap-in or press-fit caps/covers, or on faces facing the inside; cable runs inside the links through a continuous channel with a clip-on cover along each link (wire-cover panel). No external wires visible.
4. Component spaces (design real pockets, show them in a cutaway render): ESC and AS5600 in each actuator end cap, with an access hatch; CAN transceiver, 120 ohm terminators and wiring junction in a hatch in the upper arm; STS3215 servos fully cradled with horn access; wiring service loop room at each joint; a labelled strain-relief on the base.
5. Wrist and gripper: compact tapered wrist and a proper gripper body with rounded jaws, not a rectangular nose block; keep wrist cluster mass about 220 g or less.
6. Base: low rounded base housing blending to the turret; turntable bearing hidden under a seam ring; case cutouts keep the existing carrier PCB and ports reachable.
7. Keep reach about 348 mm, joint ranges from arm_params, torque margins and the table guard. Do not change the actuator interface.

## Rendering (must do, this is how it is judged)
Render with real shading, not wireframe or flat matplotlib: use Blender (if present) or any available path tracer/rasteriser (e.g. trimesh+pyrender, or three.js headless) to make at least 6 shaded renders: front, side, iso home, iso extended, top, and one exploded or cutaway view showing the component pockets. Put them in cad/arm/renders/style/. Light grey and one accent colour like the reference style. Look at the renders yourself and keep iterating (at least 3 design iterations) until the arm reads as a sleek, production-looking product. Write down in docs/STATUS-style.md what changed after each iteration.

## Deliverables
Updated parametric CAD, STL/STEP exports (print orientation and supports updated, parts still fit a 220 mm bed, all watertight), shaded renders, updated BUILD.md print list and fastener table, docs/arm-verification.md re-run, a short before/after note, and docs/STATUS-style.md. Commit and push often.
