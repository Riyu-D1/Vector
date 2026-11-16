# Fix 5: createProject fails — build into the user's open project

Read REPORT_EASYEDA.md and FIX1-4 briefs. Same rules (branch easyeda-pro-carrier only, no force push/PR/merge, never invent data, don't touch ~/Vector, read-only on ~/Documents/EasyEDA-Pro). Be FAST: user is waiting; aim to finish in ~15 min.

## v1.4.0 real-GUI diagnostics
- Footprint draw WORKS. Symbol draw WORKS. Device: lib='SOMA' + assoc=ref WORKS (read-back matches); use 'SOMA' first.
- dmt_Project.createProject -> FAIL (error text not shown). HALF_OFFLINE mode.

## Do
1. Make the Build use the CURRENTLY OPEN project (dmt_Project.getCurrentProjectInfo). The user creates "SOMA Carrier v1.3 (EasyEDA)" manually and opens it. Use its existing schematic/PCB if present, else create schematic/PCB/board inside it (dmt_Schematic.createSchematic / dmt_Pcb.createPcb / dmt_Board.createBoard with the project uuid). If no project is open, show one dialog telling the user to create/open it. Keep createProject only as a logged attempt with real error text.
2. Diagnostics: run the downstream chain inside the open project on a separate test schematic/PCB if possible (place KEEP device, importChanges, pad count >0, one track, save), real error text everywhere. If it can't avoid touching the real docs, skip downstream in diagnostics and just report project info.
3. Rebuild v1.5.0, tests pass, copy to ~/Downloads (delete older soma-carrier .eext), commit + push origin easyeda-pro-carrier, append "Fix 5" to REPORT_EASYEDA.md with short user steps.
