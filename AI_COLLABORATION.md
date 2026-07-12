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
- Generation is resilient, validation is not: the on-demand endpoint deterministically
  repairs near-miss passage IDs (`repair_unknown_sources` — a model sometimes emits a
  real ID with one trailing character added or dropped; a unique prefix match identifies
  the intended passage) and gives the model one corrective retry with the validation
  errors fed back before failing. Validation rules themselves are never loosened — a
  wrong-but-plausible source is exactly what the feature exists to prevent. Trigger: a
  user hit `unknown sources: ['op-050f959b963a17925']` (17 hex chars; real IDs are 16)
  on case 667589, 2026-07-12. The Sunday batch pipeline does not use the repair/retry
  path yet — worth unifying if batch failure rates matter.

### Case Information Placement

Case identity and student-facing metadata live in a `Case Information` card at the top
of the case-page sidebar, before Authority Report and Citation Network. The sidebar is the
right home because these fields are reference material used while reading, while the page
header should remain concise. The card uses structured API fields (court, decision date,
reporter/neutral citation, docket, precedential status) plus the curated subject. Raw import
metadata is intentionally not displayed: cluster IDs, match confidence, and ingestion source
are operational details rather than useful legal study context. Rejected alternative: leaving
the old `Additional Information` card below the citator panels, where large authority reports
made it effectively undiscoverable. (Claude diagnosis + Sol implementation, 2026-07-12.)

## Open Questions

Genuine design questions left for the next assistant. If you can resolve one (with
evidence), do so and move the conclusion into Architecture Decisions; if you disagree
with an existing decision, add your case here instead of silently changing the code.

- `validate_structured_summary` enforces a 400–800 word band and fixed per-section claim
  limits for every case. Is one band right for both short procedural opinions and long
  cases with substantial dissents, or should limits scale with opinion length? (Raised
  2026-07-12 by Claude while unifying the validators; no evidence gathered yet.)

## Current Handoffs

### Search: word-boundary title matching
Owner: unknown assistant (found live in the working tree, 2026-07-12 ~11:10 UTC)
Status: appears complete — implemented, tested, and direct-deployed to the backend
Files: `backend/search_utils.py`, `backend/test_search_utils.py`, `backend/main.py` (search endpoint)
Summary: search now matches title terms at word boundaries via `case_title_terms`
alongside the ILIKE pattern. Found uncommitted while another assistant's session was
(or had just been) active. Claude committed it to `main` on 2026-07-12 so the
backend's GitHub auto-deploy would not wipe the direct deploy on the next push —
not to claim the work. Owner: please verify the commit matches your intent, add your
rationale here, and clear this entry.
Deployment: direct deploys `104a19cd` / `fe1d8976` (2026-07-12), then via auto-deploy
Commit: committed by Claude on the owner's behalf

Resolved from the prior handoff: the case-info card was moved above the citator panels and
rebuilt from structured fields. The unrelated legacy `/citator` endpoint remains broken but
has no frontend caller; it is tracked here so a future API cleanup does not lose the finding.

Follow-up fix (Claude, 2026-07-12): case dates on the case page rendered one day early
(and one year early for Jan 1 dates) in US timezones — date-only strings like
`1938-04-25` were parsed as UTC midnight but formatted in local time. All date rendering
in `CaseDetailClient.tsx` now goes through UTC-pinned helpers (`formatCaseDate`,
`caseYear`). If you render `decision_date` anywhere new, use those helpers or pass
`timeZone: 'UTC'`.

## Deployment State

- Case Information sidebar redesign deployed to the frontend as Railway deployment
  `eb3c15d1-0b59-4ad0-86d0-2b0928a8eb4f` on 2026-07-12; implementation is included in
  the commit that records this decision.
- Earlier 2026-07-12 deployments were committed to `main` as `c1fed18` and `a6dad3d`.

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
