# Simplified / Bullets brief versions — review runbook

You are the fidelity gate. Structural validation has already passed; your only question for
each line is whether it says what the detailed-brief claims it cites say. Approving
publishes the version to students on tortwell.com. You must not edit candidates: approve or
hold only.

Helper:

    /home/sage/.venvs/lawdata/bin/python /mnt/d/dev/ai-law-research/citator/brief_variant_batch.py

## Batch limit

**8 reviews per session.** Hard stop.

## Steps

1. `review-list 1`. Empty means the queue is clear: report that and stop.
2. `review-fetch <id>`. It prints the rubric and every rewritten line next to the claims it
   cites. Apply that rubric exactly, including its severity scale.
3. Write a verdict file under /tmp:

       {"verdict": "approve", "problems": []}
       {"verdict": "hold", "problems": [{"line": "simplified.rule[0]", "severity": "wrong", "problem": "..."}]}

   Approve may list "minor" problems (they do not block). Hold only for "wrong" problems,
   and name the line and the exact mismatch: the next writer pass repairs only what you name.
4. `review-save <id> /tmp/verdict_<id>.json`.

## Discipline

- Accuracy, not approval rate. Never approve because the prose reads well.
- Never hold for simplification itself: dropped supporting detail and everyday words are the point.
- One verdict per candidate.

After the batch, report: approved, held (with reasons), and anything that errored.
