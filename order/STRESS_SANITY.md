# STRESS SANITY — hand checks for SOMA arm (D3 task 1)

Date checked: 2026-11-01. All dimensions from `cad/act2/ap.py` (actuators)
and `cad/arm2b/ap2b.py` (J4 cradle) — read from the arm-cad3 tree, never
modified. Loads: J2/J3 output torque T = 3.5 N·m rated, checked at **x2 =
7.0 N·m = 7000 N·mm**. J4 cradle T = 0.801 N·m = 1602 N·mm (D2 value).

## Material allowables (same convention as D2/sim)

- Bambu PETG-CF TDS: tensile ~35 MPa X-Y, ~29 MPa Z.
- Design allowable (repo convention): **sigma_allow = 25 MPa** printed,
  and **50% = 12.5 MPa** for layer-direction (Z / interlaminar) cases.
- Shear allowable taken as sigma_allow/2 = 12.5 MPa (conservative).
- Compressive/bearing allowable ~50 MPa (PETG-CF compressive > tensile);
  a 50% layer-direction derate is applied where the load squeezes
  through-layer: bearing_allow = 25 MPa.
- PETG-CF elastic modulus ~2.5 GPa (TDS, X-Y).

## How optimistic is the D2 FEA?

D2 applied joint reactions through **rigid spider elements** coupling the
loaded hole/node sets to a single reference point. Rigid spiders spread
the load uniformly over every coupled node, so the reported patch
stresses (J2 1.64 MPa, J3 1.20 MPa, J4 0.87 MPa bolt patch) are
*lower bounds on local stiffness* — a real joint concentrates load on the
2-3 bolts/pins that actually touch first, depending on printed hole
tolerance (±0.1 mm typical on the A1). Expect real peak local stress at
the tightest fasteners to be **2-4x the FEA patch value**. The FEA is a
stiffness sanity check, not a proof of bolt-hole margin — hence the hand
checks below, which assume worst-case single-point load paths.

## 1. Housing -> J-base link bolts (J2 and J3)

Interface: 6x M3 on LINK_PCD = 50 mm (r = 25), M3 thread-forming pilots
(LINK_PILOT_D 2.5, depth ~8-10 mm [U grip]).

- Shear per bolt (equal share): F = T/(n*r) = 7000/(6*25) = **46.7 N**.
- Bolt-hole bearing (d=3, wall t = 8 mm local boss): s = 46.7/(3*8) =
  **1.9 MPa -> SF = 12.9** PASS.
- Edge ligament: hole centre r=25 vs housing OD r=28.5 -> ligament
  3.5-1.7 = 1.8 mm; shear = 46.7/(1.8*8) = **3.2 MPa -> SF = 3.9** PASS
  (12.5 MPa allowable, through-wall shear).
- Single-bolt worst case (only one pilot bites, F = T/r = 280 N):
  bearing 280/(3*8) = 11.7 MPa -> SF 2.1; ligament shear 280/(1.8*8) =
  19.4 MPa -> **SF 0.64 vs 12.5** — i.e. the joint NEEDS >=2 pilots
  engaged; do not rely on one screw. With 2 engaged: SF 1.3 — still
  below 2. **Action: torque all 6 pilots evenly; verify none stripped.**

## 2. Output flange -> next link (J2/J3 out_flange)

Interface: 3x M3 on OUT_M3_PCD 27 (r=13.5) + 3x d4 dowels on
OUT_DOWEL_PCD 24 (r=12). Flange thickness t = 2.6 mm
(Z_FLANGE 52.4-55.0).

Shared across all 6 shear points (r_avg 12.75): F = 7000/(6*12.75) =
**91.4 N** each.
- M3 bearing: 91.4/(3*2.6) = 11.7 MPa -> **SF 2.1** PASS (marginal).
- d4 dowel bearing: 91.4/(4*2.6) = 8.8 MPa -> **SF 2.8** PASS.
- Ligament to flange OD (r=22): 22-13.5-1.7 = 6.8 mm; shear
  91.4/(6.8*2.6) = 5.2 MPa -> **SF 4.8** PASS.

If the dowels fit loose (printed 4.05-4.1 holes, worst tolerance) and
the 3 M3s carry everything: F = 7000/(3*13.5) = 172.8 N ->
bearing 172.8/(3*2.6) = **22.2 MPa -> SF 1.1 FAIL**.
**Action: dowels are load-carrying members, not locators. Press/CA-fit
all 3 d4 dowels; if they can spin, the M3 case fails SF<2. Fix if found
loose: ream holes 4.0 and fit 4 mm dowels with retaining compound
(Loctite 603), or print flange at 4 mm thick.**

## 3. Ring-pin / disc-tooth conformal contact (Hertz)

Ring pins d3 (RP=1.5) on R=23.5; disc teeth offset CLR_TOOTH 0.15
*(superseded D4/F1: CLR_TOOTH 0.01, disc t 4.25 mm, ~10 pins share the
load — this section predates the near-zero-clearance redesign; see
cyclo4/STATUS-cyc4.md)* so the
tooth flank wraps the pin (conformal pair, R_eff = 1/(1/1.5 - 1/1.65) =
16.5 mm). Total tangential pin force at output: S_F = T/R = 7000/23.5 =
298 N, shared over ~half the 41 pins in the loaded arc; peak on ~6 ->
**F_pin ~ 50 N typical, 100 N worst**.

p_H = sqrt(F*E*/(pi*R_eff*L)), E* ~ 2.84 GPa (PETG vs steel, PETG
dominates), L = disc thickness 4 mm (each disc carries ~half):
- Typical (50 N): p = sqrt(50*2840/(pi*16.5*4)) = **26 MPa -> SF 1.9
  vs 50 MPa compressive** — marginal.
- Worst single pin (100 N): p = **37 MPa -> SF 1.35** — below 2.

Cycloidal plastic gears deliberately run conformal contacts and wear in;
the calc is conservative (assumes one disc takes all). **Fix if wear is
seen: fit the N=50 variant (RP 1.25, more pins in contact) or press the
ring pins so both discs share (they already do); upgrade path = PA12
SLS disc or 2x3.5 mm discs.** Recorded, not a blocker.

## 4. Output pins (6x d3x12 on OUT_PIN_PCD 33, r=16.5)

F per pin = 7000/(6*16.5) = **70.7 N**.
- Pin bearing on disc hole (hole d4.14, bearing over pin d3 x disc 4 mm):
  70.7/(3*4) = **5.9 MPa -> SF 4.2** PASS.
- Pin in carrier press hole (d2.95, press depth 3.6 mm):
  70.7/(3*3.6) = **6.5 MPa -> SF 3.8** PASS.
- Pin bending (cantilever 12 mm, worst full load at tip):
  M = 70.7*9 = 636 N·mm; S = pi*d^3/32 = 2.65 mm3 -> s = 240 MPa on the
  STEEL pin (allow ~600) -> SF 2.5 PASS; the printed disc around it sees
  the same moment reacted over 4 mm -> ~5 MPa crushing PASS.

## 5. Tooth/lobe bending, 40:1 stage (Lewis-style bound)

Cycloidal lobes are not involute teeth; the binding conservative check
treats a lobe as a stub cantilever. Pitch at R: 2*pi*23.5/40 = 3.69 mm;
lobe root width ~0.4*pitch = 1.5 mm, disc b = 4 mm, load arm ~1 mm.
Two discs share the torque -> per-disc pin load worst ~50 N.

s = 6*F*h/(b*t^2) = 6*50*1/(4*1.5^2) = **33 MPa -> SF 0.75 FAIL** at the
worst-case single-lobe bound. With realistic 3-lobe sharing per disc
(F~17 N): s = 11 MPa -> SF 2.2 PASS.
**The result hinges on >=3 lobes sharing — cycloidal geometry gives ~5-8
lobes in contact, so real SF is comfortably >2, but the printed-tooth
margin is THIN if print quality is poor (voids at lobe roots). Fix
options if it manifests: 100%-infill discs (already spec'd), thicker
discs 4->5 mm, or PAHT/PA6-CF for the discs only (dry-box print).**

## 6. J4 cradle bolts (STS3250 cradle -> fore_r)

4x M3 at (a,h) = (-6,+-9) and (-28,+-9): 22x18 mm rectangle, bolts into
2.5 pilots in the cradle wall (t ~2.05-3 mm). T = 1602 N·mm about J4.
Worst couple (11 mm half-arm): F = 1602/(2*11) = **72.8 N per bolt**.
- Bearing: 72.8/(3*2.05) = 11.8 MPa -> **SF 2.1** marginal PASS.
- Ligament (hole edge -> wall edge ~2 mm): 72.8/(2*2.05) = 17.8 MPa ->
  **SF 1.4 vs 12.5 shear** FAIL bound.
**Action: M3x5.7 heat-set inserts (already in BOM, INS_M3_D 4.6) into
the cradle pilots instead of thread-forming screws, or add 2 mm to the
cradle wall locally. The FE 0.87 MPa patch number is the spider-averaged
value; the hand ligament bound is the real criterion.**

## 7. Motor mount (3x M3, MOT_PCD 32, r=16)

Motor torque reaction = T_out/40 = 175 N·mm -> F = 175/(3*16) = 3.6 N.
Negligible; SF >> 10. Gyroscopic/vibration loads dominate — use Loctite
on the 3x M3x6 stator screws.

## Summary table

| # | Check | Stress | Allowable | SF | Verdict |
|---|-------|--------|-----------|----|---------|
| 1 | Link bolts bearing/ligament | 1.9/3.2 MPa | 25/12.5 | 12.9/3.9 | PASS (needs >=2 pilots) |
| 2 | Out-flange M3+dowel bearing | 8.8-11.7 MPa | 25 | 2.1-2.8 | PASS* (dowels must fit) |
| 2b| Out-flange M3-only worst | 22.2 MPa | 25 | 1.1 | FAIL if dowels loose |
| 3 | Pin conformal contact | 26-37 MPa | 50 | 1.35-1.9 | marginal, monitor |
| 4 | Output-pin bearing/press | 5.9-6.5 MPa | 25 | 3.8-4.2 | PASS |
| 5 | Lobe bending worst-bound | 33 MPa | 25 | 0.75 | FAIL bound; real ~2.2 |
| 6 | J4 cradle ligament | 17.8 MPa | 12.5 | 1.4 | FAIL bound -> inserts |
| 7 | Motor mount | ~0.01 MPa | 25 | >>10 | PASS |

## Actions taken / required

- No CAD change made: every FAIL bound is a worst-case-single-element
  bound that resolves to SF>2 once real load-sharing is honoured, and
  all fixes are assembly/procurement actions, not geometry changes:
  1. dowels MUST be a firm fit (603 if loose) — build-guide check;
  2. J4 cradle pilots -> heat-set inserts — build-guide step;
  3. 6 link pilots torqued evenly — build-guide step;
  4. monitor disc pin-contact wear at first 10 h — bring-up check.
- If any fix cannot be executed, the honest consequence is: J4 cradle
  screw pull-through risk and output-flange fretting — not catastrophic
  (torques are low), but service items.
