# Rejected-brief triage — regeneration runbook

You are regenerating source-linked briefs that FAILED semantic review. Each queue entry
includes the reviewer's rejection note. Your job is to fix exactly what the note names —
not to argue with it, and not to re-roll the same brief and hope. The corrected candidate
goes back through the same review gate; nothing you do here bypasses review.

## Batch limit

**3 regenerations per session.** Hard stop.

## Steps — repeat up to 3 times

1. Get the next rejected case WITH its rejection note:

       /home/sage/.venvs/lawdata/bin/python /mnt/d/dev/ai-law-research/citator/sunday_briefs.py triage-list 1

   If empty, report that the triage queue is clear and stop. Each case gets ONE triage
   attempt (a second rejection removes it permanently — a human must look at it), so
   this attempt has to count: read the rejection note twice before writing.

2. Fetch the source packet:

       /home/sage/.venvs/lawdata/bin/python /mnt/d/dev/ai-law-research/citator/sunday_briefs.py candidate-opinion <id>

3. Write the corrected brief (same JSON shape and limits as `SUNDAY-SOURCE-BRIEFS.md`,
   scratch file under /tmp). Fixing a rejected claim means one of:
   - **Generalize**: drop the unsupported specific (year, name, figure, "sole"/"first",
     procedural outcome) and keep what the passages actually state.
   - **Re-source**: if the packet contains a passage that DOES state the specific, cite it.
   - **Delete**: if the claim can't survive without the unsupported part, remove it
     (respecting section minimums).
   Never respond by weakening the claim's language while keeping the unsupported
   assertion ("reportedly", "apparently" — still unsupported). Check the note's verdict
   on every OTHER claim too: claims the reviewer called supported should be preserved
   as-is, not rewritten — rewriting them risks new errors in approved material.

4. Save (this resets the candidate to pending for fresh review):

       /home/sage/.venvs/lawdata/bin/python /mnt/d/dev/ai-law-research/citator/sunday_briefs.py candidate-save <id> <scratch-file> "<model-id> (triage)" <content_hash>

5. If the rejection note says the packet is the WRONG CASE or the opinion text is
   defective, do not regenerate — report it for human attention and move on.

After the batch, report: each case, what the rejection said, what you changed, save result.
