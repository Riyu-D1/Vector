# STATUS — knuckle arm (branch arm-knuckle)

## Stage 1 — 2026-10-27 — PASS
- Gate lines:
  - gate_selftest (expected-fail run): `thin: watertight=True bbox=20.0x20.0x20.0 max=20.0 minwall=0.49 BAD` / `INTERF a x b: 2000.00 mm3 BAD` / `INTERF a x thin: 1141.00 mm3 BAD` / `INTERF b x thin: 375.50 mm3 BAD` / `GATE FAIL` rc=1; single-part re-run `GATE PASS` rc=0
  - stage gate (step 9): `PRESS turret x kn_endcap: 8.36 mm3 ok (press fit)` / `GATE PASS` rc=0 — all part lines OK (vendor_J1/J2 watertight=False as expected for vendor solids)
- Files added/changed: `cad/knuckle/` (14 .py + .gitignore), `cad/vendor/` (all files — 5.3M ≤ 15M so STEPs committed too, incl. vendor `ard/` motor-protocol sources), `docs/STATUS-knuckle.md`
- Fallbacks used: none (`rm -rf cad/knuckle` of a previous untracked attempt per step 2)
- UNVERIFIED values touched: none
- Render review (3 iterations done):
  - s1_frontiso: drum + turret + knuckle assembled; J2 output face visible at open −Y knuckle end (arm interface), no floating parts, no cable/screw visible
  - s1_backiso: kn_endcap disc closes +Y knuckle end; drum skirt ear hole visible; all grey, motors hidden
  - s1_side: thin ring between drum top and turret hat, no other gaps; orange J2 face flush in knuckle bore
  - s1_top: drum skirt + turret hat concentric; 3 skirt mount holes visible; nothing floating
  - s1_front: same as side — hat ring clean, J2 output face inside knuckle rim
  - s1_cutaway: J1 inside drum on bulkhead, J2 inside knuckle, column void clear
  - s1b cutaway (turret+J2 only): J2 cap passes through the bulkhead hole into the column void — confirmed
  - iteration 3 re-render: all 6 PNGs pixel-identical (PIL diff = none)
- Questions for Riyansh: none

## Stage 2 — 2026-10-28 — PASS
- Gate lines:
  - `upper_arm: watertight=True bbox=221.0x49.8x76.0 max=221.0 minwall=1.59 BAD` / `GATE FAIL` rc=1 — identical on the allowed re-run; all other part lines OK both runs, `PRESS turret x kn_endcap: 8.36 mm3 ok (press fit)`
  - minwall 1.59 accepted (thin rim at pillar fillet), needs Riyansh OK — treated as GATE PASS per the stage's single allowed fallback
- Files added/changed: `docs/STATUS-knuckle.md` only (no code changes this stage)
- Fallbacks used: upper_arm minwall 1.59 acceptance (only BAD line, re-run once per S2 step 4)
- UNVERIFIED values touched: none
- Render review (3 iterations done):
  - s2_frontiso: upper_cover closes the −Y side flush along the pill profile; no internal parts, cables, or screws visible
  - s2_backiso: arm +Y wall clean; J3 orange output face flush at the elbow end only (motor body hidden in arm); turret + kn_endcap clean
  - s2_side: pill-profile arm over column and endcap disc; cover seam flush, no gaps or floating parts
  - s2_top: thin orange J2 sliver at the arm/knuckle rotating-gap seam (CLR gap); no cable exposed
  - s2_front: same J2 seam sliver; kn_endcap flush on the knuckle; nothing loose
  - s2_cutaway: J2 motor seated inside the knuckle cavity; arm cavity clean
  - s2b (no cover): open side shows the 4 cover pillars + magnet pockets, inner Z-web, J3 nested with only mount features showing, J3 cable notch, and the J2 cable groove over the top — all present and clean
  - iteration 3 re-render of the full list: confirmed identical to iteration 1 — cover flush, J3 hidden, no visible cable/screw/gap
- Questions for Riyansh: confirm the minwall 1.59 thin rim on upper_arm is acceptable (fallback per S2 step 4)
