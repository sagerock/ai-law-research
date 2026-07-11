#!/bin/bash
# Ten fresh sessions avoid context compaction while testing diverse source-linked briefs.
export PATH="/home/sage/.local/bin:/home/sage/.venvs/lawdata/bin:/usr/local/bin:/usr/bin:/bin"
mkdir -p /home/sage/logs
cd /mnt/d/dev/ai-law-research

LOG=/home/sage/logs/source-brief-pilot.log
echo "=== source brief pilot start $(date) ===" >> "$LOG"
for i in $(seq 1 10); do
  echo "--- pilot session $i/10 $(date) ---" >> "$LOG"
  timeout 1h /home/sage/.local/bin/claude -p \
    "Read /mnt/d/dev/ai-law-research/citator/SUNDAY-SOURCE-BRIEFS.md and execute the runbook exactly. Generate at most one candidate." \
    --allowedTools "Read" "Write" "Bash(/home/sage/.venvs/lawdata/bin/python /mnt/d/dev/ai-law-research/citator/sunday_briefs.py:*)" \
    >> "$LOG" 2>&1
  rc=$?
  echo "--- pilot session $i done $(date) (exit $rc) ---" >> "$LOG"
  [ $rc -ne 0 ] && echo "=== pilot stopping on nonzero exit ===" >> "$LOG" && break
done
echo "=== source brief pilot finished $(date) ===" >> "$LOG"
