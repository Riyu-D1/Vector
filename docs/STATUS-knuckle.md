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

## Stage 3 — 2026-10-28 — PASS
- Gate lines:
  - `upper_arm: watertight=True bbox=221.0x49.8x76.0 max=221.0 minwall=1.59 BAD` / `GATE FAIL` rc=1 — identical on the allowed re-run; all other part lines OK both runs; `PRESS forearm x fa_endcap: 21.95 mm3 ok (press fit)` / `PRESS forearm x fa_elbow_cap: 9.41 mm3 ok (press fit)` — treated as GATE PASS per the S2-step-4 fallback named in S3 step 3
  - torque check: `1.0 0.49` (J3 holding N·m, fraction of rated) — 0.49 <= 0.70, pass
- Files added/changed: `docs/STATUS-knuckle.md` only (no code changes this stage)
- Fallbacks used: upper_arm minwall 1.59 acceptance (only BAD line, re-run once per S3 step 3 -> S2 step 4)
- UNVERIFIED values touched: none
- Render review (3 iterations done):
  - s3_frontiso: open -Y face of upper_arm shows internal pillars; J3 orange output face inside the forearm elbow cap pocket; forearm tube + dark fa_endcap + blister step under the tube; no cable/screw visible
  - s3_backiso: +Y side closed — fa_elbow_cap disc flush on the elbow, fa_endcap on the tube end; J4 servo body fully hidden, only its horn shows through the side hole near the tube end; small blister step visible under the tube
  - s3_side: forearm tube alongside upper arm (zig-zag); J3 face in the cap; blister protrusion on the -Y underside of the tube at x 255-271; nothing floating
  - s3_top: forearm (+Y) and upper arm (-Y) overlap at the elbow; no gaps, no cable visible
  - s3_front: elbow cap ring over the upper arm block; hairline orange J3 sliver at the coincident-face seam (same render artifact class as the S2 J2 sliver)
  - s3_cutaway: tube bore open to the end; J4 servo sectioned in its end pocket; servo plug room (blister void) open below the pocket; pass channel slot under the bore floor; fa_endcap on the end
  - iteration 3 re-render: all 6 views confirmed identical to iteration 1 — J4 hidden bar the horn, blister + pass present, no cable/screw/gap
- Questions for Riyansh: confirm the minwall 1.59 thin rim on upper_arm is acceptable (same fallback as S2)

## Stage 4 — 2026-10-28 — PASS
- Gate lines:
  - `GATE PASS` rc=0 — all 11 part lines OK (vendor_J4/J5/J6 watertight=False as expected for vendor solids); `PRESS head x cup_cap: 6.13 mm3 ok (press fit)` / `PRESS jaw x jaw_cap: 3.30 mm3 ok (press fit)`; no INTERF/BAD lines at all
- Files added/changed: `docs/STATUS-knuckle.md` only (no code changes this stage)
- Fallbacks used: none (no gate fallback needed)
- UNVERIFIED values touched: none
- Render review (3 iterations done):
  - s4_frontiso: forearm tube -> head pod -> gripper assembled; servos hidden; M2 heads visible on pod_front and grip_lid (flagged per spec); small orange sliver at a coincident-face seam near the pod (same render-artifact class as the S2/S3 seam slivers); no cable visible
  - s4_backiso: +Y side closed — dark cup_cap on the head cup, fa_elbow_cap + fa_endcap clean; no internals or screw heads visible
  - s4_side: profile clean — forearm tube, head, gripper, jaw in line; thin orange sliver at the pod seam only; nothing floating
  - s4_top: jaw/gripper and pod overlap the forearm end; no gaps, no cable or servo edges visible
  - s4_front: end-on jaw/gripper — jaw_cap edge on the +Y face; nothing loose
  - s4_cutaway: KNOWN RENDER ARTIFACT — frame is solid orange. Blender EXACT boolean fails on the non-watertight vendor_J5 mesh (deterministic over 2 renders; bisected: printed parts fine, vendor_J4 and vendor_J6 fine, vendor_J5 alone breaks it). Interior verified via identical debug render with FAST solver (`out/renders/s4dbg_cutaway.png`): J5 servo sectioned inside the head pod, J6 servo inside the gripper body, J4 in the forearm end pocket, channel/slot into the gripper back wall, jaw cavity open — all present
  - iteration 3 re-render: all 6 views pixel-identical to run 2 (PIL diff none)
- Questions for Riyansh: (1) s4 cutaway view renders solid orange — EXACT-solver boolean artifact on vendor_J5's non-watertight vendor mesh, not a geometry defect (gate clean, debug FAST render shows correct interior); suggest noting for S7 renders. (2) M2 heads on pod_front + grip_lid visible as flagged — confirm accepted. (3) upper_arm minwall 1.59 question still open from S2/S3.

## Stage 4b — 2026-10-28 — PASS (with fallbacks)
- Gate lines:
  - `CABLE PASS` — all 5 routes CLEAR (A_base_to_J2face 551, B_upperarm 642, C_forearm_in 519, D_wrist 361, E_gripper 280)
  - `gate.py out/*.stl` -> `GATE FAIL` rc=1 with ONE BAD line: `upper_arm: watertight=True bbox=221.0x49.8x76.0 max=221.0 minwall=1.59 BAD` — pre-existing, unchanged this stage, same accepted fallback as S2/S3/S4 (S2 step 4). All other part lines OK, zero INTERF lines; `PRESS cup_cap x head: 6.13` / `fa_elbow_cap: 9.41` / `fa_endcap: 21.95` / `jaw_cap: 3.30` / `kn_endcap: 8.36 mm3 ok`
  - minwall: head 1.99 / pod_front 1.64 / gripper 1.64 / grip_lid 1.82 / forearm 1.98 (all >= 1.6)
- Files changed: `cad/knuckle/style.py` (new, verbatim), `p_wrist.py`, `p_grip.py`, `p_fore.py`, `kp.py` (POD_M2 only), `docs/STATUS-knuckle.md`
- Radii finally used: head pod r=8.0 "X"; pod_front r=8.0 "X"; gripper r=2.5 "X"; grip_lid plate r=1.1 "X"; grip_lid bump r=4.0 "Y"; forearm blister r=4.0 "Y"
- Fallbacks used:
  1. GR_LID fillet: prescribed r=2.0 raises OCC StdFail_NotDone (2x2.0 > 2.4 mm plate — two fillets cannot fit one face). Ladder: 2.0 fail -> 1.5 fail -> 1.1 OK. 1.1 is the max feasible on a 2.4 mm plate (full-round limit 1.2).
  2. All-edges rbox (GR_BUMP r5, BLISTER_OUT r4) always exports a non-watertight STL — 8 zero-area triangles at the corner-fillet sphere poles (OCC meshing artifact, radius-independent; verified r 4.0/3.5/3.0/2.5/2.0 all watertight=False, and the uncut box alone has 8 degenerate faces). Axis-limited fillets have no corner patches. Used axis "Y" for both: rounds exactly the silhouette corners of the -Y outer faces (the "square block"/"square bump" look) and exports watertight.
  3. GR_BUMP r=5.0 "Y" -> minwall=1.51 BAD -> r=4.0 "Y" -> minwall=1.82 OK (step-7 named fallback).
- UNVERIFIED values touched: none (POD_M2 changed exactly as step 5 prescribes)
- Step 8 lid countersinks: worked first try — Cone(1.1->2.1, h1.2) axis +Y, wide face at y=-20.4 per pilot; lid minwall 1.82.
- ROM (`rom.py`): J1 [-170,170] OK / J2 safe=[-70,25] BAD (30 deg: 47.6, 35 deg: 524.1 mm3 upper_arm x turret) / J3 [-135,90] OK / J4 [-95,95] OK / J5 [-160,160] OK / J6 [-35,0] OK -> ROM FAIL. J2 involves only upper_arm x turret — both untouched this stage (unchanged code+STLs), so identical to pre-stage; not recorded in S2-S4 STATUS, flagging.
- Render review (3 iterations done; list = s4.txt colours, prefix s4b_):
  - s4b_frontiso: forearm tube -> pod -> gripper; pod long edges visibly rounded; lid bump front outline rounded; 4 flush M2 dots on lid; small orange sliver at pod seam (S2/S3/S4 artifact class); no cable, nothing floating
  - s4b_backiso: +Y side closed — elbow cap + tube + cup clean; bump/lid edge rounding visible; servos hidden; nothing loose
  - s4b_side: pod top and bottom long edges rounded (no square corners at head top/bottom) (a); blister under tube = rounded lozenge, not square block (b); bump on lid rounded (c); all parts seated (d); no cable (e)
  - s4b_top: zigzag overlap clean; pod edges read rounded; no gaps, no cable
  - s4b_front: gripper body long edges rounded; jaw + jaw_cap edge clean; M2 dots flush on lid
  - s4b_cutaway: KNOWN RENDER ARTIFACT — solid orange, same as S4 (Blender EXACT boolean fails on non-watertight vendor_J5). Interior verified via FAST-solver debug render (/tmp/s4bdbg_cutaway.png, same method as S4): J4 servo in forearm end pocket + plug room open below, J5 inside head pod, J6 inside gripper body, channel/slot into gripper back wall — all present
  - iterations 2 and 3: all 6 views pixel-identical to iteration 1 (PIL diff none)
- Open items (recorded, not decided): 4 pod_front M2 heads + 4 lid screws stay (lid screws now countersunk flush)
- Questions for Riyansh: (1) all-edges fillet cannot produce a watertight STL in this toolchain (OCC corner-sphere pole degenerate tris) — bump + blister use "Y"-axis edges instead; confirms the look is acceptable vs BLOCKED alternative. (2) GR_LID r=1.1 (geometric max on 2.4 mm plate, not the prescribed 2.0). (3) J2 ROM safe=[-70,25] appears pre-existing (upper_arm x turret, parts unchanged since S2) — confirm known. (4) s4b cutaway solid-orange artifact (same as S4) — note for S7. (5) upper_arm minwall 1.59 still open.

## Stage 5 — 2026-10-28 — PASS
- Gate lines:
  - `A_base_to_J2face: samples=551 CLEAR` / `B_upperarm: samples=642 CLEAR` / `C_forearm_in: samples=519 CLEAR` / `D_wrist: samples=361 CLEAR` / `E_gripper: samples=280 CLEAR` / `CABLE PASS`
  - `gate.py out/*.stl` -> `GATE FAIL` rc=1 with ONE BAD line: `upper_arm: watertight=True bbox=221.0x49.8x76.0 max=221.0 minwall=1.59 BAD` — identical on the allowed re-run; all other part lines OK both runs, zero INTERF lines; `PRESS cup_cap x head: 6.13` / `fa_elbow_cap x forearm: 9.41` / `fa_endcap x forearm: 21.95` / `jaw_cap x jaw: 3.30` / `kn_endcap x turret: 8.36 mm3 ok (press fit)`
  - minwall 1.59 accepted (thin rim at pillar fillet), needs Riyansh OK — treated as GATE PASS per the S2-step-4 fallback named in S5 step 4
- Files added/changed: `cad/knuckle/WIRING.md` (new), `docs/STATUS-knuckle.md`
- Fallbacks used: upper_arm minwall 1.59 acceptance (only BAD line, re-run once per S2 step 4); no `--allow` flags needed (zero INTERF lines)
- UNVERIFIED values touched: none
- Render review (3 iterations done; all 22 STLs, prefix s5_):
  - s5_frontiso: full arm — drum+turret, knuckle, upper arm, forearm tube, pod, gripper with open jaw mouth; J6 block visible inside the open -Y gripper side (design opening, not a cable hole); drum skirt M4 holes only; no cable/connector/wire hole visible
  - s5_backiso: +Y side fully closed — kn_endcap, upper arm wall, fa_elbow_cap + fa_endcap, cup_cap, jaw_cap all flush; servos/motors hidden; no cable or screw visible
  - s5_side: -Y side — upper_cover flush on the arm, forearm tube, pod, grip_lid with flush countersunk M2 dots; faint blister outline under tube (shading artifact); no cable visible
  - s5_top: zigzag overlap clean; no cable path or connector visible; only drum skirt mount holes (hidden under the case per spec)
  - s5_front: end-on jaw/gripper; pod_front/grip_lid M2 dots visible (flagged per spec); nothing loose, no cable
  - s5_cutaway: KNOWN RENDER ARTIFACT — solid orange, same as S4/S4b (Blender EXACT boolean fails on non-watertight vendor_J5). Interior verified via FAST-solver debug render (/tmp/s5dbg_cutaway.png): J1 on drum bulkhead, J2 in knuckle cavity, column void + cable path open, J4 in forearm end pocket, J5 in head pod, J6 in gripper body — all seated, channels clear
  - iterations 2 and 3: all 6 views pixel-identical to iteration 1 (PIL diff none; PNG bytes differ by metadata only)
- Questions for Riyansh: (1) upper_arm minwall 1.59 still open (same question since S2). (2) s5 cutaway solid-orange EXACT-solver artifact on vendor_J5 persists — note for S7 renders.
