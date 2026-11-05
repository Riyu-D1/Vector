# PRINT.md — D13 prototype print pack (tc_master + tc_plate + tool_pen)

Smallest useful bench set for the D10/D12 automounter: master plate for the
J6 horn, one socket plate (the same plate is fused into tool_pen), and the
passive pen tool. STLs are already oriented for the bed (see below) — drop
straight into Bambu Studio.

## Files

| file | part | oriented bbox (mm) | volume | est. printed mass¹ |
|---|---|---|---|---|
| `stl/tc_master.stl` | J6-horn master plate + spigot + 3 lugs | 33.1 × 32.2 × 13.1 | 7.3 cm³ | ~5.8 g |
| `stl/tc_plate.stl` | socket plate (ring + catches + floor) | 46.0 × 46.0 × 9.4 | 7.4 cm³ | ~5.9 g |
| `stl/tool_pen.stl` | socket plate + pen/pointer barrel | 46.0 × 46.0 × 79.0 | 29.0 cm³ | ~22.8 g |

¹ printed mass = volume × 1.31 g/cm³ (PETG-CF) × INFILL_EFF 0.6 `[U]` —
solid-equivalent masses are 9.6 / 9.8 / 38.0 g. Total pack ≈ 34.5 g ≈ 27 cm³
filament. STEP copies in `step/` for reference (not for slicing).
Regenerate any file: `cradlefix venv python toolchg/print/export_print.py`.

## Orientation (already set in the STLs — do not re-orient)

All parts print **−a face down** (STATUS-toolchg convention: the −a lead
chamfers double as support-free ramps):

- `tc_master` — horn-plate back face (Ø30) on the bed, spigot + lugs up.
- `tc_plate` — socket mouth (Ø46 rim) on the bed, floor on top.
- `tool_pen` — same plate face down, pen barrel + cone tip up (79 mm tall).

## Printer / filament

- Bambu **A1**, 0.4 nozzle, 256 × 256 × 256 usable. Every bbox fits with
  huge margin (largest 79 mm tall).
- Filament: **PETG-CF** only (matches all the FEM/mass assumptions — PETG-CF
  allowables remain `[U]`).
- Temps `[U]` — not verified live on this machine: typical PETG-CF on A1 ≈
  nozzle 250–260 °C, bed 70–80 °C (textured PEI). Dry the spool first
  (~65 °C, 6–8 h `[U]`); keep part-cooling fan low-medium `[U]`.

## Slicer settings

| setting | value |
|---|---|
| layer height | 0.2 mm |
| walls / perimeters | ≥ 4 (small structural coupling — 5–6 OK) |
| top/bottom layers | 5 |
| infill | ≥ 40 % gyroid (or similar) — coupling is structural |
| brim | none needed (all have flat bed faces); tool_pen optional 3 mm brim |

## Supports — needed, paint-on / tree recommended

This is the designed-in trade-off from D10/D11 (flat-down areas measured):

- **tc_master**: the 3 lug −a bearing faces (~267 mm²) face down at z≈9.7 —
  support under the lug overhangs only (paint-on or auto tree, support
  interface ON, top z-gap ~0.2). D12 bench note: these faces carry the
  capture loads — inspect surface after print, expect to deburr.
  Horn-recess pocket ceilings (Ø7 × 2.2 pockets) bridge acceptably.
- **tc_plate / tool_pen**: the socket floor ceiling (~1040 mm², Ø36, 7 mm
  up inside the bore) + the dock-groove lower lip face down — auto/tree
  support inside the socket and a thin ring under the groove lip; pick out
  through the mouth after printing. The catch −a ramps are drawn as
  self-supporting staircases — no support needed there.
- **tool_pen** barrel/cone/set-screw bores: no support (axis vertical).

Slicer pass itself is `[U bench]` — first slice will show real support
coverage.

## Time estimate `[U]`

Rough volume-based guess at the settings above (slicer will give the real
numbers): tc_master ~1 h, tc_plate ~1 h, tool_pen ~3–4 h.
