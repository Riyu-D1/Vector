# SOMA v3 power budget — 12 V rail

Integration cross-check of the 12 V / 8 A brick against the carrier's
6 A fuse, the three B-G431B-ESC1 brushless drivers and the three
STS3215-12V servos. **Sourced** numbers come from repo docs/code;
everything else is labelled `UNVERIFIED`.

## Sourced facts

| item | value | source |
|---|---|---|
| Supply | 12 V / 8 A brick → XT60 (J16) or screw terminal (J1) | `pcb/README.md`, `docs/BOM.md` |
| Rail fuse | 6 A mini blade F1 (after JP1 switch + D4 15 V TVS) | `pcb/README.md` |
| 12 V trunk capacity | 2.5 mm track ≈ 4.6 A @10 °C / 6.2 A @20 °C (IPC-2221) | `docs/pcb-verification.md` §3.1 |
| Driver phase-current caps | J1 = **3 A**, J2 = **5 A**, J3 = **5 A** (pushed by base node every boot via SDO `CURRENT_LIMIT_A`) | `firmware/base-node/src/config.h` |
| Driver rating | B-G431B-ESC1 ≈ 5 A class (SimpleFOC `CURRENT_LIMIT_A` default 5.0) | `firmware/joint-driver/joint_driver.ino` |
| Servos | 3× STS3215-12V on bus A (J4/J5/J6), stall ≈ 30 kg·cm ≈ 2.9 N·m @12 V | `docs/torque-analysis.md` |
| Servo rail | each servo port off the fused +12 V trunk | `pcb/README.md` |
| Logic | ESP32-S3 + peripherals on 5 V from Mini-360 buck (or ext J2) | `pcb/README.md` |

## Phase current ≠ bus current (why the caps don't sum directly)

`CURRENT_LIMIT_A` caps the motor **phase (q-axis) current**, which is
what heats the motor windings and what the driver actually regulates.
The 12 V bus only supplies `d·I_phase` where `d` is the effective PWM
duty — at low speed / stalled commutation the phase current is high
while the bus draw stays well under the cap. Sustained worst case per
driver: `I_bus ≤ I_cap` (equality only near full duty — loaded motor at
speed). `UNVERIFIED` — depends on SimpleFOC modulation and load.

So the phase caps give a **loose upper bound** of 3+5+5 = 13 A on the
DC bus — *not* a promised draw. It cannot all flow at once in steady
state without the fuse winning first; that is what the fuse is for.

## Conservative budget table

| consumer | typical run A | worst sustained A | worst transient A | note |
|---|---|---|---|---|
| J1 driver (waist) | 0.5–1.5 `UNVERIFIED` | 3 (cap) | 3 | lowest cap — lightest duty |
| J2 driver (shoulder) | 1–2.5 `UNVERIFIED` | 5 (cap) | 5 | carries the 2.25 N·m load case |
| J3 driver (elbow) | 0.8–2 `UNVERIFIED` | 5 (cap) | 5 | 0.92 N·m worst-case torque |
| J4/J5/J6 STS3215 | 0.3–0.6 ea `UNVERIFIED` | ~1.5 ea `UNVERIFIED` | ~2.5 ea `UNVERIFIED` | stall current not in repo — take from datasheet on arrival |
| Logic (buck→5 V) | ~0.3 referred to 12 V `UNVERIFIED` | 0.5 | 0.6 | ESP32 ~0.5 A @5 V |
| **sum** | **~3.5–7** | **~20 theoretical** | **~20** | see verdict |

## Verdict

- **Steady-state fits.** The verification doc's ~3–4 A estimate for the
  12 V trunk is consistent with the table above: normal motion keeps
  the rail under the 6 A fuse with margin.
- **The 6 A fuse is the real power budget.** All three drivers at cap
  simultaneously is a *fault/abuse* condition, not an operating point —
  the fuse (and the J9/hardware estop path) ends it. The trunk trace
  carries 6.2 A at 20 °C, so the fuse protects the wiring as designed.
- **Phase caps stay as shipped:** J1 3 A, J2/J3 5 A. Do not raise J1 —
  it is deliberately lower; J1 sees the least torque.
- **Servo stalls are the likeliest fuse-blower** (per `bringup.md`):
  a jammed gripper or wrist holding a stall can pull several amps that
  don't show up in the host's view — watch servo temp registers
  (`READ_PARAM bus=1 reg 63`) during bring-up.
- **Regen is not clamped** beyond the 15 V TVS: hard decelerations dump
  energy back onto the rail — the TVS + bulk cap absorb small events;
  a LiPo swap is documented as 3S max in `bringup.md`.
- If the fuse proves twitchy during bring-up, the correct response is
  to lower phase caps (SDO `CURRENT_LIMIT_A`, persisted by SDO
  `SAVE_FLASH`), never to fit a bigger fuse.

## UNVERIFIED items (measure on the bench)

| item | why |
|---|---|
| True bus current per driver at cap | phase→bus ratio depends on duty/modulation; measure with the brick's meter or a shunt |
| STS3215-12V stall + running current | not in repo; datasheet for ST-3215-C047 says stall ≈ 1.6 A @7.4 V class — 12 V variant differs; `UNVERIFIED` |
| 5010 no-load + rated phase current | datasheet lists KV/geometry only |
| Buck efficiency / logic draw | Mini-360 module not characterised |
| Simultaneous-motion worst case | depends on trajectories — log TPDO3 iq + VSNS during Stage-4 bring-up |
