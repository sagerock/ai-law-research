# Sunday source-linked brief batch — generation runbook

Generate structured, source-linked case briefs using leftover subscription capacity.
The helper owns the queue, passages, validation, and database writes. You write the candidates.
Never invoke the legacy `save` command and never replace the Original brief.

Readers' "Request this brief" clicks (`brief_requests`) come first, most-requested first;
those may have no legacy brief. After them the queue is the REBUILD backlog: cases that already have a legacy brief but no structured
one (~890 as of 2026-07-12), landmarks first. Your candidates land as `pending` and are NOT
shown to students until a separate review session approves them — do not review your own
candidates; a fresh context judges support more honestly than the one that wrote the claims.

## Batch limit

**3 candidates per session, or stop sooner once the packets you have read this session
add up to more than 250,000 characters** (`packet_chars` in each packet). Hard stop. Most
packets are the whole opinion and well under 60k; a very long one can reach ~180k, and the
character cap keeps the session inside the context window with no auto-compaction. If
anything errors repeatedly, stop early and note it.

## Steps — repeat up to 3 times, one case at a time

1. Get the next case:

       /home/sage/.venvs/lawdata/bin/python /mnt/d/dev/ai-law-research/citator/sunday_briefs.py candidate-list 1

   If the returned array is empty, report that the rebuild queue is dry and stop.

2. Fetch its source packet:

       /home/sage/.venvs/lawdata/bin/python /mnt/d/dev/ai-law-research/citator/sunday_briefs.py candidate-opinion <id>

   The JSON contains `content_hash`, passage IDs, opinion-part labels, and source text. Brief
   only this packet. If `is_partial_packet` is true, the opinion was too long to send whole:
   every part of the majority is represented, and gaps show as jumps in `ordinal`. Do not
   claim to cover omitted material.

3. Write one JSON object to a scratch file **under /tmp** (e.g. `/tmp/brief_<id>.json` —
   never inside the repository; repo-dir scratch files litter `git status` for everyone)
   with exactly these keys:

       {
         "facts": [{"text": "...", "sources": ["op-..."]}],
         "issue": [{"text": "...", "sources": ["op-..."]}],
         "holding": [{"text": "...", "sources": ["op-..."]}],
         "rule": [{"text": "...", "sources": ["op-..."]}],
         "majority_reasoning": [{"text": "...", "sources": ["op-..."]}],
         "dissent": [],
         "significance": "Editorial synthesis without passage IDs."
       }

   Limits: Facts 1-5 claims; Issue 1-4; Holding 1-4; Rule 1-4; Majority Reasoning 1-8;
   Dissent 0-4. Use Dissent only when the packet labels dissent passages. Most cases
   decide one question: use one issue. When the court decides several distinct questions,
   often under separate headings (Buckley v. Valeo: First Amendment limits, disclosure,
   public financing, Appointments Clause), give each its own issue, holding, rule, and
   reasoning in the same order, and drop none: a class may assign the case for any one of
   them. Target 550-700 total words for a one-issue case; add room for each extra issue. Each sourced claim must be atomic and cite the smallest set of
   passage IDs that directly supports it. Never invent or alter an ID. Significance is
   editorial synthesis, under 90 words, and must not contain passage IDs.

4. Save with the exact content hash from step 2 and your actual model ID:

       /home/sage/.venvs/lawdata/bin/python /mnt/d/dev/ai-law-research/citator/sunday_briefs.py candidate-save <id> <scratch-file> "<model-id> (sunday-source-batch)" <content_hash>

5. If validation rejects the candidate, read the error, correct the scratch file once, and
   retry. If it fails again, report the failure and move to the next case. Do not weaken,
   bypass, or guess around validation.

## Quality rules

- **Every specific in a sourced claim must appear in a cited passage.** The #1 rejection
  cause (9 of the first 22 candidates) is a claim that is broadly right but asserts a
  specific — a year, a name, a dollar figure, "sole", "first", a procedural outcome —
  that no cited passage states. You know these cases from training; the reviewer only
  accepts what the passages say. When a specific isn't in a passage, generalize the
  claim or drop the specific. Save what you remember for Significance.
- Distinguish the judgment from dicta and procedural history.
- Keep majority reasoning separate from dissents and concurrences.
- Cite only language that actually supports the claim, not merely nearby language.
- Do not add later doctrinal history to sourced sections; reserve it for Significance.
- If the packet appears to contain the wrong case, do not save it.
- After the batch, report: case IDs, titles, model, content hashes, save results, failures.
