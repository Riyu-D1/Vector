#!/bin/zsh
source ~/.zshrc
F=~/Vector/stages/S1_mujoco_conversion.md
[ -f "$F" ] || { echo "missing $F"; exit 1; }
WT=~/Vector-wt/sim
cd ~/Vector-wt/arm2b || exit 1
cd "$WT" 2>/dev/null || { /usr/bin/git -C ~/Vector-wt/arm2b worktree add -b arm-sim "$WT" arm-2-done || exit 1; cd "$WT" || exit 1; }
echo "worktree $WT on $(/usr/bin/git branch --show-current)"
[ "$1" = "--dry" ] && { echo "dry run"; exit 0; }
devin --permission-mode dangerous -- "Read ~/Vector/ARM_KNUCKLE_V5.md rules 0.1-0.10 then do ~/Vector/stages/S1_mujoco_conversion.md exactly; stop when the commit is pushed. Never change existing files."
