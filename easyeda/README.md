# SOMA Carrier v1.3 — EasyEDA Pro rebuild extension

Rebuilds the SOMA v1.3 carrier board **natively inside EasyEDA Pro** (no KiCad
import) using the official Pro extension API. Designed for EasyEDA Pro
**v3.2.209** (Intel Mac build tested against its bundled `pro-api` 0.3.59
declarations and a live HALF_OFFLINE install).

Deliverable: `easyeda/extension/dist/soma-carrier-v13-builder_v1.1.0.eext`

## What it does when run

1. Builds library parts in a writable library (personal `SOMA` library if
   present): 26 footprints + ~40 symbols + 55 devices (`SOMA-*` names),
   built from the extracted v1.3 geometry — pads land exactly where KiCad
   had them. Footprints are drawn on an open footprint-editor tab via
   `pcb_PrimitivePad`/`pcb_PrimitivePolyline` and saved; symbols go through
   `lib_Symbol.updateDocumentSource`. Existing `SOMA-*` items are **reused
   by title** — re-runs do not duplicate (empty footprints are redrawn).
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

Every `eda.*` call is time-bounded — a hang surfaces as a warning in the
final dialog instead of freezing, and every step is written to the system
log (prefix `[SOMA]`). If a footprint cannot be drawn the part falls back
to board-level free pads so copper/nets stay correct.

## Install & run

1. Open **EasyEDA Pro 3.2**.
2. If you have never used the personal library: open the **Libraries**
   panel and create a personal library first (e.g. named `SOMA`; the
   extension writes its generated `SOMA-*` parts there; it warns and
   stops cleanly if none exists).
3. **Settings → Extensions → Extension Manager → Import** → choose
   `easyeda/extension/dist/soma-carrier-v13-builder_v1.1.0.eext`
   (import over v1.0.0 replaces it — same extension uuid).
4. Enable the extension if prompted (it needs document + library
   permissions — it creates projects/documents/library items).
5. **Optional but recommended first**: SOMA v1.3 menu →
   **Diagnostics (one-footprint round-trip)** — a ~10-second test that
   creates a throwaway footprint, draws a pad + silk, saves, re-reads
   `dataStr`, deletes it, and reports exactly which API step fails.
6. From the **SOMA v1.3** top menu → **Build SOMA Carrier v1.3…**
7. Watch the progress bar title — it shows the current step/part — and
   read the final summary dialog. Routing ~1800 segments takes a few
   minutes.

Re-runs are safe for the library (titles are reused) but each run still
creates a **new project** — delete older `SOMA Carrier v1.3 (EasyEDA)`
projects if you only want the latest.

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
    src/index.ts            # menu entries (run/diagnose/about)
    src/run.ts              # orchestrator (timeout-wrapped eda calls)
    src/fpdraw.ts           # pure footprint -> primitive-op planner
    src/schplan.ts          # pure schematic layout planner
    src/pcbplan.ts          # pure PCB planner (mil, y-flip)
    src/eda-source.ts       # SYMBOL doc-source generator
    src/coords.ts           # KiCad mm -> EDA mil transforms (FLIP_Y)
    src/parts-table.ts      # ref -> block/pin-names/LCSC notes
    src/board-data.ts       # generated from the extractor
    src/api-types.d.ts      # vendored v3.2.209 bundled API types
    test/run-tests.mjs      # headless checks (19)
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

## Notes on the v3.2.209 API (measured, not documented)

- `lib_Footprint.getDocumentSource` has **no registered handler** in this
  build — the RPC never resolves (root cause of the v1.0.0 hang at 1%).
- `lib_Footprint.updateDocumentSource` only accepts the segmented 3.0/efoo
  wire format, not the stored `FOOTPRINT 1.3` grammar.
- `lib_Symbol.get/updateDocumentSource` do work (they go through
  `loadDocJsonByUuidAndPath`, not the editor preview path).
- `lib_Footprint.openInEditor` + `dmt_EditorControl.waitForDocumentReady`
  + `pcb_Primitive*` + `pcb_Document.save` is the supported route for
  footprint content; `vi()` accepts `re.FOOTPRINT` documents.
- Footprint pad rotation is local: `pad.rot - part.rot` (extractor pads
  carry absolute rotation; lx/ly are already rotation-baked).
- `pcb_PrimitivePolyline` cannot draw courtyard layer 48 — skipped.
- Search results are fuzzy: reuse only on exact (case-insensitive) title
  match — the app normalises titles to lowercase.
