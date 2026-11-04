# BENCH CHECKLIST — soma-carrier-v16

Datasheet-verifiable items are settled in `bom.csv`/README; the items
below are the ones that genuinely need a DMM/scope on the real parts.

## Before power

- [ ] **[U] K1 (SRD-12VDC-SL-A) pin numbering** — board assumes pins
      1-2 = coil, 3 = COM, 5 = NO (KiCad lib
      `Relay_SPST_SANYOU_SRD_Series_Form_A`, Songle datasheet bottom
      view). DMM-buzz the actual relay's coil resistance (~320 ohm
      between pins 1-2) before soldering; if a clone numbers pins
      differently, rotate or re-pin it. Pads: 1=+12V, 2=RLY_LOW,
      3=+12V (COM feed), 5=+12V_MOT (NO).
- [ ] **F1 is a 10 A mini blade fuse** — do not fit the old 6 A doc
      value. Q2 P-FET protects polarity *downstream* of the jumper.
- [ ] **D4 = P6KE15A unidirectional** — band toward pin 1 (+12V_IN).
- [ ] **D1 = 1N5820** — cathode band toward pin 1 (+5V_MCU side).
- [ ] **[U] Q1/Q3 = PN2222A TO-92** — datasheet order is E-B-C
      (flat face toward you). Board pads are 1=E(GND), 2=B, 3=C; the
      legs must be spread to 0.1" pitch. A 2N2222A in metal can or a
      PN2222 with reversed C/B-E marking needs re-checking.
- [ ] **[U] J3 Mini-360 module pad order** — board is 1=+12V(IN+),
      2=GND(IN-), 3=+5V(OUT+), 4=GND(OUT-). Confirm against the
      printing on the physical module before soldering (clones move
      pads). ONE 5V SOURCE ONLY — do not also feed J2.
- [ ] **U2 = TJA1051T/3 SOIC-8** — pin 1 dot toward silk notch
      (U2.8 is the RS/slope pin, tied to GND net side; VCC=5V, VIO=3V3).
- [ ] **U3 = 74AHCT125** in the DIP-14 socket — pin 1 toward notch;
      all four /OE grounded by design.
- [ ] **U1A/U1B: DevKitC-1 USB port faces LEFT (west)** — socket
      position N = module pin N, pin 1 of each row at the USB end.
      (Verify the module's own silk pin order — Espressif revs differ.)

## After power, before bus

- [ ] **[U] D6 (3V6 zener) is DNP by default** — scope the Feetech
      bus high level at U1B.17 (RXA). Fit D6 only if overshoot > ~3.6 V.
- [ ] **[U] Buzzer flyback D7** — board assumes a 5 V *inductive*
      buzzer; if a piezo is fitted D7 is harmless either way. Confirm
      BZ1 actually sounds via BUZ (U1B.7) -> Q1.
- [ ] **Estop chain** — J9 button, J19 NC loop jumper, K1 coil via
      Q3/MOTOR_EN: prove +12V_MOT dies on estop open AND on jumper fit.
- [ ] **JP2 CAN termination** — fit the shunt only on the end-of-bus
      node (120R across CANH-CANL via R9).
- [ ] **Capacitor ratings** — BOM requires >=25 V on 12 V parts
      (C1, C2), >=10 V on 5 V parts (C3, C4, C5, C7, C8), >=6.3 V on
      the 3V3 part (C6). Do not derate below the rail.
- [ ] **J13 jog dial** — plug order GND/3V3/SW/DT/CLK matches a stock
      KY-040; verify with a scope/DMM on ENC_A/ENC_B while turning.

## Known tool warnings (not bench items)

- 13x `lib_footprint_mismatch` — intentional embedded overrides on all
  rot90 footprints + a KiCad-10 rotated-compare false positive; see
  FAB_NOTES.md. Do not update footprints from library.
