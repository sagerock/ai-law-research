#!/bin/bash
# Sunday brief batch — headless Claude Code session that generates AI case briefs
# for Law Study Group out of leftover weekly subscription capacity (reset: Mon 11am).
# 300 briefs/night: 15 sessions x 20 (recalibrated 2026-07-06: ~0.02 weekly-pts/brief,
# so a full night ≈ 6-10% of the weekly pool; Sage's week ends >50% unused regardless).
# ~3h wall-clock, done by ~10pm Sunday. Scheduled from crontab: Sundays 7:03pm.
#
# Permissions are SCOPED, not bypassed: the session may only read files, write
# files, and run the sunday_briefs.py helper through the lawdata venv python.
# Anything else it tries is denied by the harness.
export PATH="/home/sage/.local/bin:/home/sage/.venvs/lawdata/bin:/usr/local/bin:/usr/bin:/bin"
mkdir -p /home/sage/logs
cd /mnt/d/dev/ai-law-research

# 300 briefs total via 15 FRESH sessions of 20: a single long session would overflow
# the 200k context window and auto-compact repeatedly, and compaction burns extra
# usage. Fresh sessions stay inside context (20 x ~7k tokens) with zero compactions.
# The queue self-advances (briefed cases drop out of `list`), so sessions never overlap.
echo "=== sunday briefs run $(date) ===" >> /home/sage/logs/sunday-briefs.log
for i in $(seq 1 15); do
  echo "--- session $i/15 $(date) ---" >> /home/sage/logs/sunday-briefs.log
  timeout 1h /home/sage/.local/bin/claude -p \
    "Read /mnt/d/dev/ai-law-research/citator/SUNDAY-BRIEFS.md and execute the runbook exactly. Hard limit: 20 briefs this session." \
    --allowedTools "Read" "Write" "Bash(/home/sage/.venvs/lawdata/bin/python /mnt/d/dev/ai-law-research/citator/sunday_briefs.py:*)" \
    >> /home/sage/logs/sunday-briefs.log 2>&1
  rc=$?
  echo "--- session $i/15 done $(date) (exit $rc) ---" >> /home/sage/logs/sunday-briefs.log
  # stop rather than spin if sessions start failing (limits, network, etc.)
  [ $rc -ne 0 ] && echo "=== stopping on nonzero exit ===" >> /home/sage/logs/sunday-briefs.log && break
done
echo "=== run finished $(date) ===" >> /home/sage/logs/sunday-briefs.log
