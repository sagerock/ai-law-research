#!/bin/bash
# Simplified/Bullets backfill on subscription capacity. Each cycle: one writer session
# (5 cases, $GEN_MODEL, default opus: a blind 2026-10-17 comparison found its Simplified
# versions plainer on 4 of 4 cases at equal accuracy) then one review session (8 verdicts, default model:
# the gate gets the stronger reader, and a different session never judges its own work).
# Held candidates come back through the writer queue first for targeted repair.
#
# Usage: [GEN_MODEL=sonnet] [COLLECTION=15] [IDS=a,b] [REDO_MODEL=sonnet] brief_variant_burn.sh [cycles]
# Kill anytime: pkill -f brief_variant_burn
export PATH="/home/sage/.local/bin:/home/sage/.venvs/lawdata/bin:/usr/local/bin:/usr/bin:/bin"
mkdir -p /home/sage/logs
cd /mnt/d/dev/ai-law-research
LOG=/home/sage/logs/brief-variants.log
CYCLES=${1:-3}
GEN_MODEL=${GEN_MODEL:-opus}
SCOPE=""
[ -n "$COLLECTION" ] && SCOPE=" Use --collection $COLLECTION with queue."
[ -n "$IDS" ] && SCOPE="$SCOPE Use --ids $IDS with queue."
[ -n "$REDO_MODEL" ] && SCOPE="$SCOPE Use --redo-model $REDO_MODEL with queue."
TOOLS=(--allowedTools "Read" "Write" "Bash(/home/sage/.venvs/lawdata/bin/python /mnt/d/dev/ai-law-research/citator/brief_variant_batch.py:*)")

echo "=== BRIEF_VARIANTS start $(date) cycles=$CYCLES gen_model=$GEN_MODEL collection=${COLLECTION:-all} ===" >> $LOG
for i in $(seq 1 "$CYCLES"); do
  echo "--- writer session $i/$CYCLES $(date) ---" >> $LOG
  timeout 40m claude -p --model "$GEN_MODEL" \
    "Read /mnt/d/dev/ai-law-research/citator/BRIEF-VARIANTS.md and execute the runbook exactly.$SCOPE" \
    "${TOOLS[@]}" >> $LOG 2>&1 || { echo "=== stopping: writer exit $? ===" >> $LOG; break; }
  echo "--- review session $i/$CYCLES $(date) ---" >> $LOG
  timeout 40m claude -p \
    "Read /mnt/d/dev/ai-law-research/citator/BRIEF-VARIANTS-REVIEW.md and execute the runbook exactly." \
    "${TOOLS[@]}" >> $LOG 2>&1 || { echo "=== stopping: review exit $? ===" >> $LOG; break; }
done
echo "=== BRIEF_VARIANTS finished $(date) ===" >> $LOG
