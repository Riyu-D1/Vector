# SOMA first power-up checklist (bring-up) — carrier v1.3

Read this fully before touching the supply. **12 V / 8 A is real
energy** — enough to strip printed gears, burn a stalled servo or
weld a loose wire.

v1.3 adds a **hardware safety relay**: `MOTOR_EN` (IO40) drives Q3 →
relay K1 → `+12V_MOT` on J18/J20. The motors have NO power until
firmware deliberately closes it, and the NC e-stop loop on J19 can
drop it regardless of firmware. Prove that chain first — it is the
whole point of the board.

## Safety notes (always)

- 12 V 8 A brick → carrier XT60 → reverse-polarity FET Q2 → **6 A
  fuse F1**. Never bypass it.
- The e-stop is a **normally-closed** loop: J19 pin1 ↔ pin2 through
  the button. Loop open = relay coil path broken = motor rail dead.
  A cut/unplugged estop wire also estops — on purpose. The IO38 sense
  input (J9) only *reports* the loop state to firmware.
- 3S LiPo max if you ever swap the brick — no undervoltage cutoff.
- Keep clear of the arm sweep; the 4008s at 5 A can throw the links.
- Hot parts after a stall: motor bell, ESC board, servo case.

## Stage 0 — relay + e-stop proof, NO motors attached

1. Carrier only: ESP32-S3 in its socket. Nothing on J18/J20, J4–J6
   servo headers, or the CAN bus.
2. USB to the DevKit UART port. `python -m soma_arm.cli --port
   /dev/ttyXXX ping` → expect PONG fw **0x000200**.
3. `sense` → STATE: flags must show `MOTOR_EN=0`, `ARMED=0`,
   `ESTOP=0`, `CAN_ONLINE=0` (no ESCs yet), `can_ok_mask=0`.
4. **Multimeter on J18 pin 1 (+12V_MOT) vs GND: must read 0 V**
   even with 12 V on JP1 — the relay is open by default. Same on J20.
   Jumper J19 open → IO38 sense must show `ESTOP` in the next STATE.
5. Try `arm-motors` now: it must NOT close the relay (ESTOP latched +
   no ESC heartbeats) → STATE keeps `MOTOR_EN=0`, event `MOTOR_EN_OFF`
   with reason logged on console. J18/J20 stay at 0 V.
6. Close J19, `clear-estop`, `arm-motors`: still must fail — no ESC
   heartbeat yet (CAN precondition). **The rail must never come up
   before the ESCs prove they're alive.** This is the check that
   matters most; if +12V_MOT appears anyway, power down and debug
   `motor_en_step()`/the K1/Q3/J19 wiring before anything else.
7. Press the NC e-stop while watching the meter: coil path opens —
   nothing else needed, the rail can't be on anyway at this stage,
   but the STATE flag must latch ESTOP and require `clear-estop`.
8. Stop sending host frames >0.5 s → watchdog trips (flag b1), estop
   latches. `clear-estop` to recover.

**Do not continue until the relay has proven it stays open.**

## Stage 1 — CAN heartbeat precondition

9. One B-G431B-ESC1 flashed as node 2, **logic side powered from an
   unswitched supply** (its own 12 V, or ST-LINK USB — see the power
   caveat in `docs/can-protocol.md`; if the ESC logic is fed by
   +12V_MOT it can never heartbeat and the arm can never arm — this
   is UNVERIFIED, check the board's power path first). CANH/CANL to
   the carrier's TJA1051T/3 header; both ends ~120 Ω.
10. `sense` → `can_ok_mask` bit0 sets once the drive answers the
    200 ms ping round-robin (TPDO1 echo). `READ_PARAM 0 2 0x0E` →
    fw version.
11. Now `clear-estop` + `arm-motors` → EVENT `MOTOR_EN_ON`, STATE
    b4 set, **J18/J20 read 12 V**. Repeat the J19 e-stop press with
    the meter on J18: rail must die instantly, EVENT `MOTOR_EN_OFF`
    reason=1, and `arm-motors` alone won't restore it until
    `clear-estop` + `arm-motors` again — while the loop is open the
    relay physically can't close.
12. Kill the host stream >0.5 s with the rail live → watchdog drops
    MOTOR_EN (reason=2) and NMT ESTOP goes out on CAN.

## Stage 2 — one joint, on the bench

13. ESC powered (motor rail now live via J18/J20 or bench supply),
    rotor free — no cycloidal output load. `mode 2 2` (NMT CALIBRATE)
    — the motor twitches/rotates slowly, stores encoder offset +
    direction; STATUS b2 sets.
14. `mode 2 3` (NMT HOME): the joint creeps toward the hard stop at
    `HOME_SPEED_RADS`, stalls at `HOME_CURRENT_A`, sets output zero at
    the stop + `HOME_STOP_RAD` offset; STATUS b4 (homed) sets.
    **Do this once with your hand ready to kill power — the hard-stop
    offset and homing current are UNVERIFIED.**
15. `enable` → position hold. Small `move-joints` on J2 only
    (±0.1 rad) — verify direction and that `sense` pos tracks in
    **output** radians (0.1 rad out = 4 motor turns — expect to hear
    it spin).
16. 60 s hold → check ESC + motor temperature. Warm is fine;
    too-hot-to-touch is not (lower CURRENT_LIMIT_A).
17. Repeat for J3 (node 3, `CAN_TERM` on if it's the last node).

## Stage 3 — Feetech servos

18. One STS3215 on bus A, id 4. `sense` → pos J4 responds.
    `set_servo_reg`/`READ_PARAM bus=1` for raw access.
19. If no response: 1 Mbps on this wiring is UNVERIFIED — scope the
    line or drop `FT_BAUD` to 500000 both sides and retry.
20. Add J5 (id 5), J6 (id 6), gripper (id 7), then J1 STS3250
    (id 1 — set its id on the bench before installing).
    Verify each moves and reports a sane position.

## Stage 4 — assembled arm

21. All joints powered, e-stop loop closed. `arm-motors` → `enable`.
22. `demo` in sim first, then the same path at `--speed 0.2` on
    hardware. Hand near the e-stop.
23. `sense` every second while moving — `can_ok_mask` 0x03, MOTOR_EN
    stays up, servo temps sane.
24. Only then payload tests: start empty, add load gradually —
    `max-payload` on the CLI gives the per-pose derated limit
    (J4 collapses it at full reach — expected, that's the derating
    doing its job).

## If something trips

- Fuse blows → find the short first (usually servo stall or a motor
  phase). The 6 A fuse protects wiring, not parts.
- Watchdog keeps tripping → host streaming too slow; raise the rate
  — never disable it.
- MOTOR_EN won't arm → STATE flags + the `MOTOR_EN_OFF` event arg
  say exactly which condition failed (see `docs/host-protocol.md`).
- CAN errors spam → check both terminations, twisted pair, common
  GND between carrier and ESC boards.
- Relay chatters or won't hold → check the J19 loop wiring and the
  Q3/R11/R12 stage (K1 pad map is UNVERIFIED — confirm against the
  Songle SRD-12VDC-SL-A datasheet if the coil behaves oddly).
