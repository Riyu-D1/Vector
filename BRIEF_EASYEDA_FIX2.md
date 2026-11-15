# Fix 2: diagnostics show saves "succeed" but content is empty

Read BRIEF_EASYEDA.md, BRIEF_EASYEDA_FIX1.md and REPORT_EASYEDA.md first. Same rules (branch easyeda-pro-carrier only, no force push/PR/merge, never invent data, don't touch ~/Vector, don't modify EasyEDA data files directly — read-only inspection of ~/Documents/EasyEDA-Pro is fine).

## Real GUI diagnostics output from v1.1.0 (user ran it just now)
All API-surface probes OK. personal=none; libraries=SOMA; using library "SOMA".
create footprint SOMA-DIAG-83016 -> 985a0276… (96ms)
openInEditor -> tab 985a0276… (4690ms)
waitForDocumentReady -> undefined (20071ms)   <- looks like it TIMED OUT (~15s+), not ready
activateDocument -> true
pad.create -> ok id=ada23dedb6d9
polyline.create -> ok
save -> true
closeDocument -> true
verify dataStr -> EMPTY/missing
cleanup delete -> true
create symbol SOMA-DIAG-SYM-80191 -> 3347c3e3…
symbol updateDocumentSource -> true
symbol dataStr -> EMPTY/missing
cleanup delete -> true

## Do
1. Determine whether content is really not saved or the verify reads the wrong thing: e.g. lib_*.get may not return dataStr; content may live in another table/column of SOMA.elib (check documents/resources/history_data tables, the components row's docType/dataStr after a GUI-made footprint) or be saved asynchronously. Change Diagnostics to NOT delete the test items (keep them, name SOMA-DIAG-KEEP-*), and to read back via several routes (lib get, search, and report what fields come back), so we can inspect SOMA.elib afterwards.
2. Check waitForDocumentReady semantics (it returned undefined after ~15s: timeout?). Is the pad created in the right doc (the footprint tab) or did it go into some other active doc? Verify the active doc uuid/type before drawing (dmt_SelectControl / getCurrentDocumentInfo or equivalent).
3. Check whether the symbol grammar we write is accepted (updateDocumentSource true but empty means probably rejected/ignored) — compare with a symbol from the bundled easyeda-std lib and the exact format the app stores.
4. Strongly reconsider the system-library route: lib_Device.getByLcscIds / search in the system library works in this build per probes. If standard footprints (THT headers, resistors, caps, LEDs, diodes, TO-92, TO-220, screw terminals, XT60, etc.) exist there, place those and only custom-draw the few that don't. Pad numbering must map to KiCad pad nets; verify per part.
5. Rebuild as v1.2.0, tests pass, copy .eext to ~/Downloads (delete older soma-carrier .eext files there), commit + push to origin easyeda-pro-carrier. Append "Fix 2" to REPORT_EASYEDA.md with findings and exact user steps (Diagnostics first).
