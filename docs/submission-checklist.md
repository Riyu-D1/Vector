# Fabricate design-ship checklist

From the Fabricate/Hack Club submission docs — 95% of rejections are README or
completeness issues. Track everything here before submitting.

## README (done when all are true)

- [x] What the project is — one clear paragraph
- [x] What it does — feature list a stranger understands
- [x] Why it exists — personal motivation + the gap it fills
- [x] How to use it — API/tools + by-hand teaching + agent loop
- [ ] Images — full assembled CAD render(s) ← **blocker until CAD exists**
- [ ] Wiring diagram render (netlist already in architecture.md)
- [ ] Anything else that makes it obviously real (mechanism close-ups)

## Complete design (replicable by a stranger)

- [ ] CAD — STEP files of full assembly + printable STLs, organized by subassembly
- [ ] Wiring diagram (Fritzing/drawio/kiCad-style schematic of the netlist)
- [ ] BOM with links/cart screenshot ← [BOM.md](BOM.md) done, need cart screenshot
- [ ] Firmware source (base-node + wrist-node) — even draft-level
- [ ] Software (robot-os + mcp-server) — even draft-level
- [ ] SEA spring characterization procedure + calibration data format
- [ ] Assembly notes/ordering of operations

## Funding

- [ ] "I need funding" ticked on the cart panel, total build cost entered (~$450–470)
- [ ] Cart/parts-list screenshot matching the BOM
- [ ] Level selected: **Level 4** (> $400). Expect extra scrutiny — the torque
      analysis and phased build plan are the evidence the number is real.
- [ ] Nothing in the cart is already owned (servos, printer, computer excluded)

## Process

- [ ] Hackatime running on design/CAD hours from day one — scraps/journal feed
      the grant path and the build ship later
- [ ] Order early — AliExpress parts are 2–4 weeks out; servo and sensor orders
      go first, filaments/bearings are local
- [ ] Build ship submitted separately after assembly (funding box unchecked)

## Reviewer-proofing notes

- The differentiator vs. SO-101 clones is front-loaded in the README title —
  reviewers see a lot of servo arms; lead with *compliance + senses + agent
  embodiment*, not "robot arm."
- Keep the claims honest in the README: admittance-based yielding is *not* true
  backdrivability — the docs say so explicitly, which reads as competence, not
  weakness.
- The BOM alternates (Pi 5 vs OPi5, ESP32-CAM vs USB cam) show cost discipline
  without looking under-scoped.
