# Task: rebuild the SOMA v1.3 carrier board inside EasyEDA Pro via an EasyEDA Pro extension

## Why
The EasyEDA Spark sponsorship requires the board to be designed in EasyEDA Pro (staff: "all designs must be created 100% using EasyEDA Pro"; KiCad import not acceptable). The installed EasyEDA Pro is **v3.2.209** (Intel Mac, /Applications/EasyEDA-Pro.app). It has NO command-line/MCP bridge (that needs v4.1.60+, unreleased). So the route is an **EasyEDA Pro extension (.eext)** written with the official Pro API SDK, which the user imports once and runs from the editor menu. The extension builds the schematic and PCB inside EasyEDA Pro.

## Source of truth
- `order/pcb13_fix/soma-carrier-v13.kicad_pcb` (v1.3 board; there is no KiCad schematic, so derive the netlist from pad nets in the PCB), `order/pcb13_fix/bom.csv`, `STATUS-pcb13.md`, `verify_nets.py`, `audit_pins.py`.
- Board: 2-layer, 135x115 mm. Keep every net, part, footprint, mounting hole and outline identical in function to v1.3.

## Steps
1. Research the EasyEDA Pro extension API for **v3.2** (pro-api-sdk on GitHub: easyeda/pro-api-sdk, docs at prodocs.easyeda.com / pro-api docs). Confirm the APIs exist in 3.2: sch_PrimitiveComponent.create, sch_PrimitiveWire.create / net labels, pcb_PrimitiveComponent, pcb_PrimitiveLine/track, board outline, file save, and how to place LCSC library parts by LCSC part number (the C-numbers in bom.csv). If an LCSC part isn't in the library, pick an equivalent in-library part with the same footprint and record it.
2. Write a netlist extractor (Python) that turns the kicad_pcb into JSON: refdes, value, LCSC number, footprint, x/y/rotation/side, pad→net map, board outline, mounting holes, and track/via geometry.
3. Build the extension (TypeScript via the SDK, output `.eext`) in `easyeda/extension/`. When run, it should:
   a. create a new project "SOMA Carrier v1.3 (EasyEDA)"
   b. build a readable **schematic** (grouped by block: power/reverse polarity, 5V supply, ESP32-S3, CAN transceiver, relay motor rail + e-stop loop, servo bus, connectors) using net labels for connectivity
   c. convert/update to PCB, place components at the v1.3 positions, draw the outline and holes, and route tracks (replicate v1.3 track geometry where feasible; otherwise leave ratsnest and report it)
   d. save.
4. Write `easyeda/README.md` with exact, short user steps: how to import the .eext in EasyEDA Pro 3.2 (Settings → Extensions → Extension Manager → Import), enable any permission it needs, and run it from the menu.
5. You cannot click inside EasyEDA yourself. If you can verify headlessly (e.g. type-check, unit test the JSON→API call builder, mock eda API), do so. Then STOP and write `REPORT_EASYEDA.md` with: what's built, the files, any part substitutions, known gaps, and the exact steps for the user.
6. Commit everything on branch `easyeda-pro-carrier` and push to origin (`git push -u origin easyeda-pro-carrier`). NEVER push to main or any other existing branch. Don't force push.

## Rules
- Never invent part numbers, pin maps or results. If unsure, say so in the report.
- Don't touch ~/Vector (main checkout) or other worktrees.
- Don't open a PR or merge.
