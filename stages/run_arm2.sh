#!/bin/zsh
source ~/.zshrc
WT=~/Vector-wt/arm2
F=~/Vector/stages/A2a_arm_j1_j3.md
C=~/Vector/stages/code/arm2
[ -f "$F" ] || { echo "missing $F"; exit 1; }
[ -f "$C/ap2.py" ] && [ "$(ls $C/rebot_src/*.step | wc -l | tr -d ' ')" = "14" ] || { echo "missing code bundle $C"; exit 1; }
if [ ! -d "$WT" ]; then
  /usr/bin/git -C ~/Vector-wt/act2c fetch origin arm-actuator2c || true
  if /usr/bin/git -C ~/Vector-wt/act2c show-ref --verify --quiet refs/heads/arm-arm2; then
    /usr/bin/git -C ~/Vector-wt/act2c worktree add "$WT" arm-arm2 || exit 1
  else
    /usr/bin/git -C ~/Vector-wt/act2c worktree add -b arm-arm2 "$WT" act-1c-done || exit 1
  fi
fi
cd "$WT" || exit 1
B=$(/usr/bin/git branch --show-current)
[ "$B" = "arm-arm2" ] || { echo "worktree is on $B, expected arm-arm2"; exit 1; }
echo "worktree $WT on $B @ $(/usr/bin/git log --oneline -1)"
[ "$1" = "--dry" ] && { echo "dry run: Devin not started"; exit 0; }
P=~/Vector/stages/.prompt_A2a.txt
echo "Read ~/Vector/ARM_KNUCKLE_V5.md rules 0.1-0.10 then do ~/Vector/stages/A2a_arm_j1_j3.md exactly; stop when the gate passes and the commit is pushed." > "$P"
devin --permission-mode dangerous -- "$(cat "$P")"
