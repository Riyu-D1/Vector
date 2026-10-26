# SOMA carrier PCB: how to finish routing (written by someone who can SEE the board render; you cannot)

Read this whole file, then follow it in order. It replaces all the "variant" experiments.

## 0. Stop the churn first (5 min)
1. Kill every extra router run and sibling experiment: `pkill -f gen_pcb.py` then `ls -d /tmp/pcb_*` and delete them. Only ONE generator run at a time from now on. Earlier OOM kills and 8 hours of ordA/ordC/ordE/viaR/exp_periph variants did not converge. Do not start more variants.
2. Never run a search with no cap. Any single net search is capped at 250k states and 60 s. If a net does not route in that, the PLACEMENT or the PIN ASSIGNMENT is wrong. Fix that, do not search harder.

## 1. Give yourself eyes (10 min)
Write `pcb/board_view.py` (read the .kicad_pcb text, no kicad python needed). It must print:
- a text map, 1 mm per character, separately for F.Cu and B.Cu: `#` pad, `=` track, `o` via, `.` free, with an x ruler every 10 mm and a y ruler on the left;
- a table of every different-net pad pair whose copper edges are closer than 0.5 mm (this finds placement collisions);
- per unrouted net: the two copper islands and the straight gap between them.
Run it after EVERY change. Also run `kicad-cli pcb drc --format json` and read the `violations` and `unconnected_items`.

## 2. What the real render shows (last board file, 100x85 mm; the generator may now emit 115x95, so re-check numbers with board_view.py but the structure below is real)
DRC on that file: 6 shorting_items, 69 clearance, 10 unconnected, 15 pth_inside_courtyard, 12 courtyards_overlap, 6 solder_mask_bridge.

A. The shorts are mostly PLACEMENT bugs, not routing bugs. Fix by moving parts.
 - D4 (DO-201 diode, 12.7 mm long, at 26,52 rot 90) lies across the ESP32 socket row U1A and on top of R8: D4 pad 2 (26,39.3) is 1.2 mm from R8 pad 1 (27,40) and D4 pad 1 (26,52) touches U1A pad 3 (27.22,51.16). That makes the VSNS/GND and ESTOP/+12V_IN shorts. Move D4 (and D1, the same big diode at 16,35) to a free rectangle at least 14 x 6 mm that touches no header, resistor or other diode. Use board_view.py to find the free rectangle.
 - R7 (27,36) and R8 (27,40) are 4 mm apart and D4 body crosses both: after D4 moves, keep R7/R8 at least 1.5 mm pad-to-pad from anything else.
 - Right edge, header column x about 93 (J12 at 93,24 and J14 at 93,48): a GND track passes within 0.2 mm of a +3V3 via at (89.8,39.75). Remove that GND track (see 3a).
 - GND track on B.Cu hugging BUSA_DATA near (35.8,11.2)-(36.9,8.9) under J4: also goes away with 3a.
B. Courtyard overlaps and pth_inside_courtyard are crowding. Spread parts: the top band (y 5 to 20) and the left column (x 5 to 20) have the most free copper. The middle (y 36 to 64, x 30 to 90) is where everything piles up.
C. Unrouted nets, all clustered, all fixable by pin choice:
 - ENC_A, ENC_B, ENC_SW: from J13 (KY-040 header, bottom-left, 14,80) up to the ESP32 row near (31 to 32, 51 to 59). That is a 22 mm vertical run through the busiest area.
 - SP1, SP2, SP3: from J15 (spare header, 40,80) to the ESP32 row near (57 to 59, 62 to 72) and (32.6,77).
 - +5V: four broken stubs around (68 to 73, 49 to 75), the column next to BZ1 buzzer, J9, Q1.
 In the top render the bottom edge (y 70 to 85) is a long strip of headers (J13, J15, J10) with almost no free copper above it, so everything from there has to climb through one 6 to 8 mm band. This is why routing fails.

## 3. The strategy (do these in order)
a. GND is a POUR, not tracks. Delete every GND track from the router (GND must not be in the A* route list). Put one GND zone on B.Cu and one on F.Cu covering the whole board, 0.5 mm clearance to other nets, 0.3 mm min width, thermal relief on THT pads. Add stitching vias (0.6 mm via, 0.3 drill) every ~15 mm on a grid, only where free. Every through-hole GND pad then connects by itself, so about a third of the nets disappear.
   The headless zone fill crashes in this KiCad build, so: emit the zones with the generator, and run DRC for everything except GND "unconnected" (filter it in your check). Tell the user to open the board in KiCad, press `B` (fill all zones) and run DRC once. Do not spend time fighting the fill crash.
b. Free the GPIO assignment to shorten wires. These signals are interchangeable GPIOs on the ESP32-S3 and are NOT fixed-function: ENC_A, ENC_B, ENC_SW, SP1, SP2, SP3, IRIN, TEMP, NEO, LEDGPIO, BUZ, VSNS, SDA1, SCL1, SDA2, SCL2, WTX, WRX, ESTOP. For each one, pick the DevKitC-1 header pin that is physically nearest to its destination connector. Edit the pin map dict near line 213 of gen_pcb.py. Constraints: do NOT use GPIO 0, 3, 45, 46 (strapping), 19 and 20 (USB), 43 and 44 (UART0 console), 26 to 37 (flash and PSRAM, not broken out safely on N16R8), and VSNS must be an ADC1 pin (GPIO 1 to 10). Keep BUSA_DATA and BUSB_DATA and RXA, RXB on their current pins if firmware already depends on them. Write the new map into docs/build-notes.md so firmware can follow. Rule of thumb: connectors on the bottom edge use bottom-row pins, connectors on the right edge use right-hand pins.
c. Move the congested connectors to where the wires are short. Allowed moves (anything not listed stays): J13 and J15 up out of the bottom strip so there is a 10 mm clear band between them and the ESP32 row; Q1/IR1/DS1/J14 spread along the right edge with 8 mm between them; the buzzer BZ1 and its driver resistors go to the free top-right or bottom-right corner. The board may grow at most to the current generator size (115 x 95). Mounting holes stay in the four corners, 4 mm in.
d. Trace rules. Signals: 0.25 mm track, 0.2 mm clearance. +3V3: 0.4. +5V and +5V_MCU: 0.6. +12V_IN, +12V_SW, +12V (servo bus, up to several amps, fuse is 6 A): at least 1.5 mm, as short and straight as possible, F.Cu preferred, no vias on them if you can avoid it. Vias: 0.7 mm pad, 0.3 drill, at least 1.0 mm from any pad centre, never inside a pad.
e. Pin escape. THT pads are 1.7 mm square at 2.54 pitch, so the gap between neighbouring pins is 0.84 mm: exactly ONE 0.25 mm track fits between two pins, never two. The ESP32 socket rows are walls on both layers because the pins go through the board. Cross a row only through a gap and count the crossings: 20 gaps per row. The 21 mm tall channel between the two ESP32 rows is the best free routing space on the board, use it as the main bus.
f. Layer discipline: F.Cu runs mostly horizontal, B.Cu mostly vertical, switch with a via only at a bend. Group related nets (SDA1/SCL1, SDA2/SCL2, ENC_A/ENC_B/ENC_SW) side by side at 0.5 mm spacing.
g. Route order: (1) +12V trunk, (2) +5V, +5V_MCU, +3V3, (3) fixed-function nets, (4) the reassigned GPIOs. After each group run board_view.py and DRC. If a net fails in group 4, change its pin (3b) or nudge one connector (3c). Never reorder the whole run.
h. For any net the A* will not do, write its waypoints by hand in the `ROUTES` list in gen_pcb.py (it already supports waypoint lists, see the LEDGPIO entry near line 789). Use only 0 or 90 degree segments (at most one 45 degree corner), taken from your board_view map of free cells.

## 4. Definition of done (all must be true, show the numbers)
- `kicad-cli pcb drc` (ignoring GND-unconnected only until the user presses B) shows 0 shorting_items, 0 clearance, 0 hole_clearance, 0 solder_mask_bridge, 0 unconnected_items for every net except GND.
- pth_inside_courtyard and courtyards_overlap are zero, or each remaining one is two parts that are meant to nest (list them).
- Both sides rendered with `kicad-cli pcb render` (top.png, bottom.png) and copied to `pcb/`.
- Gerbers and drill re-exported to `pcb/gerbers/`, `docs/build-notes.md` updated with the new GPIO map, README PCB section updated.
- `/usr/bin/git add` the pcb folder, commit "Route carrier: GND pour, GPIO reassignment, placement fixes", push.
- Time box: 90 minutes. If a net is still open at 60 minutes, widen the board by 10 mm on the side where the net is stuck instead of searching longer.

## 5. Report back (short)
The DRC counts before and after, the final GPIO map, every part you moved with old and new coordinates, and anything you could not do.

## 6. UPDATE: the board MAY be made bigger (user approved)
The PCB sits on four standoffs in the case tray (`cad/lib/case.py`). The tray interior is 144.8 x 154.8 mm (150x160 outer minus 2.6 mm walls). This overrides the "at most 115 x 95" limit in 3c.
- Allowed size: up to 135 x 145 mm (leaves about 5 mm to every wall). Prefer the smallest growth that fixes the congestion: grow by 5 to 10 mm at a time, in the direction where the stuck nets are (the bottom edge strip first).
- Keep the four corner mounting holes 4 mm in from the corners.
- Connectors that poke through case panel cutouts (J13 jog, J9 estop, J11 OLED, BZ1 buzzer, the XT60/screw terminals) must stay on the same board edge they are on now, or `case.py` cutouts must move with them.
- If you change board size or hole positions, update in the same commit: `PCB_W, PCB_H`, `PCB_X0`, `PCB_Y0` and the standoff hole list in `cad/lib/case.py`, re-run the CAD export so `cad/export/case_*.stl` match, and update `docs/build-notes.md` and the README mention of the board size. Check the drum recess (diameter 132, centre at case 75,88) still clears the PCB's tall parts; do not put C1/C3 or the buzzer under the drum seat ring screws.

## 7. CRITICAL BUG FOUND IN THE CURRENT RUN (stop the live run, fix this first)
The ESP32 sockets U1A and U1B (now PinHeader_1x22, `rot_deg=-90`) are written into the .kicad_pcb with their pins running WEST from x=22.14, off the board: KiCad's own DRC says U1A pad 2 is at x=19.6 and pad 10 is at x=-0.72 (copper_edge_clearance). But the router log is routing to pads on the EAST side (for example +5V_MCU -> (24.7, 28.3), which is where U1B pad 2 would be if the row ran east). So the generator's rotation maths and KiCad's rotation direction disagree in sign for this footprint, the router is aiming at pads that are not where the file puts them, and every route to U1A/U1B will miss its pad. That explains the huge unconnected count and some of the "stuck" nets.
Do this now:
1. `pkill -f gen_pcb.py`. The live run is being wasted.
2. Write `pcb/check_pads.py`: parse every `(pad ...)` of every footprint in the emitted .kicad_pcb (footprint at + rotation applied the KiCad way, y down, positive angle = counter-clockwise on screen) and compare to the generator's own PADS table. Print every pad where they differ by more than 0.01 mm. This must print nothing before any routing run is allowed to continue. Run it after every placement or rotation change.
3. Fix the rotation (flip the sign of the angle written to the file, or use rot_deg=+90, whichever makes check_pads.py clean) so U1A runs from x=22.14 EAST to x=75.5 and U1B the same. Pin 1 must be at the WEST end next to the USB side, as the pin comments in gen_pcb.py say.
4. Check the other rotated footprints (every part with rot_deg other than 0: J1, J2, D1, D4, J7 to J11 etc.) with the same script. If any differ, the same sign bug is on them too.
5. Remaining real placement collisions in the last emitted board: J16 pad 2 (14.2,17.0) is 1.8 mm from D1 pad 2 (16.0,15.3), a short between +12V_IN and +5V; F1 pad 1 (17,50) is on top of the socket row near (19.6,51.16). Move F1, J16 or D1 so the minimum pad-to-pad gap is at least 1.0 mm between different nets.
6. Only then restart ONE routing run. Set a hard cap so no single leg grinds longer than 60 s (the +5V J15.3 leg was grinding for 4+ minutes at 97% CPU). A leg that hits the cap is deferred and you move to a hand-written waypoint for it (3h) or a one-pin swap (3b).

## 8. The full run just failed with 3 unrouted nets: +12V, +5V, SCL1 (diagnosis from the log and the render, do these in order)
Result of the run that finished at about 21:15: `RuntimeError: unrouted nets: ['+12V', '+5V', 'SCL1']`, the board file was NOT updated (still the placed-only board), so DRC shows 151 unconnected and nothing to look at. Fix both problems below.

A. Make the generator never throw away its work. On failure it must still write the .kicad_pcb with every route it did finish, and print the failed nets with the straight-line gap for each. Then DRC and the render show what is really open. Do this first, it takes 5 minutes.

B. +5V cannot cross the ESP32 socket row. The failing +5V leg goes from (8.0,36.0), which is NORTH of the U1A row (y=51.16), to (50.7,58.0), which is D1's right-hand pad, SOUTH of that row. The log says the search only explored y 34.7 to 50.4, so it never got past y=50.4: the U1A row of 22 pins is a wall on both layers, and the only way through is between two pins, where one 0.25 to 0.4 mm track fits but a 0.6 mm +5V track does not. Do NOT try to make the router squeeze through. Fix by placement: D1 (the Schottky on the ESP32 5V feed) joins +5V and +5V_MCU, and +5V_MCU is U1B pin 2 at (24.68,28.3) on the NORTH row. Move D1 to the north side, in the band y 20 to 26, x 24 to 36 (the 12.7 mm long body horizontal, anode left, so it ends up 3 to 6 mm above the U1B row). C1 (40,19) is a 10 mm electrolytic, so keep D1's right pad at least 2 mm outside C1's courtyard, and keep it clear of J3 (22,14). If that band is not free, put D1 anywhere on the north side with board_view.py. Then re-run check_pads.py.
   Check the same thing for every net: for each net list which side of U1A and U1B each pad is on. Any net with pads on both sides of a socket row (and not a pin of that row) needs either a part moved or a crossing through one named gap.

C. +12V to J4 pad 2 at (32.54,9.0). The start copper is at (26,14), 6.5 mm away on the same side, so this is not a crossing problem, so the failure is the goal pad being sealed by the new "box keepouts and corner discs" you added for the connector bodies. J4 is a KK-254 3-pin: pad 1 GND (30,9), pad 2 +12V (32.54,9), pad 3 BUSA_DATA (35.08,9). The pad can only be entered from the south (y>9). Check what the keepout does at (32.54, 10 to 14): if it blocks that, shrink the keepout so a 1.5 mm track can run straight south from the pad. Wide tracks must not be required to pass between pads: end the 1.5 mm trunk 1.5 mm before the pad and neck down to 0.8 mm for the last stub if clearance demands it. Then route +12V by hand as waypoints: (26,14) -> (32.54,14) -> (32.54,9). Check it with board_view.py first.

D. SCL1 failed once and then routed on retry. After A to C, if it still fails, swap which GPIO carries SCL1/SDA1 (guide 3b) so the J7/J11/J12 sensors are fed from the U1B pin nearest to them.

E. After the fixes: run ONE full route, then DRC, then report counts. Do not tune the router again; every failure after this is a placement or pin problem, so fix it by moving one part or swapping one pin, and keep the 60 s cap per leg (the last run took 30 minutes).
