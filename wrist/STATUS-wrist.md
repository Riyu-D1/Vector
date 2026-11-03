# wrist/STATUS-wrist.md — D5 wrist + gripper redesign

Stage: `~/Vector/stages/D5_wrist_gripper.md`. Worktree `~/Vector-wt/wrist`,
branch `arm-wrist` from `arm-final` (b7374e1). Everything lives in `wrist/`;
no existing product file was edited.

## What changed

The 4 structural wrist/gripper parts are redrawn as thin (~2 mm wall)
contoured shells hugging the servo cases — SO-101-style clamshell translated
to our hidden-screw language (see `wrist/RESEARCH.md`):

| Part | before | after | vol cm3 | before cm3 | delta |
|---|---|---|---|---|---|
| w_j4_cradle | box cradle 38×52.5×30 | rounded-rect sleeve + bolt plate on 4 pillars | 17.0 | 28.7 | −40.8% |
| w_link4 | block + strut 66.6×60.6×69 | horn plate + silhouette spine rib + open-mouth J5 ring cage | 16.9 | 29.8 | −43.3% |
| w_link5 | solid box 38.1×30×34.6 | horn plate + full-wrap J6 cage w/ cheek windows | 9.9 | 11.2 | −11.6% |
| w_grip_frame | slab walls + plate 56.4×64×52.4 | J6 horn plate + sculpted cheeks + open top, same rack cage | 19.3 | 20.9 | −7.7% |

Structural total 63.1 cm3 (≈80 g solid-equiv, ≈48 g at 0.6 infill) vs
90.6 cm3 (≈118 g, ≈71 g) before → **−30%** on the redesigned parts;
wrist+gripper printed total incl. unchanged racks/fingers ≈72 vs 98 cm3
(−26%). Mass constraint (≤ current, ideally lighter): **met**.

Interfaces preserved exactly: same horn faces, bolt pattern, joint axes,
servo pockets (same `pocket()` voids), rack/gear/finger solids, TCP.
No axis moved → kinematics + `software/robot-os` config untouched.
Vendor parts: none added, none removed → **BOM delta £0.00**.

## Task 1 — before measurements (arm2b out/, solid-equiv rho 1.27)

j4_cradle 28.7 cm3 (38 g) · link4 29.8 (39) · link5 11.2 (15) ·
grip_frame 20.9 (27) · racks 2×2.4 · fingers 2×1.3 → 97.8 cm3, ~128 g
solid-equiv (~77 g at 0.6). Before close-ups: `renders/before_*.png`.

## Task 4 — check results (`wrist/wrist_checks.py`, CHECKS PASS)

- REACH: J4→J5 37.60, J4→TCP 131.80, J2→TCP 374.9 — identical to A2b.
- HOLE: 4×d3.4 horn PCD14 on all 3 horn plates; measured centres err 0.000;
  fore_r2 M3 clearances + cradle d2.5 pilots on the same centres.
- CLEAR: 0.00 mm3 intersection, each new part vs its servo case (pocket clr).
- GRIP: racks stay in the 64 mm channels + engaged on the gear at full
  25 mm open; no hits.
- ROM (posed-mesh sweeps): home pose clean; J4 −70..+80° (150°, need 140);
  J5 −80..+80° (160°, need 140); J6 ±180° (360° free); J3/J2 sweeps pass.
- WALL: 8 probes across all 4 parts read 1.85–2.05 mm (design 2.0, min 1.8).
- TORQUE: J4 0.473 N·m at the modelled 0.25 kg payload (scales to ≈0.80 at
  the stage's 0.5 kg — consistent with the stage's 0.801 figure);
  J5 0.295; J2 2.31 (<3.50); J3 1.13 (<2.25); wrist+gripper 0.234 kg.
- CABLE: plug-channel probe points empty on all 4 parts.
- OVERHANG scan (per-part print orientation): flat ceilings exist —
  cradle +b rim, link4 window/tunnel ledges + horn counterbores,
  link5 window top edges, grip channel roof — listed as support in
  `PRINT_LIST-wrist.md` [U]; same class of support the old parts needed.

## Stress hand calc — J4, M = 0.801 N·m (stage worst case, 0.5 kg payload)

- Worst section: `w_link4` spine-rib / horn-plate junction carrying the
  downstream wrist+gripper+payload as a bending moment about the J4 b-axis.
  Conservative single-section model: rib 4.0 mm × ~14 mm effective height →
  S ≈ 4·14²/6 ≈ 131 mm³ → σ ≈ 801/131 ≈ **6.1 MPa** vs 25 MPa cross-layer
  [U] → **SF ≈ 4 ≥ 2**.
- Cradle bolt group: couple across Δa = 22 mm → ~18 N shear per M3 bolt —
  negligible vs M3 capacity.
- Cradle pillars Ø8: ~0.4 MPa compression — negligible.
- No FEM run; hand calc only. Cross-layer 25 MPa is [U] (PETG-CF, no coupon
  data); printed orientation of the rib layers is along the bend direction.

## Cable routing (4 servo TTL cables)

- J4: plug exits up through the sleeve slot; guide groove on the +h face
  leads it toward −a to the forearm.
- J5: plug exits −b through the link4 back-panel tunnel; 2 cable-tie
  cleats on the −a wall.
- J6: plug exits through the −a end-cap slot; 2 cleats on the −a face.
- Gripper: plug region open via the cheek cage; cleat on the −b cheek.
All four channels verified empty by probes; cleats/groove are printed
features (reBot restraint idea). [U] real-wire bend radii not verified.

## Render notes (iteration log: before set, after v1, full-asm, after v2, side-by-side)

- `after_frontiso`: shells hug each servo; orange case faces show through
  windows + the open-top grip cheeks; rack cage unchanged.
- `after_backiso`: cradle pillars + bolt plate behind the sleeve; J5 tub
  open side; horn-plate face clean.
- `after_side`: silhouette ~unchanged vs before (interfaces preserved),
  air where the slabs were; J4 plug visible above the sleeve — expected.
- `after_top`: plan outline narrower around J4; pillar gap + plate visible.
- `after_front`: gripper end-on — rounded bracket, rails/lips intact,
  fingers + gear aligned.
- `after_cutaway`: all four cases seated in ~2 mm pockets w/ clearance;
  plug tunnels open; wall runs read ~2 mm.
- `asm_frontiso` / `asm_side`: full arm composition — wrist sits right,
  no visual collisions, transition off the forearm reads smooth.
- Cables not modelled (channels verified by probes only) [U].

## Failures / fallbacks (honest)

- First-draft `p_wrist5.py` had dead code + two wrong sketch planes — the
  whole geometry file was rewritten rather than patched.
- `TypeError: 'bool' object is not callable` — misuse of `is_valid` as a
  method in an early smoke test; property, not a call. No design impact.
- An aggressive 4 mm `fillet` on a polygon failed the kernel — fell back
  to `RectangleRounded` profiles + 45° chamfer cuts (design uses no fillets).
- First build came out heavier than baseline on 2 parts — diagnosed: sleeve
  ran 13.6 mm past the case end (solid slab) and `bh(0,…)` placed the link5
  tube at a=0 so the bore cut missed. Fixed; volumes above.
- Home-pose collision `w_link4 × w_link5` (55 mm³): my tub bottom wall sat
  0.11 mm into link5's horn plate — original leaves that bottom open;
  matched it (wall bottom at h 15.2, B.J5_POCKET_H0).
- J6 sweep collision `vendor_sts3215_g × w_link5` at ±10°: my cage ran 1.9 mm
  past B.L5_FRONT_A into the grip-servo plug sweep — shortened to 60.6.
- `out_asm/` (assembly.stl/.step, 43 MB) and `renders/_tmp/` are kept local
  only — not committed (generated; stage requires only `wrist/out` parts).
- `docs/STATUS-knuckle.md` was NOT appended: the stage scopes all work to
  `wrist/`; this file is the stage status.

## [U] unverified

- PETG-CF cross-layer strength 25 MPa (no coupon data).
- 0.6 printed/solid mass factor (ap2 convention).
- M3×10 thread-forming pilot grip in PETG-CF (ap2b convention).
- Support spans/ledges flagged in PRINT_LIST — slicer check pending.
- STS3215 rated 0.98 N·m [U] (ap2b tag), vendor dims from existing models.
- Cable-tie cleat positions sized for the plugs, not real wires.

## Artifacts

`wrist/out/` — 4 new parts STL+STEP + the unchanged vendor/rack/finger
parts (posed home). `wrist/out_asm/` — full-assembly STL+STEP (local).
`renders/` — before set, after set, asm set, `before_after_{frontiso,side}`.
Code: `ap5.py` (params), `p_wrist5.py` (geometry), `build_wrist.py`,
`wrist_checks.py` (CHECKS PASS), `export_wrist_asm.py`, `render_blend.py`
(verbatim helper), `lists_{before,after}.txt`.
