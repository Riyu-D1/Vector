#!/bin/zsh
source ~/.zshrc
F=~/Vector/stages/P3_carrier_v13.md
[ -f "$F" ] || { echo "missing $F"; exit 1; }
cd ~/Vector-wt/pcb12 || exit 1
echo "on $(/usr/bin/git branch --show-current)"
[ "$1" = "--dry" ] && { echo dry; exit 0; }
devin --permission-mode dangerous -- "Read ~/Vector/ARM_KNUCKLE_V5.md rules 0.1-0.10 and ~/Vector/ROUTING_GUIDE.md, then do ~/Vector/stages/P3_carrier_v13.md exactly; start at step 0, stop when pushed. Never change existing files except the step 0 commit."
