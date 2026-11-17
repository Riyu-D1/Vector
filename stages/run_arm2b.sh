#!/bin/zsh
source ~/.zshrc
WT=~/Vector-wt/arm2b
F=~/Vector/stages/A2b_arm_wrist_gripper.md
C=~/Vector/stages/code/arm2b
[ -f "$F" ] || { echo "missing $F"; exit 1; }
grep -q "NOT READY\|GATE_BLOCK\|GATE_MIN" "$F" && { echo "A2b brief not ready (untested placeholders): not starting"; exit 1; }
[ -f "$C/ap2b.py" ] && [ -f "$C/arm2b_checks.py" ] && [ "$(ls $C/rebot_src/*.step | wc -l | tr -d ' ')" = "2" ] || { echo "missing or incomplete code bundle $C"; exit 1; }
if [ ! -d "$WT" ]; then
  /usr/bin/git -C ~/Vector-wt/act2c fetch origin arm-arm2 --tags || true
  /usr/bin/git -C ~/Vector-wt/act2c rev-parse -q --verify refs/tags/arm-2a-done >/dev/null || { echo "tag arm-2a-done missing: run A2a first"; exit 1; }
  if /usr/bin/git -C ~/Vector-wt/act2c show-ref --verify --quiet refs/heads/arm-arm2b; then
    /usr/bin/git -C ~/Vector-wt/act2c worktree add "$WT" arm-arm2b || exit 1
  else
    /usr/bin/git -C ~/Vector-wt/act2c worktree add -b arm-arm2b "$WT" arm-2a-done || exit 1
  fi
fi
cd "$WT" || exit 1
B=$(/usr/bin/git branch --show-current)
[ "$B" = "arm-arm2b" ] || { echo "worktree is on $B, expected arm-arm2b"; exit 1; }
echo "worktree $WT on $B @ $(/usr/bin/git log --oneline -1)"
[ "$1" = "--dry" ] && { echo "dry run: Devin not started"; exit 0; }
P=~/Vector/stages/.prompt_A2b.txt
echo "Read ~/Vector/ARM_KNUCKLE_V5.md rules 0.1-0.10 then do ~/Vector/stages/A2b_arm_wrist_gripper.md exactly; stop when the gate passes and the commit is pushed." > "$P"
devin --permission-mode dangerous -- "$(cat "$P")"
