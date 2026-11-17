#!/bin/zsh
# waits for stage-4b-done with a PASS status, then launches stage 5 once
cd ~/Vector-wt/knuckle || exit 1
LOG=~/Vector/stages/auto_next.log
echo "$(date) watching for stage-4b-done" > $LOG
for i in $(seq 1 720); do
  if /usr/bin/git tag | grep -qx stage-4b-done; then
    sleep 20
    if awk '/## Stage 4b/,0' docs/STATUS-knuckle.md | head -1 | grep -q PASS && ! grep -q "BLOCKED" docs/STATUS-knuckle.md; then
      echo "$(date) 4b PASS -> launching stage 5" >> $LOG
      osascript -e 'tell application "Terminal" to do script "zsh ~/Vector/stages/run_stage.sh 5"'
    else
      echo "$(date) 4b not PASS or BLOCKED -> not launching" >> $LOG
    fi
    exit 0
  fi
  sleep 60
done
echo "$(date) timed out" >> $LOG
