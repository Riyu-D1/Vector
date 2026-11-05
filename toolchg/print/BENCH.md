# BENCH.md — assembly + first-bench card (D13 prototype pack)

Scope: master on the J6 horn + passive pen tool. Everything here is done
**by hand with the arm unpowered** — no 12 V bus, no J6 motion in this pack.

## Assemble

1. **Inspect prints.** Deburr the master's lug −a faces (they printed on
   support — D12 note: that's the loaded face). Pick support out of the
   socket bore (floor ceiling) and the dock-groove lip. Check the pen bore
   Ø8.5 clears your marker.
2. **Master → J6 horn.** Offer the master to the horn exactly like the
   stock w_grip_frame plate: 4× M3 button-heads into the PCD14 horn holes
   (counterbored heads flush with the plate face); refit the horn centre
   screw through the Ø7.2 access bore. Plate face should sit ~0.3 mm clear
   of the socket face when seated (as designed).
3. **Fit the detent.** Thread the M4 ball plunger into the radial bore at
   the groove band (needs an M4 thread at the bore mouth — insert or
   print-thread, `[U bench fit]`). DIY option: Ø4 ball + ~Ø3.2×8 spring +
   M4 grub. Ball tip should just reach into the socket bore (r17.2) — it
   must NOT block lug entry (C4 verified clearance is small).
4. **Pen tool.** Drop a ~Ø8 marker into the barrel, tip out the cone;
   snug the 2× M3 grubs (self-tap) to clamp it.

## First bench (all by hand)

5. **Seat by hand.** Hold the tool socket to the master at the entry roll
   (lugs centred in the catch gaps — key notch / keel-down phase), push to
   the floor, twist **+60°** to lock. The detent ball should ride a lug OD
   then click into the lug-1 dimple.
6. **Lock/unlock ×20.** Twist +60° lock / −60° unlock ×20. Feel for:
   smooth ramp, positive detent click, no binding, no chewing of the lug
   −a faces. Note anything that grinds — the entry allowance is the thin
   margin (C2 worst case).
7. **TCP repeatability.** Tape paper to the table, seat the pen tool,
   touch the tip dot; undock + redock ×20, dot each time. Measure the
   spread — **target < 0.5 mm** (est. ≤0.5 mm `[U bench]` — this is the
   number that decides adopt/reject per D10 recommendation).
8. **Optional pull test.** Gentle hand pull/rock on a locked tool — no
   visible slip or rock.

## Caveats (do not skip)

- **F9 payload caveat stands**: do NOT hang the 0.5 kg payload on a
  printed grip tool yet — `tool_grip` cheek SF ~0.87 `[U]` inherited from
  w_grip_frame. **This pack is pen-only** (~23 g, passive).
- Pogo pass-through not exercised in this pack; 12 V tool bus comes later.
- Safety: the detent ball + spring are **small parts** — keep the plunger
  assembled, work over a tray. No powered motion yet — hand twist only.
