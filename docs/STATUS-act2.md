# STATUS — printed actuator (branch arm-actuator2)

## Stage A1 — 2026-10-28 — FAIL (3 minwall BADs with no allowed fallback left; all other gates pass)

- Gate lines:
  - Step 2 (G1): `RATIO 40.0`, `CYC PASS` (40:1); `CYC PASS` (50:1 dry check)
  - Step 7 (G2/G3): `housing..front_ring: watertight=True` x9, `LENGTH 55.00 OK`, `OD 57.00 OK`, `ACT PASS`, rc=0
  - Step 8 (G4/G5, first full run): `housing minwall=1.01 BAD`, `mid_plate minwall=0.83 BAD`, `hub minwall=1.24 BAD`, all other parts `OK`, zero `INTERF` lines on the 19-part run, `GATE FAIL`
  - Step 8 (re-run after pocket fallback): `housing minwall=0.99 BAD`, `mid_plate 0.83 BAD`, `hub 1.24 BAD`, `GATE FAIL`
  - Step 9 (G6): `mesh_clearance(40) = (0.144, 0.144)`, `mesh_clearance(40, second) = (0.144, 0.144)` — pass

- BLOCKED (minwall, spec'd geometry, no allowed fallback remaining):
  - `BLOCKED: gate housing minwall 0.99` — residual after the pocket fix: ~0.55 mm webs between the 41 Ø3.05 pin-groove holes (pitch 3.598, spec) and the 1.0 mm ligament bore→CSK tunnel at Z 31.5 (hole spec `OD/2-4..OD/2+0.1`). Both are exactly the spec'd dims; not fixable without changing ap.py values no step authorises.
  - `BLOCKED: gate mid_plate minwall 0.83` — Ø2.5 radial CSK pilot centred at Z 31.5 in a 4.0 plate leaves 0.75 mm roof/floor + breakthrough lips at the plate edge. Spec'd dims.
  - `BLOCKED: gate hub minwall 1.24` — Ø2.5 grub pilot at Z 35.8 leaves 0.75 mm to the cam1 bottom face (Z 33.8) + breakthrough lips on bore/cam. Spec'd dims.
  - Interference is clean: the complete run printed no INTERF lines at all (no --allow used).

- Part bboxes + volumes (step 5):
  housing (-28.5,28.5,-28.5,28.5,0,54.4) 45.9 | mid_plate (-23.4..23.4, 29.5..33.5) 5.9 | hub (-7.92..7.92, 33.8..47.2) 1.5 | disc1 (-21.78..22.62 x, 33.8..37.8) 4.3 | disc2 (-22.69..21.85 x, 38.1..42.1) 4.3 | carrier (-21.5..21.5, 42.4..52.4) 12.1 | out_flange (-22..22, 52.4..55.0) 3.8 | pin_ring (-25.95..25.95, 43.5..45.4) 1.0 | front_ring (-26..26, 52.4..54.4) 0.9 | 10 vendor_* parts (motor Ø44.5 z7.5..41.5, magnet, ringpins, outpins, dowels z49.3..57.3, 6808, 6702a/b, 685, as5600)
  - Note: expected `disc1 x max ≈ 22.84`; actual 22.62. The doc figure = r_max 22.42 of the clr=0 pin-centre curve + E; the real offset outline (r=1.65) has x_max 22.203 + E 0.42 = 22.62.
  - `ls out/*.step | wc -l` = 19; `ls out/*.stl | wc -l` = 19.

- 50:1 dry run (step 12): disc1 (-22.06,22.66,-22.4,22.4,33.8,37.8) 4.4, disc2 (-22.7,22.1,-22.36,22.36,38.1,42.1) 4.4, housing (-28.5..28.5, 0..54.4) 46.2; restored `RATIO = 40`, rebuilt.

- Render review (one line per view):
  - frontiso: output end up — orange flange, 3 grey dowels proud 2.3 mm, M3 holes, dark front_ring, plain Ø57 wall, one radial CSK hole; no bumps/cables.
  - backiso: back face — Ø10 encoder window in the wall; flange + dowel tips at the rim; plain cylinder outline.
  - side: smooth cylinder + the 270° radial CSK hole, countersink opens outward; nothing else on the surface.
  - top: output face — 3 dowels (PCD24) alternating with 3 M3 holes (PCD27), front_ring then housing rim, concentric.
  - front: wall with the 0° CSK hole flared outward; left edge shows flange + ring + dowel tips; no floating parts.
  - cutaway: order confirmed — motor bell → dark mid_plate → blue disc1 + green disc2 (6702 halves beside) → orange carrier + output pins → grey 6808 halves + pin_ring → orange flange; ring pins sit half buried in the bore-wall grooves beside the discs; countersinks open outward; nothing floats.

- Printability: housing back-face down, mid_plate front-face down, carrier plate-down, discs/rings/flange flat, hub cam1-down. Bridging: housing pocket ceiling spans 23.4 mm (OK on A1); Ø10 encoder window; radial Ø3.4/Ø2.5 holes print as horizontal holes (OK). Largest part Ø57 ≪ 256 bed. No supports needed.

- Fallbacks used:
  - housing pocket floor: `Z_ENC_POCKET` (0.0, 2.0) → (0.0, 1.8) and window start 1.9 → 1.7 (the stage's allowed housing fallback; removed the 115 borderline 1.6-mm samples).
  - mid_plate watertight=False → step-7 "extend cutters by 0.01": wire groove r0 6.0 → 5.99 (it was exactly tangent to the Ø12 stator hole, a 0-thickness face). Rebuilt, watertight=True.
  - Added `vendor_as5600` (23×23 board proxy filling the pocket, follows Z_ENC_POCKET): section-1 lists 9 vendor functions but the stage expects "9 printed + 10 vendor" = 19 parts; the AS5600 board is the only in-module BOM item without a proxy.
  - No `--allow` used (no INTERF pairs flagged).

- UNVERIFIED values touched: SHAFT_OUT, MOT_PCD, STATOR_HOLE_D, ENC_W (board 23×23 assumed), BRG_6808 lands, Tarot dims (MOT_D/MOT_H/SHAFT_D), LINK_PILOT_D grip length, MOT_SCREW_ANG.

- Files added: `cad/act2/{ap.py,cyc.py,p_act.py,build_act.py,act_checks.py,BOM.md,NOTICE.md}`, `renders/a1_{frontiso,backiso,side,top,front,cutaway}.png` (all ≤1.5 MB), `docs/STATUS-act2.md`. `out/` not committed.

- Questions for Riyansh: Q1 measure the Tarot 4008 (OD, height incl. base, base face to bell top); Q2 shaft length beyond the stator base (need ≥ 12); Q3 stator base hole PCD and thread, centre boss Ø; Q4 AS5600 board size and chip height; Q5 PETG or PA-CF for the discs?
- Open question for the designer: the three minwall BADs above come straight from spec'd dims (pin-web 0.55, CSK ligament 1.0, pilot/grub roofs 0.75). Print is still feasible (local thin lips, not structural walls) — flagging rather than changing ap.py without authorisation.
