#!/bin/bash
# Sunday brief batch — headless Claude Code session that generates AI case briefs
# for Law Study Group out of leftover weekly subscription capacity (reset: Mon 11am).
# Batch is hard-capped at 100 in citator/SUNDAY-BRIEFS.md to preserve Monday-morning
# headroom (calibrated 2026-07-05: ~7k tokens/brief). Scheduled from crontab: Sundays 7:03pm.
#
# Permissions are SCOPED, not bypassed: the session may only read files, write
# files, and run the sunday_briefs.py helper through the lawdata venv python.
# Anything else it tries is denied by the harness.
export PATH="/home/sage/.local/bin:/home/sage/.venvs/lawdata/bin:/usr/local/bin:/usr/bin:/bin"
mkdir -p /home/sage/logs
cd /mnt/d/dev/ai-law-research

# 100 briefs total, but 5 FRESH sessions of 20: a single long session would overflow
# the 200k context window and auto-compact repeatedly, and compaction burns extra
# usage. Fresh sessions stay inside context (20 x ~7k tokens) with zero compactions.
# The queue self-advances (briefed cases drop out of `list`), so sessions never overlap.
echo "=== sunday briefs run $(date) ===" >> /home/sage/logs/sunday-briefs.log
for i in 1 2 3 4 5; do
  echo "--- session $i/5 $(date) ---" >> /home/sage/logs/sunday-briefs.log
  timeout 1h /home/sage/.local/bin/claude -p \
    "Read /mnt/d/dev/ai-law-research/citator/SUNDAY-BRIEFS.md and execute the runbook exactly. Hard limit: 20 briefs this session." \
    --allowedTools "Read" "Write" "Bash(/home/sage/.venvs/lawdata/bin/python /mnt/d/dev/ai-law-research/citator/sunday_briefs.py:*)" \
    >> /home/sage/logs/sunday-briefs.log 2>&1
  echo "--- session $i/5 done $(date) (exit $?) ---" >> /home/sage/logs/sunday-briefs.log
done
echo "=== run finished $(date) ===" >> /home/sage/logs/sunday-briefs.log
