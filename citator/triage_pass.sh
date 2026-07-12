#!/bin/bash
# Triage pass: regenerate briefs rejected at semantic review, feeding each rejection
# note back to the generator (TRIAGE-BRIEFS.md), then re-review. Two-strike rule lives
# in `triage-list`: a case rejected twice never reappears here — humans only.
# Waits for any running source_rebuild_burn to finish first so parallel sessions don't
# stack up against the 5-hour session bucket (calibrated 2026-07-06: ~25 pts/hour each).
# Usage: triage_pass.sh [cycles]   (1 cycle = 1 triage session of 3 + 1 review session)
# Kill anytime: pkill -f triage_pass marker: TRIAGE_PASS
export PATH="/home/sage/.local/bin:/home/sage/.venvs/lawdata/bin:/usr/local/bin:/usr/bin:/bin"
mkdir -p /home/sage/logs
cd /mnt/d/dev/ai-law-research
LOG=/home/sage/logs/triage-pass.log
CYCLES=${1:-5}
TOOLS=(--allowedTools "Read" "Write" "Bash(/home/sage/.venvs/lawdata/bin/python /mnt/d/dev/ai-law-research/citator/sunday_briefs.py:*)")

echo "=== TRIAGE_PASS queued $(date) cycles=$CYCLES ===" >> $LOG
while pgrep -f source_rebuild_burn >/dev/null; do sleep 120; done
echo "=== TRIAGE_PASS start $(date) ===" >> $LOG
for i in $(seq 1 "$CYCLES"); do
  echo "--- triage session $i/$CYCLES $(date) ---" >> $LOG
  timeout 40m /home/sage/.local/bin/claude -p --model sonnet \
    "Read /mnt/d/dev/ai-law-research/citator/TRIAGE-BRIEFS.md and execute the runbook exactly. Hard limit: 3 regenerations this session." \
    "${TOOLS[@]}" >> $LOG 2>&1
  rc=$?
  echo "--- triage session $i done $(date) (exit $rc) ---" >> $LOG
  [ $rc -ne 0 ] && echo "=== TRIAGE_PASS stopping on triage nonzero exit ===" >> $LOG && break

  echo "--- review session $i/$CYCLES $(date) ---" >> $LOG
  timeout 40m /home/sage/.local/bin/claude -p \
    "Read /mnt/d/dev/ai-law-research/citator/SOURCE-BRIEF-REVIEW.md and execute the runbook exactly. Hard limit: 8 reviews this session." \
    "${TOOLS[@]}" >> $LOG 2>&1
  rc=$?
  echo "--- review session $i done $(date) (exit $rc) ---" >> $LOG
  [ $rc -ne 0 ] && echo "=== TRIAGE_PASS stopping on review nonzero exit ===" >> $LOG && break
done
echo "=== TRIAGE_PASS finished $(date) ===" >> $LOG
