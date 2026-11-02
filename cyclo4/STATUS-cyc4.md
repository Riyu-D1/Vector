# STATUS — cyclo4 (stage D4, PETG-CF printed redesign)

Branch `arm-cyc4`, worktree `~/Vector-wt/cyc4`, base `arm-ver` @ 82df20f.
All work in `cyclo4/` on a copy of `cad/act2`; no product files changed.

## Design basis (revised brief)

Printed PETG-CF discs only; ISO 8734 steel dowel ring pins stay (already in
BOM). No metal discs, no other filament, no bought gearhead.
Design torque = worst-case STATIC torque at 0.5 kg payload, full reach
(`upgrade1/gravity_up1.py`, pose `Q_WORST = [0, +70, -70, 0, 0, 0] deg`):

| joint | static max (swept) | design T used |
|-------|--------------------|---------------|
| J2    | 2.616 N·m          | 2.70 N·m      |
| J3    | 1.837 N·m          | 1.85 N·m      |

Requirement: lobe contact SF >= 2 on that static design torque. No x2 dynamic
factor, no slam-shock case. Firmware output-torque cap + soft E-stop ramp
enforce the envelope (see below). If SF 2 were unreachable, report max safe
torque/payload instead — it was reachable (nominally), see Tolerance risk.

## Load model — `load_model.py`

Blanche/Yang-style load distribution on the REAL profile (40 000-pt
`cyc.disc_outline`, pin-vs-flank gap field over a crank rev, Hertz contact
stiffness per pin, iterates disc rigid-body shift until moment = applied T).
Out-pin bearing uses the correct kinematics: carrier rotates with the disc,
so hole clearance is uniform = CLR_OUT.

Validation (`load_model.validate()`):
- clr=0: 20/41 pins engaged ≈ half — matches published ideal-drive theory
  (Blanche & Yang 1989; Qi et al., Alexandria Eng J 91 (2024) 403-418;
  Coatings 13 (2023) 2029 isogeometric FEA).
- clr=0.15 (old build): engagement collapses to 2 pins — matches the
  published clearance sensitivity (Li Xin Xu 2019, doi 10.1177/0954406218809732).
- Linear-stiffness solver vs Hertz solver at matched K: ratio 1.00.

## Result (n_theta = 65)

| | J2 @ 2.70 N·m | J3 @ 1.85 N·m |
|---|---|---|
| engaged pins/disc | 10–11 of 41 | 9–10 of 41 |
| Fmax/disc | 13 N | 10 N |
| flank rho | -2.9 mm | -2.9 mm |
| p0 (Hertz) | 38 MPa | 33 MPa |
| equiv. stress (0.6 p0) | 23 MPa | 20 MPa |
| allowable [U] | 50 MPa | 50 MPa |
| **SF** | **2.21 OK** | **2.56 OK** |
| out-pin bearing p | 6.4 MPa (SF 7.8) | 4.4 MPa (SF 11.4) |
| lobe root bending [U] | ~5 MPa | ~4 MPa |

Before (this brief's loads, old geometry 2x4.0 / clr 0.15): SF 0.92 / 1.01.

## The pick

**40:1 geometry unchanged** (N40/NP41, R23.5, RP1.5, E0.42 — Ø3 ISO 8734
dowels stay). Two changes only:

- `CLR_TOOTH 0.15 -> 0.01` — near-zero flank offset. Pins engage the flat,
  near-conjugate flank region instead of 2 pins on lobe tips; engagement
  jumps 2-3 -> 10-11 pins. THIS is the whole redesign; clearance dominates
  every other lever.
- Disc thickness `4.0 -> 4.25 mm` — fills the free axial gap; disc2 top
  (42.30) stays under the carrier plate (42.4). No structural change.
- `CLR_OUT = 0.12` — separate out-pin hole clearance; the disc's orbit
  needs this and must NOT follow CLR_TOOTH down (would bind).

Swept and rejected: N50/N45 (worse SF at same geometry), RP=1.6 (+0.1 SF but
needs Ø3.2 dowels — marginal stock), E=0.50 (outside solver validity),
3-disc stack (no axial room), thicker discs alone (insufficient at normal
clearance), gearhead/metal/other filament (out of brief).

## Cross-check — `fea_contact.py` (2D plane-stress ccx)

gmsh T6 mesh (868 nodes) of the REAL flank arc + Ø3 pin at the analytical
peak contact (disc1, pin 7, crank 28.8 deg), hard node-to-surface contact,
pin driven down 0.014 mm in 56 increments. Result: F(delta) starts at
delta = gap = 0.010 mm (matches CLR_TOOTH), at F* = 12.9 N/disc
pmax = **15.0 MPa** vs analytical Hertz 37 MPa. FEA is ~2.5x LOWER — the
conforming contact spreads wider than the single-curvature Hertz model
assumes, i.e. the analytic number is conservative. Both are far under the
50 MPa allowable. Caveats: coarse 868-node mesh, frictionless, plane-stress,
no lobe root check — it is a cross-check of p0 only, as staged.

## Max safe torque / payload

Bisected at SF = 2.0 (n_theta=25): J2 3.65 N·m, J3 3.64 N·m.
`gravity_up1.max_payload` under the proposed caps (J2 3.0, J3 2.0 N·m):
**0.59 kg** (J3-limited) — meets the 0.5 kg target with ~18% headroom.

## Firmware enforcement (needed, not yet applied — spec for follow-up)

Current `firmware/base-node/src/config.h` has `PHASE_CURRENT_LIMIT_A = {5.0,
5.0}` (spec 5 A, "conservative until bench test"). 5 A x Kt 0.0289 x 40 x
eta 0.7 = 4.05 N·m — above the SF-2 envelope.
Required caps: **J2 = 3.0 N·m (~3.7 A), J3 = 2.0 N·m (~2.5 A)**
(output torque = I_phase x Kt x ratio x eta). Plus a soft E-stop ramp:
on watchdog/estop, ramp phase current to 0 over ~50-100 ms rather than
step-off, to avoid an inertial torque spike through the discs.
This is a one-line config change in an existing product file — left for the
arm firmware owner, flagged in BOM_delta.md.

## Tolerance risk — stated plainly

`CLR_TOOTH = 0.01` nominal is far inside FDM scatter (±0.05-0.10 mm). The
model predicts SF 2.2 only because MORE pins share the load as clearance
approaches zero; per-unit SF will scatter roughly 1.0-2.2 depending on the
as-printed effective clearance. Mitigations:
- print profile is offset so positive scatter lands as slight interference
  -> self-corrects by run-in (greased, hand-cycled before loading);
- selective pin fit: 41 dowels, try-assemble, swap any tight quadrant;
- the torque caps bound worst-case even if a unit runs looser/tighter.
Residual risk is real: a unit that lands at effective 0.05+ clearance is
back near SF ~1.1-1.5 and must not be run at design torque. This design is
a run-in/selective-fit design, not a print-and-ship one. Bench-verify
backlash + a loaded run-in on the first unit before J2/J3 go under load.

## CAD verification

- `cyc.py` gates: **CYC PASS** (K1 0.733, rho_min 1.931 > RP+clr, pin gap
  0.598, mesh clearance ~0.004-0.005 mm — the designed conjugate mesh; gate
  thresholds scaled with CLR_TOOTH).
- `act_checks.py`: **ACT PASS** — all parts watertight, L = 55.00 mm,
  OD = 57.00 mm.
- repo `gate.py` (STL pairwise interference, cad/knuckle): **GATE PASS** —
  all 19 parts watertight, min wall OK, no interfering pairs.
- DXF reference drawings regenerated: `dxf/disc1.dxf`, `dxf/disc2.dxf`,
  `dxf/output_pin_plate.dxf` (optional — discs are printed, not cut).

## Still unverified

PETG-CF E=4 GPa / allow 50 MPa are [U] along-layer literature numbers;
wear/fretting at 10-11 simultaneous contacts under grease; real printed
clearance distribution and run-in rate; out-pin hole tolerance at 0.12;
firmware cap change and soft-ramp not yet implemented; no physical test.
