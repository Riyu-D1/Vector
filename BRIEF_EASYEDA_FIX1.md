# Fix 1: extension hangs at 1% in the real EasyEDA Pro 3.2.209

Read BRIEF_EASYEDA.md and REPORT_EASYEDA.md first for context. Same rules apply (branch easyeda-pro-carrier only, no force push, no PR/merge, never invent part numbers, don't touch ~/Vector).

## What happened in the real GUI (evidence)
- App is in HALF_OFFLINE mode (~/Documents/EasyEDA-Pro/config.json). User made a library "SOMA" -> ~/Documents/EasyEDA-Pro/libraries/SOMA.elib (SQLite). Personal-library lookup failed at first; commit ce85f50 added fallbacks/timeouts (it now finds a library).
- The run then sits at "1%"/early progress forever.
- SOMA.elib `components` table has exactly 2 rows: titles `soma-pinheader_1x02_p2.54mm_vertical-r0` and `soma-c_disc_d5.0mm_w2.5mm_p2.50mm-r0`, docType 4, **dataStr EMPTY (length 0)**. So lib_Footprint.create succeeds but updateDocumentSource never writes and appears to never resolve (hang).
- ~/Documents/EasyEDA-Pro/logs/warn/20261115.log shows `unhandledRejection {}` lines during runs and `json api /api/v2/components/add {"code":1000001,"msg":"重复数据"(duplicate data)}` on the 2nd run (re-creating the same footprint title).
- Progress bar did not update after "1%" (it may not repaint during long awaits — don't rely on it alone).

## Do
1. Inspect SOMA.elib schema read-only (and the app's bundled easyeda-std / example .eprj files) to learn exactly what a valid footprint/symbol/device row's dataStr looks like, and find why updateDocumentSource hangs (wrong grammar? needs the doc opened in an editor tab first? not supported for local libs in HALF_OFFLINE?). Search bundled pro-api docs/examples for the supported way to create a footprint with pads in v3.2 (e.g. open the footprint doc via the editor and use pcb_PrimitivePad.create inside it, or lib_Footprint import APIs).
2. Strongly consider the robust route: use **system library (easyeda-std / LCSC) parts** for placement where a matching footprint exists (lib_Device.search / getByLcscIds in the system library), and only generate custom parts where none exists (relay, ESP32 DevKitC sockets, etc.). Never invent C-numbers; only use ones the API returns. Record every mapping, and check pad numbering vs the KiCad pad nets.
3. Make every eda call time-bounded (timeout -> clear message, not a hang), surface rejections in a final dialog, write a step log via eda.sys_Log (or similar) AND show which step/part it's on in the progress title. Make re-runs safe: reuse existing parts with the same title instead of re-creating (avoid 重复数据).
4. Add a "Diagnostics / dry-run" menu item that tries creating ONE footprint end-to-end and reports exactly which call failed — so the user can test in 10 seconds.
5. Rebuild the .eext, run headless tests, copy the .eext to ~/Downloads/ (overwrite), commit and push to origin easyeda-pro-carrier. Append a "Fix 1" section to REPORT_EASYEDA.md with root cause (or best evidence), what changed, and exact user steps (including deleting the 2 empty soma-* footprints from the SOMA library if needed).
6. Do NOT modify SOMA.elib or any EasyEDA data files directly; read-only inspection only. Don't kill EasyEDA.
