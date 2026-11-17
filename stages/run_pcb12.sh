#!/bin/zsh
source ~/.zshrc
F=~/Vector/stages/P1_carrier_v12.md
[ -f "$F" ] || { echo "missing $F"; exit 1; }
WT=~/Vector-wt/pcb12
cd ~/Vector || exit 1
[ -d "$WT" ] || /usr/bin/git worktree add -b pcb-v12 "$WT" || exit 1
cd "$WT" || exit 1
echo "worktree $WT on $(/usr/bin/git branch --show-current)"
[ "$1" = "--dry" ] && { echo "dry run"; exit 0; }
devin --permission-mode dangerous -- "Read ~/Vector/ARM_KNUCKLE_V5.md rules 0.1-0.10 and ~/Vector/ROUTING_GUIDE.md, then do ~/Vector/stages/P1_carrier_v12.md exactly; stop when the commit is pushed. Never change existing files."
