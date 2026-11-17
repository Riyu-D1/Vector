# Stage P4 — Audit the SOMA carrier PCB v1.3 and re-route it so it looks hand-routed (fewer vias, go-arounds, not autorouted)
> Rules 0.1-0.10 of `~/Vector/ARM_KNUCKLE_V5.md` and `~/Vector/ROUTING_GUIDE.md` apply. Never edit existing files/branches. Step 0: `cd ~/Vector && /usr/bin/git fetch origin`, create worktree `~/Vector-wt/pcb14` on new branch `pcb-v14` from `origin/pcb-v13`. Copy `pcb13/` to `pcb14/` (rename files `soma-carrier-v14*`), work only in `pcb14/`. Leave `pcb13/` untouched. Tag `pcb14-done`, push branch+tags, STOP. Do not merge to main.

## Part A — Audit the existing v1.3 board (report before changing anything, real output)
1. `kicad-cli pcb drc --format json` on the v1.3 file: counts per type (shorting, clearance, hole_clearance, unconnected, courtyard, mask bridge). GND "unconnected" is expected until zones are filled (user presses B in KiCad); filter it and say so.
2. `verify_nets.py`, `audit_pins.py`, `check_pads.py`: run, show output.
3. Net-by-net routing review: list every net with track length, number of vias, layers used, min width. Flag: any power net (+12V_IN, +12V_RP, +12V_SW, +12V_MOT, +12V fuse 6 A path) below 1.5 mm; +5V below 0.6; +3V3 below 0.4; signal below 0.25; vias closer than 1.0 mm to a pad centre; acute angles (<90 deg) and stubs/dead-ends; tracks within 0.3 mm of board edge or mounting holes; routes with large detours vs straight-line length (ratio > 2.5); vias that exist only to hop a single obstacle.
4. Electrical sanity vs the schematic intent in `STATUS-pcb13.md`: reverse-polarity FET Q2 orientation, relay K1/D5 flyback polarity, Q3 pinout, MOTOR_EN path, ESP32 strapping pins not misused, VSNS on ADC1. Report real findings only; fix real bugs in v1.4 and list them.
Also count vias total and report it as the BEFORE number.

## Part B — Re-route for a hand-routed look (placement stays; at most 1-2 mm nudges to open a channel, each logged)
Build on the existing generator (`gen_pcb.py` supports waypoint `ROUTES`) or rewrite tracks directly in pcbnew Python; write waypoint lists by hand from `board_view.py` free-cell maps. Do NOT use a grid autorouter or Freerouting (they get stuck in loops, per earlier runs). Look-and-feel rules:
- Few vias: target at least 50 % fewer vias than BEFORE. Prefer routing AROUND a part or around the end of a header row on the same layer over hopping layers. Use a via only when a net truly must cross another net's copper. No via for a net that can go around.
- Only 0 deg and 45 deg segments; every corner is two 45 deg bends (chamfered), never a single 90 deg and never zigzag/staircase. Long straight runs between bends; no tiny jogs under 2 mm.
- Group related nets as tidy parallel bundles (same pitch, e.g. 0.5 mm gap) that turn together around corners with concentric offsets (SDA1/SCL1, ENC_A/ENC_B/ENC_SW, bus lines, CAN H/L as a tight pair). Bundles enter and leave pads in the same order.
- Layer discipline: F.Cu mostly horizontal, B.Cu mostly vertical; GND remains a pour (keep/restore zones on both layers with stitching vias on a regular grid, user presses B in KiCad).
- Power: wide, short, straight (+12V trunk >= 1.5 mm, F.Cu, no vias if possible; +5V 0.6; +3V3 0.4; signals 0.25, 0.2 clearance). Use teardrops or smooth width transitions where track meets a pad only if KiCad supports it headless; otherwise skip.
- Tracks leave THT pads straight out of the pad, never at a shallow angle; only ONE track between two neighbouring header pins.
- Keep consistent clearance to board edge (>= 1 mm) and symmetrical-looking spacing around parts; avoid long parallel runs of unrelated nets closer than 0.5 mm (crosstalk look).
- No stubs, no dead-end copper, no duplicate overlapping segments (merge collinear segments).

## Part C — Prove it
- DRC after: 0 shorting, 0 clearance, 0 hole_clearance, 0 solder_mask_bridge, 0 unconnected for every net except GND (until zones filled); courtyard items zero or listed as nest-by-design. Show before/after table incl. via count and total track length.
- `verify_nets.py` passes (every net connects exactly the same pads as v1.3: netlist equivalence check, show it).
- Render top and bottom (`kicad-cli pcb render` or board_view PNGs) into `pcb14/`; look at them yourself and fix anything that still looks staircase/autorouted. Re-export Gerbers + drill + bom.csv to `pcb14/gerbers/` (JLCPCB-ready zip if the existing fab.sh does it).
- `pcb14/STATUS-pcb14.md`: audit findings (honest, with real numbers), what changed, via/length before-after, nudges with coordinates, anything not done, [U] list. Commit, tag `pcb14-done`, push. STOP.
Safety note for the README: the board carries a 12 V rail with a 6 A fuse and a relay switching motor power; LiPo/battery wiring and the e-stop loop are the user's responsibility to check before powering. No mains on this board.
