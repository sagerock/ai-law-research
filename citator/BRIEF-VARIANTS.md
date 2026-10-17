# Simplified / Bullets brief versions — writer runbook

Write the Simplified and Bullets versions of approved source-linked briefs, on subscription
capacity. The helper owns the queue, validation, and database writes; you write candidates.
Your candidates are staged, NOT published: a separate review session approves them. Never
review your own candidates.

Helper (use exactly this interpreter and path):

    /home/sage/.venvs/lawdata/bin/python /mnt/d/dev/ai-law-research/citator/brief_variant_batch.py

## Batch limit

**5 cases per session.** Hard stop. If the session prompt gives `--ids`, `--redo-model`, or `--redo-prompt`, pass them to every `queue` call. A `"state": "redo"` item is a live version being rewritten for plainer wording: write it fresh from `fetch`. Stop early if anything errors repeatedly.

## Steps — one case at a time

1. `queue 1` (add `--collection <id>` if the session prompt names a collection). An empty
   array means the queue is dry: report that and stop. A `"state": "repair"` item is a held
   candidate; its notes name the lines the reviewer rejected.
2. `fetch <id>`. The `instructions` field is the full specification, including the numbered
   detailed brief. Follow it exactly. If the output has a `repair` block, start from
   `previous_candidate` and rewrite ONLY the lines in `reviewer_notes`, copying every other
   line unchanged.
3. Write the JSON object (keys `simplified` and `bullets`, nothing else) to a scratch file
   under /tmp, e.g. `/tmp/variant_<id>.json`. Never inside the repository.
4. `stage <id> /tmp/variant_<id>.json "<your model id>"`. If it returns errors, fix exactly
   those and stage once more. If it fails again, report it and move on. Never weaken or
   guess around validation.

## Quality rules (the reviewer holds lines that break these)

- Plain words, same law: never loosen the test, change "may"/"must", or describe it in a
  different doctrine's vocabulary (a discrimination holding is not a "burden" holding).
- Keep every part of the outcome, including partial remands.
- Use only what the cited claims say. You know these cases from training; the reviewer
  accepts only the detailed brief. No outside facts, names, votes, or later history.
- Reread each sentence: it must make sense alone and say what its claims say, not the opposite.

After the batch, report: case IDs, titles, stage results, failures.
