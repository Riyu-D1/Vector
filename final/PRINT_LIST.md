# final/PRINT_LIST.md — Stage F1+F2 print + tolerance plan

Final arm = `cad/arm2b` structure + `cad3/out` D2-changed parts + **2×
`cyclo4` 40:1 cycloidal actuator modules** (J2, J3 — the D4 redesign:
PETG-CF discs, near-zero flank clearance, run-in/selective-fit design)
+ **D6 K-KEEL wrist/gripper** (`wrist2/out` — F2: the arm2b wrist parts
j4_cradle/link4/link5/grip_frame are replaced by the w_* set).
Volumes/bboxes measured from the exported STLs (trimesh); mass = solid
equivalent at PETG-CF 1.31 g/cm³.

Printer: **Bambu A1, bed 256×256×256, PETG-CF only** (hardened 0.4 nozzle
required — see `order/BOM_FINAL_GBP.csv`). Dry the filament first.

## Filament (unchanged from D2)

| Option | UK shop | Price/kg | Checked |
|---|---|---|---|
| Bambu PETG-CF 1 kg | uk.store.bambulab.com | £32.99 | 1 Nov 2026 [S] |
| eSUN ePETG-CF 1 kg | 3djake.uk | £26.50 | 1 Nov 2026 [S] |

## Arm structure — qty 1 (D2 list + F2 wrist swap)

STLs in `cad/arm2b/out/` (unchanged), `cad3/out/` (**D2**) and
`wrist2/out/` (**D6** — the four `w_*` structural parts plus the D6
finger/rack set; fingers and racks are the arm2b geometry shifted
+5.6 mm in a along the wrist axis, kept posed with the D6 train).

| Part | STL | Mass g | Bbox mm | Orientation | Supp. | Walls/Infill |
|---|---|---|---|---|---|---|
| base_plate | arm2b | 505 | 140×200×14 | Flat on plate face | No | 6 / 40% |
| base_link | arm2b | 319 | 92×92×63.7 | Upright (as-built) | No | 6 / 40% |
| j1_cradle | arm2b | 136 | 57.5×57.3×54.5 | Open cup up | No | 6 / 40% |
| base_reinf | arm2b | 36 | 92×92×6.9 | Flat | No | 6 / 40% |
| yaw_limit | arm2b | 17 | 77×77×7.1 | Flat | No | 6 / 100% |
| link1 | arm2b | 56 | 83.7×77.2×84 | Flat face down | No | 6 / 40% |
| front_spacer_j2 | arm2b | 4 | 34.8×4×34.7 | Flat | No | 6 / 100% |
| flange_j2 **D2** | cad3 | 6 | 34.8×11.6×34.8 | Disc face down | No | 6 / 100% |
| back_spacer_j2 **D2** | cad3 | 13 | 57×4.7×56.8 | Flat ring down | No | 6 / 100% |
| upper_out | arm2b | 25 | 61×7×187.5 | Flat side down | No | 6 / 40% |
| upper_back | arm2b | 36 | 61×4×187.5 | Flat side down | No | 6 / 40% |
| front_spacer_j3 | arm2b | 5 | 34.8×5×34.7 | Flat | No | 6 / 100% |
| flange_j3 **D2** | cad3 | 7 | 34.8×12.6×34.8 | Disc face down | No | 6 / 100% |
| back_spacer_j3 **D2** | cad3 | 13 | 57×4.7×56.8 | Flat ring down | No | 6 / 100% |
| dogleg_l | arm2b | 25 | 76.1×5×99 | Flat cheek down | No | 6 / 40% |
| dogleg_r | arm2b | 25 | 76.1×5×99 | Flat cheek down | No | 6 / 40% |
| fore_l2 | arm2b | 31 | 171.6×4×57 | Flat plate down | No | 6 / 40% |
| fore_r2 | arm2b | 31 | 171.6×4×57 | Flat plate down | No | 6 / 40% |
| w_j4_cradle **D6** | wrist2 | 22 | 49.6×52.5×29.0 | Bolt plate on bed, sleeve mouth up | Yes — under sleeve +b rim [U] | 6 / 40% |
| w_link4 **D6** | wrist2 | 15 | 81.0×45.6×52.8 | Horn plate down | Yes — horn counterbores, plug tunnel roof [U] | 6 / 40% |
| w_link5 **D6** | wrist2 | 9 | 50.2×33.8×52.2 | −a end on bed, keel fins up | Yes — cheek-window top edges [U] | 6 / 40% |
| w_grip_frame **D6** | wrist2 | 21 | 62.4×64.0×59.8 | Keel bottom on bed, channel up | Yes — channel roof + window ledges | 6 / 40% |
| vendor_rack_u/d **D6** | wrist2 | 3 ea | 6×36×12 | Flat flank down | No | 6 / 100% |
| finger_u/d **D6** | wrist2 | 2 ea | 14.4×4×25.2 | Flat side down | No | 6 / 100% |

## Actuator modules — qty 2 (J2 + J3), cyclo4 D4 geometry

STLs in `cyclo4/out/`. **The discs are the whole tolerance story — read
the disc profile + coupon + pin-fit sections before slicing.**

| Part | Mass g | Bbox mm | Orientation | Supp. | Walls/Infill |
|---|---|---|---|---|---|
| housing | 73 | 57×57×54.4 | Back plate down | No | 6 / 40% gyroid |
| front_ring | 1 | 52×52×2.0 | Flat | No | 6 / 40% |
| pin_ring | 1 | 51.9×51.9×1.9 | Flat | No | 6 / 40% |
| **disc1** | 6 | 44.7×44.7×**4.25** | Flat — see disc profile below | No | **100%** |
| **disc2** | 6 | 44.8×44.8×**4.25** | Flat | No | **100%** |
| carrier | 16 | 43×43×10 | Flat | No | 6 / 100% |
| out_flange | 5 | 44×44×2.6 | Flat | No | 6 / 100% |
| hub | 6 | 20×44×18 | Flange face down | No | 6 / 100% |
| mag_puck | 1 | 12×12×6 | Flat | No | 6 / 100% |

(D4 changes vs cad/act2: disc thickness 4.0 → **4.25**, flank clearance
offset 0.15 → **0.01**, out-pin hole radial clearance 0.15 → **0.12**.
40:1 geometry unchanged: N40/NP41, R 23.5, RP 1.5, E 0.42, Ø3×10 ISO
8734 dowels.)

## Disc print profile — critical

`CLR_TOOTH = 0.01` is inside FDM scatter (±0.05–0.10); the design relies
on run-in + selective pin fit. Print the discs to make the flank land
**slightly tight**, then run them in — never loose:

- **Orientation: flat** — disc face on the bed so layers lie **in the
  disc plane** (flank load is in-plane; no Z-split risk).
- **0.12 mm layers** for flank fidelity (4.25 mm ≈ 35 layers).
- **100% infill** (or ≥6 walls + ≥80% — the flank is the part; any
  internal void is a wear pit).
- **No supports** — geometry needs none; support scars on the flank or
  bore would ruin the clearance.
- **Ironing OFF** — ironing resmooths the top skin but smears the hole
  edges and shifts the flank/out-pin dimensions locally.
- **Elephant-foot compensation 0.2 mm** — the first-layer squish widens
  the flank tips; without compensation the disc jams the pins at the
  bed side (burr ~0.2–0.3 mm).
- **Flank dimension tolerance**: after the elephant-foot pass, the flank
  must measure within ±0.05 mm of nominal — verify with the calibration
  coupon (below) on the same plate/settings BEFORE printing discs.
  If the coupon reads tight >0.05, add −0.05 mm XY hole/contour
  compensation in the slicer and re-coupon; if loose >0.05, +0.05.
- Print all 4 discs in one plate in one go, same filament, same nozzle
  wear state — matched sets only. A1 is open-frame: no drafts across
  the bed, standard PETG-CF temps, fan low for layer strength.

## Calibration coupon — `final/out/coupon.stl` (+ `coupon.step.gz`)

Print this FIRST, ~20 min, before the discs. One plate with 4 stations
replicating the real pin-vs-flank mesh (crank angle 0, true pin
positions, bore Ø3.05 = the housing's hole):

- Stations left→right: flank clearance **0.00 / 0.05 / 0.10 / 0.15 mm**,
  5 pin bores each (ISO 8734 Ø3×10 dowels — the BOM ring pins).
- Insert 5 dowels per station, push each pin toward the flank, measure
  the radial gap with feeler gauges. Nominal gap = the station's CLR
  (0.00 / 0.05 / 0.10 / 0.15) for every pin — at crank 0 all 5 engage
  on the conjugate flat.
- **Reading**: measured gap = nominal CLR + printer offset error. If the
  0.00 station binds (pins won't seat) and 0.05 measures ~0.00, the
  printer runs ~+0.05 tight — the discs at CLR 0.01 will land near-zero
  = exactly the design intent (run-in clears the last microns).
  If even 0.15 measures <0.05, the printer prints flanks oversize — add
  XY compensation and re-coupon. **Pass = a station that reads ≥0.00
  and ≤0.05 actual** — that is the effective working clearance the
  run-in assumes (per-unit SF 1.6–2.2 instead of the nominal 2.2).
- Also confirm the 5 dowels drop in/out of the bores with finger
  pressure only — if they press, the housing holes will press too
  (good to know before gluing).

## Post-process + run-in — pass criteria

Per module, after printing:

1. **Deburr/elephant foot**: scrape the first-layer edge of each disc
   with a blade; the flank tips must not stand proud.
2. **Sand/ream the flank**: 400→800 grit, ONE or TWO passes along the
   lobe tips only — remove print ridges, not material. Ream the 6 out-pin
   holes to a running fit (Ø4.08 nominal; a 4.0 reamer or a 3/32 drill
   by hand — the out-pins must spin freely, the orbit needs the 0.12
   clearance). Do NOT ream the ring-pin bores in the housing.
3. **Selective pin fit** (see next section) — dry, before grease.
4. **Run-in**: grease the ring pins + disc flanks (PTFE or lithium), fit
   the 6702 bearings, hand-cycle the input shaft — full turns both ways,
   ~200 revolutions (or a slow drill at <200 rpm for 10 min). The mesh
   should start notchy and free up; if it stays notchy after 200 rev,
   take the discs out, find the tight quadrant, swap those 2–3 ring pins
   for looser-tolerance spares, repeat.
5. **Pass criteria**: (a) backlash at the output ≤ ~1° by hand
   rock-test [U — measure on first unit], (b) input spins 10 full turns
   by one finger with no catch, (c) no white powder inside after run-in
   (powder = flank shredding, not bedding — stop, re-check pin fit).

## Selective pin-fit procedure — 41 dowels + spares

The BOM buys 2× boxes of 50 ISO 8734 Ø3×10 dowels (~98 pieces after the
82 needed). Dowel Ø tolerance is m6 (+0.002/+0.008); printed holes and
printed flanks scatter ±0.05. Sort, don't force:

1. Number the 41 pin stations per module (paint dot every 10th groove
   helps). Seat all 41 dowels dry — light finger push only; a dowel
   that needs pliers goes to the spare pile, the groove gets a cleaner
   pass with a 3.0 mm drill bit BY HAND (never a drill press — you'd
   oval it).
2. Fit disc1 over the out-pins, crank to a position where its flank
   sits against pins 0–10 on the +X side. Rock the input by hand:
   - **Binds**: those pins are the tight set — pull 2–3 of them, try
     spares from the second box (pin Ø varies ±0.006; a −Ø pin gains
     ~0.01 clearance). Worst case: micro-sand ONE pin's contact flat.
   - **Clicks/rattles** at mid-rock: loose — a +Ø spare in that slot.
3. Repeat for disc2 (it contacts the OPPOSITE side — the -X pins).
4. Pass = both discs rock through a full crank turn with uniform drag,
   no catch point. Write the swapped stations on a card in the
   electronics box — if a pin ever needs replacing, re-check that slot.

## Totals

- Arm 1044 (D6 wrist structure 51.6 cm³ replaces arm2b's 90.6) + modules
  ~175 + coupon 22 ≈ **1241 cm³** solid → **~1.6 kg** at full density;
  real extruded ≈ **0.8–0.9 kg [U]** — one 1 kg spool prints everything
  + coupon + ~1 spare disc. Budget a 2nd spool for disc re-prints if
  the first set's run-in fails.
