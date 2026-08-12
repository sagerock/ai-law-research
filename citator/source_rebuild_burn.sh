#!/bin/bash
# Source-linked brief REBUILD burner: convert legacy briefs to structured briefs
# using leftover subscription credits. Each cycle runs three sessions:
#
#   1. triage — repair rejected briefs using the reviewer's own notes. Runs
#      first because it is the highest-yield work available: rejections fail on
#      1-3 claims out of ~16, and repair-with-notes approves at roughly twice
#      the rate of fresh generation (observed 2026-08-12: 9/15 triage vs 90/282
#      fresh). The two-strike rule in triage-list bounds it: a case rejected
#      twice leaves the queue for a human.
#   2. gen — 3 fresh candidates ($GEN_MODEL, default sonnet: cheap, and every
#      candidate is gated by review anyway; set GEN_MODEL=opus for casebooks
#      that prove too hard for sonnet, e.g. Con Law justiciability opinions).
#   3. review — 8 verdicts, default model: the gate deserves the strongest
#      reader, and a different model reviewing avoids same-model blind spots.
#
# Usage: [GEN_MODEL=opus] [PRIORITY_CASEBOOK_ID=1499] source_rebuild_burn.sh [cycles]
# Kill anytime: pkill -f source_rebuild marker: SOURCE_REBUILD
export PATH="/home/sage/.local/bin:/home/sage/.venvs/lawdata/bin:/usr/local/bin:/usr/bin:/bin"
mkdir -p /home/sage/logs
cd /mnt/d/dev/ai-law-research
LOG=/home/sage/logs/source-rebuild.log
CYCLES=${1:-5}
GEN_MODEL=${GEN_MODEL:-sonnet}
ALLOWED_TOOLS_GEN=(--allowedTools "Read" "Write" "Bash(/home/sage/.venvs/lawdata/bin/python /mnt/d/dev/ai-law-research/citator/sunday_briefs.py:*)")

echo "=== SOURCE_REBUILD start $(date) cycles=$CYCLES gen_model=$GEN_MODEL casebook=${PRIORITY_CASEBOOK_ID:-default} ===" >> $LOG
for i in $(seq 1 "$CYCLES"); do
  echo "--- triage session $i/$CYCLES $(date) ---" >> $LOG
  timeout 40m /home/sage/.local/bin/claude -p --model "$GEN_MODEL" \
    "Read /mnt/d/dev/ai-law-research/citator/TRIAGE-BRIEFS.md and execute the runbook exactly. Hard limit: 3 regenerations this session." \
    "${ALLOWED_TOOLS_GEN[@]}" >> $LOG 2>&1
  rc=$?
  echo "--- triage session $i done $(date) (exit $rc) ---" >> $LOG
  [ $rc -ne 0 ] && echo "=== SOURCE_REBUILD stopping on triage nonzero exit ===" >> $LOG && break

  echo "--- gen session $i/$CYCLES $(date) ---" >> $LOG
  timeout 40m /home/sage/.local/bin/claude -p --model "$GEN_MODEL" \
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
