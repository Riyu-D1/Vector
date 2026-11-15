# REPORT_EASYEDA — SOMA Carrier v1.3 rebuild as an EasyEDA Pro extension

Status: **built and headlessly verified — not yet run inside the EasyEDA GUI**
(I cannot click inside EasyEDA; see "Verification status" below).

## What was built

An EasyEDA Pro extension (`.eext`) that recreates the SOMA v1.3 carrier
board natively inside EasyEDA Pro 3.2.209, plus the extractor that feeds
it data. Source of truth: `order/pcb13_fix/soma-carrier-v13.kicad_pcb`
(there is no KiCad schematic — the netlist is derived from pad nets, as
instructed).

Files:

```
easyeda/extract/extract.py                     KiCad10 s-exp → JSON extractor
easyeda/extract/board-data.json                extracted data (inspectable)
easyeda/extension/extension.json               extension manifest (eda ^3.2.0)
easyeda/extension/src/index.ts                 entry: run/about menu fns
easyeda/extension/src/run.ts                   orchestrator
easyeda/extension/src/schplan.ts               schematic layout planner (pure)
easyeda/extension/src/pcbplan.ts               PCB plan builder (pure)
easyeda/extension/src/eda-source.ts            SYMBOL/FOOTPRINT source gen
easyeda/extension/src/coords.ts                mm→mil, y-flip, rotation
easyeda/extension/src/parts-table.ts           per-ref blocks/pin names/LCSC
easyeda/extension/src/board-data.ts            embedded board data (generated)
easyeda/extension/src/board-data-types.ts
easyeda/extension/src/api-types.d.ts           vendored v3.2.209 bundled types
easyeda/extension/build.mjs                    esbuild+jszip → .eext
easyeda/extension/test/run-tests.mjs           18 headless checks
easyeda/extension/test/build-test.mjs          test bundler+runner
easyeda/extension/dist/index.js                bundled extension (379 KB)
easyeda/extension/dist/soma-carrier-v13-builder_v1.0.0.eext   ← deliverable (53 KB)
easyeda/README.md                              user steps
easyeda/_research/                             SDK clone + app-asset extracts
                                               (gitignored — local only)
```

## How it works

1. **Library generation** — the extension generates `SOMA-*` footprints,
   symbols and devices in the personal library via
   `lib_Footprint/Symbol/Device.create` + `updateDocumentSource`, using
   the document-source grammar reverse-engineered from the app's bundled
   `easyeda-std.elib`. Footprint geometry is **per (footprint,rotation)**
   with the component's KiCad rotation baked into pad coordinates, so
   every component is placed at rotation 0 and no rotation-sign
   convention is involved.
2. **Project/board** — `dmt_Project.createProject("SOMA Carrier v1.3
   (EasyEDA)")` → `dmt_Schematic.createSchematic` → `dmt_Pcb.createPcb`
   → `dmt_Board.createBoard` (exact flow from the bundled API docs).
3. **Schematic** — `sch_PrimitiveComponent.create` per part; designator +
   value via `modify`. Every connected pin gets a named wire stub plus a
   net flag (power/GND) or BI net port (signals); the stub wire itself
   carries the net name so connectivity survives even if flag/port
   creation fails. Parts are grouped into 7 labelled blocks.
4. **PCB** — `pcb_Document.importChanges(schUuid, force=true)` → all
   components moved to v1.3 anchors (mil, y-flipped); missing parts are
   created directly from their footprint + `setState_Net` per pad.
   Board outline `pcb_PrimitivePolyline` on layer 11; 4 M3 mounting holes
   as non-plated pads on layer 12; **all 1,815 non-degenerate track
   segments** replicated via `pcb_PrimitiveLine`, 164 vias, both GND
   pours, board silk labels; `pcb_Document.save()`.

## Coordinate handling (the one assumption to eyeball)

KiCad: mm, +Y down. EasyEDA PCB documents: mil, **+Y up** ("右上方为 XY
的正方向" — bundled docs). The extension maps every point `(x,−y)·39.3701`
and every angle `−θ`. This is a single switch — `FLIP_Y` in
`src/coords.ts`. If the produced board appears vertically mirrored,
set `FLIP_Y=false`, rebuild, re-import.

## Part substitutions / LCSC notes

`bom.csv` contains **no LCSC C-numbers** (generic UK-sourced THT), so
nothing could be placed "by LCSC part number". Instead every part gets a
generated KiCad-exact footprint (pad positions are what actually matter;
e.g. the 2N2222As and VS1838B sit on 0.1″ header-strip sockets, and the
relay uses a custom Form-A footprint — no catalogue footprint matches).
Verified LCSC equivalents found in the bundled system library, recorded
in `src/parts-table.ts` for BOM reference only (not used for placement):

| ref | part | LCSC equivalent (verified present) |
|-----|------|-----------------------------------|
| K1  | SRD-12VDC-SL-A (Form A) | C93716 |
| Q1, Q3 | 2N2222A | C118536 |
| D5  | 1N4007 | C2457 |
| Q2  | IRF4905PBF | C2564 |

No other C-numbers were assumed or invented.

## Netlist fidelity

All 37 named nets and all 177 pads are preserved 1:1. Spot-checked in
tests: `K1: 1:+12V 2:RLY_LOW 3:+12V_MOT 5:+12V` (Form-A pinout per
`gen_pcb.py`), `Q2: 1:RP_GATE 2:+12V_SW 3:+12V_RP`, `U2` (TJA1051) pins
1–8. 25 pads are intentionally unconnected (unused DevKitC socket pins,
spare header pins) — identical to the KiCad board.

## Verification status

Verified headlessly (all real, no GUI claims):

- `tsc -p tsconfig.json` — clean against the **vendored v3.2.209 bundled
  API declarations** (`src/api-types.d.ts`, copied from the installed
  app's `pro-api/0.3.59.1ca9efb5`).
- 18 checks in `test/run-tests.mjs` pass, including: extracted counts
  (55 parts/4 holes/1836 tracks/164 vias/2 zones/37 nets), transform
  math, generated source grammar (DOCTYPE/PAD/PIN records parse and
  match elib conventions), pad-local+anchor = absolute invariant for
  rotated and unrotated parts, schematic coverage of every connected
  pin, and a mock-`eda` run of the whole pipeline asserting the exact
  API call sequence (55 devices, 55 placements, 152 net labels, 1815
  tracks, 164 vias, 4 NPTH pads, 2 pours, 1 outline, both saves).

NOT verified (impossible without GUI access):

- Any API call at runtime (the extension has never executed inside
  EasyEDA). Every call used was confirmed present in the installed app's
  bundled v3.2.209 declarations and docstrings — but behaviour,
  permission prompts and failure modes are unproven.
- Y-flip convention on this build (single-switch fix documented above).
- Whether `updateDocumentSource` accepts the "1.3"/"1.0" elib grammar
  verbatim (the code reads each new item's template and reuses its
  DOCTYPE line; grammar assumed identical).
- Net port/flag symbol resolution and orientation.
- `importChanges` acceptance of generated components.

## Known gaps / honest limitations

- **21 zero-length track segments** in the KiCad source are skipped
  (degenerate `(start==end)` artifacts).
- Footprint mask/paste-expansion FILL records (elib layers 49–51) are not
  emitted; assumed editor-computed. Electrical connectivity unaffected.
- Silk inside footprints is simplified (arcs flattened to polylines);
  board-level silk text is best-effort.
- Mounting holes are free NPTH pads, not schematic/BOM parts (matches
  KiCad, where they are mechanical footprints outside the netlist).
- K1 pad map: `STATUS-pcb13.md` contains an older conflicting relay
  description; the extracted mapping follows `gen_pcb.py`'s corrected
  Form-A pinout, which the kicad_pcb itself confirms. Kept as authored.
- ESP32 DevKitC socket strips genuinely overhang the west board edge in
  v1.3 (pads to x=−31 mm); replicated faithfully — not a bug.
- Extension is not idempotent; run once on a clean state.
- Track creation is ~1,815 API calls — expect a few minutes runtime.

## Exact user steps

See `easyeda/README.md`. Short version: create a personal library →
Settings → Extensions → Extension Manager → Import the `.eext` →
**SOMA v1.3** menu → **Build SOMA Carrier v1.3…** → wait for the summary
dialog → DRC-check.

---

# Fix 1 — real-GUI run hung at 1% during library generation (v1.1.0)

## Symptom (measured on EasyEDA Pro 3.2.209, HALF_OFFLINE)

- Run stalled immediately after the library lookup succeeded; progress
  title froze at an early step forever.
- `~/Documents/EasyEDA-Pro/libraries/SOMA.elib` afterwards contained
  exactly two `components` rows — `soma-pinheader_1x02_p2.54mm_vertical-r0`
  and `soma-c_disc_d5.0mm_w2.5mm_p2.50mm-r0` — `docType=4`,
  **`dataStr` empty (0 bytes)**. `create` succeeded; content never landed.
- Warn log: `unhandledRejection {}`, and on the second run
  `POST /api/v2/components/add → {"code":1000001,"msg":"重复数据"}`
  (duplicate title — v1.0.0 was not re-run safe).

## Root cause (verified against the bundled app code, not guessed)

`src/run.ts` (v1.0.0) created footprints with
`create → getDocumentSource → updateDocumentSource`. In this build:

1. **`lib_Footprint.getDocumentSource` has no registered handler** in
   `LIB_Footprint`'s RPC map (pro-ui `ui.js`). The `rpcCall` promise
   never settles — no rejection, no timeout. That is the freeze: the
   extension awaited a promise that can never resolve, right after
   `create` — matching the two empty rows observed (created, never
   written, never errored).
2. Even if it did resolve, **`lib_Footprint.updateDocumentSource` only
   accepts the segmented 3.0/efoo wire format** (`DOCHEAD` JSON segments,
   `head||data`), not the stored `FOOTPRINT "1.3"` line grammar we
   generated — so the write path was dead either way. Its documented
   flow is `create → openInEditor → getDocumentSource → edit →
   updateDocumentSource → close`, and when no live editor tab exists it
   boots a hidden preview iframe (`rpcInitFrameInfo → pcb/decode →
   pcb/saveCompiler`) — a path that cannot be relied on in HALF_OFFLINE.
3. `lib_Symbol.*` is unaffected — symbol updates go through
   `loadDocJsonByUuidAndPath` (library worker), which is registered and
   works. Only the footprint path was broken.

Secondary defects found and fixed while in here:

- Second runs hit `重复数据` — nothing searched/reused by title before
  creating.
- `polygonSource` emitted a trailing `'L'`; the app's polygon validator
  requires ≥2 numbers after every `'L'` — every outline/pour polygon
  would have failed validation.
- Extracted pad `rot` is absolute (component rot baked in); inside a
  footprint doc it must be `rot - part.rot`, or rotated parts' pads get
  double-rotated. The old `footprintSource` had the same bug.
- `pcb_PrimitivePolyline` cannot create layer-48 courtyard polylines
  (not in `TPCB_LayersOfLine`) — courtyard op dropped.

## What changed (v1.1.0)

- **Footprints are now drawn, not source-pasted.** New pure module
  `src/fpdraw.ts` turns a part into ordered primitive ops; `run.ts`
  executes them on a real footprint-editor tab:
  `create/reuse → openInEditor → waitForDocumentReady → activateDocument
  → pcb_PrimitivePad/pcb_PrimitivePolyline → pcb_Document.save →
  closeDocument`. (`vi()` accepts `re.FOOTPRINT` docs — all `pcb_Primitive*`
  APIs work there.)
- **Symbols** keep `lib_Symbol.updateDocumentSource` (that path works);
  existing non-empty symbols are skipped.
- **Reuse-first everywhere.** `lib_*.search` + exact case-insensitive
  title match before every create (the app normalises titles to
  lowercase); a failed create falls back to search (covers
  duplicate-title races). Empty `dataStr` footprints are redrawn in
  place — the two stale `soma-*` rows get filled by the next run instead
  of duplicated. No more `重复数据`.
- **Every `eda.*` call is time-bounded** (`call()` wraps each RPC with a
  per-call timeout); a hang becomes a named warning, not a freeze.
  `eda.sys_Log.add` writes a `[SOMA]` step log; the progress-bar title
  shows the current step/part.
- **Free-pad fallback.** If a footprint cannot be given content, the
  part is still placed on the board as absolute-position pads + silk +
  designator, so copper/net connectivity survives a partial library
  failure.
- **Diagnostics menu item** (`diagnose`, all three menus): API-surface
  probe → library discovery → one-footprint round trip (create, open,
  pad, silk, save, close, re-read `dataStr`, delete) → symbol round
  trip. ~10 s; reports the exact step that fails.
- Tests updated: footprint-op tests replace footprint-source tests;
  mock-eda smoke test now asserts the whole new call sequence (26
  footprints via editor tabs, 0 calls to the dead `getDocumentSource`/
  `updateDocumentSource` footprint APIs, per-footprint saves). 19/19
  pass; `tsc --noEmit` clean.

## What to do in EasyEDA (exact steps)

1. **Import** `easyeda/extension/dist/soma-carrier-v13-builder_v1.1.0.eext`
   (copied to `~/Downloads`; same extension uuid, replaces v1.0.0).
2. **SOMA v1.3 → Diagnostics (one-footprint round-trip)** — expect
   `verify dataStr -> … chars` and `cleanup delete -> true`. If any line
   says MISSING/FAIL, that line names the broken call — send it back.
3. Optional cleanup of the two stale rows: the run now **reuses** them
   by title and draws content into them, so deletion is unnecessary —
   but if you prefer a clean slate, delete
   `soma-pinheader_1x02_p2.54mm_vertical-r0` and
   `soma-c_disc_d5.0mm_w2.5mm_p2.50mm-r0` in the library editor first.
4. **SOMA v1.3 → Build SOMA Carrier v1.3…** — footprint tabs will open
   and close while library parts are drawn (26 ×). The summary dialog
   lists any per-call warnings; the `[SOMA]` entries in the system log
   give the full step trace.
5. If a footprint-editor tab is left open at the end (a
   `closeDocument` warning will say so), close it manually — content is
   already saved.

## Still open / next candidates

- If `openInEditor` itself misbehaves on this build, diagnostics will
  show it on the `openInEditor` line — the alternative worth trying next
  is generating the segmented 3.0 wire format directly, or using
  `lib_Device.getByLcscIds` system-library parts for the standard
  footprints (C93716/C118536/C2457/C2564 mappings in
  `src/parts-table.ts` remain available).
- Mounting holes, pours, silk-text approximation, and the free-pad
  fallback are unchanged from the notes above.
