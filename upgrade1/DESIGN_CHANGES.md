# D1 — Design changes needed (study; NO product files were modified)

Chosen changes, from `gravity_up1.py` (all numbers real — see STATUS-up1.md
for sources and [U] flags):

1. **J4 wrist-pitch servo: STS3215 → Feetech STS3250 (ST-3250-C001)**
   Same case envelope (45.22×24.72×35 mm vs 45.2×24.7×35 mm — +0.02 mm,
   inside TOL.loose 0.3 mm), same 25T/OD5.9 mm spline, same 12 V TTL
   half-duplex bus. Rated 16 kg·cm = **1.569 N·m** (was 0.98). Mass 74.5 g
   (was 55 g, **+19.5 g**, sits on the forearm/stator side).

2. **J2 coaxial torsion balance spring** — one-way engagement for q2 > 0,
   τ_s = 0.55 N·m/rad · q2 → 0.67 N·m assist at the +70° limit pose.
   Candidate stock part: Springmasters (Redditch, UK) metric torsion
   spring, ~2.0–2.2 mm wire / OD 22–27 mm / ~5 active coils / ~70 mm legs
   (e.g. parts 471671, 471672); rate to be shimmed/measured on the bench.

## CAD file changes (by file name — edits NOT made, listed only)

> Note: `cad/` on `arm-fw2` models the earlier all-servo arm (J2=HTD-45H
> servo + SEA cartridge); the shipped J2 is the 40:1 printed cycloidal +
> Tarot 4008. The same change points apply in whichever tree owns the
> current J2 geometry — file names below are the cad/ owners.

| File | Change needed |
|---|---|
| `cad/params.py` | Add `SERVO_3250 = ServoSpec(name="STS3250", body_w=45.22, body_d=24.72, body_h=35.0, mass_g=74.5, stall_kgcm=50.0, bus="TTL", volts=12.0)`; retarget `JOINTS["J4"]` to it. Add a `BALANCE_SPRING` spec block (k=0.55 N·m/rad, wire Ø2.0–2.2, coil OD 22–27, ~5 coils, legs ~70 mm, one-way engage q2≥0). |
| `cad/lib/joint.py` | `make_pitch_joint` J2 instance: add (a) a Ø ~14–15 mm mandrel boss concentric with the joint axis on the bracket (static) cheek — matches stock spring's suggested mandrel (14.8 mm on Springmasters 471671); (b) a fixed-leg anchor slot (~Ø3 mm) in the bracket paddle; (c) a stop pin/slot (~Ø3 mm) on the **yoke** plate that picks up the free leg only when q2>0 (one-way). J4 instance: **no change** — same envelope, same spline; regenerate only. |
| `cad/lib/wrist.py` | No geometry change (STS3250 fits the J4 bracket pocket and J5 pod unchanged). Regenerate to confirm. |
| `cad/lib/links.py` | None — spring legs anchor on the J2 joint parts, not the link. |
| `cad/lib/base.py` | None. |
| `cad/lib/sea.py` | None — the balance spring is a separate part, not the SEA cartridge. |
| `cad/assembly.py` | Re-export `j2_bracket`, `j2_yoke`-equivalents (new spring seats), wrist/J4 parts unchanged. |
| `docs/BOM.md` | Actuation table: STS3215-12V qty 5→4; add/move J4 to the STS3250 line (J1 already uses STS3250 → STS3250 qty becomes 2). Add: 1× torsion spring (~£4.71 ea at 100-pc price break, single-unit per quantity table — springmasters.com/shop/471671/, checked 2026-11-01). |

## New mass

- J4 servo: +19.5 g at the forearm end (in the model, `fore` body,
  ~0.105 m behind the J4 axis).
- Spring + mandrel/stop hardware: ~15–25 g est. **[U]** — sits at the J2
  axis where its gravity moment ≈ 0, so it is not modelled (conservative:
  the model carries only the verified +19.5 g).
- Net arm mass change: ≈ +35–45 g total.

## Wiring / PCB impact

- **Bus A (TTL, 1 Mbaud):** none — STS3250 speaks the same Feetech
  half-duplex packet protocol, same 3-pin daisy chain, already proven on
  this bus at J1. `software/robot-os` and `firmware/base-node` servo map
  unchanged (J4 keeps id 4).
- **Power:** same +12V rail (carrier J4/J5 pin 2, unswitched post-F1).
  Rated current 1.4 A vs 0.9 A (+0.5 A typical); stall 4.2 A vs 2.7 A.
  F1 stays 6 A mini-blade; simultaneous all-stall was already
  theoretically above the fuse — mitigation stays firmware-side (servo
  torque/current limits, see below). 12 V/8 A PSU budget still inside.
- **Firmware config (no code change required for the study):** set J4's
  `TORQUE_LIMIT` register (addr 48 in `soma_arm/feetech.py`) so the
  printed wrist parts never see more than the ~30 kg·cm they were
  designed around — the 50 kg·cm stall is headroom, not a target.
- **J2 spring:** no electrical impact. No connector/PCB changes anywhere.
