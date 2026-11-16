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

---

# Fix 2 — saves "succeeded" but verify reported empty (v1.2.0)

## Symptom (real GUI run of v1.1.0 diagnostics on 3.2.209)

- All API probes OK; library `SOMA` selected (`personal=none`).
- Footprint round-trip: `create` ✓ → `openInEditor` ✓ (4.7 s) →
  `waitForDocumentReady` → **undefined after ~20 s (timeout)** →
  `activateDocument` ✓ → pad ✓ → polyline ✓ → `save` ✓ → `close` ✓ →
  **`verify dataStr → EMPTY/missing`** → `delete` ✓.
- Symbol round-trip: `create` ✓ → `updateDocumentSource` ✓ →
  **`dataStr → EMPTY/missing`** → `delete` ✓.

## Root cause — the verify read a field that does not exist

`lib_Footprint.get()` / `lib_Symbol.get()` (and `search()`) return
**metadata only**. The `ILIB_FootprintItem` / `ILIB_SymbolItem`
interfaces in this build have `uuid/name/libraryUuid/description/…` —
**no `dataStr` property**. The v1.1 diagnostic read `item.dataStr`, got
`undefined`, and reported EMPTY. It says nothing about whether content
persisted. (The two stale `soma-*` component rows in `SOMA.elib` with
empty `dataStr` are a separate v1.0.0 artifact — footprint docs in Pro
are stored as separate `documents`/`resources` records, not inline
`dataStr`.)

Two more confirmed dead ends, verified against the `pro-ui` handler map
(not just the type declarations):

1. **`waitForDocumentReady` and `getDocumentReadyState` have NO
   registered handlers** in 3.2.209 — the call hangs forever and the
   ~20 s "undefined" was our own timeout wrapper firing. The SDK
   docstring also explains the mechanism: lazy-opened tabs only finish
   loading **after `activateDocument`**, and v1.1 waited before
   activating — a guaranteed stall even where a handler exists.
2. **`lib_*.getDocumentSource` has no handler** (same class of hang as
   Fix 1). Documented in `api-types.d.ts`, absent at runtime.

The working readback path in this build is therefore:

```
openInEditor -> activateDocument -> poll
  dmt_SelectControl.getCurrentDocumentInfo() until uuid/type match ->
  sys_FileManager.getDocumentSource() on the ACTIVE document
```

`sys_FileManager.getDocumentSource()` is registered and reads the
currently active document's source — this is the route the bundled SDK
examples use.

## Symbols were probably fine all along

Direct inspection confirmed `eda-source.ts` already emits valid Pro
`DOCTYPE/SYMBOL/1.0` JSON-record grammar (`HEAD`, `PART`, `PIN`,
`ATTR`, `POLY`) — the same grammar stored for system symbols. The
"empty" symbol verdict was the same false-negative `dataStr` check.
v1.2.0 keeps the generator and adds a real verify: the first written
symbol is opened, activated, read back via
`sys_FileManager.getDocumentSource()`, and its `"PIN"` records are
counted.

## What changed (v1.2.0)

- **No more `dataStr` verification anywhere.** Content checks now use
  active-doc source reads and primitive counts only.
- **Footprint draw sequence hardened**: `openInEditor →
  activateDocument → poll getCurrentDocumentInfo (uuid match) → count
  pads → draw → re-count → save → close`. If the tab never becomes the
  active doc, drawing is skipped (a warning names it) instead of
  primitives landing in whatever document had focus.
- **`waitForDocumentReady`/`getDocumentReadyState` removed** from the
  build and diagnostics — they have no handlers and hang.
- **`lib_Footprint.getDocumentSource`/`updateDocumentSource` remain
  uncalled** (handler absent / wrong wire format).
- **Re-run safety without re-drawing**: after a verified draw, the
  library item's `description` is tagged `soma:v1.2-drawn` /
  `soma:v1.2-src` via `lib_*.modify`. Later runs skip tagged items; an
  untagged-but-populated footprint is detected by the pad count and
  skipped, never double-drawn.
- **System-library footprints for 21 of 26 keys.** New
  `src/syslib-match.ts` maps every `(footprint, rotation)` key to a
  bundled `easyeda-std` footprint found by geometric pad matching
  (pad count, relative positions under rotation+translation, pad
  numbers, hole ≥ drill). Devices associate the system footprint
  directly (`lib_Device.create` accepts foreign-library uuids) and
  `pcb_PrimitiveComponent.create` places it with a per-key rotation +
  origin offset so system pads land on the KiCad pad positions. The five
  unmatched keys (XT60, blade-fuse direct-solder, 1x22 header, DO-41,
  1.5 mm test point) stay on the draw-in-editor path — see
  `CUSTOM_KEYS` in `syslib-match.ts`.
- **Pad-number domain mapping.** KiCad pad numbers are translated into
  each footprint's numbering before symbol/schematic/PCB net assignment
  (`FpRef.pm`). Identity for all matches except K1: the `hf3ff-012-1hs`
  relay footprint numbers its coil pads swapped, so KiCad 1→sys 2,
  2→1, 3→3, 5→5.
- **Device reuse checks associations.** An existing `SOMA-<ref>` device
  pointing at a stale footprint/symbol uuid is deleted and recreated, so
  re-runs migrate from the old empty-footprint devices to the new
  system-backed ones.
- **Diagnostics rewritten**: items are named `SOMA-DIAG-KEEP-*` and
  **kept** (no delete) for post-run inspection; readback is multi-route
  (lib `get`, `search`, render image, pad count, active-doc source);
  the active doc's uuid/type is printed before drawing; system-library
  probes cover `getSystemLibraryUuid`, a footprint `search`/`get`,
  `lib_Footprint.copy`, and `lib_Device.getByLcscIds`.
- Tests: 22 checks pass, including match-table coverage (every board
  key is in `SYS_FP_MATCH` or `CUSTOM_KEYS`, padmaps cover every pad
  number, worst-fit < 5 mil) and a rewritten mock-eda smoke test that
  asserts the new call sequence (21 sys probes, 5 custom draws, zero
  calls to the unhandled APIs, active-doc polling, tag writes, sys-lib
  device associations, K1 → `hf3ff` uuid).

## What to do in EasyEDA (exact steps)

1. **Import** `easyeda/extension/dist/soma-carrier-v13-builder_v1.2.0.eext`
   (copied to `~/Downloads`; same extension uuid, replaces v1.1.0).
2. **SOMA v1.3 → Diagnostics (keeps test items)** — expect:
   `activateDocument -> true`, `active doc -> type=… uuid=…`,
   `pad.getAll -> 1 pads`, `docSource -> … chars`,
   `symbol docSource -> … chars, 2 PIN recs`, and system-library hits.
   Afterward you'll find `SOMA-DIAG-KEEP-*` footprints/symbols in the
   SOMA library — open one in the library editor to eyeball the pad.
   Delete them whenever convenient.
3. **SOMA v1.3 → Build SOMA Carrier v1.3…** — expect far fewer editor
   tabs (only the 5 custom footprints are drawn; the other 21 come from
   the system library). The summary reports
   `N system + M drawn footprints, K symbols, 55 devices`.
4. Verify the board: all 55 components placed (K1 relay is the HF3FF
   footprint — coil pads intentionally renumbered), mounting holes,
   tracks, vias, pours, then DRC.

## Still open / honest caveats

- System-footprint selection is geometry-verified but not a
  manufacturer-exact substitution in all cases (e.g. the D10 radial cap
  uses a `bd12.5` body — pad pitch and drills match, courtyard is
  larger; the TO-220 uses the horizontal-hole `…-t` variant). Check the
  substitutions that matter for fabrication in `src/syslib-match.ts`.
- The relay's swapped coil numbering is handled by the padmap; if EasyEDA
  imports pin→pad by pin NAME rather than number, K1's coil nets could
  swap — verify RLY_LOW/RLY_SW on the PCB.
- `sys_FileManager.getDocumentSource` reads the ACTIVE doc — if the
  app's notion of "active" differs when tabs are closed programmatically,
  a read could see a stale document; the uuid/type check in
  `waitActiveDoc` guards this.
- The 5 custom footprints still depend on `openInEditor` behaving in the
  library editor; diagnostics exercises exactly that path first.

---

# Fix 3 — symbols save empty; system-library footprint get/copy fail (v1.3.0)

## Symptom (real GUI run of v1.2.0 diagnostics on 3.2.209)

- **Footprint draw path confirmed working end-to-end**: `openInEditor`
  (4.5 s) → `activateDocument` true → active doc type 4, uuid match →
  pad ✓ → polyline ✓ → `pad.getAll` 1 → `getDocumentSource` 27 232 chars
  (`{"type":"DOCHEAD"}||{"docType":"PCB",…}`) → save ✓ → close ✓.
- **Symbols silently empty**: `lib_Symbol.create` ✓ →
  `updateDocumentSource` with the `DOCTYPE/SYMBOL/1.0` line grammar
  (1 165 chars) returned **true** → open/activate (type 2, uuid match) →
  `getDocumentSource` returned **350 chars, 0 `"PIN"` records**. The
  write was accepted and ignored.
- **System-library lookup failed**: system lib uuid
  `0819f05c4eef4c71ace90d822a990e87`; `lib_Footprint.search('hdr-th_2p')`
  → **10 hits OK**; `lib_Footprint.get(mappedUuid, sysLibUuid)` → FAIL;
  `lib_Footprint.copy(mappedUuid, sysLibUuid, SOMA, …)` → FAIL;
  `lib_Device.getByLcscIds(['C2564','C118536'])` → 2 hits (contents were
  not printed by v1.2.0 diagnostics — they are printed in full now).
- Misc: `lib get` returns `libraryUuid ""`, `lib search` returns the
  literal string `"SOMA"` for the personal library under HALF_OFFLINE.

## Root cause

- **The live document source is the segmented `DOCHEAD` format**, the
  same one the PCB doc exposes. The `DOCTYPE/SYMBOL/1.0` *line* grammar
  is what the `.elib` file stores on disk — `updateDocumentSource`
  accepted it but never converted it into live records, so the symbol
  saved with zero pins. Generating `DOCHEAD` segments by hand is fragile;
  the documented route for symbol content is the same one already proven
  for footprints: **draw primitives inside the open library-editor tab**.
  `api-types.d.ts` marks `sch_PrimitivePin` as symbol-editor-only and the
  bundled SDK examples create pins exactly this way
  (`sch_PrimitivePin.create(x, y, num, name, rot, len, null, 'None', 'Passive')`
  inside a `lib_Symbol.openInEditor` tab).
- **The hardcoded footprint uuid + configured system-library uuid pair
  was not the identity `get`/`copy` accept** in HALF_OFFLINE. `search()`
  succeeds and each hit carries its own `uuid` *and* `libraryUuid` —
  those are the values device/pcb associations consume, so the fix is to
  resolve through the hit instead of the constant. No `copy()` into the
  personal library is needed: `lib_Device.create` and
  `pcb_PrimitiveComponent.create` both accept foreign-library uuids
  (verified for associations in the API types; GUI verify pending).

## What changed (v1.3.0)

- **Symbols are drawn, not source-written.** New `src/symdraw.ts` plans
  the same DIP geometry as before (pin pitch 10, half-length-10 pins on a
  100-wide box, name + `PREFIX?` labels) as primitive ops. `run.ts` opens
  each symbol via `lib_Symbol.openInEditor`, activates it, polls
  `getCurrentDocumentInfo` for uuid/type match, then creates
  `sch_PrimitivePin` per pin, `sch_PrimitiveRectangle` for the body, and
  `sch_PrimitiveText` for labels — counting pins via
  `sch_PrimitivePin.getAll` before and after.
- **Two persistence routes.** After drawing, the tab is saved with
  `sch_Document.save()` (the sibling of `pcb_Document.save()` proven by
  the footprint path) **and** the live `getDocumentSource` text is pushed
  back through `lib_Symbol.updateDocumentSource` — the live source *is*
  the segmented DOCHEAD format that call accepts, unlike the 1.0-line
  grammar v1.2 sent. A symbol is `ok` only when the pin count is met and
  at least one write returns true.
- **Reopen-verify, not save-verify.** "Saved" proved nothing in v1.2, so
  the first drawn symbol is closed, reopened, and its pin count checked
  again — only that proves the library item persisted. Old
  `soma:v1.2-src` tags are no longer trusted (they marked writes that
  returned true but produced empty items); symbols are tagged
  `soma:v1.3-drawn` only after a verified draw. Footprints keep their
  `soma:v1.2-drawn`/`soma:v1.3-drawn` trust — that path is proven.
- **System footprints resolve via the search hit.** `resolveSysFootprint`
  calls `lib_Footprint.search(sysFpName, sysLibUuid)` and uses the exact
  hit's `uuid` + `libraryUuid`; `get()` remains only as a fallback when
  search is unavailable. `lib_Footprint.copy` is no longer used.
  Diagnostics prints every hit (name/uuid/libraryUuid), the exact args of
  each probe, and full error payloads instead of `FAIL`.
- **System devices probed end-to-end.** Diagnostics dumps every
  `getByLcscIds` hit including its `symbol`/`footprint` associations,
  fetches one device item, then creates a personal `SOMA-DIAG-KEEP-DEV-*`
  device bound to the system footprint + a fresh symbol and reads it
  back — the same association shape the build uses for all 21 keys.
- **Empty-pad guard on the board.** After `importChanges` moves and
  `pcb_PrimitiveComponent.create` places a part, the component's pin
  count is checked (`getAllPinsByPrimitiveId`); a component that landed
  with 0 pads despite a "resolved" footprint gets the free-pad overlay
  instead of silent missing copper.
- **Correctness over elegance.** If a sys-lib footprint cannot be
  resolved, the key falls back to the proven draw-in-editor path
  automatically; all 26 keys can be custom-drawn if system access stays
  unreliable. K1's padmap (KiCad 1→sys 2, 2→1, 3→3, 5→5) is unchanged and
  now drives symbol pin numbering too, so pin→pad import lands on the
  right copper.
- **Diagnostics rewritten for the new path.** Symbol round-trip prints
  the full empty-doc source, draws pins/box/text, prints the post-draw
  source head + PIN-record count, saves both ways, closes, reopens, and
  counts pins again. All `SOMA-DIAG-KEEP-*` artifacts are kept.
- Tests: **26 checks pass** — new symdraw unit tests (KiCad-domain vs
  fp-domain pin lists, K1 coil swap, op shapes, dedup key) and a
  rewritten mock-eda smoke test asserting the new call sequence (21 sys
  searches, 5 custom draws, 46 unique symbols drawn via primitives with
  pin-count readbacks, one reopen-verify, zero calls to unhandled APIs,
  sys-lib associations on devices and board components, K1 → `hf3ff`).

## What to do in EasyEDA (exact steps)

1. **Import** `~/Downloads/soma-carrier-v13-builder_v1.3.0.eext`
   (same extension uuid, replaces v1.2.0).
2. **SOMA v1.3 → Diagnostics (keeps test items)** — watch for:
   - `EMPTY SOURCE (… chars): …` — the real empty symbol doc;
   - `drew N symbol primitives (0 failed)`, `post-draw source … PIN recs`
     and **`REOPENED -> 2 pins via getAll`** — pins must persist across
     reopen, not just exist in the open tab;
   - `sys search -> 10 hits` with per-hit `uuid=`/`lib=` lines;
   - `sys fp get(hit args) -> {…}` succeeding where `(mapped args)`
     failed, or both failing with the full error text shown;
   - `device.create with sys fp assoc -> uuid …` + `created device read`
     — proves the association resolves.
   Afterwards the `SOMA-DIAG-KEEP-*` footprint/symbol/device sit in the
   SOMA library — open the symbol to eyeball pins/box, then delete all
   three whenever convenient.
3. **Only if diagnostics pass**, run **SOMA v1.3 → Build SOMA Carrier
   v1.3…**. Old `soma:v1.2-src` symbols are redrawn automatically;
   expect `21 system + 5 drawn footprints, ~46 symbols, 55 devices` in
   the summary line (symbol count is the deduplicated pin-set count).
4. Verify the board: 55 components placed, K1 on the `hf3ff` footprint
   with coil pads intentionally renumbered (check RLY_LOW/RLY_SW land on
   the correct pads), mounting holes, tracks, vias, both pours, then DRC.
5. If the summary reports footprint fallbacks or symbol warnings, read
   the `[SOMA]` lines in the system log — every failing call name and
   error payload is logged.

## Still open / honest caveats

- **Headless ≠ GUI.** The 26 checks run against a mock that reproduces
  the observed API contract (search-hit uuids, per-symbol pin
  persistence). Whether `sch_PrimitivePin.create` commits to the library
  via `sch_Document.save`, `updateDocumentSource(liveSource)`, or
  something else entirely is exactly what step 2's reopen-verify decides —
  Diagnostics prints which write route reported success. If *neither*
  persists pins across reopen, that is a hard blocker: report the diag
  output and we switch to generating `DOCHEAD` segments directly via
  `sys_FileManager.setDocumentSource` (probed OK, last resort because the
  segment schema is undocumented).
- Pin shape/type are set to `None`/`Passive` for all pins — electrically
  correct for import mapping; cosmetic clock/power decorations can be
  added later.
- Symbol labels are drawn as plain text (`SOMA-<ref>`, `PREFIX?`); if
  EasyEDA needs proper `Designator`/`Name` *attribute* records for BOM
  fields, `sch_PrimitiveAttribute` is the follow-up — verify in-GUI
  whether the plain texts satisfy the panel.
- If a sys-hit `uuid`/`libraryUuid` pair still fails in
  `lib_Device.create`/board placement, that key auto-falls back to a
  drawn footprint — the summary's `M drawn` count shows how many fell
  back; the diag `device.create with sys fp assoc` line predicts it.
