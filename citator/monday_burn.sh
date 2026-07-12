#!/bin/bash
# One-off Monday-morning burner: the weekly pool resets at ~11:01am with ~66% unused —
# spend it on briefs until 10:40, then stop hard. Same scoped-permission sessions as
# the Sunday batch (20 briefs each, fresh context per session). Kill anytime:
#   pkill -f monday_burn marker: MONDAY_BURN
export PATH="/home/sage/.local/bin:/home/sage/.venvs/lawdata/bin:/usr/local/bin:/usr/bin:/bin"
mkdir -p /home/sage/logs
cd /mnt/d/dev/ai-law-research
LOG=/home/sage/logs/monday-burn.log
CUTOFF=1040
MAX_SESSIONS=15   # ~300 briefs (Sage: "let's do like 300 right now")

echo "=== MONDAY_BURN start $(date) ===" >> $LOG
i=0
while [ "$(date +%H%M)" -lt "$CUTOFF" ] && [ "$i" -lt "$MAX_SESSIONS" ]; do
  i=$((i+1))
  echo "--- burn session $i $(date) ---" >> $LOG
  timeout 40m /home/sage/.local/bin/claude -p \
    "Read /mnt/d/dev/ai-law-research/citator/SUNDAY-BRIEFS.md and execute the runbook exactly. Hard limit: 20 briefs this session." \
    --allowedTools "Read" "Write" "Bash(/home/sage/.venvs/lawdata/bin/python /mnt/d/dev/ai-law-research/citator/sunday_briefs.py:*)" \
    >> $LOG 2>&1
  rc=$?
  echo "--- burn session $i done $(date) (exit $rc) ---" >> $LOG
  # if a session errors out (e.g., usage/session limit hit), stop rather than spin
  [ $rc -ne 0 ] && echo "=== MONDAY_BURN stopping on nonzero exit ===" >> $LOG && break
done
echo "=== MONDAY_BURN finished $(date) after $i sessions ===" >> $LOG
