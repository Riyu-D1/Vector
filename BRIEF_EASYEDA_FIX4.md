# Fix 4: draw ALL footprints (system library unusable), then make the full build robust

Read REPORT_EASYEDA.md and the FIX1-3 briefs. Same rules (branch easyeda-pro-carrier only, no force push/PR/merge, never invent data, don't touch ~/Vector, read-only on ~/Documents/EasyEDA-Pro).

## v1.3.0 real-GUI diagnostics (just now)
- Drawn footprint: WORKS (pads persist, 27k-char DOCHEAD source, save/close ok).
- Drawn symbol: WORKS — 5 primitives, 2 pins, sch_Document.save true, closed, REOPENED -> 2 pins, 3742-char source.
- System library: search works (hits have uuid + lib=0819f05c...), but lib_Footprint.get(sysUuid, sysLib) FAIL, lib_Footprint.copy FAIL, lib_Device.create in 'SOMA' with a system footprint association FAIL. Errors printed as "[object Object]" — fix error formatting to JSON.stringify / e.message.
- Also: lib_Device.create('SOMA', ...) failed — this may be the library uuid arg: search reports libraryUuid "SOMA" but get reports "". Test lib_Device.create with a SOMA-drawn symbol + SOMA-drawn footprint (the diag KEEP items) and print the real error. Devices MUST work for the build.

## Do
1. Force all 26 footprint keys onto the proven draw-in-editor path (disable system-footprint use; keep the code behind a flag off by default). Undo K1 padmap swap since we now draw KiCad-exact pads (identity mapping everywhere). Keep LCSC numbers only as BOM attributes where previously verified.
2. Fix device creation: Diagnostics must create a device from a drawn symbol + drawn footprint in SOMA and read it back (get -> association shows both). Figure out the correct libraryUuid arg (try 'SOMA', the search hit libraryUuid, undefined/personal) and use what works.
3. Then check the downstream build path with Diagnostics too, minimal: create a tiny test project, place that one device on the schematic (sch_PrimitiveComponent.create), importChanges to PCB, confirm the PCB component has pads (getAllPinsByPrimitiveId), draw one track, save. Print each step with real error text. Keep artifacts.
4. Make the Build resumable/idempotent (skip verified tagged items) and show "part N/55" in the progress title.
5. Rebuild as v1.4.0, tests pass, copy to ~/Downloads (delete older soma-carrier .eext there), commit + push origin easyeda-pro-carrier, append "Fix 4" to REPORT_EASYEDA.md with exact user steps.
