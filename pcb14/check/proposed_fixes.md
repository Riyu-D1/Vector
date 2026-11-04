# proposed_fixes.md — exact corrections for CHECK-pcb14 findings

Report-only audit: **nothing below is applied to the board.** Each fix is
an exact, verifiable change for a v1.5 (or a rework of v1.4 copper).
F-numbers match `CHECK-pcb14.md`.

---

## F1 — ESP32-DevKitC-1 socket mirror (severity: blocks-power-on)

**Defect.** `gen_pcb.py` L258–262 assumes "socket pin N maps to module
J-position (23-N)", i.e. header pin 1 at the non-USB end. On the real
module both J1 and J3 are numbered from the USB/antenna end, so with the
silkscreened "USB->W / TOP=J1 BOT=J3" mounting, socket pad N meets
module J-position **N**, not 23−N. Result: two 3V3→GND shorts, 5 V onto
the +3V3 rail, IO43 (U0TXD) shorted to GND, signals on IO3/IO45/IO46
strapping pins, and all 17 signal nets on mirrored GPIOs.

**Exact fix (copper).** Keep the documented USB-west mounting; re-route
so that each socket pad carries the net intended for module J-position
N — i.e. move every live net on each header to its mirror pad:
`new_net(pad p) = old_net(pad 23−p)`.

Corrected U1B (J1 side) pad table:

| Pad | Module pin | Net after fix | Was |
| --- | --- | --- | --- |
| 1 | J1-1 3V3 | +3V3 | GND |
| 2 | J1-2 3V3 | +3V3 | +5V_MCU |
| 3 | J1-3 EN | NC | NC |
| 4 | J1-4 IO4 | NEO | NC |
| 5 | J1-5 IO5 | IRIN | NC |
| 6 | J1-6 IO6 | TEMP | RXA |
| 7 | J1-7 IO7 | BUZ | VSNS |
| 8 | J1-8 IO15 | NC (BUSB spare) | NC |
| 9 | J1-9 IO16 | LEDGPIO | NC |
| 10 | J1-10 IO17 | BUSA_DATA | NC |
| 11 | J1-11 IO18 | SCL1 | SDA1 |
| 12 | J1-12 IO8 | SDA1 | SCL1 |
| 13 | J1-13 IO3 (strap) | NC | BUSA_DATA |
| 14 | J1-14 IO46 (strap) | NC | LEDGPIO |
| 15 | J1-15 IO9 | NC | NC |
| 16 | J1-16 IO10 | VSNS | BUZ |
| 17 | J1-17 IO11 | RXA | TEMP |
| 18 | J1-18 IO12 | NC (RXB spare) | IRIN |
| 19 | J1-19 IO13 | NC | NEO |
| 20 | J1-20 IO14 | NC | NC |
| 21 | J1-21 5V | +5V_MCU | +3V3 |
| 22 | J1-22 GND | GND | +3V3 |

Corrected U1A (J3 side) pad table:

| Pad | Module pin | Net after fix | Was |
| --- | --- | --- | --- |
| 1 | J3-1 GND | GND | GND |
| 2 | J3-2 IO43 (U0TXD) | NC | GND |
| 3 | J3-3 IO44 (U0RXD) | NC | NC |
| 4 | J3-4 IO1 | CAN_RX | NC |
| 5 | J3-5 IO2 | CAN_TX | ENC_A |
| 6 | J3-6 IO42 | NC (SDA2 spare) | ENC_B |
| 7 | J3-7 IO41 | NC (SCL2 spare) | ENC_SW |
| 8 | J3-8 IO40 | MOTOR_EN | NC |
| 9 | J3-9 IO39 | NC (WRX spare) | NC |
| 10 | J3-10 IO38 | ESTOP | NC |
| 11–13 | J3-11..13 IO37/36/35 | NC | NC |
| 14 | J3-14 IO0 (strap) | NC | NC |
| 15 | J3-15 IO45 (strap) | NC | MOTOR_EN |
| 16 | J3-16 IO48 | ENC_SW | NC |
| 17 | J3-17 IO47 | ENC_B | NC |
| 18 | J3-18 IO21 | ENC_A | CAN_TX |
| 19 | J3-19 IO20 (USB D+) | NC | CAN_RX |
| 20 | J3-20 IO19 (USB D−) | NC | NC |
| 21 | J3-21 GND | GND | NC |
| 22 | J3-22 GND | GND | GND |

**Generator fix.** In `gen_pcb.py`, where the DevKitC pad map is built
(comment at L258), map pad N to module J-position **N** (delete the
`23-N` reversal). Equivalently swap the two lists above into the
explicit pad→net table.

**Verification.** After re-route, `verify_nets.py` and
`audit_pins.py` should show: U1B.1/2=+3V3, U1B.21=+5V_MCU, U1B.22=GND;
U1A.1/21/22=GND, U1A.2=NC; and every GPIO net on the J-position shown
above. Continuity-bench: U1B.1 must NOT be GND.

**Firmware impact: none** — GPIO assignments documented in the README
(IO4 NEO, IO5 IRIN, IO6 TEMP, IO7 BUZ, IO8 SDA, IO10 VSNS, IO11 RXA,
IO16 LEDGPIO, IO17 BUSA, IO18 SCL, IO1/2 CAN RX/TX, IO38 ESTOP,
IO40 MOTOR_EN, IO15/47/48 ENC_A/B/SW) are preserved exactly; only the
copper moves.

**Alternative (not recommended):** flipping the module so USB faces
east does NOT work — that puts J3 on the top header, breaking every
J1/J3 row assignment. There is no module orientation that repairs the
mirroring; the copper must change.

---

## F2 — NeoPixel DIN level (will-not-work / out-of-spec)

WS2812B `VIH = 0.7·VDD` = 3.5 V @ 5 V; board drives 3.3 V data.
Options, in order of preference:

1. **Level shifter**: add a 74AHCT125 (or 74HCT08/32 spare gate) between
   the NEO GPIO and J14.2, powered from +5V — input threshold ≈2.0 V,
   output ≈5 V. Clean fix, ~$0.20.
2. **Drop the strip's VDD**: insert a 1N400x in J14 pin 3's feed so the
   first pixel sees ≈4.3 V → VIH ≈3.0 V < 3.3 V. Works for a single
   strip; the diode drop is inside spec for WS2812B VDD (3.5–5.3 V).
3. **Sacrificial pixel**: run the first LED's VDD from ~4.3 V via a
   diode; its DOUT then drives the rest at full level.
4. Regardless of option: add ~330–470 Ω in series with DIN and a
   470–1000 µF cap at the strip's supply pins (Adafruit guideline).

---

## F3 — +12 V path ampacity vs 10 A fuse (will-not-work at rating)

Weakest links: +12V_IN crosses one 0.3 mm-drill via; all +12V* nets are
2.5 mm tracks ≈6.3 A @20 °C rise (1 oz). Fixes:

- **Vias**: place ≥4 vias (0.7/0.3 mm) in parallel on the +12V_IN layer
  jump (and audit every high-current layer change — target ≤½ fuse
  rating per path).
- **Tracks**: widen +12V_IN/+12V/+12V_MOT/+12V_SW/+12V_RP to ≥4.5 mm
  (≈10 A @20 °C, 1 oz) or flood-fill them on the spare layer where
  geometry allows.
- **Fuse**: alternatively return F1 to 6 A (the pcb12-era value, roughly
  matching 6.3 A copper) **only if** combined motor stall stays <6 A —
  two stalled STS3215 ≈5.4 A leaves no headroom for J18/J20 loads, so
  the wider-copper option is the right fix for the 10 A fuse.
- **Relay**: SRD-12V contacts are 10 A @30 VDC — at the fuse limit with
  no margin; for >10 A motor loads spec a higher-contact part.

---

## F4 — Servo DATA level into ESP32 ([U] → conditional fix)

If bench measurement shows the STS3215 drives BUSA_DATA high above
3.6 V: add a divider (e.g. 6.8k/10k) or a 3.3 V zener + the existing R1
at the ESP32 end of R1, or a dedicated single-gate shifter (74LVC1G07-
style open-drain works for half-duplex). R1 alone only limits injection
current; it does not fix the level.

---

## F5 — Fuse documentation drift (cosmetic)

`pcb14/README.md` still says "6A" for F1; board value, silk and
STATUS-pcb12 say 10 A (deliberate change). Update the README text next
documentation pass. Board itself is consistent — no copper change.

---

## F6 — J13 header order vs KY-040 (will-not-work if plugged direct)

Board order: `+3V3, GND, ENC_B, ENC_A, ENC_SW`; KY-040 module order:
`GND, VCC, SW, DT, CLK`. Two acceptable fixes:

1. **Re-pin J13** in a future rev to GND,VCC,SW,DT(ENC_B),CLK(ENC_A) so a
   KY-040 plugs straight in, and update silk "JOG 3V-G-B-A-SW" to
   "JOG G-3V-SW-B-A".
2. **Keep the header** and document a mapped cable (KY-040 pin→J13:
   1→2, 2→1, 3→5, 4→3, 5→4) — silk already prints the board order, so
   this is a documentation-only fix for a bare EC11, which is what
   README actually specifies.

---

## Cosmetic / advisory (no fix required, logged for completeness)

- 16× `silk_overlap` DRC warnings — move offending silk off pad edges
  at next rev; some labels sit at 0.8 mm text height (JLCPCB min 1.0 mm).
- 11× `lib_footprint_mismatch` — local footprint edits are deliberate
  (documented in STATUS-pcb13/14); no action.
- +5V wired-OR (J2 vs J3) — label "use one 5 V source only" on silk.
- Buzzer has no flyback diode — optional 1N4148 across BZ1 if a magnetic
  buzzer is fitted.
- Mini-360 VOUT must be set to 5.0 V before connection (bench step).
- IRF4905 tab orientation deserves a silk marker (tab = Drain = pad 2).
- STATUS-pcb14's claim that the ESP32 socket map was verified should be
  corrected at next doc pass — it was verified against the generator's
  own assumption, not against the real module.
