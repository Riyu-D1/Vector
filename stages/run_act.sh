#!/bin/zsh
# usage: ~/Vector/stages/run_act.sh   (Stage A1 printed actuator; Devin on branch arm-actuator2)
# add --dry to only create/check the worktree without starting Devin
source ~/.zshrc
WT=~/Vector-wt/act2
F=~/Vector/stages/A1_printed_actuator.md
[ -f "$F" ] || { echo "missing $F"; exit 1; }
if [ ! -d "$WT" ]; then
  /usr/bin/git -C ~/Vector-wt/knuckle fetch origin arm-knuckle || true
  if /usr/bin/git -C ~/Vector-wt/knuckle show-ref --verify --quiet refs/heads/arm-actuator2; then
    /usr/bin/git -C ~/Vector-wt/knuckle worktree add "$WT" arm-actuator2 || exit 1
  else
    /usr/bin/git -C ~/Vector-wt/knuckle worktree add -b arm-actuator2 "$WT" arm-knuckle || exit 1
  fi
fi
cd "$WT" || exit 1
B=$(/usr/bin/git branch --show-current)
[ "$B" = "arm-actuator2" ] || { echo "worktree is on $B, expected arm-actuator2"; exit 1; }
echo "worktree $WT on $B @ $(/usr/bin/git log --oneline -1)"
[ "$1" = "--dry" ] && { echo "dry run: Devin not started"; exit 0; }
P=~/Vector/stages/.prompt_A1.txt
echo "Read ~/Vector/ARM_KNUCKLE_V5.md rules 0.1-0.10 then do ~/Vector/stages/A1_printed_actuator.md exactly; stop when the gate passes and the commit is pushed." > "$P"
devin --permission-mode dangerous -- "$(cat "$P")"
