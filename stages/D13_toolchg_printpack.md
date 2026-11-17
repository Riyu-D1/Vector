# Stage D13 — Print-ready pack for the tool-changer prototype (master + tool plate + pen)
> Rules 0.1-0.10 of `~/Vector/ARM_KNUCKLE_V5.md` apply. Step 0: `cd ~/Vector && /usr/bin/git fetch origin --tags`; create worktree `~/Vector-wt/toolchgprint` on new branch `arm-toolchg-print` from `origin/arm-toolchg-fix` (tip of D12, tag `toolchgfix-done`, commit da55594). Work only under `toolchg/print/`. Tag `toolchgprint-done`, push branch+tags, STOP. Do not merge. Do not buy anything.

## Context
D12 closed F1–F8; STATUS says **ready to print prototype**. Print the smallest useful set first: `tc_master`, one `tc_plate` (or the plate fused into `tool_pen`), and `tool_pen`. Read `toolchg/STATUS-toolchgfix.md`, `toolchg/tc_params.py`, `toolchg/p_toolchg.py`, `toolchg/build_toolchg.py`. CAD Python: cradlefix venv if soma venv missing. Bambu A1: 256×256×256 mm usable, PETG-CF only.

## Goal
A folder the user can drop into Bambu Studio / the A1 and print, plus a short assembly + bench card. No redesign.

## Tasks
1. Rebuild the three print parts (`tc_master`, `tc_plate`, `tool_pen`) and export clean STL (and STEP) into `toolchg/print/stl/` and `toolchg/print/step/`. Orient each STL for the STATUS print orientation (master −a face down; tool_pen plate-face down; plate accordingly). Name files clearly: `tc_master.stl`, `tc_plate.stl`, `tool_pen.stl`.
2. Print settings card `toolchg/print/PRINT.md`: filament PETG-CF; nozzle/bed temps as typical for PETG-CF on A1 `[U]` if not verified live — mark `[U]`; layer 0.2 mm; walls ≥4; infill ≥40% gyroid or similar for the coupling; supports: call out that master lug −a faces need support (D12 bench note) and suggest support interface / paint-on; estimate filament g and time per part from volumes (master ~5.8 g, plate ~5–6 g, pen ~22 g solid-equivalent — state printed estimate with INFILL_EFF). Bed fit check: each bbox fits 256³ in the stated orientation.
3. Hardware kit for this prototype only (`toolchg/print/BOM-prototype.md`): M4 ball plunger or Ø4 ball+spring+M4 grub (use the live UK sources D12 found: Good Hand K0316 ~£2.50 / WDS 823 ~£6.23 — re-check or mark date); M3 screws/inserts for horn mount; M3 grub for pen; 5× pogo pins if you can source UK today else `[U]` with the CAD bore Ø1.8. Qty 1 set. No invented prices.
4. Assembly + first-bench card `toolchg/print/BENCH.md`: assemble master on J6 horn; fit detent; seat pen tool by hand; twist lock/unlock ×20; measure TCP repeatability with the pen on paper (target <0.5 mm); note the F9 payload caveat (do not hang 0.5 kg on the grip tool yet — this pack is pen-only). Safety: small spring/ball parts, 12 V bus later not in this pack.
5. Optional: a single 3MF or Bambu project if the toolchain on the Mac can write one without installs; otherwise STL+PRINT.md is enough. Screenshot or render of the three parts on the bed (top view) into `toolchg/print/bed_preview.png` (<1.5 MB).
6. `toolchg/print/STATUS-print.md`: file list, masses, settings, BOM status, anything still `[U]`. Commit, tag, push, STOP.
