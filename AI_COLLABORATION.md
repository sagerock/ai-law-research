# AI Collaboration

This file is the shared surface for AI coding assistants working on Law Study Group.
Read it before substantial work and update it when your work changes it.

This is a collaboration channel, not just a status log. Assistants here cannot talk to
each other directly — this file is the message bus. The most valuable thing you can
record is a **why**, not a **what**: the code already shows what was done, but the
reasoning behind a choice is invisible in the code and is exactly what stops the next
assistant from accidentally relitigating or undoing it. Disagreement is welcome — if you
think a recorded decision is wrong, say so under Open Questions rather than silently
changing it.

## Working Agreement

- Treat the repository and production services as the source of truth; verify claims before recording them here.
- For every durable decision, record the rationale and (briefly) what was considered and rejected.
- Record active work, blockers, and deployment state. Do not use this as a chat transcript.
- Keep entries concise and remove stale information when it is superseded.
- Never include API keys, tokens, connection strings, user data, or other secrets.
- Do not overwrite another assistant's active work. Note overlapping work under Current Handoffs.
- Production deployment does not imply a Git commit or push. Record those states separately.
  (House style: this repo pushes straight to `main`; commit and push promptly after deploying
  so the Deployment State section below can stay empty.)

## Architecture Decisions

### Opinion Loading

Production opinion consumers use the shared loader in `backend/opinion_loader.py`.

Fallback order and why:

1. PostgreSQL `cases.content` — primary store, no extra network hop.
2. S3 `opinions/{case_id}.txt` — full opinion texts are too large to keep them all in
   Postgres, so overflow lives in S3.
3. CourtListener — last and opt-in only. It is a third-party remote call, so callers must
   explicitly pass a fetcher (`fetch_courtlistener`) to permit remote hydration, and it is
   attempted only for numeric IDs because non-numeric case IDs are not CourtListener IDs.

The case-detail endpoint, summary generation, explicit opinion hydration, Case Ask AI, and
citation passage verification use this loader. API case responses expose `opinion_source`
when available. Rejected alternative: each endpoint keeping its own fallback logic — that
is what existed before 2026-07-12, and per-endpoint copies invite silent divergence.

### Source-Linked Briefs

- The frontend offers `Generate Summary` when no brief exists, and `Add Source-Linked
  Brief` when only a legacy brief exists — legacy briefs are kept rather than replaced so
  existing pages never lose content while the structured pipeline catches up.
- Structured briefs and candidates are stored in `ai_summaries` and
  `structured_summary_candidates`. Candidates are staged separately so a failed or
  low-quality generation never overwrites a live brief.
- Stable opinion passages are stored in `opinion_passages` and referenced with `op-...`
  IDs, so brief claims cite passages that survive re-chunking of the opinion text.
- Shared validation and prompt helpers live in `backend/structured_briefs.py`. The Sunday
  briefs pipeline (`citator/sunday_briefs.py`) delegates to the same
  `validate_structured_summary` so batch-generated and on-demand briefs are held to
  identical rules; it previously had its own near-identical copy, which would inevitably
  have drifted.
- Why this feature exists at all: a source link proves a cited passage *exists*, not that
  it *supports* the claim. Structural validation covers the first half; the semantic
  review gate covers the second, so the gate is load-bearing — without it the briefs are
  merely decorated with citations, not verifiable. Keep it strict even when it slows
  brief throughput. (Sage + Claude, 2026-07-12.)

## Open Questions

Genuine design questions left for the next assistant. If you can resolve one (with
evidence), do so and move the conclusion into Architecture Decisions; if you disagree
with an existing decision, add your case here instead of silently changing the code.

- `validate_structured_summary` enforces a 400–800 word band and fixed per-section claim
  limits for every case. Is one band right for both short procedural opinions and long
  cases with substantial dissents, or should limits scale with opinion length? (Raised
  2026-07-12 by Claude while unifying the validators; no evidence gathered yet.)

## Current Handoffs

### Case-info panel buried at the bottom of the case-page sidebar
Owner: Claude (investigated); second opinion requested from GPT 5.6 Sol
Status: ready for review — diagnosis done, fix is a design decision
Files: `frontend/app/case/[id]/CaseDetailClient.tsx` (sidebar, ~lines 1420–1587)
Summary: Sage remembers case information at the top of the right column on case pages;
it appears to have disappeared. Investigation findings (all verified against production
on 2026-07-12, using Erie R.R. v. Tompkins `/cases/304-us-64` as the test case):

- Nothing was ever removed. Full git history of the sidebar shows the same three panels
  since the file's first commit: Authority Report (added June, commit `a42dc72`),
  Citation Network, and "Additional Information" (the metadata card) — in that order,
  metadata card always last.
- All three panels render in the production DOM today (verified via live DOM query;
  accessibility snapshots taken too early miss the client-fetched panels).
- Diagnosis: before the Authority Report shipped, most cases had an empty (hidden)
  Citation Network, so the "Additional Information" card was effectively the *top* of
  the sidebar. The Authority Report now renders thousands of citers in expandable tiers
  (Erie: 16,828), pushing the case-info card below the fold by several screens. Buried,
  not deleted.
- The card's content is also weak: for CourtListener-imported cases it shows raw
  metadata (`cluster id`, `match confidence`, `source`, `subject`) instead of what a
  student wants (court, decision date, reporter cite, docket number, precedential
  status) — all of which the API already returns as top-level fields.

Proposed fix (Claude's view, open to disagreement): add a proper "Case Information"
card pinned at the top of the sidebar built from the structured case fields
(court_name, decision_date, reporter_cite, neutral_cite, docket_number, precedential,
subject), and drop the raw-metadata "Additional Information" card rather than keeping
both. Question for Sol: is top-of-sidebar the right home, or does case info belong in
the page header under the title? And is any raw metadata worth keeping?

Related production bug found during investigation: `GET /api/v1/cases/{id}/citator`
returns 500 in production (e.g. case 103012). The frontend no longer calls it (it uses
`/authority`, which works), so user impact is nil, but the endpoint is broken or should
be removed.
Next: Sol reviews the diagnosis and proposal; whoever implements updates this entry.
Deployment: not deployed
Commit: diagnosis only, nothing to commit yet

## Deployment State

No deploy/commit gap. The 2026-07-12 direct Railway deployments (backend opinion-loader
refactor `b12ed65d`, frontend source-linked upgrade button `bca2303c`) were committed to
`main` on 2026-07-12 as `c1fed18` and `a6dad3d`.

## Update Template

Use this format under Current Handoffs while work is active:

```text
### <short task name>
Owner: <assistant/tool>
Status: planned | in progress | blocked | ready for review
Files: <paths being changed>
Summary: <what is changing and why>
Next: <specific next action>
Deployment: not deployed | deployment ID
Commit: not committed | commit hash
```
