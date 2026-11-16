# FINAL ONE-SHOT: finish the SOMA v1.3 carrier natively in EasyEDA Pro 3.2.209 (deadline: TODAY)

You are in worktree ~/Vector-wt/easyeda, branch `easyeda-pro-carrier`. Only commit and push to this branch. Never touch main.
Read REPORT_EASYEDA.md (all Fix sections) and BRIEF_EASYEDA_FIX5.md first. Everything below supersedes them. Work fast and do not stop to ask questions: make the best decision, log it, and keep going.

## Goal
One `.eext` (v2.0.0). The user imports it into EasyEDA Pro 3.2.209, opens his project "SOMA Carrier v1.3 (EasyEDA)", clicks **SOMA v1.3 → Build SOMA Carrier v1.3…** once, and ends up with:
1. All 26 footprints, symbols and devices in library 'SOMA' (this already works, so reuse it).
2. A complete schematic in the open project: every part placed and every net from the v1.3 KiCad netlist connected, using net labels (not drawn wires) for reliability.
3. A PCB in the same project: board outline, all footprints placed at the v1.3 KiCad positions and rotations (XT60 top-left, motor terminals along the bottom; keep the FLIP_Y logic and verify it), nets assigned to pads, tracks routed at the v1.3 widths where the API allows, and GND pours on both layers.
4. The design passes EasyEDA DRC with zero errors, or anything left is listed with the reason.
5. Gerber/fab output, if the API can export it.

## Facts proven in 3.2.209 (do not re-investigate)
- WORKS: draw footprints in an editor tab (openInEditor → activateDocument → pcb_PrimitivePad/Polyline → pcb_Document.save → closeDocument). Draw symbols with sch_PrimitivePin/Rectangle/Text, then sch_Document.save. lib_Device.create with lib='SOMA' and the assoc ref.
- BROKEN: lib_Footprint.getDocumentSource (hangs), waitForDocumentReady (no handler), updateDocumentSource with the 1.0 grammar, system-library get/copy/assoc, and **dmt_Project.createProject (FAILS)**.
- Wrap every API call in a timeout of at most 10 s. Never wait forever. On failure, log the exact error and try the next fallback.

## Fixes required
A. **Project:** NEVER create a project. Use dmt_Project.getCurrentProjectInfo(). If no project is open, show a dialog: "Open your project 'SOMA Carrier v1.3 (EasyEDA)' first, then run Build again" and stop. Inside the project, reuse the existing schematic/board/PCB documents, or create them with dmt_Schematic / dmt_Board / dmt_Pcb create calls. Try every available create variant (check the API typings in the extension SDK / node_modules for the real 3.2 names) and log which one worked.
B. **Schematic placement:** sch_PrimitiveComponent.create(device from 'SOMA', x, y, rotation) for every designator. Set the designator and value. Connect nets with sch_PrimitiveComponent net flags or net labels placed on the pin ends (read pin positions back from the placed component). Fallback: short wires plus a net label per pin.
C. **PCB:** import the schematic changes into the PCB using whatever 3.2 API exists (e.g. pcb_Document.importChanges or a "update PCB from schematic" call). If none exists, place footprints with pcb_PrimitiveComponent.create and set the pad nets directly. Board outline: pcb_PrimitivePolyline on the BoardOutline layer from the v1.3 Edge.Cuts. Tracks: pcb_PrimitiveLine per KiCad segment (layer, width, net). Vias: pcb_PrimitiveVia. Pours: pcb_PrimitivePour GND on top and bottom. Then rebuild the copper.
D. **Progress UI:** a progress bar or toast per stage, and a final summary dialog with counts (parts placed, nets, tracks, vias, DRC errors) and any failures with their exact error text. Also write the full log to the console and the warn log.
E. **DRC:** call pcb_Drc.check (or the 3.2 equivalent) and include the result in the summary. Fix any real errors in the builder data (not by loosening rules) and re-run.
F. **Diagnostics menu:** keep it, but make it finish in under 30 s and test chain A–C on a throwaway sheet inside the open project, deleting it afterwards.

## Source data
Use the v1.3 KiCad files already parsed by the extension (netlist, positions, tracks, outline). If tracks or outline aren't parsed yet, extend the parser from the .kicad_pcb in the repo. KiCad pin numbers are the single source of truth, so relay K1 pin order must match the KiCad footprint.

## Verify before finishing
- Run the existing tests (26 must still pass). Add tests that check, for the v1.3 data: all designators present, every net has at least 2 pins, the track count equals KiCad's, and the outline is closed.
- Do a dry-run mode that runs the full build against a mocked API and prints the counts, and paste its output into the report.

## Deliver
1. Bump to v2.0.0, build the `.eext`, copy it to ~/Downloads/soma-carrier-v13-builder_v2.0.0.eext, and delete older soma-carrier-v13-builder_*.eext files there.
2. Commit and push to origin `easyeda-pro-carrier`.
3. Append a "Final (v2.0.0)" section to REPORT_EASYEDA.md: what changed, test and dry-run output, which API names worked, any known gaps, and exact user steps (open the project → Extension Manager → Import v2.0.0 → SOMA v1.3 → Build → send the summary and a PCB screenshot).
Do not merge to main. Do not invent results: if something can't be verified without the GUI, say so in the report.
