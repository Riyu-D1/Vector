# STATUS — PCB v1.6 (pcb-v16)

Stage P7: black solder mask + white silkscreen + vector board art +
clean-up of every remaining v1.5 issue. Built in worktree
`~/Vector-wt/pcb16` on branch `pcb-v16` from `origin/pcb-v15`
(6777b69). v1.5 product files untouched; routing identical to v1.5
(same `routes_v15` content carried as `routes_v16.py`).

## DRC before -> after (kicad-cli 10.0.4, --severity-all)

| Check | v1.5 | v1.6 |
|---|---|---|
| violations total | 21 | 13 |
| silk_overlap | 7 | **0** |
| silk_over_copper | 1 (D6 "K" on R1.2) | **0** |
| lib_footprint_mismatch | 13 | 13 — all documented intentional, see below |
| unconnected pads | 0 | 0 |
| shorts / clearance | 0 | 0 |

## Silk fixes (all 8 -> 0)

- `PWR-ON` label moved (10,55) -> (10,63.5): was overlapping JP1's
  reference.
- `Q2` reference REF_FIX -> (12,65.5): was inside the TO-220 outline.
- `BZ FLYBK` label moved (80,108) -> (82,104): was overlapping the old
  v1.5 title; now sits between D7 and J17 under `CAN G-H-L`.
- `U2` reference REF_FIX -> (81.5,82): was colliding with C5's silk
  circle (both directions flagged).
- `J19` reference REF_FIX -> (92,79.6): was inside D5's outline.
- `U3` reference REF_FIX -> (102,46): was inside the DIP-14 outline.
- D6 "K" mark (library fp_text, F.SilkS) mirrored across the body
  local y -1.8 -> +2.4: was sitting on R1 pad 2 at (51.62,44);
  now at world (56.4,44), 0.95 mm clear of D6's pad. Logged
  coordinates per stage: before (52.2,44) -> after (56.4,44).

## lib_footprint_mismatch — documented, intentional

13 warnings, all on footprints placed at rotation 90 deg: J2, F1, Q2,
J1, R5, U1A, U1B, D6, J11, J9, J13, U3, J15. On this KiCad 10.0.4
build rotating *any* footprint to 90 deg triggers the warning
(verified: an unflagged rot0 resistor flags when only its `at`
rotation becomes 90) — pad `at` rotations differ from the unrotated
library copy. The affected footprints also carry deliberate local
overrides (pin-1 silk marks, REF_FIX reference moves, injected pad
nets), so they are *meant* to differ from the library. Kept as local
overrides; do not "update from library".

## Part A — design

- **Black mask / white silk**: stackup F.Mask/B.Mask `color Black`,
  F.SilkS/B.SilkS `color White`, `copper_finish "HASL lead-free"`.
  Emitted by `template_header()` in gen_pcb.py. Colour is an
  order-time option, not a Gerber feature — select Black+White at
  JLCPCB. See FAB_NOTES.md.
- **Art**: `art/not_a_robot.png` -> CAPTCHA "I'm not a robot"
  checkbox, ~(88,1.5)-(126,14.5) mm, top right (clear of H2); a +12 V
  F.Cu trunk crosses the box — allowed silk-over-masked-track.
  `art/sad_page.png` -> pixel sad-page icon, ~(46,61.5)-(60,79.1) mm
  beside J15. Converted by `art/make_art.py` (PIL threshold -> native
  grid snap (23x29 for the icon) -> maximal-rect merge) into filled
  `gr_poly` rects on F.SilkS (147 + 15 rects).
- **Silk tidy**: all gr_text at 1.0 mm except title 1.8 mm; new title
  block `SOMA BASE CARRIER v1.6` (51,108) + `hand-routed 2026-11`
  (51,111.3) inside an F.SilkS rect (30,105.8)-(72,113.5).
- **Renders**: `render-top.png`, `render-bottom.png`.

## Part B — remaining v1.5 issues

- Docs fixed: servo data line = Feetech half-duplex TTL bus (not
  RS-485/UART) in README + gen comments; U2 = TJA1051T/3 everywhere;
  D7 confirmed a real placed footprint at (66,104); DS18B20 is on
  DSG/DST/DSV THT pads (README row fixed).
- `bom.csv` rewritten — every ref on the board (65 parts) with value,
  footprint, count, cap voltage ratings (>=25 V on 12 V, >=10 V on
  5 V, >=6.3 V on 3V3), socket note for U3, PN2222A E-B-C note, J3
  Mini-360 pad-order note, K1 pin note, D4 = P6KE15A unidirectional.
- Routing preserved: `net_stats.py` identical v1.5 -> v1.6 —
  TOTAL track 3484.7 mm, vias 88. No part moved; no route nudge
  needed (all silk fixes were text-level). Hand-routed style kept
  (0/45 deg, chamfered corners, no autorouter, no stubs).

## Gates — exact output lines

- `kicad-cli pcb drc --severity-all`: `Found 13 violations` /
  `Found 0 unconnected pads` (13 = documented fp mismatch only).
- `python3 check_pads.py`: `OK — 201 file pads all match internal map,
  all on-board`.
- `python3 reroute.py --check soma-carrier-v16.kicad_pcb`:
  `legs 159, segments 400, vias 86, total track 3479.5 mm`,
  `warnings: 0`.
- `python3 verify_nets.py` (KiCad python): `RESULT: PASS` — every net
  one copper island.
- `python3 audit_pins.py`: U1A/U1B pad->net table IDENTICAL to v1.5
  (diff of all 22 pads per socket).
- `grep -c '(net "GND")' soma-carrier-v16.kicad_pcb` -> 75; zones = 2,
  filled_polygon = 19, rule_area = 0 (pours survived the pcbnew save).
- Art in Gerber: `soma-carrier-v16-F_Silkscreen.gto` contains filled
  regions in x88-126/y1.98-14.22 (checkbox) and x46-60/y61.5-79
  (sad icon) — verified by coordinate scan.

## Render review notes

- iter1 (basic, default preset): art + labels legible; board renders
  copper-orange — CLI ignored stackup mask colour (v1.5 renders
  identically orange; "Red" test also ignored).
- iter2 (high quality): same — confirms it's the renderer preset, not
  the board. Stackup strings verified in-file.
- iter3 top (`v16_black` user preset): black mask + white silk; CAPTCHA
  art crisp; title block readable inside its border; moved refs clear;
  D6 K on far body side; tracks visible as darker grooves (still
  inspectable).
- iter4 bottom (same preset): GND pour + pads/vias fine;
  `github.com/Riyu-D1/Vector` B.SilkS reads correctly (mirrored); no
  silk collisions.
- zoom inspections: checkbox text crisp at 0.24 mm cells, clear of H2;
  sad icon pixel-crisp with fold corner, clear of J15 and SPARE label.

## Fallbacks used

- `bitmap2component` is GUI-only on this machine -> custom PIL/rect
  pipeline in `art/make_art.py` (documented above).
- `lib_footprint_mismatch` resolved by documentation (stage-allowed
  fallback) — content-identical modulo rotation + deliberate local
  edits; updating is impossible-by-construction on rot90 instances.
- `kicad-cli render` ignores `--use-board-stackup-colors` on this
  build -> added a user-defined 3D preset `v16_black` in the local
  KiCad `3d_viewer.json` for honest renders (user config only, not a
  repo file).

## [U] items (bench)

SRD coil-pin bottom view, PN2222A marking, Mini-360 pad order, D6
population call, buzzer inductive check, estop-chain test, JP2 term
placement — all listed in BENCH_CHECKLIST.md.

## Files changed (vs pcb15 copy)

- `soma-carrier-v15.*` renamed -> `soma-carrier-v16.*` and the
  .kicad_pcb fully regenerated (placement + art + stackup + reroute +
  fill).
- `gen_pcb.py`: v16 outputs, black/white stackup patch, title block +
  date line, art emission, REF_FIX +4 (Q2/U2/J19/U3), D6 K-mark fix,
  `PWR-ON`/`BZ FLYBK` moves, docstring + bus-language comment fixes.
- `routes_v16.py` (v15 content, unchanged), `reroute.py`,
  `check_pads.py`, `audit_pins.py`, `net_stats.py`, `verify_nets.py`,
  `fill_zones.py`, `pmap.py`, `board_view.py`: v16 filenames/imports.
- `fab.sh`: repointed at the pcb16 worktree.
- `art/`: two PNGs + `make_art.py` + generated `art_polys.py`.
- `bom.csv`: rewritten complete. `README.md`: v1.6 + corrections.
- New: `FAB_NOTES.md`, `BENCH_CHECKLIST.md`, `STATUS-pcb16.md`,
  `render-top.png`, `render-bottom.png`, `gerbers/` (v16-named only),
  `soma-carrier-v16-jlcpcb.zip` (15 v16-named files incl. drill).
- `STATUS-pcb15.md` kept as the v1.5 record (unchanged).
- `drc_report.txt` regenerated.

## Open questions

- Whether JLCPCB's auto silk-clip preserves the fine art features
  (cells 0.24 mm): all art sits on masked areas, so no clipping is
  expected; sub-0.3 mm fills may widen slightly at plot — accepted.
- `board_view.py` on the filled 1.2 MB file did not finish in a
  reasonable time (killed); the placeonly map + renders + DRC +
  coordinate-level Gerber inspection cover the same check.
- `soma-carrier-v16-copper.svg`, `-top.png`, `-bottom.png`,
  `-drc.rpt`, `drc.json` were refreshed from the v1.6 board (the copy
  had stale v1.5 content under v16 names).
