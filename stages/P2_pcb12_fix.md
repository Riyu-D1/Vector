# Stage P2 — fix 2 broken nets on carrier v1.2. Work ONLY in `~/Vector-wt/pcb12` on branch `pcb-v12` (continue it). Edit only files inside `pcb12/`. Never touch `pcb/` or any file outside `pcb12/`. Rules 0.1–0.10 of `~/Vector/ARM_KNUCKLE_V5.md` apply. Status file: append a section "P2" to `pcb12/STATUS-pcb12.md`.

## Problem (from the last DRC, `pcb12/drc.json`)
Two unconnected items, nothing else must change:
1. `+5V`: PTH pad R3.1 at (54.0, 56.0) is not tied to the main +5V copper (a via at (46.99, 21.08) is on the net).
2. `ESTOP`: the F.Cu track ends at (51.816, 51.435), about 0.9 mm short of pad U1A.13 at (52.62, 51.16); a B.Cu fragment near (27.178, 81.407) is an island; continuity U1A.13 <-> J9.1 (30, 95) is broken. THIS IS A SAFETY NET (emergency stop), it must be fully connected.

## Rules
- Do NOT rerun the whole auto-router and do NOT regenerate the board (it takes 30+ min and moves other copper). Edit the existing `pcb12/soma-carrier-v12.kicad_pcb` directly by adding track segments (and at most 2 vias per net) with a small Python script that appends `(segment ...)` / `(via ...)` text before the final `)`; use the same layer names, net numbers and syntax already in that file. First copy the file to `pcb12/soma-carrier-v12.before-P2.kicad_pcb`.
- Track width: ESTOP 0.25 mm, +5V 0.6 mm. Clearance to other nets ≥ 0.2 mm; vias 0.7 mm pad / 0.3 drill, ≥ 1.0 mm from other pads. 0 or 90 degree segments, at most one 45 degree corner.
- Use `pcb12/board_view.py` and the DRC JSON to find free copper cells; remove nothing except the dangling ESTOP stub if it blocks the new route.
- Also port the same edits into `pcb12/gen_pcb.py` `ROUTES` only if easy; if not, say in the status that the .kicad_pcb is the source of truth.

## Steps
1. `cd ~/Vector-wt/pcb12` and `git status --short` (must be clean). Run `kicad-cli pcb drc --severity-all --format json --output /tmp/drc_before.json pcb12/soma-carrier-v12.kicad_pcb` and print counts per type and the 2 unconnected items.
2. Fix +5V: route from R3.1 to the nearest copper that is already on the +5V net (find by net number), then ESTOP: connect the F.Cu stub end to U1A.13 and join the B.Cu fragment so U1A.13 reaches J9.1 continuously.
3. Run DRC again to `pcb12/drc.json`. Pass: `unconnected_items` empty except GND-only items, `shorting_items` 0, `clearance` 0, `track_dangling` 0. Max 3 fix rounds; if still failing, STOP and report the exact items.
4. Re-export gerbers to `pcb12/gerbers/` as in `pcb12/fab.sh` and re-render `pcb12/soma-carrier-v12-top.png`.
5. Write the P2 section with literal DRC counts. Run `git status --short`: only paths under `pcb12/`. `git add pcb12 && git commit -m "P2: fix ESTOP and +5V continuity" && git tag pcb-12b-done && git push origin pcb-v12 --tags`. STOP.
