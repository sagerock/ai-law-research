# AI Collaboration

This file is the shared surface for AI coding assistants working on Tortwell (formerly Law Study Group).
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
  so the Deployment State section below can stay empty. Note: both Railway services now
  auto-deploy from GitHub `main`, so a push replaces any direct deploy — commit before or
  with your direct deploys, or the next assistant's push will silently roll yours back.)

## Working Styles

Sage's observation from the first day of multi-assistant collaboration (2026-07-12), kept
here as context, not as assignment — either assistant may do any work: Claude tends toward
strategy and framing (this doc's rationale-first structure, turning vague reports into
diagnoses before code, coordination when sessions collide); Sol tends toward fast, precise
implementation (case-info card, abbreviated-caption search — shipped and deployed while
Claude was still mid-investigation on an adjacent bug). Practical use: cross-cutting or
ambiguous problems benefit from a Claude-style framing pass first; well-scoped
implementation is Sol's fast path. Structure teaches behavior — keep this doc's templates
demanding rationale, and every assistant's entries get better.

## Architecture Decisions

### Rebrand: Law Study Group → Tortwell (2026-07-13)

Sage bought `tortwell.com` on 2026-07-13; the site will rebrand from "Law Study Group"
to **Tortwell**. Why: the primary growth channel is word-of-mouth between law students,
and that loop requires that someone who hears the name once can google their way back.
"Law study group" is a generic head term whose SERP is permanently owned by Barbri, the
ABA, FindLaw, and law-school libguides — the site does not appear in the top 10 for its
own name. Considered and rejected: "AI Law Study Group" (collides with the fast-growing
wave of AI-and-law student organizations, and "AI law" misparses as the law of AI);
~90 coined candidates screened for .com availability, empty SERP, and trademark
adjacency, with finalists **Gunnerly** (rejected — "gunner" is the outline-hoarding
archetype, tonally opposed to a free sharing platform, and outsiders hear "gun") and
**Braxby** (rejected — SERP already tenanted by a BoJack Horseman character and a UK
lighting shop). Tortwell won on: effectively empty SERP, reads as a warm surname with a
"torts" wink, and "well" = a shared source everyone draws from, which is the product.
The name is deliberately not brief-specific because the long-term vision (Sage,
2026-07-12) is a free platform for law-school study generally, with briefs as the wedge.
The visual identity was deliberately left unchanged for the domain cutover (changing both
at once would have added risk) and landed the next day — see "Tortwell visual identity"
below. The descriptor stays adjacent to the coined name for clarity.

### Tortwell visual identity (2026-07-13)

Source of truth: Sage's Claude Design project "Tortwell brand identity"
(claude.ai/design project `837c8c71-e066-4431-913d-49f67f90e922`, file `Tortwell
Brand.dc.html`). Sage picked the tortoise mascot direction (design badge MARK-B,
"'Tort'-oise, slow-and-steady studying"), the well/shell roundel (MARK-C) for the
favicon, and tagline "Free law-school study tools, sourced to the opinion" — chosen
because "sourced to the opinion" carries the trust story and outlives the brief-only era.
Implementation decisions (Claude, 2026-07-13):

- Palette swapped in place: `globals.css` keeps the existing `sage-*`/`cream` class
  names but retunes them to the design's warmer values, so the whole app shifted brands
  without touching every file. New `honey-*` scale is the signature accent — the
  casebook-highlighter color. Rule from the design: **honey = source links**; keep that
  association exclusive so the highlight color keeps meaning "verifiable against the
  opinion."
- Fonts: Instrument Serif/DM Sans → Source Serif 4/Hanken Grotesk via `next/font`
  (body variable name unchanged; display variable renamed `--font-serif-display`).
  Source Serif has real weights (Instrument had only 400), so `font-display` headings
  can now use `font-semibold`.
- Marks live in `components/TortoiseMark.tsx` (`TortoiseMark`, `TortwellRoundel`, with
  an `onDark` variant). The design bans gavels/scales/columns/bees — the header's old
  Scale icon is gone; don't reintroduce courthouse clichés.
- Case page: structured-brief source buttons are now honey "source" tags; the Holding
  section renders in a honey card; emoji section headers became badge pills.
- Homepage trust strip and "More than briefs" chips only link to routes that exist;
  Practice hypos and Flashcards are unlinked "SOON" chips — update them when those ship.
- Deferred: dark mode (the design specifies tokens — warm near-black `#22201c`, honey
  `#e8c67e`, sage `#9aa78a` — but the app has no theme infrastructure; add it as its own
  project, not piecemeal).

Verified: unit tests pass, production build passes, homepage and Twombly case page
visually checked against the design's screenshots via local dev + Playwright.

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

### Structured Brief Rebuild (legacy → source-linked)

The ~900 legacy briefs are being rebuilt as source-linked briefs using leftover
subscription credits, not API dollars. Design decisions and why (2026-07-12):

- The rebuild queue (`sunday_briefs.py candidate-list`) covers only cases that already
  have a legacy brief — the legacy Sunday batch keeps covering un-briefed cases, so the
  two queues never race for the same case. Priority mirrors the legacy batch: landmarks,
  curated 1L, then citation count — most-visited pages convert first.
- Generation and semantic review run in SEPARATE fresh sessions (`SUNDAY-SOURCE-BRIEFS.md`
  vs `SOURCE-BRIEF-REVIEW.md`, wrapped by `source_rebuild_burn.sh`). A context that wrote
  a claim is the worst judge of whether its citation supports it. Generation runs on
  Sonnet (cheap; every candidate is gated anyway), review on the strongest default model —
  spend quality where it's load-bearing.
- Review verdicts are scripted (`review-list` / `review-fetch` / `review-save`): approve
  publishes; hold records a `semantic_review` failure that also removes the case from the
  rebuild queue until a human clears it — a brief that failed review must not be silently
  regenerated and re-approved by the same pipeline.
- Held pilot cases (5 of 10) stay held; the pilot's 50% hold rate is the reason the gate
  exists, not a reason to loosen it.
- Rejected cases get ONE scripted triage pass (`triage-list` + `TRIAGE-BRIEFS.md` +
  `triage_pass.sh`): the regenerating session receives the reviewer's rejection note and
  must fix exactly what it names; the corrected candidate re-enters the normal review
  gate. Two-strike rule: a second rejection removes the case permanently — humans only.
  Why one retry with feedback rather than unlimited re-rolls: the dominant rejection
  cause is trained-knowledge bleed (specifics no cited passage states — 9 of the first
  22 candidates), which note-guided correction fixes cheaply, while repeated blind
  regeneration would eventually luck a wrong brief past review. The generation runbook
  now warns against unsourced specifics up front (added mid-run 2026-07-12; watch
  whether the rejection rate drops before tuning further).

### Source-Linked Brief Is the Only Brief Shown

When a case has an approved source-linked brief, the page shows ONLY it; the traditional
brief is hidden, not deleted. Why: (1) the linked brief is the only version whose claims
passed semantic review — it has a verifiable pedigree the legacy text never had; (2) with
both visible, students read the lower-friction plain version and never build the
click-to-verify habit that is the site's core pedagogical differentiator; (3) Sage
validated the linked brief under real class pressure (evidence class, 2026-07-12) and did
not miss the old one. Cases without an approved structured brief (and cases whose
candidates were rejected) keep showing the traditional brief — the rule is per-case.
The brief-preference voting UI retires with this change (it compared two versions that
are no longer both visible) and is replaced by a report-a-problem link that asks the
question that still matters: is this brief wrong? Rejected alternative: keeping both
visible and letting preference votes decide — it optimizes for comfort over the
verification habit, and the votes would mostly measure friction, not quality.
(Sage decision + Claude rationale; Sol implementation, 2026-07-12.) Anonymous problem
reports use a keyed one-way IP fingerprint solely for a five-per-hour rate limit; raw IPs
are never stored. The server derives the displayed summary version rather than trusting a
client-supplied tag. Historical preference endpoints and data remain for analysis, but the
frontend no longer calls or displays them.

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

### Abbreviated Case Captions in Search

Homepage case search treats meaningful caption words as order-independent, literal title
tokens after removing connectors such as `v.` and `versus`. This allows a textbook caption
like `United States v. Ince` to find the stored `United States v. Nigel D. Ince`. PostgreSQL
English full-text stemming was rejected for this path because it reduced `Ince` to `inc`,
creating corporate-name false positives such as `Prince`. Exact citation and contiguous-title
matches still rank ahead of token matches. (Sol, 2026-07-12.)

## Open Questions

Genuine design questions left for the next assistant. If you can resolve one (with
evidence), do so and move the conclusion into Architecture Decisions; if you disagree
with an existing decision, add your case here instead of silently changing the code.

- `validate_structured_summary` enforces a 400–800 word band and fixed per-section claim
  limits for every case. Is one band right for both short procedural opinions and long
  cases with substantial dissents, or should limits scale with opinion length? (Raised
  2026-07-12 by Claude while unifying the validators; no evidence gathered yet.)

## Current Handoffs

### Tortwell domain migration
Owner: Sol
Status: deployed; external SEO submission remains
Files: `frontend/` (branding strings, metadata, `sitemap.ts`, `robots.ts`), Railway
service/domain config, Supabase auth settings
Summary: migrate the deployed site from `lawstudygroup.com` to `tortwell.com` (purchased
2026-07-13; see the Rebrand decision above for rationale). Sage explicitly assigned this
to Sol. Known surface area, not a prescription: Railway custom domain + DNS for the
frontend service; permanent 301s from `lawstudygroup.com` (keep the old domain
registered indefinitely — it holds the existing case-page rankings and any inbound
links); `NEXT_PUBLIC_SITE_URL`; Supabase auth redirect/site URLs (Google OAuth was
verified working 2026-07-01 — re-verify after the URL change); user-visible branding
strings ("Law Study Group" title/tagline/site name); sitemap + robots regeneration;
Google Search Console change-of-address. Watch for hardcoded `lawstudygroup.com`
references outside `NEXT_PUBLIC_SITE_URL`.
Decision: use a host-conditioned permanent Next.js redirect while both domains point to the
same frontend service. It preserves arbitrary paths and query strings and keeps the legacy
domain operational without a second service. Canonical URL generation is centralized in
`frontend/lib/site.ts`. Keep internal infrastructure identifiers such as the existing S3 bucket.
Completed: `tortwell.com` and `www.tortwell.com` are attached to Railway with valid TLS;
Cloudflare DNS and Supabase Site URL/redirect allowlists were updated; frontend and backend
canonical URL variables now use `https://tortwell.com`; Tortwell branding, metadata, generated
links, robots, and all six sitemap chunks are live. `lawstudygroup.com` returns a path- and
query-preserving permanent 308, and `www.tortwell.com` redirects to the apex. Existing visual
identity was retained. Supabase's sender display name and all six authentication email templates
(confirmation, recovery, invite, magic link, email change, reauthentication) use Tortwell; no
`Law Study Group` text remains in hosted mailer settings. Local verification: 80 backend tests,
6 frontend tests, typecheck, and
production build passed. Live verification covered branding, canonical case metadata, redirects,
robots, sitemap chunks, and the auth callback route.
Next: Sage should smoke-test Google/GitHub sign-in, email confirmation, and password recovery
with real accounts, then submit the Tortwell sitemap and Search Console change-of-address.
Deployment: frontend `f00e583f-c19a-4b07-a44f-89d9aa355de9` (successful canonical cutover);
backend `2bb03141-2583-4d4f-9e54-9655cfc2ad54`.
Commits: `53b6f34`, `d14a323`, `379b21b`

### Cheng Evidence textbook coverage
Owner: Sol (mechanical data), Claude (generation/review worker)
Status: in progress
Files: `citator/export_casebook_citations.py`, `citator/sunday_briefs.py`, `backend/main.py`
Summary: Textbook `2467` is the priority source-linked brief queue. Citation authority and
outgoing edges were processed for all 69 CourtListener-backed cases in the 75-case book; six
locally curated `cheng-ev-*` cases cannot use the numeric bulk citation graph. Zero-result cases
are valid corpus results (for example Smith v. Savannah Homes has no incoming rows; Frye and
Meza have no mapped outgoing rows). The source-linked generator no longer requires a legacy
brief first. Approved structured-only briefs now display and count on textbook pages; semantic
review remains mandatory before publication. Display-capped authority citers (newest 100 per
tier) now receive lightweight internal stubs, so every authority case shown on these pages links
to Law Study Group and lazily hydrates on first visit. Baseline was 29 legacy briefs but only 8
approved source-linked briefs.
Next: Run and monitor the source rebuild until the 67-case source-linked gap is exhausted;
triage rejected candidates under the existing two-strike process. Audit the six synthetic cases
manually for external citation identifiers rather than forcing them through CourtListener IDs.
The 23-cycle source rebuild was started in the background on 2026-07-12 (PID/log details are
machine-local; canonical log `/home/sage/logs/source-rebuild.log`).
Deployment: backend `364f07d7-c184-45bb-9811-6f785b7a2da0` successful
Commit: `f020d18`

Resolved (Sol, 2026-07-12): local backend testing now uses a project `.venv` pinned to
production's Python 3.11 via `uv`. Run `make test-setup` once and `make test-local` thereafter.
`pytest.ini` limits discovery to unit suites in `backend/` and `citator/`, excluding live/network
scripts under `scripts/`. Initial verification passed all 80 tests.

### Crawford citation coverage
Owner: Sol
Status: completed
Files: `citator/citator_pipeline.py`, `citator/export_cited_cases.py`
Summary: Populated citation coverage for Crawford v. Washington, site case/CourtListener cluster
`134724` (`541 U.S. 36`), from the 2025-12-02 CourtListener corpus. Production now has an
authority report with 12,180 distinct citing cases (49 binding, 3,301 same-line lower, 8,829
persuasive sister, 1 same-case history) and 65 outgoing cited-case edges. Added reusable
opinion-to-cluster tracing and an idempotent, transaction-protected outgoing citation exporter;
its second Crawford run inserted zero duplicate edges. No user-facing request button was built.
Next: none. The authority API and citation API were both verified live.
Deployment: n/a (offline data operation)
Commit: included in the commit that records this completion

Resolved (Sol, 2026-07-12): approved source-linked briefs are now the only version shown;
legacy text remains stored as fallback. Preference voting was removed from the frontend and
replaced with anonymous-friendly, rate-limited problem reporting. Implementation and migration
are in `67977a8`; backend deployment `9991329f`, frontend deployment `59d09313`.

### Structured brief rebuild — first supervised cycle
Owner: Claude (with Sage)
Status: in progress
Files: `citator/sunday_briefs.py`, `citator/SUNDAY-SOURCE-BRIEFS.md`,
`citator/SOURCE-BRIEF-REVIEW.md`, `citator/source_rebuild_burn.sh`
Summary: rebuild queue opened beyond the pilot; semantic review scripted. First
supervised cycle (2026-07-12 morning, log `/home/sage/logs/source-rebuild.log`):
3 candidates generated by Sonnet 5 in ~12 min; review approved Piper Aircraft and
Parklane Hosiery and rejected World-Wide Volkswagen for attributing foreseeability
reasoning to the wrong court — the gate catching a real hallucination on its first
scaled run. The review session also caught and fixed the 'held' vs 'rejected'
status-constraint bug mid-run (committed as 9800bc2). Throughput: ~3 briefs per
~22-minute cycle; ~890 remaining.
Next: monitor the 10-cycle daytime run (log `/home/sage/logs/source-rebuild.log`) and
tonight's cron output. A 5-cycle triage pass (`/home/sage/logs/triage-pass.log`) is
queued behind the daytime run and will regenerate the ~15 rejected cases with their
rejection notes; cases it fails a second time need human attention.
Decision (Sage, 2026-07-12): Sunday credits focus on the rebuild until the ~890-case
backlog is done. The 7:03pm cron now runs `source_rebuild_burn.sh 15`; the legacy
un-briefed-cases batch (`run_sunday_briefs.sh`) is paused, not retired — restore or
split the pool when the rebuild clears. Both brief versions stay on rebuilt pages
(traditional + source-linked); brief-preference votes will inform any later change.
Deployment: n/a (citator scripts run locally against prod DB)
Commit: see git log for this branch

Resolved: the abbreviated-caption search work (Sol) was found uncommitted mid-session;
Claude committed it as `3eda0f6` so a push would not roll back Sol's direct deploy, and
Sol recorded its rationale under Architecture Decisions. Verified working in production
(`United States v. Ince` finds `United States v. Nigel D. Ince`).

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

- Single source-linked brief display and problem reporting: commit `67977a8`; backend
  auto-deploy `9991329f-b88f-4662-a27e-8a615af3e1e4`; frontend auto-deploy
  `59d09313-bc91-444c-84a7-56839dd5ccfa` (all successful, 2026-07-12). No gap.
- Abbreviated-caption search fix: committed as `3eda0f6` and live via backend auto-deploy
  `c32f6e5c` (2026-07-12), superseding Sol's direct deploy `8e6d6219`. No gap.
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
