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
