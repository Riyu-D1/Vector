# Run order — knuckle arm (Devin)
Run one stage at a time from any terminal: `~/Vector/stages/run_stage.sh N` (N = 1..7).
Wait until the stage commits and tags `stage-N-done` (check: `cd ~/Vector-wt/knuckle && /usr/bin/git tag | grep stage-`), read `docs/STATUS-knuckle.md`, then run N+1.
1 S1_base_J1 → 2 S2_shoulder_upperarm → 3 S3_elbow_forearm → 4 S4_wrist_gripper → 4b S4b_wrist_style → 5 S5_cables_covers → 6 S6_firmware_software → 7 S7_assembly_checks_renders.
If a stage writes `BLOCKED:` in STATUS, do not start the next stage; ask Grok Bot.
Reference code (tested): ~/Vector/stages/code/ (also copied to ~/Vector-wt/knuckle/cad/knuckle/ untracked; S1 re-copies it).
