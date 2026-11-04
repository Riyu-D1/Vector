# FAB NOTES — soma-carrier-v16

| Parameter | Value |
|---|---|
| Board | 135 x 115 mm, rectangular |
| Layers | 2 (F.Cu + B.Cu, GND pours both sides) |
| Thickness | 1.6 mm |
| Copper | 1 oz (35 um) |
| **Solder mask** | **Black** (both sides) |
| **Silkscreen** | **White** (both sides) |
| Surface finish | **HASL lead-free** assumed (board stackup records it); ENIG also fine |
| Min track | 0.25 mm signal / 2.5 mm 12 V trunk |
| Min clearance | 0.22 mm copper-to-copper |
| Vias | 0.6 mm pad / 0.3 mm drill |
| Smallest hole | 0.7 mm (test pads) |

## Order-time options (JLCPCB)

- Base material: FR-4, 2 layers, 1.6 mm, 1 oz outer copper.
- **Solder mask colour: Black.**
- **Silkscreen colour: White.**
- Finish: LeadFree HASL (default) — ENIG acceptable.
- Remove order number / serial: yes (or let it land wherever it fits).

## Black-mask warnings (read before ordering)

- **Black solder mask hides copper and tracks** — trace/pour inspection
  with the naked eye is much harder than on green. The GND pours and
  power trunks were DRC-verified + Gerber-inspected; do not expect to
  visually trace shorts on the finished board.
- **Contrast**: white silk on black mask reads well at the sizes used
  here (all text >= 1.0 mm height, >= 0.15 mm stroke), but pin-1 marks
  and the fine art are still subtle under poor light.
- Minimum silk per JLCPCB: text height >= 1.0 mm, stroke width >=
  0.15 mm, width:height ~1:6. Source:
  https://jlcpcb.com/help/article/instructions-for-ordering
  (section 9, "Silkscreen/Texts") and
  https://jlcpcb.com/blog/character-design-specifications
- All silk sits over solder mask or bare FR4 — JLCPCB auto-clips silk
  over pad openings; there is no silk-over-pad in this design anyway
  (DRC: 0 silk_overlap, 0 silk_over_copper).

## Board art

Two monochrome vector graphics on F.SilkS, emitted as filled `gr_poly`
rectangles (no raster content):

- CAPTCHA "I'm not a robot" checkbox, ~(88,1.5)-(126,14.5) mm, top
  right, clear of the H2 mounting hole. A +12 V F.Cu trunk passes under
  the checkbox box — intentional, silk-over-masked-track is allowed.
- Pixel "sad page" icon, ~(46,61.5)-(60,79.1) mm, left of the J15
  spare header.

Sources: `art/not_a_robot.png`, `art/sad_page.png`, converted by
`art/make_art.py` (PIL threshold -> grid snap -> maximal-rect merge).
Regenerate with `python3 art/make_art.py` then `python3 gen_pcb.py`.

## Mask expansion / bridge

KiCad DRC clean at all severities for mask rules. The tightest
solder-mask bridges sit between the 2.54 mm-pitch header pads
(1.7 mm pads -> 0.84 mm mask sliver) — comfortably inside JLCPCB's
0.1 mm-class mask-bridge capability.

## lib_footprint_mismatch (13 warnings — documented, intentional)

All 13 `lib_footprint_mismatch` warnings are on footprints placed with
rotation 90 deg: J2, F1, Q2, J1, R5, U1A, U1B, D6, J11, J9, J13, U3,
J15. Verified on this KiCad 10.0.4 build that rotating *any* footprint
to 90 deg flags it as a mismatch (pad `at` rotations vs unrotated
library copy) — it is a comparison limitation, not a content error.
The affected footprints also carry deliberate local edits (per-instance
pin-1 silk marks, moved references, injected pad nets); they are meant
to differ from the stock library entries and are kept as local
overrides. Do not "update footprint from library" — that would strip
the pad nets.

## Gerbers

`soma-carrier-v16-jlcpcb.zip` = gerbers/ folder, v16-named files only:
F.Cu, B.Cu, F/B.Mask, F/B.Silkscreen, Edge.Cuts + Excellon drill.
The F.Silkscreen Gerber contains the board art (verified by inspection).
