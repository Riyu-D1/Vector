#!/bin/zsh
# usage: run_stage.sh N   (N = 1..7)
source ~/.zshrc
N="$1"
F=$(ls ~/Vector/stages/S${N}_*.md 2>/dev/null | head -1)
[ -z "$F" ] && { echo "no stage file for N=$N"; exit 1; }
cd ~/Vector-wt/knuckle || exit 1
P=~/Vector/stages/.prompt_S${N}.txt
echo "Read ~/Vector/ARM_KNUCKLE_V5.md then do $F exactly; stop when the gate passes and the commit is pushed." > "$P"
devin --permission-mode dangerous -- "$(cat "$P")"
