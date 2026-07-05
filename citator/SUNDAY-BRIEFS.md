# Sunday brief batch — runbook

You are running the weekly Sunday batch: generate AI case briefs for Law Study Group
using leftover subscription capacity. YOU write each brief; the helper script only
moves data. Work sequentially, stop at the batch limit, report at the end.

## Batch limit

**20 briefs per session.** Hard stop — the cron wrapper runs 5 fresh sessions per
Sunday (100 total). The per-session cap keeps each session inside the 200k context
window with zero auto-compactions (compaction burns extra usage); the total cap
preserves Monday-morning headroom before the weekly reset. If anything errors
repeatedly, stop early and note it; never push past 20 in one session.
(Calibration 2026-07-05: a brief costs ~6.5-7k tokens ≈ $0.05 Opus-equivalent, so a
full Sunday ≈ $5-equivalent — small against a weekly Max allowance.)

## Steps

1. Get the queue (JSON of un-briefed cases, priority-ordered):

       /home/sage/.venvs/lawdata/bin/python /mnt/d/dev/ai-law-research/citator/sunday_briefs.py list 20

2. For EACH case, one at a time:
   a. Fetch the opinion (already truncated to the site's 20k-char window):

          /home/sage/.venvs/lawdata/bin/python /mnt/d/dev/ai-law-research/citator/sunday_briefs.py opinion <id>

   b. Read the opinion and write the brief YOURSELF — do not summarize the summary,
      brief the actual opinion text. Use EXACTLY this structure (it must match the
      site's paid endpoint format; the emoji headers are load-bearing):

          **📋 Facts**
          4-5 sentences: parties, what happened, procedural history — the facts crucial
          to the legal issues.

          **⚖️ Issue(s)**
          The legal question(s), framed as questions. Number them if multiple.

          **📚 Holding**
          The court's decision on each issue, plus outcome (affirmed/reversed/remanded).

          **💡 Reasoning**
          4-6 sentences: why the court decided this way — principles, statutes,
          precedents; key quotes if particularly important.

          **🎯 Significance**
          3-4 sentences: why the case matters, what principle it establishes, how it
          is used in practice.

   c. Write the brief to a scratch file, then save it:

          /home/sage/.venvs/lawdata/bin/python /mnt/d/dev/ai-law-research/citator/sunday_briefs.py save <id> <scratch-file> "<your-model-id> (sunday-batch)"

      Pass your actual model id (e.g. "claude-opus-4-8 (sunday-batch)") so the
      stored briefs stay honest about provenance. The save command validates
      structure and refuses malformed briefs.

3. After the batch (or early stop), report: how many saved, which cases, any failures.
   If the `list` command returns fewer than 20 cases, the queue is running dry —
   say so prominently so Sage can decide the next priority tier.

## Notes

- Landmark cases (Erie, Palsgraf, Celotex...) come first in the queue — give them
  your best work; they are the most-visited pages on the site.
- Some opinions are old-reporter OCR with artifacts; brief what the text supports
  and do not invent facts the excerpt does not contain.
- Cost is logged as $0 / source='subscription' — correct, these use no API dollars.
