#!/bin/zsh
source ~/.zshrc
F=~/Vector/stages/F4_link_stress.md
[ -f "$F" ] || { echo "missing $F"; exit 1; }
cd ~/Vector-wt/fea || exit 1
echo "on $(/usr/bin/git branch --show-current)"
[ "$1" = "--dry" ] && { echo dry; exit 0; }
devin --permission-mode dangerous -- "Read ~/Vector/ARM_KNUCKLE_V5.md rules 0.1-0.10, then do ~/Vector/stages/F4_link_stress.md exactly in the existing worktree; stop when pushed. Never change existing product files."
