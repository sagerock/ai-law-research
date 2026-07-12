#!/bin/bash
# Source-linked brief REBUILD burner: convert legacy briefs to structured briefs
# using leftover subscription credits. Alternates generation sessions (3 candidates
# each, --model sonnet: cheap, and every candidate is gated by review anyway) with
# review sessions (8 verdicts each, default model: the gate deserves the strongest
# reader; also a different model reviewing avoids same-model blind spots).
# Usage: source_rebuild_burn.sh [cycles]   (1 cycle = 1 gen + 1 review session)
# Kill anytime: pkill -f source_rebuild marker: SOURCE_REBUILD
export PATH="/home/sage/.local/bin:/home/sage/.venvs/lawdata/bin:/usr/local/bin:/usr/bin:/bin"
mkdir -p /home/sage/logs
cd /mnt/d/dev/ai-law-research
LOG=/home/sage/logs/source-rebuild.log
CYCLES=${1:-5}
ALLOWED_TOOLS_GEN=(--allowedTools "Read" "Write" "Bash(/home/sage/.venvs/lawdata/bin/python /mnt/d/dev/ai-law-research/citator/sunday_briefs.py:*)")

echo "=== SOURCE_REBUILD start $(date) cycles=$CYCLES ===" >> $LOG
for i in $(seq 1 "$CYCLES"); do
  echo "--- gen session $i/$CYCLES $(date) ---" >> $LOG
  timeout 40m /home/sage/.local/bin/claude -p --model sonnet \
    "Read /mnt/d/dev/ai-law-research/citator/SUNDAY-SOURCE-BRIEFS.md and execute the runbook exactly. Hard limit: 3 candidates this session." \
    "${ALLOWED_TOOLS_GEN[@]}" >> $LOG 2>&1
  rc=$?
  echo "--- gen session $i done $(date) (exit $rc) ---" >> $LOG
  [ $rc -ne 0 ] && echo "=== SOURCE_REBUILD stopping on gen nonzero exit ===" >> $LOG && break

  echo "--- review session $i/$CYCLES $(date) ---" >> $LOG
  timeout 40m /home/sage/.local/bin/claude -p \
    "Read /mnt/d/dev/ai-law-research/citator/SOURCE-BRIEF-REVIEW.md and execute the runbook exactly. Hard limit: 8 reviews this session." \
    "${ALLOWED_TOOLS_GEN[@]}" >> $LOG 2>&1
  rc=$?
  echo "--- review session $i done $(date) (exit $rc) ---" >> $LOG
  [ $rc -ne 0 ] && echo "=== SOURCE_REBUILD stopping on review nonzero exit ===" >> $LOG && break
done
echo "=== SOURCE_REBUILD finished $(date) ===" >> $LOG
