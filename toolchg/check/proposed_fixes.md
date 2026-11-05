# D11 proposed fixes — NOT APPLIED (audit-only stage)

Each entry: severity, evidence, exact file:line patch. Product files are
untouched by design. Refs are to `origin/arm-toolchg` @ 7003ea8.

---

## F1 — blocks-dock · key notch cuts the wrong direction (0.05 mm, not 1.5 mm)

`toolchg/p_toolchg.py:167-168` in `tc_plate()`:

```python
s = s - box(g0 + 0.25, g1 - 0.25, -kw, kw,
            T.H_AX - T.TC_DOCK_R - T.TC_KEY_D, T.H_AX - T.TC_DOCK_R + 0.05)
```

The box spans h ∈ [H_AX − DOCK_R − 1.5, H_AX − DOCK_R + 0.05]. At phase
270 the groove floor sits at h = H_AX − DOCK_R, so this removes **1.5 mm
of empty space below the floor** and only **0.05 mm of plate material**.
The intended pocket (into the plate, toward the axis) is in the +h
direction, not −h.

Evidence: C5 measured `8.40 mm3` docked-tool × rack interference (≈ the
RACK_KEY tab volume 2.5 × ~4.2 × 1.35); wall probe at groove floor ph270
= 1.75 mm vs 1.80 nominal (the 0.05 nick); `RACK_KEY = (2.5, 1.4)` tab
protrudes 1.4 mm into a groove whose notch is 0.05 mm deep → the tool is
propped ~1.35 mm off the seat on first real dock.

Proposed patch (`toolchg/p_toolchg.py`):

```python
s = s - box(g0 + 0.25, g1 - 0.25, -kw, kw,
            T.H_AX - T.TC_DOCK_R - 0.5, T.H_AX - T.TC_DOCK_R + T.TC_KEY_D)
```

(cut from 0.5 mm below the floor for a clean Boolean up to KEY_D = 1.5 mm
into the plate — gives the 1.4 mm tab 0.1 mm axial clearance).

Companion check fix — `toolchg/tc_checks.py:111` gate `v < 40.0` is far
too loose to notice an un-engaged key (it passed 8.4 mm³). Propose
`v < 0.5` plus an explicit key-tab probe, e.g. intersect the RACK_KEY tab
box against `tc_plate()` and require ~0 mm³, and a separate positive
check that the notch void exists at TC_KEY_PH.

## F2 — blocks-adopt · catch tip below 1.8 mm min wall; single-catch fault SF<2

`toolchg/p_toolchg.py:143-155` `_catch()` profile
`(a0,18.6) → (a0+2.2,13.2) → (a1,13.2) → (a1,18.6)` puts a 2.2 mm-long
ramp under the catch; the resulting wall at r13.5 measures **1.14 mm**
(radial BRep probe), 1.75 mm at r15 — under the stated `TC_WALL_MIN = 1.8`.
This is the lug-bearing capture member.

Structural evidence (D11 added FEM, `check/fea/plate_1catch.*`): the
whole 0.5 kg+tool wrench on ONE catch's +a face (single-lug fault /
pre-seated transient) gives raw maxVM **32.0 MPa** > 25 MPa cross-layer
`[U]` and filtered **16.85 MPa** → SF 1.48 < 2. Hotspot @
(71.2, −11.2, −10.0) = a 71.2, r≈13.2 — the thin tip itself. Nominal
3-catch loading gives 0.60 MPa (SF ~42), so margin relies entirely on
symmetric engagement.

Proposed patch: shorten the ramp so the tip reaches full thickness
sooner — `a0 + 2.2` → `a0 + 1.2` at line 152:

```python
prof = pl * Polygon((a0, T.TC_RING_RIN + 0.4),
                    (a0 + 1.2, T.TC_CATCH_R),
                    (a1, T.TC_CATCH_R), (a1, T.TC_RING_RIN + 0.4),
                    align=None)
```

At r13.5 the wall then measures ~2.1 mm. Trade-off: the −a lead ramp
steepens 22°→~12.5° (still printable −a down, still a print ramp). If the
ramp length must stay for print reasons, alternative: keep the polygon
but extend `TC_CATCH_A[1]` 72.2→73.3 and move `TC_GROOVE_A[0]`/`TC_LUG_A[0]`
to keep the 0.2 mm running clearance — bigger coordinate change, not
preferred.

For the fault-case margin: after the wall fix re-run
`check/fea/run_checkfea.py extra` — if SF is still <2 the alternatives
are deeper catches (`TC_CATCH_R` smaller = more overlap on the lug,
re-check C1 clearance), a wider catch arc (`TC_CATCH_ARC` 60→70, eats
the entry gap — re-check C1), or a bench-verified precondition that the
detent always seats all three lugs before payload.

## F3 — blocks-adopt · notch pocket leaves only 0.3 mm over the socket bore

Same defect family as F1: after F1's correct 1.5 mm pocket the material
under the pocket floor is `DOCK_R − RIN − KEY_D = 20.0 − 18.2 − 1.5 =
0.3 mm` — far under the 1.8 mm min wall, and the nominal groove-floor
wall itself is `20.0 − 18.2 = 1.8 mm` exactly at the limit (measured
1.75–1.82). The param set as written cannot satisfy both "notch depth
1.5" and "ring wall ≥1.8 under the groove".

Proposed patch (`toolchg/tc_params.py`):
`TC_DOCK_R = 20.0` → `20.6` and `TC_KEY_D 1.5` → `1.2` — keeps
`20.6 − 18.2 = 2.4 mm` wall under the groove, `2.4 − 1.2 = 1.2 mm` under
the notch, and `20.6 − 1.2 = 19.4 ≥ 18.2 + 1.2` clears the bore.
Alternatively raise `TC_RING_ROUT 23.0→23.5` (+0.5 mm on the OD, heavier).
Either must be re-checked against the rack fork seat radius.

## F4 — blocks-build · BOM detent ball Ø5 cannot enter the Ø4.2 bore

`toolchg/STATUS-toolchg.md:181` — "Steel ball Ø5 + compression spring
~Ø4×8 + M3 grub". But `TC_DET_D = 4.2` (tc_params.py:87, commented "M4
spring plunger") and `TC_DIMPLE_D = 3.0` (line 92, "~3mm plunger ball").
A Ø5 ball is larger than the Ø4.2 bore; a Ø4 spring is 0.1 mm from the
bore wall.

Proposed patch (STATUS BOM row):
"Steel ball **Ø4** + compression spring **~Ø3.2×8** + **M4** grub/plunger
— or one commercial M4 ball plunger" — ball Ø4 fits Ø4.2 (0.1/side), and
Ø4 ball into Ø3.0 dimple gives ~0.5 mm engagement (consistent with
TC_DET_PR = 1.0 "ball tip reaches r17.2" vs lug OD 17.3).

## F5 — minor · BOM lists 2 × Ø3×10 dowels; no dowel holes exist

`toolchg/STATUS-toolchg.md:183`. `tc_plate()` has ring+floor, catches,
groove, notch, detent bore, pogo bores — no Ø3 keying bores anywhere;
the plate is fused to the tool body (`tool_grip() = tc_plate() + _neck()
+ ...`). Stale BOM entry (concept-B residue).

Proposed patch: delete the row, or mark "unused — plate fused to body".

## F6 — minor · pen set-screw Ø3.0 bore vs "M3 insert" wording

`toolchg/tc_params.py:144` `PEN_SET_D = 3.0` "M3 set-screw insert";
`p_toolchg.py:246` radial Ø3.0 bores. Ø3.0 suits an M3 grub
**self-tapping into PETG** but is far undersize for an M3 heat-set insert
(OD ~4.2–4.6). Proposed patch: rename comment to "M3 set screw,
self-tap pilot Ø3.0" — or `PEN_SET_D → 4.3` if a real insert is intended.

## F7 — minor · STATUS claims needing number corrections

- `STATUS-toolchg.md:82` "~1 mm³ detached slivers" → measured
  **10.80 + 33.79 = 44.6 mm³** on `tool_grip` (inherited from
  `w_grip_frame` STL, measured 10.80 + 33.66 there — inheritance
  confirmed; the "~1 mm³" figure is off by ~45×).
- `STATUS-toolchg.md:78` "≤45° overhangs are designed-in" — measured
  suspended flat-down area (stated print orientations): tc_plate
  **2865 mm²** (incl. ~1040 mm² socket-floor ceiling inside the bore),
  tc_master **403 mm²** (lug −a bearing faces + detent ceiling),
  tool_pen 2892, tool_grip 2825, tc_vendor_g 1840 mm²; tc_rack 0 mm².
  These print with support; the master lug faces printing on support is
  a surface-quality risk on the capture path — worth a bench note.
- `toolchg/tc_checks.py:111` C5 gate 40.0 mm³ (see F1 companion).

## F8 — minor · committed arm_tc.xml drifts from sources

`toolchg/mjcf_tc/arm_tc.xml` `g_tc_master` mass="0.0054" vs 0.0056 on a
fresh `build_tc.py` run — the committed scene predates the final master
mass. Proposed patch: re-run `build_tc.py` and commit the regenerated
xml (or drop generated xmls from the repo entirely).

## F9 — blocks-adopt (inherited) · tool_grip body peaks 28.7 MPa > 25 [U] at clevis pin bore

D11 added FEM (`check/fea/tool_grip.*`, 125393 n / 70160 C3D10): NFIX =
3 catch faces + socket-floor face, NLOAD a≥120 with the 0.5 kg+tool
wrench at TCP. Filtered maxVM **28.73 MPa** at (110, ±12.5, −52) — the
clevis/bracket pin-bore edge — SF 0.87 < 2; max|U| 7.95 mm at the rail
tip. The section is inherited verbatim from `w_grip_frame` (wrist2
checked only the spine-rib junction at 11.9 MPa — this bore was never
gated), so the same margin exists on the shipped stock grip.

Proposed patch (design-side, not this stage): bore-edge relief —
`BR_HOLE` region gets a +0.6 mm boss ring or the bore Ø drops to match a
real pin + bush; alternatively state the material assumption honestly
(printed along-layer at the bracket vs cross-layer) and bench-verify.
Until resolved, cap the grip-tool rated payload below 0.5 kg or keep the
[U] 25 MPa assumption flagged as load-limiting for BOTH the stock and
tool grippers. Also note the ~8 mm tip flex: coupling repeatability
claims (sub-mm) are dwarfed by body compliance — add to the
repeatability bench item.
