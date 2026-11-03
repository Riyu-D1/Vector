# wrist2/STATUS-wrist2.md — D6 bolder wrist + gripper redesign (v2 of D5)

Stage: `~/Vector/stages/D6_wrist_v2.md`. Worktree `~/Vector-wt/wrist2`,
branch `arm-wrist2` from `arm-wrist` (a5234b3). All CAD work lives in
`wrist2/`; the kinematics/gravity/test updates are edited directly in
`software/robot-os/` on this branch (allowed by the stage) and snapshotted
at `wrist2/patches/robot-os-d6-wrist2.patch`. No other product file was
edited; `arm-wrist`, `arm-knuckle`, main checkout untouched.

## Design intent — K-KEEL

D5 kept every servo position, so the outline stayed boxy. D6 moves the
servos: **J5 becomes a dorsal fin servo above the tool axis (b = 0,
case riding up) and J6 + gripper servo pack inline in a ventral keel
17 mm below the axis.** The grip sets the envelope; the shells are thin
cheek plates + open cages, and the silhouette tapers continuously from
the cradle into the fingers.

Two layouts probed at servo-case level (`layout_probe.py`), D5 as ref:

| layout | J5 (a,h) | J6 (a,h) | case union b | case union h | bbox cm3 | note |
|---|---|---|---|---|---|---|
| D5 ref | 37.6, 24.2 | 53.4, 0 | −12.4..35.1 (47.5) | −35.1..64.4 (99.5) | 128.3 | J5 offset +b — the wide slab |
| D-DECK | 30.0, −17.8 | 53.4, 0.6 | ±12.4 (24.8) | −58.0..35.7 (93.7) | 128.1 | deep belly under axis: J2-pose sweep risk, bottom-heavy look |
| **K-KEEL** | 30.6, 7.6 | 64.0, −11 | ±12.4 (24.8) | −46.1..47.8 (93.9) | 125.5 | fin up + keel down, balanced around the axis |

K-KEEL picked: width 24.8 vs 47.5 (−48%, the front-view slab is gone),
lowest union volume, taper symmetric about the tool axis, gripper-led.
D-DECK was equal on volume but put all the mass under the axis (worse
J2-sweep margin and a heavier look). Final geometry shifted the roll axis
to h = −17 and the grip train +5.6 mm in a after the J6/g interleave fix
below — numbers here are the probe's; final values are what shipped.

## Final geometry (mm, wrist frame a/b/h)

| chain | D5 | D6 |
|---|---|---|
| J4→J5 | 37.6 | 30.6 |
| J5→J6 | 19.2 | 22.4 |
| J6→TCP | 75.0 | 84.4 |
| TCP h below J4 axis | 0 | −17.0 (keel roll axis) |
| J4→TCP | 131.8 | 137.4 (+5.6) |
| J2→TCP reach | 374.9 | 380.5 (in 375 ± 10) |

J5 axis a 30.6 h +7.6 (case a 20.5..65.7, h −1.5..47.8) · J6 axis a 53.0
h −17.0 · grip servo a 107.0 h −17.0 · roll axis h −17.0.
Vendor parts unchanged: J4 STS3250 (cad3), J5/J6/gripper STS3215, same
racks/gear/fingers (grip train shifted +5.6 in a with the servo move).
`fore_l2/r2` interface kept verbatim — same bolt centres, same d38 pilot.
J2/J3 actuators + cyclo4 untouched. **BOM delta £0.00.**

## Parts (`build_wrist6.py`, all watertight)

| Part | vol cm3 | solid g | ~0.6 g | D5 cm3 | delta |
|---|---|---|---|---|---|
| w_j4_cradle | 17.0 | 21.6 | 13.0 | 28.7* | −40.8% |
| w_link4 | 11.4 | 14.5 | 8.7 | 29.8 | −61.7% |
| w_link5 | 6.9 | 8.7 | 5.2 | 11.2 | −38.8% |
| w_grip_frame | 16.3 | 20.7 | 12.4 | 20.9 | −22.0% |

*D5's cradle was already the D5 redesign vs arm2b 28.7 — D6 keeps that
volume class. Structural total 51.6 cm3 (D5 63.1, arm2b 90.6) → −18% vs
D5. Modelled wrist+gripper mass incl. vendor parts: **0.225 kg ≤ 0.234**
constraint met.

w_j4_cradle: sleeve + bolt plate (interface identical to D5). w_link4:
J4 horn plate + spine rib rising into the J5 fin cage. w_link5: J5 horn
plate + thin cheeks carrying the J6 pocket + keel webs. w_grip_frame:
J6 horn plate (clipped outline for roll clearance) + slim rails cage +
rack channels, open top.

## Task 3 — check results (`wrist2/wrist2_checks.py`)

- REACH: J4→J5 30.60 ✓, J5 horn face +3.0 ✓, roll line −17.0 ✓,
  J4→TCP 137.40 ✓, J2→TCP 380.5 ✓.
- HOLE: 4×d3.4 horn PCD14 on all 3 horn plates, centres err 0.000;
  fore_r2 M3 clearances + cradle d2.5 pilots on the same centres. PASS.
- CLEAR: 0.00 mm3 intersection, each new part vs its servo case. PASS.
- GRIP: racks in the 64 mm channels, engaged on the gear, no hits at
  25 mm open. PASS.
- MASS: wrist+gripper 0.225 kg ≤ 0.234 (D5 modelled). PASS.
- TORQUE @0.5 kg (new masses/offsets):
  **J4 0.827 N·m ≤ STS3250 derated 1.569/1.4 = 1.12** (stage model 0.801
  — ours is slightly higher because TCP grew 5.6 mm) PASS;
  **J5 0.603 ≤ 0.98/1.4 = 0.70** with J4 turned 90° PASS;
  **J3 1.77 ≤ 2.0 cap** PASS;
  **J2 3.28 > 3.0 printed-disc cap — FAIL (honest): the J2 cyclo disc
  cap is exceeded at full reach with the rated 0.5 kg payload. Not a D6
  regression — the same load case over-caps on D5 geometry too (J2 lever
  is upstream of the wrist); robot-os enforces the cap and refuses the
  move (test_torque_caps). Max payload at that pose: 0.380 kg (J2-limited);
  J4's own bound is 0.467 kg.**
- STRESS J4 hand calc, M = 0.801 N·m: worst section is the w_link4
  spine-rib/horn-plate junction, S ≈ 67 mm3 → σ ≈ 11.9 MPa vs 25 MPa
  cross-layer [U] → **SF 2.1 ≥ 2** PASS.
- WALL: 11 probes, 1.85–5.85 mm (design 2.0+, min 1.8). PASS.
- ROM (posed-mesh sweeps): home pose clean; J4 −90..+85° (175°, need 140);
  J5 −70..+70° (exactly 140); **J6 ±180° (360°, free)**; J3 215°, J2 185°
  arm sweeps pass. PASS.
- CABLE: plug-channel probes empty on all 4 parts (4 servo channels kept:
  J4 sleeve slot, J5 fin tunnel, J6 keel slot, g cheek). PASS.
- OVERHANG (per-part print orientation): flat ceilings exist — same class
  of support as D5, listed in `PRINT_LIST-wrist2.md` [U]. PASS.

`CHECKS FAIL` overall **only** because of the J2 cap above — every
wrist-scoped check passes.

## Task 2 — kinematics / software (`software/robot-os` on arm-wrist2)

- `config.py`: J5 (127.0,0,223.8), J6 (149.4,0,199.2), TCP (233.8,0,199.2);
  W_J5 (0.0306,0,0.0076), W_J6 (0.0224,0,−0.0246), T_TCP (0.0844,0,0);
  L_WRIST = |(w3a, w3z)|.
- `kinematics.py`: J4 back-projection now uses the 2-vector
  (w3a, w3z) = W_J5+W_J6+T_TCP — required since the TCP hangs 17 mm
  below the J4 pitch axis (scalar `l3` was wrong for that). FK/IK/tests
  for the rest of the arm unchanged.
- `gravity.py`: wrist rows re-massed/re-centroided from measured D6
  volumes (AB-pose centroids); wrist5/grip body origins moved to the new
  axes. J2/J3 torque caps untouched.
- **pytest: 66 passed, 0 failed** (`python3 -m pytest tests/ -x -q`,
  7.6 s). FK/IK round-trips, gravity torques (J2 3.249 / J3 1.756 /
  J4 0.828 at the AB pose 0.5 kg), payload bounds and disc-cap refusal
  all re-verified.
- TCP change reported: +5.6 mm in a, −17.0 mm in h vs D5
  (home TCP (228.2,216.2) → (233.8,199.2)).
- No URDF/MJCF files exist in the tree — nothing else to patch.

## Cable routing (4 servo TTL cables, all channels kept)

- J4: plug exits up through the sleeve slot (unchanged from D5).
- J5: plug exits the fin case's −a end, guided down the link4 tunnel.
- J6: plug exits through the keel end-cap slot in w_link5.
- Gripper: plug region open via the grip cage cheek window; exits −a
  under the J6 horn plate (interleaved, see below).
Probes verify each channel empty; real-wire bend radii [U].

## Render notes (looked at them myself)

`renders/` — before set (arm2b), after set, asm set,
`before_after_{frontiso,side}` composites.

- `after_side` vs `before_side`: the dark slab is gone — thin link plate,
  exposed servo cases stacked fin-over-keel, slim grip rails to the
  fingers. The outline tapers continuously into the gripper.
- `after_frontiso`: shells hug the cases; grip end reads narrow and open.
- `asm_frontiso`/`asm_side`/`asm_front`: full arm — the wrist now reads
  slim and gripper-led off the fore; no visual collisions.
- Honest: the two middle servo cases are still vendor boxes — nothing
  printable can shrink them — but the printed structure around them is
  thin and tapered and the grip end is minimal. Not boxy any more.

## Iteration log / failures (honest)

- Wrong profile-plane helper: `_ab` used y_dir (0,0,1) instead of (0,1,0);
  parts landed rotated. Fixed, rebuilt.
- False home-pose collisions: checks loaded vendor STLs from arm2b/out
  (old poses) instead of wrist2/out; loader now prefers OUT. Real
  intersections after that: zero.
- Real J6↔g case overlap 653 mm3: adopted D5's interleave — g case body
  sits behind the J6 horn plate, its plug threads under/behind the plate.
  J6 moved back to a 53.0, g to a 107.0, grip train +5.6 (A_SH) — residual
  overlap 0.
- J6 roll clip ±20° → g plug + plate swept J5: plate outline clipped to a
  polygon inside the roll envelope; grip-frame back wall moved a 70..73.5.
  Final J6 sweep free ±180°.
- J5 yaw clip: fin tail/cage front violated the swept-plug-tube rule;
  profiles re-drawn inside the sweep clearance (envelope_check verified
  every gap before committing).
- TCP grew to 137.4 (+5.6 vs the 131.8 target) after the interleave fix —
  accepted: J2→TCP 380.5 stays inside 375 ± 10.
- `out_asm/` (10.6 MB stl / 34.1 MB step, 175 solids) and `renders/_tmp/`
  kept local only — not committed (generated).
- Wall-probe hits in voids/windows re-targeted to solid points; all 11
  probes now read real material.

## [U] unverified

- PETG-CF cross-layer strength 25 MPa (no coupon data).
- 0.6 printed/solid mass factor (ap2 convention).
- STS3215 rated 0.98 N·m [U] (ap2b tag); vendor dims from existing models.
- M3 pilot grip in PETG-CF; support spans in PRINT_LIST — slicer check.
- Cable cleat/tunnel sizes set from plug dims, not real wires.
- J2 cap 3.0 N·m is the printed cyclo-disc limit — the FAIL above is a
  load-capacity limit, not a geometry defect; needs payload or pose
  management in software (already enforced) or a future J2 disc redesign
  (out of scope: stage says do not touch J2).

## Artifacts

`wrist2/out/` — 13 parts STL+STEP posed home (4 structural + vendor
proxies + racks/gear/fingers at the D6 train). `wrist2/out_asm/` — full
assembly STL+STEP (local). `wrist2/renders/` — before/after/asm sets +
before_after composites. Code: `ap6.py`, `p_wrist6.py`, `build_wrist6.py`,
`wrist2_checks.py` (all wrist checks pass; J2 cap FAIL documented),
`layout_probe.py`, `envelope_check.py`, `export_wrist2_asm.py`,
`render_blend.py` (verbatim), `lists_{before,after}.txt`,
`patches/robot-os-d6-wrist2.patch` + README.
