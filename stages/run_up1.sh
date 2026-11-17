#!/bin/zsh
source ~/.zshrc
F=~/Vector/stages/D1_joint_upgrade.md
[ -f "$F" ] || { echo "missing $F"; exit 1; }
cd ~/Vector || exit 1
echo "on $(/usr/bin/git branch --show-current)"
[ "$1" = "--dry" ] && { echo dry; exit 0; }
devin --permission-mode dangerous -- "Read ~/Vector/ARM_KNUCKLE_V5.md rules 0.1-0.10, then do ~/Vector/stages/D1_joint_upgrade.md exactly, starting by creating the worktree it names; stop when pushed. Never change existing product files."
