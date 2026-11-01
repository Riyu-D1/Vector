# STATUS — Stage D1: strengthen J2 & J4 for 0.5 kg payload (design study)

Date: 2026-11-01. Worktree `~/Vector-wt/up1`, branch `arm-up1` (from
`arm-fw2` @96959c6). Everything new lives in `upgrade1/` — no product
files touched. Baseline model: `software/robot-os/soma_arm/gravity.py`.

## Baseline (reproduced, real run)

`max_payload` at the worst in-limit horizontal pose
`q=[0, +70°, −70°, 0,0,0]`:

- **max_payload = 0.3906 kg — J2-limited** (bounds: J2 0.3906, J3 0.517,
  J4 0.487). Matches the stage's quoted 0.391 kg / 0.487 kg.
- Links-only torques: J2 +1.393, J3 +0.541, J4 +0.154 N·m.
- At 0.5 kg: J2 3.194 N·m (114 % of the 80 % derated 2.8), J3 1.759
  (98 %), J4 0.801 (102 % of derated 0.784).

## J4 — options ranked (need 0.801 N·m at 0.5 kg vs 0.784 allowed → short by 0.017)

1. **(a) Feetech STS3250 swap — RECOMMENDED.** Real datasheet
   (feetech.cn ST-3250-C001 rev A/0 2024-01-16, checked 2026-11-01):
   rated **16 kg·cm = 1.569 N·m**, stall 50 kg·cm, 12 V, TTL half-duplex,
   45.22×24.72×35 mm, 74.5 g, 25T spline — the *same* envelope as
   STS3215, so the J4 bracket/yoke take zero geometry change. J4 util at
   0.5 kg → 51 % of rated. UK: eBay UK item 286817716163 ≈ £15.31 +
   ~£4.48 postage (GBP listing, ships from China — flagged [U]); Amazon
   UK B0FLJ6289C £136.15 (checked 2026-11-01); EU ref: Gotronic €68.50.
   Same servo already runs at J1 on this bus.
2. (b) Printed reduction/counterweight/torsion-spring on J4: the 0.017
   N·m gap is tiny but every variant adds an unverified mechanism or
   bracket redesign; rejected — a drop-in part exists.
3. (c) Mass cut downstream of J4: downstream ≈ 0.246 kg; needs ~13 g at
   0.13 m removed — masses are FEA-derived, no verifiable per-component
   cut exists; rejected.

## J2 — options ranked (need ~0.55 N·m relief at the +70° pose; worst-over-q3 3.346 vs 2.8 allowed)

1. **(a) Coaxial torsion balance spring — RECOMMENDED.** k = **0.55
   N·m/rad**, one-way engaged for q2 > 0 → τ_s = 0.55·q2, 0.67 N·m at
   +70°. Computed worst-case J2 curve (0.5 kg, q4 level-tool, q3 swept):
   raw 1.89 @0°, 2.66 @+30°, 3.35 @+70° → net with spring 1.89, 2.38,
   **2.67** — under 2.8 everywhere with −15 % rate tolerance (k=0.45 was
   rejected: only 0.004 N·m margin). UK part: Springmasters metric
   torsion spring ~2.0–2.2 mm wire, OD 22–27 mm, ~5 coils, 70 mm legs —
   parts 471671/471672, ~£4.71 ea at 100-pc break
   (springmasters.com/shop/471671/, checked 2026-11-01); achieved rate
   [U] — shim on bench. Gas-strut alternative (SGS Engineering UK,
   price [U]) is workable but bulkier/visible; printed spiral spring
   (SEA-disc precedent, `cad/lib/sea.py`) creeps under 100 % duty —
   both rejected as primary.
2. (b) Higher current limit vs real Tarot 4008 data — rejected as
   primary: Tarot's "30 A max continuous / 497 W" is a drone prop rating
   at speed, not stall-holding; winding R ≈ 0.145 Ω (xcopterCalc entry)
   → 5 A stall ≈ 3.6 W vs 8 A ≈ 9.3 W — plausible but [U]; the 40:1
   printed cycloidal's tooth rating is also [U]. Cannot justify >3.5
   rated without bench data — recorded for the bench plan.
3. (c) Mass shave on upper arm/elbow actuator: the 0.30 kg lumps are the
   motor+gearbox assemblies (85 g motor + gearbox/ESC/housing, split
   [U]); ~50 g at the elbow saves ~0.11 N·m — short of the ~0.55 needed;
   rejected as primary (still worth doing opportunistically).

## Updated model — `upgrade1/gravity_up1.py` (real output)

Per-joint torque N·m (% of rated) at `q=[0,+70°,−70°,0,0,0]`:

| Payload | J1 | J2 (3.5) | J3 (2.25) | J4 (1.569) | J5 | J6 |
|---|---|---|---|---|---|---|
| 0 kg    | 0.000 (0%) | +0.764 (21.8%) | +0.561 (24.9%) | +0.154 (9.8%) | 0 | 0 |
| 0.25 kg | 0.000 (0%) | +1.664 (47.6%) | +1.170 (52.0%) | +0.478 (30.4%) | 0 | 0 |
| 0.5 kg  | 0.000 (0%) | +2.565 (73.3%) | +1.778 (79.0%) | +0.801 (51.0%) | 0 | 0 |

- **max_payload = 0.5089 kg** (bounds: J2 0.565, J3 0.509, J4 0.851) —
  ≥ 0.5 kg target met; **J3 is now the limiter** (+1.8 % headroom).
- Product test suite still green: `python3 -m pytest tests` → **62
  passed** (unchanged — no product files modified).
- New tests: `python3 -m pytest upgrade1/test_gravity_up1.py -q` →
  **10 passed**.

## [U] table

| Item | Value used | Why unverified / where to confirm |
|---|---|---|
| J2 spring achieved rate | 0.55 ±10 % N·m/rad target | Stock-part rate not published; wind/select + measure on bench (hang masses, fit k) |
| Spring wire/stress margin | 2.0–2.2 mm stainless, ~5 coils | σ ≈ 0.85 GPa at 0.67 N·m on Ø2.0 — near stainless limit; Ø2.2 or music wire if marginal (bench check) |
| STS3250 landed UK price | ~£20 budget | eBay UK GBP listing ships from China (≈£19.8 landed); Amazon UK £136; shop around |
| STS3250 continuous rating in wrist duty | rated 16 kg·cm @12 V | Datasheet "rated torque" — verify against duty/heat on bench like other servos |
| Spring + mandrel mass | 15–25 g est. | Not modelled (sits at J2 axis, ~zero moment arm); weigh on bench |
| Tarot 4008 stall-holding current | 5 A cap kept | 30 A rating is prop duty; stall thermal unproven — bench before raising |
| 40:1 cycloidal tooth rating | 3.5 N·m kept | Printed-gear strength unverified — torque-rig bench test |
| J3 headroom | bound 0.509 kg | Only +1.8 % over target; if more margin wanted: same spring trick at J3 or elbow mass cut |
| Gas strut alternative price | [U] | SGS Engineering (UK) sells configurable struts — get a quote if the torsion spring falls out |

## Open questions for the user

1. J3 margin at 0.5 kg is only +1.8 % — accept, or also treat J3 (spring
   or lighter elbow) in a follow-up?
2. J4 gets a 50 kg·cm stall servo — keep the firmware TORQUE_LIMIT cap
   near the old 30 kg·cm ceiling to protect printed wrist parts?
3. Buy route for STS3250 — cheap eBay import (~£20) vs Amazon UK
   (£136) vs EU (€68.50)?
4. Folded-pose behaviour: spring is one-way (disengaged for q2 ≤ 0) —
   confirm the J2 stop geometry can live inside the current knuckle.
