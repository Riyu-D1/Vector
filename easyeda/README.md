# SOMA Carrier v1.3 — EasyEDA Pro rebuild extension

Rebuilds the SOMA v1.3 carrier board **natively inside EasyEDA Pro** (no KiCad
import) using the official Pro extension API. Designed for EasyEDA Pro
**v3.2.209** (Intel Mac build tested against its bundled `pro-api` 0.3.59
declarations).

Deliverable: `easyeda/extension/dist/soma-carrier-v13-builder_v1.0.0.eext`

## What it does when run

1. Generates library parts in your **personal library**: ~20 footprints +
   ~40 symbols + 55 devices (`SOMA-*` names), built from the extracted
   v1.3 geometry — pads land exactly where KiCad had them.
2. Creates project **"SOMA Carrier v1.3 (EasyEDA)"** with a schematic and
   PCB linked as one board.
3. Draws the schematic: all 55 parts in 7 labelled blocks (power +
   reverse polarity, 5 V/MCU supply, status LEDs + buzzer, ESP32-S3
   sockets, CAN + BUS-A, motor relay + e-stop, peripherals), every
   connected pin wired to a named net flag / net port.
4. Pushes to PCB (`importChanges`), places all components at their
   v1.3 positions, draws the 135×115 mm outline, 4× M3 mounting holes
   (non-plated), replicates all ~1800 track segments and 164 vias,
   adds GND pours on both copper layers, and saves.

## Install & run (once)

1. Open **EasyEDA Pro 3.2**.
2. If you have never used the personal library: open the **Libraries**
   panel and create a personal library first (the extension writes its
   generated `SOMA-*` parts there; it warns and stops cleanly if none
   exists).
3. **Settings → Extensions → Extension Manager → Import** → choose
   `easyeda/extension/dist/soma-carrier-v13-builder_v1.0.0.eext`.
4. Enable the extension if prompted (it needs document + library
   permissions — it creates projects/documents/library items).
5. From the **SOMA v1.3** top menu → **Build SOMA Carrier v1.3…**
6. Wait for the progress bar to finish (routing ~1800 segments takes a
   few minutes) and read the final summary dialog.

> Run it **once**, on a clean editor. It is not idempotent — a second run
> creates another project and duplicate `SOMA-*` library parts.

## After it finishes — verify

- Progress dialog shows `tracks placed: ~1815/1815` and no `FATAL`.
- PCB: J16/XT60 should sit at the **top-left** edge, motor terminals
  J18/J20 at the **bottom**, mounting holes in the four corners.
- If the layout appears **vertically mirrored**, the Y-axis convention
  differs on your build: edit `src/coords.ts` (`FLIP_Y = false`),
  `node easyeda/extension/build.mjs`, and re-import the `.eext`.
- Run **Design → Check DRC** and **Nets → netlist** to confirm all 37
  nets connected (ratsnest should be empty).

## Development layout

```
easyeda/
  extract/extract.py        # KiCad PCB -> JSON extractor (source of truth)
  extract/board-data.json   # extracted data for inspection
  extension/
    src/index.ts            # menu entry (run/about)
    src/run.ts              # orchestrator
    src/schplan.ts          # pure schematic layout planner
    src/pcbplan.ts          # pure PCB planner (mil, y-flip)
    src/eda-source.ts       # SYMBOL/FOOTPRINT doc-source generators
    src/coords.ts           # KiCad mm -> EDA mil transforms (FLIP_Y)
    src/parts-table.ts      # ref -> block/pin-names/LCSC notes
    src/board-data.ts       # generated from the extractor
    src/api-types.d.ts      # vendored v3.2.209 bundled API types
    test/run-tests.mjs      # headless checks (18)
    build.mjs               # esbuild + zip -> .eext (no npm install)
    test/build-test.mjs     # bundles & runs tests
  _research/                # sdk clone + extracted app assets (not shipped)
```

## Rebuild / test

```bash
cd /Users/deepakdiwan/Vector-wt/easyeda
python3 easyeda/extract/extract.py          # regenerate board-data
node easyeda/extension/build.mjs            # rebuild .eext
node easyeda/extension/test/build-test.mjs  # headless tests (esbuild+node)
```

Type-check (vendored SDK typescript):

```bash
easyeda/_research/easyeda-api-sdk/node_modules/.bin/tsc \
  -p easyeda/extension/tsconfig.json
```
