#!/bin/zsh
# usage: ~/Vector/stages/run_act2c.sh   (Stage A1c actuator rotor-flange drive; Devin on branch arm-actuator2c)
# add --dry to only create/check the worktree without starting Devin
source ~/.zshrc
WT=~/Vector-wt/act2c
F=~/Vector/stages/A1c_actuator_rotor_drive.md
[ -f "$F" ] || { echo "missing $F"; exit 1; }
if [ ! -d "$WT" ]; then
  /usr/bin/git -C ~/Vector-wt/act2 fetch origin arm-actuator2b || true
  if /usr/bin/git -C ~/Vector-wt/act2 show-ref --verify --quiet refs/heads/arm-actuator2c; then
    /usr/bin/git -C ~/Vector-wt/act2 worktree add "$WT" arm-actuator2c || exit 1
  else
    /usr/bin/git -C ~/Vector-wt/act2 worktree add -b arm-actuator2c "$WT" arm-actuator2b || exit 1
  fi
fi
cd "$WT" || exit 1
B=$(/usr/bin/git branch --show-current)
[ "$B" = "arm-actuator2c" ] || { echo "worktree is on $B, expected arm-actuator2c"; exit 1; }
echo "worktree $WT on $B @ $(/usr/bin/git log --oneline -1)"
[ "$1" = "--dry" ] && { echo "dry run: Devin not started"; exit 0; }
P=~/Vector/stages/.prompt_A1c.txt
echo "Read ~/Vector/ARM_KNUCKLE_V5.md rules 0.1-0.10 then do ~/Vector/stages/A1c_actuator_rotor_drive.md exactly; stop when the gate passes and the commit is pushed." > "$P"
devin --permission-mode dangerous -- "$(cat "$P")"
