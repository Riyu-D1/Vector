#!/bin/zsh
source ~/.zshrc
F=~/Vector/stages/F4_link_stress.md
[ -f "$F" ] || { echo "missing $F"; exit 1; }
cd ~/Vector-wt/fea || exit 1
echo "on $(/usr/bin/git branch --show-current)"
[ "$1" = "--dry" ] && { echo dry; exit 0; }
devin --permission-mode dangerous -- "Read ~/Vector/ARM_KNUCKLE_V5.md rules 0.1-0.10, then do ~/Vector/stages/F4_link_stress.md exactly in the existing worktree. It was interrupted: first read fea_link/STATUS-fea-link.md and resume from what exists there (do not redo finished work, and count the CalculiX solves already used against the limit of 4); also delete the stray untracked files --version.* in the worktree root; stop when pushed. Never change existing product files."
