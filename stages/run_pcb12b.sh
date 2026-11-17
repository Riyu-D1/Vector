#!/bin/zsh
source ~/.zshrc
F=~/Vector/stages/P2_pcb12_fix.md
[ -f "$F" ] || { echo "missing $F"; exit 1; }
cd ~/Vector-wt/pcb12 || exit 1
echo "on $(/usr/bin/git branch --show-current)"
[ "$1" = "--dry" ] && { echo dry; exit 0; }
devin --permission-mode dangerous -- "Read ~/Vector/ARM_KNUCKLE_V5.md rules 0.1-0.10, then do ~/Vector/stages/P2_pcb12_fix.md exactly; stop when pushed. Do not rerun the full router. Never change files outside pcb12/."
