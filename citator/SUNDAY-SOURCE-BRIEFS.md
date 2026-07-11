# Sunday source-linked brief pilot runbook

Generate exactly one structured, source-linked case brief using leftover subscription capacity.
The helper owns the queue, passages, validation, and database writes. You write the candidate.
Never invoke the legacy `save` command and never replace the Original brief.

## Steps

1. Get one pilot case:

       /home/sage/.venvs/lawdata/bin/python /mnt/d/dev/ai-law-research/citator/sunday_briefs.py candidate-list 1

   If the returned array is empty, report that the pilot is complete and stop.

2. Fetch its source packet:

       /home/sage/.venvs/lawdata/bin/python /mnt/d/dev/ai-law-research/citator/sunday_briefs.py candidate-opinion <id>

   The JSON contains `content_hash`, passage IDs, opinion-part labels, and source text. Brief
   only this packet. If `is_partial_packet` is true, do not claim to cover omitted material.

3. Write one JSON object to a scratch file with exactly these keys:

       {
         "facts": [{"text": "...", "sources": ["op-..."]}],
         "issue": [{"text": "...", "sources": ["op-..."]}],
         "holding": [{"text": "...", "sources": ["op-..."]}],
         "rule": [{"text": "...", "sources": ["op-..."]}],
         "majority_reasoning": [{"text": "...", "sources": ["op-..."]}],
         "dissent": [],
         "significance": "Editorial synthesis without passage IDs."
       }

   Limits: Facts 1-4 claims; Issue exactly 1; Holding 1-2; Rule 1-2; Majority Reasoning
   1-4; Dissent 0-4. Use Dissent only when the packet labels dissent passages. Target
   550-700 total words. Each sourced claim must be atomic and cite the smallest set of
   passage IDs that directly supports it. Never invent or alter an ID. Significance is
   editorial synthesis, under 90 words, and must not contain passage IDs.

4. Save with the exact content hash from step 2 and your actual model ID:

       /home/sage/.venvs/lawdata/bin/python /mnt/d/dev/ai-law-research/citator/sunday_briefs.py candidate-save <id> <scratch-file> "<model-id> (sunday-source-batch)" <content_hash>

5. If validation rejects the candidate, read the error, correct the scratch file once, and
   retry. If it fails again, report the failure and stop. Do not weaken, bypass, or guess
   around validation.

## Quality rules

- Distinguish the judgment from dicta and procedural history.
- Keep majority reasoning separate from dissents and concurrences.
- Cite only language that actually supports the claim, not merely nearby language.
- Do not add later doctrinal history to sourced sections; reserve it for Significance.
- If the packet appears to contain the wrong case, do not save it.
- Report the case ID, title, model, content hash, and save result when done.
