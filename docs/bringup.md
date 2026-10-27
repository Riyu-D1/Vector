# SOMA v3 first power-up checklist (bring-up)

Read this fully before touching the supply. **12 V / 8 A is real energy** —
enough to strip printed gears, burn a stalled servo or weld a loose wire.

## Safety notes (always)

- 12 V 8 A brick → carrier XT60 → **6 A fuse on the carrier** (already
  fitted). Never bypass it. Logic rail (5 V buck) fused separately.
- The e-stop is a **normally-closed** loop: J9 pin1 ↔ pin2 through the
  button to GND. Loop open = estop. A cut/unplugged estop wire also
  estops — that's on purpose, wire it before powering motors.
- If you ever run off a LiPo instead of the brick: 3S max (12.6 V),
  fire-safe charging, never unattended — the board has no undervoltage
  cutoff for the motor rail. Prefer the brick for bring-up.
- Keep clear of the arm sweep; 5010s at 5 A can throw the links fast.
- Hot parts after a stall: motor bell, ESC board, servo case. Wait
  before handling.

## Stage 0 — no motors attached

1. Carrier only: plug ESP32-S3 into its socket, nothing on J4–J6, J15.
2. USB to the DevKit **UART** port. `python -m soma_arm.cli --port
   /dev/ttyUSBX ping` → expect PONG fw 0x000100. (macOS: `/dev/cu.usbserial*`;
   Linux: `/dev/ttyUSB*`/`/dev/ttyACM*`.)
3. Check `sense` returns a STATE frame with flags armed=0, estop=0.
4. Jumper J9 open → next STATE must show `flags & 0x01` (ESTOP). Close
   the loop, send `clear-estop` → flag clears. **Do not continue until
   the estop line proves itself.**
5. Stop sending host frames >0.5 s → watchdog must trip (flags b1) and
   latch estop. `clear-estop` + `enable` to recover.

## Stage 1 — CAN bus up, motors disconnected

6. SN65HVD230 module on J15: pin3→CTX/D, pin4←CRX/R, pin5→VCC(3V3), pin2→GND.
   **Do not use pin 1 (+5V) — the module is 3.3 V.**
7. One B-G431B-ESC1 flashed as CAN id 1 (`joint-driver/`), CAN_TERM off
   (single-node test: enable it instead on the ESC if the ESP32 side
   has no 120 Ω — bench layout decides; bus works with both ends ~120 Ω).
8. 12 V to the ESC1 only. `sense` → `can_ok_mask` bit0 sets once the
   drive starts answering (PDO1 ping every boot is logged on console).
9. `READ_PARAM 0 <node> 0x000F` (SDO STATUS) via CLI `limit`/`param`
   → STATUS bit2 shows whether the drive is calibrated.

## Stage 2 — one joint, on the bench

10. Rotor free (no cycloidal output load). `NMT CALIBRATE` (CLI:
    `mode 1 2` or SDO 0x0C) — the motor twitches/rotates slowly, stores
    offset. Repeat per joint; only re-run if the magnet/encoder moves.
11. `enable` → the joint position-holds. Small `move-joints` command on
    J1 only (e.g. ±0.2 rad) — verify direction, smoothness, no fuse trips.
12. Verify `sense` pos tracks the command; check ESC/motor temperature
    after 60 s hold — warm is fine, too-hot-to-touch is not (lower the
    current cap if so).
13. Repeat for J2 and J3 one at a time. Set per-joint current caps
    (J1 3 A, J2/J3 5 A) — the base node pushes them every boot anyway.

## Stage 3 — Feetech servos

14. 12 V on, one STS3215 on bus A, id 4. `sense` → pos J4 responds.
    `set_servo_reg`/`READ_PARAM bus=1` for raw access.
15. If no response: the 1 Mbps bus is UNVERIFIED on this wiring — scope
    the line or drop `FT_BAUD` to 500000 both sides and retry.
16. Add J5 (id 5), then J6 gripper (id 6). Verify each moves and reports
    sane position before assembling.

## Stage 4 — assembled arm

17. All joints powered, e-stop loop closed. `enable`.
18. `demo` in sim first, then the same path at `--speed 0.2` on hardware.
    Hand near the estop.
19. `sense` every second while moving — watch `can_ok_mask` 0x07 and
    servo temps (READ_PARAM bus=1 reg 63).
20. Only then: payload tests. Start empty, add load gradually to 250 g.

## If something trips

- Fuse blows → find the short before replacing (usually servo stall or
  motor phase). The 6 A fuse protects wiring, not parts.
- Watchdog keeps tripping → host streaming too slow; raise rate or raise
  `LINK_TIMEOUT_MS` (recompile) — never disable it.
- CAN errors spam → check both terminations, twisted pair, common GND
  between carrier and ESC boards.
