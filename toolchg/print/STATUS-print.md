# STATUS-print — D13 print-ready pack for the tool-changer prototype

Stage `stages/D13_toolchg_printpack.md` executed against
`ARM_KNUCKLE_V5.md` rules 0.1–0.10. Work done entirely inside
`~/Vector-wt/toolchgprint` on branch `arm-toolchg-print` (base
`origin/arm-toolchg-fix` @ `da55594`, tag `toolchgfix-done`); only files
under `toolchg/print/` were added — no existing file anywhere was
touched. CAD runs used the cradlefix venv
(`/Users/deepakdiwan/Vector-wt/cradlefix/.venv/bin/python`, build123d
0.13.0) since the soma venv does not exist on this machine (same as
D11/D12). Blender 4.5 for the bed preview.

## What the pack is

A drop-in folder for Bambu Studio / the A1: the smallest useful prototype
set — `tc_master`, `tc_plate`, `tool_pen` — rebuilt from the **tested**
`p_toolchg.py` at the D12 tip (geometry untouched, no redesign), oriented
−a face down per the STATUS print convention, exported as STL + STEP, plus
a settings card, a prototype BOM, and an assembly + first-bench card.

## Files (all under `toolchg/print/`)

| file | committed? | note |
|---|---|---|
| `stl/tc_master.stl`, `stl/tc_plate.stl`, `stl/tool_pen.stl` | no — `*.stl` gitignored per rule 0.4 / `toolchg/.gitignore` | watertight, oriented, z_min = 0 |
| `step/tc_master.step`, `step/tc_plate.step`, `step/tool_pen.step` | no — `*.step` gitignored | reference copies |
| `export_print.py` | yes | regenerates stl/+step/ from `p_toolchg` (cradlefix venv) |
| `PRINT.md` | yes | settings card |
| `BOM-prototype.md` | yes | qty-1 hardware kit |
| `BENCH.md` | yes | assembly + first-bench card |
| `bed_preview.png` | yes (640 KB < 1.5 MB) | top view of the 3 parts on the 256 mm bed |
| `bed_preview.py` | yes | regenerates the preview (Blender) |
| `STATUS-print.md` | yes | this file |

## Build proof (export_print.py output)

```
tc_master  bbox  33.1 x  32.2 x  13.1 mm  vol   7.3 cm3  wt True  m_solid 9.6 g  m_print 5.8 g
tc_plate   bbox  46.0 x  46.0 x   9.4 mm  vol   7.4 cm3  wt True  m_solid 9.8 g  m_print 5.9 g
tool_pen   bbox  46.0 x  46.0 x  79.0 mm  vol  29.0 cm3  wt True  m_solid 38.0 g  m_print 22.8 g
```

Volumes identical to the D12 rebuild (7.3 / 7.4 / 29.0 cm³); printed-mass
estimates (× 1.31 g/cm³ × INFILL_EFF 0.6) match D10's 5.8 / 22.2 g within
rounding. Bed-face verification (downward facets at z≈0): master 627 mm²
(Ø30 horn-plate back), plate/pen 619 mm² each (Ø46 socket-mouth rim) —
orientation is truly −a down; master lug −a bearing faces face down
(~275 mm² measured on the STL ≈ D11's ~267 mm²).

## Settings summary (full card in PRINT.md)

PETG-CF; 0.2 layer; ≥4 walls; ≥40 % gyroid; supports: paint-on/tree under
the master lug −a faces and inside the socket (floor ceiling + groove
lip); nozzle/bed temps `[U]` typical PETG-CF (250–260 / 70–80 °C). Every
bbox fits 256³ with margin.

## BOM status

- M4 ball plunger: UK sources carried from D12 — same-day check
  (2026-11-05): Good Hand K0316 ~£2.50 (45 stock), WDS 823 ~£6.23
  (stock<10), Ross Handling ~£6.72. Ball Ø2.5 vs CAD Ø4 `[U bench fit]`.
- Horn mount: 4× M3 ISO 7380 (Ø3.4 PCD14 horn holes, as stock) +
  stock horn centre screw `[U length]`.
- Pen: 2× M3 grub self-tap `[U]`.
- Pogos: UK-sourced today — P75-series test probes (~Ø1.36 barrel,
  Amazon UK £4.99–£10.99/100, PicClick £7.81/100); barrel vs Ø1.8 bore
  `[U fit]`; **optional — the pen tool is passive**.

## Still `[U]` (unchanged from D11/D12, plus this stage's)

- PETG-CF allowables + printer temps + INFILL_EFF 0.6 mass model.
- Print-time estimates (~1 / ~1 / ~3–4 h) — slicer gives real numbers.
- Slicer pass / support coverage — `[U bench]`.
- Detent plunger bench fit; pogo barrel fit in Ø1.8 bores; horn-screw
  length; M3 grub self-tap.
- TCP repeatability ≤0.5 mm claim — the bench card measures it.
- F9: `tool_grip` payload caveat — pen-only pack, called out in BENCH.md.

## 3MF note

Optional task 5: no 3MF-capable toolchain on this Mac (no Bambu Studio /
PrusaSlicer / 3MF writer found; Blender 4.5 exports no 3MF). Per the stage,
STL + PRINT.md is the pack — skipped without installs.

## Recommendation

Print the three parts in PETG-CF per PRINT.md, run the BENCH.md card,
and record twist feel + the ×20 TCP-spread measurement in
`STATUS-toolchgfix.md`'s bench list — that number decides the
adopt/reject call from D10.
