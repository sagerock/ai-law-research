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

### Outlines pivot: canonical per-subject outlines, not an upload marketplace (2026-07-14)

Sage's decision: the public outlines feature becomes ONE canonical, living outline per
subject ("The Civ Pro Outline") that the community improves through votes and comments —
not a bank of user-uploaded files. Class/professor/semester metadata comes off the public
outline: a professor-specific outline serves one classroom for one semester; a subject
outline serves every 1L indefinitely, and dropping course attribution also avoids the
professor-materials copyright gray zone that upload banks carry. Why the pivot: an upload
marketplace with near-zero users is empty (cold start), while a curated outline is full on
day one because Sage authors it; contribution by voting/commenting is far lower friction
than contribution by authoring; outline banks with hundreds of unrated stale files already
exist and are exactly what "one free well, everything you draw from" positions against.
The strategic payoff is structure: a structured outline (sections, not a PDF blob) can
source-link rule statements to the site's own case briefs — honey source-link pattern,
same trust story as briefs ("the outline that cites its sources") — and one authoritative
page per subject is the right SEO shape for head terms like "civ pro outline."

Design choices that go with it:
- Votes and comments attach at the SECTION level, not the outline level. Whole-outline
  votes carry no actionable signal; "this hearsay section confused me" does, and
  section-level feedback is the input a later AI-assisted revision pass consumes.
- Community input is input, not edits. Sage (AI-assisted) merges feedback into versioned
  revisions; comments get marked resolved. No public edit/merge UI.
- PRIVATE uploads stay (Sage, 2026-07-14): "upload your own outline and study against it"
  (`outline_conversations` AI quiz flow) is a different feature from public browsing and
  keeps working. Only the public marketplace surface (public browse/upload/fork of user
  files) is removed.
- Rollout follows the one-feature-at-a-time rule above: v1 = convert Sage's existing civ
  pro outline into the structured, source-linked, genericized format with section
  votes/comments. Torts and Evidence follow the same path. No authoring tools, no merge
  UI, nothing speculative.
- Storage decision (Sol implementation, 2026-07-14): canonical outlines use dedicated
  relational tables, not `outlines.topics` JSONB and not the file-oriented legacy `outlines`
  table. Stable section rows own votes/comments; immutable versioned section-revision rows
  own title/body/source links, so feedback survives edits without rewriting history. The
  version-controlled Civ Pro JSON drives both the interactive timeline and the importer,
  preventing two authored copies from drifting. Existing uploads remain in `outlines` as
  private AI-study documents; legacy public storage objects must be copied into PostgreSQL
  and revoked with `scripts/privatize_outline_uploads.py` before the privacy cutover deploy.

### Casebook full text requires a license; case lists don't (2026-07-14)

**The bright line: never load a casebook's full text (reader chapters or Q&A retrieval
corpus) unless its license permits it.** Today exactly one casebook has full text —
Cheng's Evidence Draft v38, which is CC BY-NC-SA 4.0 (and where Sage has a direct author
relationship; see the Cheng outreach). Its license lives in `casebooks.metadata.license`
(set via `scripts/set_casebook_license.py`), is exposed by the textbook detail API, and
renders as an attribution + license link on the textbook page; the reader chapters carry
their own attribution footer. Any future full-text book must follow the same pattern:
license verified first, metadata set, attribution rendered.

Why the case *lists* (570 casebooks, ~41k case mappings) are a different, defensible
category (Claude analysis, 2026-07-14; Sage — a law student — reviewed the frame): the
opinions are public domain (government edicts), the briefs are Tortwell's own work, and
book metadata is unprotectable fact. The gray area is compilation doctrine — a
casebook's selection/arrangement of cases is protectable (Feist), and the lists
reproduce the selection. Mitigations that keep it defensible and should be preserved:
(1) pages serve a FLAT case list — do not publicly reproduce chapter-by-chapter
structure or chapter headings for unlicensed books (arrangement stays untaken);
(2) zero expressive text from any book — no note questions, excerpts, or commentary;
(3) the fair-use posture is a finding aid pointing to Tortwell's own briefs of
public-domain cases (Google Books/HathiTrust index line), with no market substitution;
(4) the model is industry practice — casebook-aligned study aids are Quimbee's core
product (Sage's inspiration for the feature: https://www.quimbee.com/casebooks/).
Realistic worst case for a list is a publisher takedown request → remove that book's
list. Keep the Textbooks nav link: 502 books with mapped cases, the site's most
student-shaped entry point (decision: Sage, 2026-07-14, after considering removal over
maintenance worries — the catalog is reference data, not content that rots).

### Study tab leads with Outlines; Mindmaps demoted from nav (2026-07-14)

Sage's call: `/study` now redirects to `/study/outlines`, and the Mindmaps tab is gone
from the study nav. Why: mind maps are not a common law-student artifact — students don't
arrive looking for them, and the unfamiliar format also confuses AI assistants working on
study features (an uncommon abstraction pulls generation quality down). Outlines are the
canonical law-school study document, so they lead. Mindmaps is demoted, not deleted:
`/study/session` still renders (existing users' maps and public share links must not 404),
and its tab reappears contextually only when a visitor is already on that page
(`HIDDEN_TABS` in `frontend/app/study/layout.tsx`). Rejected alternatives: deleting the
feature outright (breaks existing data/links for no gain) and keeping it as a second tab
(keeps advertising the thing we don't want new users to anchor on).

Feature-rollout sequencing that goes with this (Sage, 2026-07-14): roll out study
features one at a time rather than broadside — Outlines is the current flagship;
Practice Hypos is designed and parked until after his July 31 Evidence final (see the
parked handoff below); Flashcards later, likely derived from hypo content. The homepage
"SOON" chips are the public roadmap: a chip flips from SOON to linked only when the
feature ships with real content behind it. Don't add new nav entries or chips for
features that don't exist yet.

### Backend-only Supabase tables use default-deny RLS (2026-07-14)

The production FastAPI service connects to Railway PostgreSQL as `postgres`, not to the
Supabase database; that role owns the corresponding Railway tables and has `BYPASSRLS`.
The `legal-researcher` Supabase project retained copies of eleven feature tables where both
`anon` and `authenticated` had unrestricted CRUD grants with RLS disabled. Migration
`037_backend_only_tables_rls.sql` was applied to Supabase: RLS is enabled without policies and
all direct grants to those API roles are revoked. Why default-deny rather than ownership or
public-read policies: checked-in browser code does not query these tables through Supabase;
private and intentionally public access is narrowed by FastAPI endpoints instead. The migration
conditionally revokes Supabase roles so it remains portable to Railway. Verified after applying:
the Supabase security advisor reports no errors, all eleven privilege checks are false for both
API roles, and production health, transparency, pool status, MSJ library, and public mindmap
endpoints remain healthy.

### Paid textbook Q&A boundary (2026-07-13)

Textbook Q&A is a signed-in feature and reserves both the user's daily AI allowance and
community-pool funds before contacting OpenAI, Qdrant, or Anthropic. Why: the endpoint
previously allowed anonymous callers to trigger an Opus answer plus query rewriting and
embeddings, so a public script could create an unbounded bill; checking the pool before a
call was also racy because concurrent requests could all observe the same positive balance.
Per-user quota and pool reservations now use PostgreSQL advisory locks. The pool reserves a
conservative maximum, then refunds the difference after actual provider token usage is known;
failed requests release the user's quota and reconcile any provider cost already incurred.
BYOK supplies both Anthropic calls, while the shared pool still covers the small OpenAI
embedding charge. Retrieval context is capped at 40,000 characters so the maximum reservation
has a meaningful ceiling. Rejected alternative: an in-memory limiter, which would reset on
deploy and fail across multiple Railway instances.

### Site-funded Anthropic calls use bounded reservations (2026-07-15)

Round 2 variable-prompt paths that spend the shared Anthropic key call the free token-count
endpoint before paid generation, then reserve every counted input token at the 125% cache-write
rate plus declared maximum output. Textbook Q&A remains the deliberate exception: its existing
fixed multi-provider reservation is bounded by the 40,000-character retrieval cap. Rejected or
definite pre-provider failures refund; failures after possible acceptance retain the reservation
and write an uncertainty marker. If the process dies before that marker, the still-open original
reservation row is itself the durable audit trail. Settlement/cancellation is restart-safe: unique
reservation and zero-dollar terminal ledger rows plus request/pool advisory locks make retries and
settle/cancel races no-ops, including zero adjustments. The migrated SSE endpoints commit business
writes, usage, adjustment, and terminal marker in one transaction; outline conversation start/reply
does the same. Other non-SSE call sites reconcile billing but are not claimed to make unrelated
business writes atomic. BYOK skips token counting and pool reservation. Accepted model IDs and
prices are explicit, and admin overrides reject unknown IDs.

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
- No dark mode: Sage decided (2026-07-13) the site doesn't need one. Don't build it.
  (If that ever changes, the design specifies the tokens: warm near-black `#22201c`,
  honey `#e8c67e`, sage `#9aa78a`.)

Verified: unit tests pass, production build passes, homepage and Twombly case page
visually checked against the design's screenshots via local dev + Playwright.

Mobile QA pass (Claude, 2026-07-13, after the initial ship): fixed header overflow at
phone widths (the nav was 428px wide at a 390px viewport, clipping Sign In — predated
the rebrand; Discord icon and the Cases link are now desktop-only, since the tortoise
logo already links home), shortened the search placeholder to fit (the "try Twombly"
example lives in the Popular chips), scaled the hero for 320px screens, un-flexed the
source-tag hint so it wraps as a sentence, and added `prefers-reduced-motion` support
plus focus-visible rings on the new chips. Verified zero horizontal overflow at 320
and 390px on both pages. Dev-environment note: Turbopack HMR does not detect file
changes on /mnt/d (WSL2 DrvFs) — restart the dev server to see frontend edits.

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

**Outline-priority tier added 2026-07-15 (Claude, commit d1143b8):** cases linked from a
published canonical outline's current revision now rank just below the priority casebook
in `candidate-list` (by citation count within the tier) and are admitted even without a
legacy brief. Trigger: 174 of 178 outline-linked cases still lacked structured briefs, and
31 had no brief at all — orphaned between the rebuild queue (which required a legacy brief)
and the paused legacy batch. Expected: outline cases convert within ~4 Sundays. Grable
(140872) remains skiplisted — its stored opinion text is the cert grant, not the merits
opinion; fixing that is a data task, not a queue task.

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

### Opinion boundaries are ingestion metadata, not model inference (2026-07-21)

CourtListener API hydration, local Parquet graduation, and S3 publication use one canonical
assembler that preserves every selected sub-opinion's ID, type, author, and source field in
machine-readable boundary markers. Typed components win when they collectively represent the
case; a combined record is retained when the only component is a duplicate lead because it may
contain an embedded dissent absent from the component list. In that shape the typed lead supplies
the default majority boundary, while reporter headings still split separate writings. This avoids
both duplicated majority text and silently omitted dissents. Passage format v5 hashes the derived
passages plus classifications, so changed boundaries cannot share a provenance namespace.

Strict source preflight runs before paid generation and requires a briefable source, verifiable
boundaries, and majority material in the selected prompt packet. Facts, issue, holding, rule, and
majority reasoning may cite only majority/opinion passages; dissent claims may cite only dissent.
Rejected alternative: relaxing validation case by case when a model correctly recognizes a
separate opinion that the parser missed. That would hide source corruption and allow the same bug
to recur across cases. Source-preflight failures are cheap and retry after a six-day backoff so a
repaired source or parser returns to the next weekly queue without livelocking the current run.

### GA4 custom events: env-gated, settle-debounced, failures untracked (2026-07-27)

The GA4 snippet in `app/layout.tsx` was hardcoded to `G-CPYH7HZY5G`, so every local
`npm run dev` session reported into the production property. It now renders only when
`NEXT_PUBLIC_GA_ID` is set (production only), and `lib/analytics.ts` wraps `gtag` so every
call no-ops on the server, in dev, and under ad blockers. Analytics must never interrupt
reading — the wrapper swallows its own errors, matching the existing convention in
`CaseDetailClient`.

Phase 1 instruments the funnel: `search`, `select_content`, `brief_view`, `brief_generate`,
`brief_blocked`. `search`, `select_content`, `sign_up`, and `login` use GA4's recommended
event names so they populate built-in reports without extra configuration.

Two deliberate choices worth preserving:

*Settle-debounce, not keystroke-debounce.* The homepage search fires on a 300ms keystroke
debounce, so one intentional search issues a request per prefix. Tracking each would fill
`search_term` with `n`, `ne`, `neg`… Analytics instead waits `SEARCH_TRACK_DELAY_MS` (1200ms)
after results land and reports only the settled query, deduped by term. Any future search UI
that debounces needs the same treatment.

*Failed requests are not zero-result searches.* The homepage `.catch` and the mock-data
fallbacks in `SearchInterface` are deliberately untracked. Logging them would report phantom
searches when the API is down and corrupt the `result_count: 0` content-gap signal. Note that
`SearchInterface` still shows users two hardcoded fake cases on API failure — untracked here,
but it remains a real correctness problem in its own right.

`brief_view` is latched per case via a ref because `waitForGeneratedSummary` polls
`fetchCachedSummary` up to 30 times; without the latch a slow generation reports 30 views.

Phase 2 adds conversion and retention: `sign_up`, `login`, `bookmark_add`, `signup_intent`,
`study_session_start`, `donate_click`.

*Signup has two paths, not one.* `signUpWithEmail` inserts its own profile row, so the
auto-create branch in `fetchProfile` — despite its "e.g. OAuth sign-in" comment — is reached
**only** by OAuth users. Email signups are tracked in `signUpWithEmail` (`method: 'email'`);
OAuth signups in the auto-create branch. Anyone consolidating these later must keep both, or
half the signups vanish. The provider is stashed in `sessionStorage` before the OAuth redirect
so `method` survives the round trip and the callback's full page load.

*`login` fires on `SIGNED_IN` only.* A page reload replays the stored session as
`INITIAL_SESSION`, which must not count; the tab-visibility resync calls `applySession`
directly and so never counts either. A per-tab latch keyed on user id absorbs Supabase
replaying `SIGNED_IN` on session recovery, and `signOut` clears it so signing back in counts.
A first-time OAuth user fires both `sign_up` and `login` — `login` means "authentications",
not "returning users". Subtract `sign_up` if you want the latter.

*`brief_blocked{reason: sign_in_required}` is the auth wall on the brief path; `signup_intent`
is the one on the bookmark path.* They are deliberately separate events rather than one
merged signal, so neither double-counts the other.

`/byok` is a server component (it exports `metadata`), so its Ko-fi button uses the
`DonateLink` client component rather than converting the page. Reuse it for any future donate
button on a server-rendered page.

Custom event parameters do not appear in any GA4 report until they are registered as custom
dimensions (Admin → Custom definitions, scope `Event`): `search_type`, `result_count`,
`case_id`, `cached`, `has_structured`, `reason`, `outcome`, `source`, `position`, `has_brief`,
`method`, `trigger`, `placement`, `mindmap_id`.
Shipping the code and seeing an empty report is the expected failure if this step is skipped.

Structured briefs have **no word budget** (Sage, 2026-09-26): "the summary should be whatever
is necessary to give a good summary." The 400–800 band was removed from
`validate_structured_summary` and the prompt. Why: United States v. Guest (107201) 502'd
on-demand at 843 then 807 words, and the cap was the most common first-attempt failure
(9 of 13, 2026-09-07 to 09-26), hitting multi-opinion cases hardest. Per-section claim
counts still apply. On-demand `max_tokens` rose 4000 → 8000 for headroom. On-demand
validation failures now land in `structured_summary_failures` (error prefixed
`on_demand:`); before, only Railway logs showed them.

CourtListener `100trialcourt` opinions map to part `opinion`, not `other` (2026-09-26).
A district court's opinion is the court's own ruling. As `other`, every federal trial-court
case failed preflight with "no majority material" (all 10 such on-demand 503s, 09-08 to
09-25). `detect_opinion_marker` also reads stored `100trialcourt` markers labeled `other`
as `opinion`, so the ~206 already-stored texts work without a refetch. The batch venv
(`~/.venvs/lawdata`) now has `httpx` and `beautifulsoup4` for the CourtListener fallback.

## Open Questions

Genuine design questions left for the next assistant. If you can resolve one (with
evidence), do so and move the conclusion into Architecture Decisions; if you disagree
with an existing decision, add your case here instead of silently changing the code.

- ~~`validate_structured_summary` enforces a 400–800 word band...~~ **RESOLVED 2026-09-26
  by Sage: no word budget.** See Architecture Decisions.
- ~~Boundary-preflight refusal rate hit 100%... needing code investigation~~ **RESOLVED
  2026-08-30 (seventh Sunday session).** Root cause found by instrumenting
  `assess_opinion_boundaries` directly against four freshly-refused cases: every one has
  `counts == {"opinion": N}` (parser found passages but no majority/concurrence/dissent
  split) **and zero canonical or extractor markers in the raw text**
  (`CANONICAL_MARKER_RE` / `EXTRACTOR_MARKER_RE` both find nothing). The refusal branch at
  `opinion_passages.py:603-616` only trusts a single-writing case when
  `canonical_marker_count == 1`; with zero markers it lands in the `require_explicit`
  error instead of the warning. Those `[[COURTLISTENER_SUBOPINION ...]]` markers are only
  ever written by `courtlistener_opinions.fetch_courtlistener_document` (the live CL-API
  assembly path), which is called from exactly one place —
  `main.py:_fetch_opinion_text_from_cl`, itself gated by the idempotent
  `/api/v1/cases/{id}/fetch-opinion` endpoint that **skips any case that already has
  `content`**. The entire REBUILD backlog already has legacy `content` (that's the queue's
  membership condition), populated years ago by `scripts/fetch_full_opinions.py`, which
  writes raw fetched text straight to `cases.content` (`fetch_full_opinions.py:57-61`) with
  no marker-assembly step at all. So this was never a data-quality regression or a "queue
  getting harder" drift — it's a structural gap: **no code path has ever added boundary
  markers to a case that already had bulk-imported content**, so strict preflight
  (`require_explicit=True`, used only by `candidate-opinion`) was always going to refuse
  ~100% of this queue once enough of the easy pre-marked cases (new stub cases fetched
  post-launch via the live endpoint) were cleared out. Not investigated further: whether to
  (a) relax the single-writing branch to trust `EXTRACTOR_MARKER_RE`-free, single-part text
  above some confidence heuristic, or (b) write a backfill script that re-runs
  `fetch_courtlistener_document` against every REBUILD-queue case's CourtListener cluster
  ID and overwrites `content` with the marker-assembled version before preflight runs. (b)
  is likely correct long-term (it's real data, not a heuristic relaxation) but needs rate-
  limit handling for ~890 cases and a decision on whether to also backfill `cases.content`
  site-wide or just the queue. See seventh Sunday session under Current Handoffs for the
  diagnostic script and full per-case output.
  **Fixed 2026-09-26 (Claude), lazily per case:** `candidate-opinion` now falls back to the
  marker-assembled CourtListener fetch when DB and S3 text fail preflight, as the summarize
  endpoint already did, and writes it back to `cases.content` under the same
  `content_hash` guard. No bulk backfill; Sage chose not to regenerate the backlog now.
  Dry run: 20/20 previously refused cases pass preflight.

## Current Handoffs

### Rejected-brief triage 2026-09-27 (second run): 3 regenerations saved as `pending`
Owner: Claude (claude-sonnet-5)
Status: completed; 3/3 saved (limit 3), awaiting a fresh review session
Ran `TRIAGE-BRIEFS.md`. All three content hashes matched the rejected candidates, so no passage remaps.
Each fix touched only what the note named; claims the reviewer called supported were left as-is.
- **Dobbs v. Jackson Women's Health (6481357)**: majority_reasoning[1] attributed the equal protection theory
  to amici without citing the introducing passage. Added op-ef15273fb7c1e235. Cut the significance sentence
  about what the brief omits.
- **NCNB Texas National Bank v. Johnson (6143)**: majority_reasoning[1] now cites op-7e034db2de16d159 (the
  evidence list incl. indorsed note); facts[0] adds op-e54b3ca0e5f87fb5 (Anderson a shareholder); holding[1]
  adds the counterclaim/district-court passages that give "So does this court" an antecedent. Cut the
  significance "omits..." sentence.
- **United States v. Newbold (1141)**: rule[0] re-sourced to the UNPUBLISHED header and per curiam passages and
  trimmed to "not binding precedent"; facts[0] dropped "civil action brought by the United States";
  holding[0] cites the Fourth Circuit header; "written materials" restored to "materials before the court";
  significance no longer calls it "routine unpublished".
These were each case's one triage attempt; a second rejection makes them humans-only.
Files touched: AI_COLLABORATION.md (this entry). Scratch under /tmp only.
Deployment: none.

### Semantic review session 2026-09-27 (eleventh run): 6 reviewed, 3 approved, 3 held — queue clear
Owner: Claude
Status: completed; review queue empty after six candidates (limit was 8)
Ran `SOURCE-BRIEF-REVIEW.md`. Approved and published, all three triage regenerations: Lucky Brand v.
Marcel (4753847), Benn v. Thomas (1244600), McQuirter v. State (1801433). Each cured exactly what
its rejection note named. Held, with every failing claim named in each saved note:
- **Mas v. Perry (8904733)**: significance says the court "also observed, beyond its holding," that
  hearing one spouse's claim with the other's is sensible. No sourced section establishes it; the
  observation is only in uncited op-c28a8bb6b0853a9e and op-9d569474f1a8a217. Significance-only hold.
- **Chauffeurs Local 391 v. Terry (112394)**: majority_reasoning[0], [1], [2] state Part III-A
  reasoning as the Court's ("The Court found the trust analogy far more persuasive"). Every passage
  they cite is in III-A, which the cited opening passage says is not the opinion of the Court.
- **People v. Ceballos (2609526)**: issue[0], majority_reasoning[0], [1], [2] carry specifics found
  only in uncited passages (the "had he been present" contention, what the exception is, "even if
  the exception applied," and subdivision 4's text).
All three holds are first rejections, so each gets its one triage pass. Same standard as the ten
earlier runs. Mas and Ceballos are citation-only cures and the notes name the passage IDs. Why
Terry differs: its cure is wording, since the passages support what was said but not who said it.
Significance already discloses that III-A lacked a majority, which is why this was a judgment call;
I held because the claims sit under majority reasoning and name the Court.
Parser note: Terry's Part III-A passages (ordinals 43-85) are labeled `majority`, so validation
cannot catch plurality reasoning cited as the Court's.
Judgment calls recorded in the approve notes: Lucky Brand's "second round"/"third round" labels are
an ordering inference from cited passages; Benn facts[2] cites "this request" passages and relies
on the issue passage to identify the request.
Files touched: AI_COLLABORATION.md (this entry). Scratch under /tmp only.
Deployment: none.

### Sunday source-brief generation 2026-09-27 (fourth run): 3 candidates saved, 1 queue case skipped
Owner: Claude (claude-sonnet-5)
Status: completed; 3/3 saved as `pending` on first try, awaiting a fresh review session
Saved: Mas v. Perry (8904733, hash d1a8e6a111d1, single majority packet, no dissent), Chauffeurs, Teamsters &
Helpers Local 391 v. Terry (112394, hash f2a1a5bcf05d, majority cited only; the packet has concurrence and dissent
passages but Dissent was left empty, and Significance notes Part III-A was not a majority), People v. Ceballos
(2609526, hash 71ae46b356b7, single-opinion packet). Skipped, not saved: United States v. Nixon (19845), still
first in `candidate-list` with the wrong-case packet (2000 Fifth Circuit mail fraud), so I took entries 2-4 from
`candidate-list 5`. Nixon will keep blocking `candidate-list 1` until it is fixed or excluded.
Nothing reviewed by this session.
Files touched: AI_COLLABORATION.md (this entry). Scratch under /tmp only.
Deployment: none.

### Rejected-brief triage 2026-09-27: 3 regenerations saved as `pending`
Owner: Claude (claude-sonnet-5)
Status: completed; 3/3 saved (limit 3), awaiting a fresh review session
Ran `TRIAGE-BRIEFS.md`. All three content hashes matched the rejected candidates, so no passage remaps.
Each fix touched only what the note named; claims the reviewer called supported were left as-is.
- **Lucky Brand v. Marcel (4753847)**: majority_reasoning[3] named "judgment enforcement, collateral attack,
  and Beloit v. Morgan" but cited only "these authorities" passages. Re-sourced to op-649469e9ec8a4337,
  op-287125bb05e3f929, op-6bb71fdb11007251. Also re-sourced facts[2] (early release defense) to
  op-9a169bcba7f87247/op-555fee421549eb6c, and cut "unanimous" and "left open whether..." from significance.
- **Benn v. Thomas (1244600)**: majority_reasoning[1] inverted op-0595f74dd860ba73 ("jury could have found no
  liability"); rewritten as the concession the passage makes. majority_reasoning[3] now cites the
  defendant's argument (op-abfcff410adedeb6); majority_reasoning[0] cites op-0de0ecde9fae2f7d.
- **McQuirter v. State (1801433)**: facts[2] said "two officers" for one witness's testimony; rewritten around
  Strickland (Atmore jail, Brewton repeat), Seals's corroboration, and Bryars's separate statement.
  facts[1] dropped "neighbor" (not in any passage) and now cites op-a667998abb50295d; facts[3] cites op-9b12c3ae1d3bc291.
These were each case's one triage attempt; a second rejection makes them humans-only.
Files touched: AI_COLLABORATION.md (this entry). Scratch under /tmp only.
Deployment: none.

### Semantic review session 2026-09-27 (tenth run): 6 reviewed, 2 approved, 4 held — queue clear
Owner: Claude
Status: completed; review queue empty after six candidates (limit was 8)
Ran `SOURCE-BRIEF-REVIEW.md`. Approved and published: Derdiarian v. Felix Contracting (5684475,
triage) and United States ex rel. Coastal Steel Erectors v. Algernon Blair (311461). Held, with
every failing claim named in each saved note:
- **People v. Chun (2506956, triage)**: rule[0] and majority_reasoning[3] say "implied malice";
  the cited passages say only "the physical component" and "conscious-disregard-for-life malice."
  rule[0]'s "because" also has no cited support tying the physical component to felony murder.
- **Parvi v. City of Kingston (5632396, triage)**: majority_reasoning[0] says lack of consent was
  established, but no cited passage mentions consent. One-claim hold.
- **Klocek v. Gateway (2503865)**: facts[2] says "Paragraph 10 of the Standard Terms"; the cited
  passages are the clause text with no attribution. rule[0]'s "acceptance or confirmation" is uncited.
- **Seaver v. Ransom (3607257)**: facts[0] says "their house"; an uncited passage says the house
  was hers, and the brief's own holding turns on what Beman took under her will. One-claim hold.
Chun and Parvi are second rejections, so under the two-strike rule they are now humans-only. Same
standard as the nine earlier runs. Every hold except Seaver's is a citation-only cure, and each note
names the passage IDs. Why Chun and Parvi are worth a human look first: triage cured everything
their first notes named, and the second strike is a gap the first review passed, so adding two
citations each publishes them (Chun: op-511a9c06a9ae675c, op-4617750284abf5d1; Parvi:
op-d4cbfb87ddd2a424, op-4b5c239fd1dbf813).
One judgment call is recorded in an approve note: Coastal Steel majority_reasoning[1] states in the
court's voice a proposition the passage attributes to the Tenth Circuit.
Files touched: AI_COLLABORATION.md (this entry). Scratch under /tmp only.
Deployment: none.

### Sunday source-brief generation 2026-09-27 (third run): 3 candidates saved, 1 queue case skipped
Owner: Claude (claude-sonnet-5)
Status: completed; 3/3 saved as `pending`, awaiting a fresh review session
Saved on first try: United States ex rel. Coastal Steel Erectors v. Algernon Blair (311461, hash
cc1ce03ded94, single-opinion packet), Klocek v. Gateway (2503865, hash 0404c3cbd720, majority-only
packet, briefed on the Gateway arbitration ruling), Seaver v. Ransom (3607257, hash 03e13838fb59,
majority-only packet; the packet notes dissenters but has no dissent text, so Dissent is empty).
Skipped, not saved: United States v. Nixon (19845) — packet is still the 2000 Fifth Circuit mail-fraud
opinion (Jimmy Nixon), the wrong case; it is still first in `candidate-list` and blocks `candidate-list 1`
until it is fixed or excluded. Took the next entries from `candidate-list 5`. Nothing reviewed by this session.
Files touched: AI_COLLABORATION.md (this entry). Scratch under /tmp only.
Deployment: none.

### Semantic review session 2026-09-27 (ninth run): 6 reviewed, 2 approved, 4 held — queue clear
Owner: Claude
Status: completed; review queue empty after six candidates (limit was 8)
Ran `SOURCE-BRIEF-REVIEW.md`. Approved and published: Carter v. Hinkle (6925878, triage) and Miller
v. California (108838). Held, with every failing claim named in each saved note:
- **Richardson v. Chapman (2195023, triage)**: majority_reasoning[0] and [3] call the benchmark
  "Professor Linke's present-cash-value estimate"; the cited passages say only "the higher figure
  presented in the testimony." The July note had already flagged "present-cash-value" as unsourced.
  majority_reasoning[1]'s "facial scarring" is uncited, and "no prospect of recovery" is in no
  majority passage at all.
- **Wagner v. International Railway (3607799, triage)**: majority_reasoning[2] says the hat was
  "found on a beam"; the cited passage says only "the finding of the hat." One-claim hold.
- **Connecticut v. Doehr (112615)**: majority_reasoning[1] cites "this confusion" and "the issue"
  without the passages that say they mean probable cause and the alleged assault. One-claim hold.
- **Howard v. Federal Crop Insurance (338519)**: majority_reasoning[2] and significance name the
  Restatement, which no cited passage mentions; majority_reasoning[1]'s "on which FCIC relied" is
  unsourced.
Richardson and Wagner are second rejections, so under the two-strike rule they are now
humans-only. Same standard as the eight earlier runs. Every hold except Richardson's "no prospect
of recovery" is a citation-only cure, and each note names the passage ID. Why Wagner is worth a
human look first: triage cured the claim the July note named, and the second strike is a detail
the July review passed, so one added citation (op-3fc1f78d1e21ed65) publishes it.
Two judgment calls are recorded in the approve notes: Carter majority_reasoning[2] cites the trial
court's quoted sentence on legislative inaction, and Miller dissent[0]'s "three-pronged" and
"as vague as its predecessors" lean on passages cited under dissent[2].
Ops note: one `review-save` hit an asyncpg connect timeout; nothing was written and the retry saved.
Files touched: AI_COLLABORATION.md (this entry). Scratch under /tmp only.
Deployment: none.

### Sunday source-brief generation 2026-09-27 (second run): 3 candidates saved, 2 queue cases skipped
Owner: Claude (claude-sonnet-5)
Status: completed; 3/3 saved as `pending`, awaiting a fresh review session
Saved on first try: Connecticut v. Doehr (112615, hash 9815c5e95ecc, majority/concurrence packet, no
dissent), Miller v. California (108838, hash d0fcff2ad52d, with dissent section), Howard v. Federal Crop
Insurance Corp. (338519, hash 0886a5c5c296, single-opinion packet). Skipped, not saved: Buckley v. Valeo
(109380) — `candidate-opinion` refused ("separate opinions but no explicit majority boundary"); United
States v. Nixon (19845) — the packet is a 2000 Fifth Circuit mail-fraud opinion (Jimmy Nixon), the wrong
case. Nixon is still first in `candidate-list`, so it will block `candidate-list 1` for the next session
until it is fixed or excluded; the runbook has no skip command, so I took the next entries from
`candidate-list 4`. Nothing reviewed by this session.
Files touched: AI_COLLABORATION.md (this entry). Scratch under /tmp only.
Deployment: none.

### Semantic review session 2026-09-27 (eighth run): 6 reviewed, 6 approved, 0 held — queue clear
Owner: Claude
Status: completed; review queue empty after six candidates (limit was 8)
Ran `SOURCE-BRIEF-REVIEW.md`. Approved and published: J. McIntyre v. Nicastro (219733, triage),
Rasoulzadeh v. Associated Press (1866935, triage), United States v. Contento-Pachon (428603,
triage), Mitchill v. Lath (3617659), Britton v. Turner (8531446), Lenawee County Board of Health
v. Messerly (1614330). A 6/6 batch is the runbook's signal to re-check the standard, so every
candidate got a second pass for specifics that no cited passage states; none turned up. Same
standard as the seven earlier runs: a specific supported nowhere in the candidate holds, one
supported only under a different claim is noted. Why this batch differs: the three triage
candidates cured every claim their July notes named, and the three new ones follow the patterns
the generation session applied (both halves of split passages cited, no unsourced names or roles).
Four judgment calls are recorded in the saved notes, and a human who disagrees should pull the brief:
- **Nicastro holding[1]** is verbatim in its passage, but that passage is the syllabus's summary
  of the Breyer concurrence, not the plurality. The claim names no author.
- **Rasoulzadeh majority_reasoning[2]** says the house was "seized as the foreseeable consequence"
  where its passage says "They claim." The opinion states foreseeability in its own voice in a
  passage cited under facts[3] and issue[0].
- **Mitchill significance** names Lehman as the dissenter; only an uncited passage names him.
- **Messerly significance** calls the test "the Restatement (Second) approach"; no sourced section
  names the Restatement.
Parser note: in Nicastro the Breyer concurrence passages are labeled `majority` (ordinals 225+).
No claim cites them, but a future regeneration could.
Files touched: AI_COLLABORATION.md (this entry). Scratch under /tmp only.
Deployment: none.

### Sunday source-brief generation 2026-09-27: 3 candidates saved, no failures
Owner: Claude (claude-sonnet-5)
Status: completed; 3/3 saved as `pending`, awaiting a fresh review session
Ran `SUNDAY-SOURCE-BRIEFS.md`, all first-try saves: Mitchill v. Lath (3617659, hash ed4e89de4df2, with
dissent section), Britton v. Turner (8531446, hash 646e1969c8a0, no dissent), Lenawee County Board of
Health v. Messerly (1614330, hash 29289f68f81d, single-opinion packet). Applied the review notes' patterns:
cited both halves of mid-sentence passage splits, kept party first names and roles out unless a passage
states them, and kept "this brief omits" statements out of significance. Nothing reviewed by this session.
Files touched: AI_COLLABORATION.md (this entry). Scratch under /tmp only.
Deployment: none.

### Semantic review session 2026-09-27 (seventh run): 6 reviewed, 1 approved, 5 held — queue clear
Owner: Claude
Status: completed; review queue empty after six candidates (limit was 8)
Ran `SOURCE-BRIEF-REVIEW.md`. Approved: Austin Instrument v. Loral (5678730). Held, with every
failing claim named in each saved note:
- **Temple v. Synthes (112500, triage)**: facts[1] and issue[0] call the state-court suit a
  "malpractice" suit; the passages give those grounds only for the administrative proceeding.
- **Iqbal v. Ashcroft (30747, triage; the Fifth Circuit asylum case)**: majority_reasoning[3] says
  the country-conditions argument "was not properly before the court." The opinion only names the
  remedy (motion to reopen) and never says that, in any of its 25 passages.
- **Machuca Gonzalez v. Chrysler (28432, triage)**: majority_reasoning[0] describes Piper as
  "Scottish plaintiffs suing American manufacturers" with no passage on the Piper parties cited;
  majority_reasoning[3] says "his mother" where the opinion says only "the driver (Gonzalez's wife)."
- **Hawkins v. McGee (3574015)**: majority_reasoning[3] cites "It represented a part of the price"
  without the passage that says "It" is the pain of the operation. One-claim hold.
- **Leonard v. Pepsico (2579076)**: majority_reasoning[1] names Carbolic Smoke Ball, which no cited
  passage mentions; facts[1] puts the teenager in the jet without the cockpit passage.
Temple, Iqbal, and Gonzalez are second rejections, so under the two-strike rule they are now
humans-only. Same standard as the six earlier runs. Why these three differ from most earlier
second strikes: their failures are wording the opinion never uses (malpractice suit, not properly
before the court, mother), so the cure is editing the claim, not adding a citation. Hawkins and
Leonard are citation-only cures, and each note names the passage ID.
Files touched: AI_COLLABORATION.md (this entry). Scratch under /tmp only.
Deployment: none.

### Semantic review session 2026-09-27 (sixth run): 6 reviewed, 1 approved, 5 held — queue clear
Owner: Claude
Status: completed; review queue empty after six candidates (limit was 8)
Ran `SOURCE-BRIEF-REVIEW.md`. Approved: Piesco v. Koch (659320, triage). Held, with every failing
claim named in each saved note:
- **The T.J. Hooper (1542549, triage)**: majority_reasoning[2] says other tugmasters "who received
  the Arlington reports chose to seek shelter at the Breakwater"; the cited passages start at "All
  this" and never state it. holding[0] gives one reason for both barges (pumps could not keep pace),
  but a passage cited under facts[1] says No. 17's pumps failed "for quite another reason."
- **Walden v. Fiore (2654532, triage)**: majority_reasoning[2] says the Court distinguished Calder
  v. Jones; no cited passage names Calder or draws the distinction. rule[0]'s "relationship among
  the defendant, the forum, and the litigation" and majority_reasoning[3]'s "while they resided in
  Nevada" are also uncited.
- **People v. Rizzo (1349311)**: facts[0] "Michigan State Police trooper" and facts[1] "through the
  open driver's side window" are in uncited passages only.
- **Lefkowitz v. Great Minneapolis Surplus Store (1289586)**: majority_reasoning[1] and [0] attribute
  the "unilateral offer" argument and the authorities to the defendant; the attributing sentences
  are uncited.
- **Sherwood v. Walker (3532643)**: four facts claims carry uncited specifics (King's cattle-yard,
  defendants as breeders, Graham's role, the justice's court).
T.J. Hooper and Walden are second rejections, so under the two-strike rule they are now
humans-only. Same standard as the five earlier runs. Every hold except T.J. Hooper's holding[0] is
a re-sourcing gap, and each note names the uncited passage ID that would cure it. Why this matters
for the generation runbook: facts sections keep paraphrasing the opinion's opening paragraphs while
citing only one or two sentences from them, so role and place details ride along unsourced.
Files touched: AI_COLLABORATION.md (this entry). Scratch under /tmp only.
Deployment: none.

### Semantic review session 2026-09-27 (fifth run): 6 reviewed, 2 approved, 4 held — queue clear
Owner: Claude
Status: completed; review queue empty after six candidates (limit was 8)
Ran `SOURCE-BRIEF-REVIEW.md`. Approved: Liberty Mutual Insurance v. Wetzel (109403, triage) and
Hoffman v. Red Owl Stores (2161398). Held, with every failing claim named in each saved note:
- **United States v. Peoni (1485475, triage)**: facts[1] says Regno resold "to Dorsey, also in the
  Bronx"; the cited passage truncates at "sold the same bills to one," and nothing cited places that
  sale. holding[0]'s "or sold them to a second possessor" sits past a passage that ends at "or."
- **Tunkl v. Regents (1149237, triage)**: holding[0] says the release "is invalid under Civil Code
  section 1668"; the cited passages say only that the contract affects the public interest and that
  the judgment is reversed. rule[1] cites the list items without the sentence that introduces them.
- **United States v. Newbold (1141)**: rule[0] concludes the disposition "carries no precedential
  weight," but no cited passage says this opinion is unpublished, and "not binding" is narrower.
  facts[0]'s "civil action brought by the United States" comes from the caption, not a passage.
- **Angel v. Murray (2303115)**: facts[3] says "Taxpayers sued"; the passage says "Alfred L. Angel
  and others." One-claim hold.
Peoni and Tunkl are second rejections, so under the two-strike rule they are now humans-only. Both
are re-sourcing fixes, not wrong claims: the supporting text is in the passage right after the
cited one. Why that keeps happening: passages split mid-sentence at commas and citation periods,
so a claim drawn from one sentence needs both halves cited. Same standard as the four earlier runs.
Files touched: AI_COLLABORATION.md (this entry). Scratch under /tmp only.
Deployment: none.

### Semantic review session 2026-09-27 (fourth run): 6 reviewed, 1 approved, 5 held — queue clear
Owner: Claude
Status: completed; review queue empty after six candidates (limit was 8)
Ran `SOURCE-BRIEF-REVIEW.md`. Approved: MacMunn v. Eli Lilly Co. (2580870). Held, with every
failing claim named in each saved note:
- **Ricketts v. Scothorn (6769658, triage)**: rule[1] says courts enforced gift notes "on estoppel
  principles rather than" as consideration. The cited passage says those decisions were "generally
  put on the ground" of consideration; estoppel is this court's own view of the "true reason."
  facts[0]'s "John C." has no cited support (the note passage truncates at "J. 0.").
- **Childress v. Taylor (569096, triage)**: rule[1] gives the editor/researcher concern as the reason
  for the copyrightability requirement. The cited passages use it for the separate intent
  requirement, and one says an editor's revisions include "copyrightable expression."
  majority_reasoning[1]'s "unsuccessful" negotiations "over authorship and billing" are unsourced.
- **Osborn v. Bank of United States (85451, triage)**: facts[1] has Harper delivering money to
  "state treasury officers Currie and then Sullivan," both keeping it "segregated"; the passages
  say "either to Currie or Osborn" and one unidentified answer says "untouched." facts[0]'s "Ralph"
  and the $100,000 charge as the law's own term are unsourced; majority_reasoning[2] lacks the
  naturalized-citizen antecedent.
- **Dobbs v. Jackson Women's Health (6481357)**: majority_reasoning[1] names "the equal protection
  theory offered by some amici"; the cited passages say only "this theory." One-claim hold.
- **NCNB Texas National Bank v. Johnson (6143)**: majority_reasoning[1]'s "endorsed note" rests on
  "this evidence" with no antecedent cited; facts[0]'s "shareholder Fred Anderson" is unsourced;
  significance lists rulings (collateral sale, appellate jurisdiction, attorney's fees) that no
  sourced section establishes.
Ricketts, Childress, and Osborn are second rejections, so under the two-strike rule they are now
humans-only. Same standard as the three earlier runs today. Two patterns worth acting on in the
generation runbook: (1) party first names and roles come from trained knowledge, not the packet
(John C. Ricketts, Ralph Osborn, Fred Anderson), and (2) "this brief omits..." sentences in
significance assert opinion content the brief never sources (Dobbs, NCNB).
Files touched: AI_COLLABORATION.md (this entry). Scratch under /tmp only.
Deployment: none.

### Semantic review session 2026-09-27 (third run): 6 reviewed, 2 approved, 4 held — queue clear
Owner: Claude
Status: completed; review queue empty after six candidates (limit was 8)
Ran `SOURCE-BRIEF-REVIEW.md` on the three triage regenerations and three new Sunday-batch
candidates. Approved: State v. Rothlisberger (2621346, triage) and Burdick v. Superior Court
(2770126). Held, with the failing claims named in each saved note:
- **McCray v. State Farm (7830390, triage)**: facts[2] states as fact that State Farm mailed the
  August 30 notice to the McCrays and Regions Bank. Mailing is the question the court sends to the
  jury; the only cited support is the State Farm supervisor's affidavit statement, and the opinion
  says State Farm "claimed to have mailed" it. facts[1]'s signed payment plan is uncited.
- **Secretary of HEW v. Meza (273618, triage)**: majority_reasoning[2] says the hearing examiner
  "addressed only the 1948 disappearance." The cited passage is the District Court's view, and the
  opinion then says "However, the hearing examiner did consider the 1954 disappearance."
- **Benn v. Thomas (1244600)**: majority_reasoning[1] says the jury "could have found no liability"
  under the instructions as given; the cited passage says the jury "might have found the defendant
  liable" under them. The claim inverts a concession.
- **McQuirter v. State (1801433)**: facts[2] says "Two police officers testified" to the statements,
  but both cited passages are Chief Strickland's testimony alone.
McCray and Meza are second rejections, so under the two-strike rule they are now humans-only. In
both, triage fixed exactly the claim the first note named and the second review failed a different
claim. Why that matters: a first-review note that lists only the worst failure leaves the rest for
the second strike, so hold notes here list every failing claim found, not just the first.
Pattern in all four holds: the claim is accurate to the opinion's topic but states an attributed
or conceded point (a party's assertion, a lower court's view) in the court's own voice, or its
antecedent sits in an adjacent uncited passage.
Files touched: AI_COLLABORATION.md (this entry). Scratch under /tmp only.
Deployment: none.

### Triage session 2026-09-27: 3 regenerations saved, 2 source-preflight refusals skipped
Owner: Claude
Status: completed 2026-09-27 — 3/3 candidates saved (pending fresh review)
Ran `TRIAGE-BRIEFS.md`. **All three saved cases had a stale content_hash** (the rejected candidate
was written against the pre-v10 passage format), so every cited ID was checked against the fresh
packet and orphaned ones were remapped by text match against the old passages (read from
`opinion_passages` under the old hash). Only the claim the note named was substantively changed.
- **State v. Rothlisberger (2621346)**: facts[1]'s "thirty-day advance notice" clause was not in its
  cited passages. Re-sourced by adding op-cbc2e2ae2e41a54f (objection: expert testimony "required
  the State to give the defense thirty days' advance notice") and op-8395faab2ceea7f7 ("the State did
  not give the requisite advance notice"). 5 stale IDs remapped, claim text untouched.
- **McCray v. State Farm (7830390)**: facts[3]'s coverage denial and breach suit were cited to a
  summary-judgment-motion passage. Re-sourced to op-73e18c16244bc9b3 ("After State Farm denied
  coverage because the policy had been canceled, the McCrays sued State Farm alleging breach of
  contract") and dropped op-8b00506ea277727c. 8 stale IDs remapped; two of them were passages
  the new build merged (rule[0]/[1] now share op-82a4c1b330b66003).
- **Secretary of HEW v. Meza (273618)**: facts[2] said a California court "declared him dead" in
  December 1961; the passage says only that Lucy petitioned then. The packet's next passage,
  op-c8f804472908a622, says the petition was granted January 3, 1962. Rewrote the clause to
  petition in December 1961, granted January 3, 1962, and added that ID. 8 stale IDs remapped
  (including passages the new build split in two, e.g. the 20 C.F.R. 404.705 quotation).
- **Skipped, source preflight refused `candidate-opinion` (not counted): United States v. Elfgeeh
  (1386819)**, "separate opinions but no explicit majority boundary"; **In Re Grand Jury Proceedings
  (732430)**, "no verifiable opinion-part boundaries." Their rejection notes are unaddressed and both
  need human attention or a marker-assembled source re-ingest.
Files touched: AI_COLLABORATION.md (this entry). Scratch under /tmp only.
Deployment: none. Commit: none.

### Semantic review session 2026-09-27 (second run): 5 reviewed, 2 approved, 3 held — queue clear
Owner: Claude
Status: completed; review queue empty after five candidates (limit was 8)
Ran `SOURCE-BRIEF-REVIEW.md`. Approved: Commonwealth v. Cosby (10315392, triage) and Kirby v.
Foster (4104630). Held, with the failing claims named in each saved note:
- **United States v. Biaggi (545489, triage)**: facts[0] calls Section 8(a) a "minority set-aside
  program" that the Defense contracts came through; facts[1] credits "Biaggi and other lobbyists"
  where the passage says only "its lobbyists and lawyers"; facts[3] lists the kinds of challenges
  raised on appeal. No cited passage states any of the three.
- **Gordon v. United States (277392, triage)**: one-character misquote only. rule[1] quotes
  "far outweighs"; the passage reads "far outweigh." Every claim is otherwise supported, so this
  is the cheapest human clear in the held set.
- **Lucky Brand Dungarees v. Marcel Fashions (4753847)**: majority_reasoning[3] names Marcel's
  authorities (judgment enforcement, collateral attack, Beloit v. Morgan); the cited passages say
  only "these authorities."
Biaggi and Gordon are second rejections, so under the two-strike rule they are now humans-only.
Same standard as the first run today. Worth a decision from Sage: whether an inflected quote
("outweigh" → "outweighs") should hold a candidate, since the runbook's verbatim rule has no
tolerance and a second strike is permanent.
Files touched: AI_COLLABORATION.md (this entry).
Deployment: none.

### Semantic review session 2026-09-27: 6 reviewed, 1 approved, 5 held — queue clear
Owner: Claude
Status: completed; review queue empty after six candidates (limit was 8)
Ran `SOURCE-BRIEF-REVIEW.md`. Approved: Bristol-Myers Squibb v. Superior Court (2294163, the
California breast-implant limitations case). Held, with the failing claims named in each saved note:
- **Parker v. Twentieth Century-Fox (1453074, triage)**: significance asserts "Sullivan's
  fact-intensive dissent"; the candidate has no dissent section and no cited passage mentions one.
- **Daimler AG v. Bauman (2649076, triage)**: issue[0]'s passages never state the question posed;
  facts[0] says "Daimler AG's predecessor" with no passage stating that relationship.
- **Obergefell v. Hodges (2812209, triage)**: majority_reasoning[3] and [2] rest on sentences
  that are not cited; facts[0] "consolidated" and facts[2] "a Michigan couple" are unsourced.
- **Derdiarian v. Felix Contracting (5684475)**: facts[3] calls Lawton "plaintiff's traffic-safety
  expert" but the passages say only "According to Lawton"; majority_reasoning[2] cites "such
  dereliction" without its antecedent.
- **Parvi v. City of Kingston (5632396)**: dissent[0] names "Chief Judge Breitel"; no cited
  passage names the dissent's author.
The three triage candidates are second rejections, so under the two-strike rule they are now
humans-only. Standard applied: a specific that no cited passage anywhere in the candidate
supports is a hold; a specific supported only by a passage cited under a different claim was
noted but did not by itself block (the one approval has such a note). Dominant failure is still
unsourced specifics: author names, party identities, and antecedents split into an uncited
neighboring passage.
Files touched: AI_COLLABORATION.md (this entry).
Deployment: none.

### Collection notes keep their line breaks; Con Law Week 6 collection repairs (2026-09-27)
Owner: Claude
Status: completed
Collection, legal-text, and bookmark notes rendered in plain `<p>` elements, so every newline
collapsed into a space and multi-part notes ran together. Added `whitespace-pre-line` to the five
note paragraphs in `frontend/app/shared/[id]/page.tsx` and `frontend/app/library/page.tsx`.
Collection 15 (Con Law): the assigned *Pennhurst* (1981, 451 U.S. 1, cluster `110458`) was imported
as a stub, hydrated through `fetch-opinion`, and swapped into the slot that held the 1984 Eleventh
Amendment decision (`111094`). The five Module 06(G) Tenth Amendment cases were appended (positions
78–82). Record and idempotent re-apply: `scripts/import_conlaw_week06_2026.py`. Notes for Week 6 cases
use single newlines between parts; the 66 older collection-15 notes still use blank lines.
Deployment: frontend via GitHub `main` auto-deploy.

### Louisiana v. Callais (2026) imported; Shelby County v. Holder repaired (2026-09-26)
Owner: Claude
Status: completed and verified in production
Sage's Con Law reading pairs these cases. `scripts/import_callais_2026.py` (idempotent, `--dry-run`)
imported the Apr. 29, 2026 merits decision as `10850261` (`146 S. Ct. 1131`, the cite from Sage's
Westlaw excerpt; no U.S. page yet), hydrated through `fetch-opinion`. The "Revisions: 5/04/26" cluster
`10852760` differs only in the syllabus argument dates, so it was not imported. The existing `10618593`
row, the June 27, 2025 reargument order that had held the `louisiana-v-callais` name slug, was
retitled "Louisiana v. Callais (order restoring case for reargument)".
Shelby (`931614`) carried only `133 S. Ct. 2612`, so "570 U.S. 529" found nothing. Its
`reporter_cite` now leads with the U.S. cite, and `133-sct-2612` still resolves. Its S3 slip-opinion
text had no sub-opinion markers, so every majority passage was generic `opinion` and generation failed
validation ("dissent[0] cites non-dissent passage"). The canonical CourtListener assembly is now stored
in `cases.content` with its hash (289 majority, 427 dissent passages). Briefs were generated as
summary `1301` (Callais) and `1302` (Shelby), costing $0.26 each.
Open: 334 Supreme Court rows still carry only an S. Ct. cite and fail U.S.-cite search. Other S3-only
slip opinions probably hit the same validation failure.
Also fixed: legacy `GET /cases/{id}/citator` returned 500 for every case (it selected the nonexistent
`citations.snippet` and `c2.*`, including full content). The frontend does not call it.

### Triage session 2026-09-20: 3 regenerations, all clean content_hash — no remap needed
Owner: Claude
Status: completed 2026-09-20 — 3/3 candidates saved (pending fresh review)
Ran `TRIAGE-BRIEFS.md`. All three original content_hash values matched the fresh packets.
- **Anderson v. Minneapolis, St. P. & S. St. M. Ry. (8024230)**: facts[3]'s "material or
  substantial factor" condition lacked its antecedent sentence — added op-d927bca6d5c3737a
  (the instruction sentence just before "If it was, the defendant is liable, otherwise it is
  not"). Text unchanged.
- **Milkovich v. Lorain Journal (112470)**: facts[2] said a "similar column" was held opinion
  "on a later remand"; the passage says the same Diadiun column, in Scott's separate appeal.
  Reworded to that; sources unchanged.
- **Lake River v. Carborundum (456374)**: the penalty conclusion is split across two passages —
  op-c4b76533c2dfb3b8 is only the "Mindful that..." lead-in and op-f236345ca965f5df carries
  "we conclude that the damage formula... is a penalty... designed always to assure Lake River
  more than its actual damages." Re-sourced holding[1] and majority_reasoning[2] to the latter.
  Added op-7ca8b7ffb594da94 (costs saved on breach) to majority_reasoning[1], op-677ebc184ac1b7c0
  ("Ferro Carbo," an abrasive powder) to facts[0], and op-c1178dba2c21cea0 ("the lien was no
  good") to holding[0]. Claim text untouched. Worth knowing: passage boundaries split mid-sentence
  at citation periods, so a conclusion's antecedent/lead-in is often its own passage.
Files touched: AI_COLLABORATION.md (this entry).
Deployment: none.
Commit: none (file already carries other sessions' uncommitted edits).

### Sunday source-brief batch 2026-09-13 (third session): 0/3 — sixth same-day confirmation, 30 straight refusals
Owner: Claude
Status: stopped early per runbook — no candidates saved; queue not exhausted
Ran `SUNDAY-SOURCE-BRIEFS.md`. Probed further than the two earlier sessions today before
stopping, to get a larger disjoint sample: McDougald v. Garber (5689474), Thing v. La Chusa
(1355526), MacKe Co. v. Pizza of Gaithersburg (2085649), Petterson v. Pattberg (3613600),
Schnell v. Nell (7128023), Batsakis v. Demotsis (5191007), Odorizzi v. Bloomfield School
District (2186877), People v. Staples (1675395), United States v. Jones (538), Gruen v.
Gruen (5688364), Jacque v. Steenberg Homes (1877286), Javins v. First National Realty
(8896568), Prah v. Maretti (1585688), Ploof v. Putnam (6705877), Moore v. Regents of
University of California (2608931), United States v. Strouse (27196), Nanakuli Paving &
Rock Co. v. Shell Oil (8924868), Stambovsky v. Ackley (6068674), Crabtree v. Elizabeth Arden
Sales Corp. (5637024), People v. Beeman (1247976), United States v. Jewell (334191),
Commonwealth v. Welansky (6571142), Helling v. Carey (1180369), Freund v. Washington Square
Press (2584616), Sun P.P. Assn. v. Remington P.P. Co. (3645684), American Standard, Inc. v.
Schectman (5985441), Transatlantic Financing Corp. v. United States (272453), Cotnam v.
Wisdom (6668608), Oppenheimer & Co. v. Oppenheim, Appel, Dixon & Co. (2003766), and Ortelere
v. Teachers' Retirement Board (5677295) — 30 of 30 refused at `candidate-opinion`, 29 with
"source has no verifiable opinion-part boundaries" and one (United States v. Strouse) with
the sibling error "source has separate opinions but no explicit majority boundary." Zero
overlap with the eight cases the two earlier sessions today logged against this runbook, and
zero overlap with the 63+ REBUILD-queue cases logged refusing since 2026-08-30. Per step 5
these don't count against the 3-candidate limit, so this reports 0/3. Did not touch
`opinion_boundary_preflight.py`/`opinion_passages.py` — the root cause was already diagnosed
2026-08-30 (see Open Questions) and a fix is out of scope for a content-generation session.
This is the sixth same-day confirmation (across both this runbook and `TRIAGE-BRIEFS.md`)
that the wall is unchanged; the wider sample here doesn't change the diagnosis, only
confirms it holds across a much larger slice of the queue than prior sessions checked in one
sitting. No new recommendation: someone still needs to pick up one of the two Open Questions
fixes (relax the single-writing preflight branch, or backfill marker-assembled content via
`fetch_courtlistener_document`) before either runbook will produce a candidate.
Files touched: AI_COLLABORATION.md (this entry).
Deployment: none.
Commit: this entry only.

### Triage session 2026-09-13 (fifth run, same day): 3 regenerations, all clean content_hash — no remap needed
Owner: Claude
Status: completed 2026-09-13 — 3/3 candidates saved
Ran `TRIAGE-BRIEFS.md` with a fresh 3-regeneration budget. All three cases' original
content_hash matched the fresh packet exactly (no ID remap needed):
- **Hamdi v. Rumsfeld (137001)**: holding[0]'s enemy-combatant category definition
  ("part of or supporting forces hostile... engaged in an armed conflict against it") was
  cited only to the passage stating the *conclusion* that such detention is authorized, not
  to anything defining the category — added op-5382ab3a76f5c322, the passage that states the
  definition verbatim. facts[2]'s "hearsay affidavit" characterization of the Mobbs
  Declaration wasn't in any cited passage (which only say it's the government's sole
  evidentiary support) — re-sourced by adding op-37d315c6883ceb73 (the District Court's own
  criticism of "the generic and hearsay nature of the affidavit") and reworded to attribute
  the characterization to the District Court rather than asserting it as flat fact. Two
  secondary antecedent gaps from the note: rule[0]'s "duration of the relevant conflict"
  phrase was cited only under holding[0] — added op-252067f25c979ed6, which states that exact
  phrase in the rule's own context. facts[1]'s "seized in 2001" had no cited passage giving a
  year — added op-239f6a64fba2bcb3 + op-544ffe1acb2a46a8 ("By 2001... resided in
  Afghanistan. At some point that year, he was seized..."). majority_reasoning[3]'s framing
  ("dire effect on warmaking the government forecast") wasn't among its four cited
  "because"-clause passages — added op-ae7c08cf0679d11c, the actual framing sentence.
- **Zivotofsky v. Kerry (2808294)**: majority_reasoning[2]'s closing sentence ("Congress
  nonetheless retains substantial authority... precede and follow an act of recognition")
  fell in the gap between two already-cited Syllabus fragments — added op-27ab13871ebb1d19,
  the missing middle sentence, found by ordinal-adjacency to the two existing citations.
  significance asserted a specific dissent lineup ("The Chief Justice and three other
  Justices dissented...") that no cited passage supports and that the note flagged as
  independently inaccurate (Thomas concurred in part/dissented in part, not a plain dissent);
  deleted the sentence rather than force a citation for editorial text that structurally
  can't carry passage IDs.
- **Burton v. Wilmington Parking Authority (106208)**: dissent[1] attributed a separate
  writing to "Justice Frankfurter" by name, but its one cited passage never names its
  speaker. The packet does have an authorship header for it (`op-e013af3de4002c30`,
  "Dissent by Frankfurter:"), but `candidate-save`'s validator hard-rejects it — that header
  is mislabeled `opinion_part: "concurrence"` (it trails the prior concurrence's last
  passage rather than being tagged with the dissent section it actually introduces), so
  citing it under `dissent` fails "cites non-dissent passage" regardless of what it says.
  Generalized instead: dropped the "Justice Frankfurter" name (the runbook's own example of
  an unsupported specific to drop) and kept the substance, which the remaining passage does
  support. Noting the mislabeled-header pattern here in case it recurs elsewhere — the fix
  applied is a content workaround, not a correction to the underlying passage tagging.

### Triage session 2026-09-13 (fourth run, same day): 3 regenerations, all clean content_hash — no remap needed, all via re-sourcing
Owner: Claude
Status: completed 2026-09-13 — 3/3 candidates saved
Ran `TRIAGE-BRIEFS.md` with a fresh 3-regeneration budget, after the three same-day sessions
below found the preflight wall blocking the entire triage queue. This run's `triage-list`
returned a fully open queue — none of the three cases hit `candidate-opinion` refusals, and
all three original content_hash values matched the fresh packet exactly, so every fix was
pure re-sourcing against the existing passage set (no ID remap needed):
- **Feinberg v. Pfeiffer Company (1577996)**: facts[1] cited the board resolution's date and
  "in recognition of her long service" motive to two passages that stated neither — re-sourced
  the date to op-7cb380db2286f482 ("On December 27, 1947, the annual meeting...") and the
  motive to op-add9c196f3235341 (the Chairman's remark that plaintiff "has given the
  corporation many years of long and faithful service"). facts[2] attributed the 1956 pension
  reduction to "a new company officer, on advice of an accounting firm" citing only a passage
  with an unidentified "He" — found Sidney Harris's 1953 succession to the presidency
  (op-58e6f52e393f51e1) and the new accounting firm's recommendation (op-cfa3b196955568b8)
  elsewhere in the packet and re-sourced to them. rule[1]'s "a promise resting only on past
  services is without consideration" clause was cited only to the defendant's argument
  passage, not the court's own adoption — no passage states the court adopting this in its own
  voice (both parties' briefs concede/urge it, the court doesn't independently rule on it), so
  deleted the clause rather than force a citation that doesn't exist.
- **Bristol-Myers Squibb Co. v. Superior Court (4403809)**: dissent[0] enumerated four specific
  availment grounds (400+ employees, research/policymaking facilities, distributor contract,
  ~$1 billion Plavix sales) citing only the general "purposefully availed itself" passages —
  found each specific stated verbatim a few passages later in Sotomayor's dissent
  (op-623fd45a9d8c21de, op-c73d355458ad37b6, op-fbaa65896a6e8c9a-2) and re-sourced to them.
  facts[0]'s "engages in business activities in California, including selling Plavix there"
  clause wasn't in either cited passage (DE incorporation/NY HQ and a list of things BMS did
  NOT do in CA) — found the majority opinion states this almost verbatim (op-219ca4828e09e636)
  and added it. majority_reasoning[3]'s description of the sliding-scale approach ("relaxes the
  required connection... as unrelated contacts grow more extensive") wasn't in the one cited
  passage, which only names and rejects the approach — found the actual mechanism described a
  few passages earlier (op-fdd4d8b7ff245a27) and added it.
- **City of Chicago v. Morales (118299)**: dissent[0] had two support gaps. The "no
  constitutional right to loiter" framing was near-opposite of its cited passage (which says
  citizens "were free to stand about... with no apparent purpose"); found Scalia's actual
  no-right statement later in the dissent responding to the plurality (op-e29e2336f3ca1ede,
  "not the slightest evidence for the existence of a genuine constitutional right to loiter")
  and added it. The accident-scene analogy cited only the sentence saying it was "similar to
  the second... example given above" without stating the example itself — added the uncited
  earlier paragraph describing the actual accident-scene dispersal analogy
  (op-351e40cfaface3f5, op-79fb6a379f3fe9df, op-66c9469560714baa), exactly as the rejection
  note suggested. Left significance's vote-lineup sentence untouched — the note flagged it as
  a secondary observation and confirmed it accurate, and significance is structurally unsourced
  editorial text (can't carry passage IDs), so there was nothing to fix.

Takeaway: the preflight wall the three sessions below hit was specific to the 16 cases already
logged with a recent `source_preflight` failure, not a systemic block on the triage queue —
once `triage-list`'s 6-day rotation cycled to a fresh set of cases, `candidate-opinion` worked
normally for all three.

### Triage session 2026-09-13: 0/3 — the preflight wall now also blocks the triage queue, not just REBUILD/Sunday
Owner: Claude
Status: stopped early per runbook — no candidates saved; queue not exhausted
Ran `TRIAGE-BRIEFS.md`. Every one of 16 rejected candidates probed this session refused at
`candidate-opinion` with the same diagnosed wall ("source has no verifiable opinion-part
boundaries" / "source has separate opinions but no explicit majority boundary"): Parker v.
Twentieth Century-Fox (1453074), Daimler AG v. Bauman (2649076), Obergefell v. Hodges
(2812209), United States v. Biaggi et al. (545489), Commonwealth v. Cosby (10315392), Morris
W. Gordon v. United States (277392), State v. Rothlisberger (2621346), United States v.
Elfgeeh (1386819), In Re Grand Jury Proceedings (732430), McCray v. State Farm (7830390),
Secretary of HEW v. Meza (273618), United States v. Jordan (cheng-ev-jordan-edny-2024),
People v. Rodriguez (cheng-ev-rodriguez-2022), Ricketts v. Scothorn (6769658), Alice
Childress v. Taylor et al. (569096), Osborn v. Bank of United States (85451). Per step 5 of
the runbook these don't count against the 3-regeneration limit since no candidate was
written, so this reports as 0/3 rather than a failed 3/3.

This is new information, not a repeat of the known wall: the Open Questions entry and every
prior "wall" session (eight on 2026-08-30, one on 2026-09-06) diagnosed and confirmed 100%
refusal specifically in the REBUILD/Sunday-source-brief queue (bulk-imported `cases.content`
with zero `COURTLISTENER_SUBOPINION` markers). The triage queue is a different population —
previously-generated candidates that already passed this same preflight once (that's how
they got a candidate to reject in the first place) — and the two most recent triage sessions
(2026-09-06, both runs) saved 3/3 cleanly. This session found the wall now spans the triage
queue too, at the same 100% rate, with zero overlap against the 63+ REBUILD-queue cases
already logged refusing. Did not investigate why triage went from passing to 100%-blocked in
the week since 09-06 — plausible causes (content re-fetched/reset for these specific cases,
the queue rotating into a harder cohort, or a shared-code change) weren't checked; flagging
rather than guessing, per the existing convention of not debugging preflight from a
content-generation session. The fix is still whichever of the two Open Questions options
someone picks up (backfill via `fetch_courtlistener_document`, or relax the single-writing
preflight branch) — this is the first evidence that leaving it unfixed now also stalls the
triage runbook, not just the Sunday one.
Files touched: AI_COLLABORATION.md (this entry).
Deployment: none.
Commit: this entry only.

### Triage session 2026-09-13 (second run, same day): 0/3 — confirms the wall is queue-wide, not those 16 cases
Owner: Claude
Status: stopped early per runbook — no candidates saved; queue not exhausted
Ran `TRIAGE-BRIEFS.md` again, apparently right after the first 2026-09-13 session above (same
day, same wall). Because `triage-list` excludes any case with a `source_preflight` failure
logged in the last 6 days, this run's `triage-list` calls returned a completely disjoint set
from that session's 16 — proof the wall isn't specific to those cases. Probed 10, all refused
at `candidate-opinion` with the same two errors: United States v. Peoni (1485475), Tunkl v.
Regents of University of California (1149237), The T.J. Hooper (1542549), Walden v. Fiore
(2654532), Piesco v. Koch (659320), Temple v. Synthes Corp. (112500), Iqbal v. Ashcroft
(30747), Machuca Gonzalez v. Chrysler Corp (28432), J. McIntyre Machinery v. Nicastro
(219733); Liberty Mutual Insurance v. Wetzel (109403) hit the sibling error ("source has
separate opinions but no explicit majority boundary"). Zero overlap with the prior session's
16. Per step 5 these don't count against the 3-regeneration limit, so this reports 0/3. Did
not probe further once the pattern was clear (two full disjoint batches at 100% in one day is
enough to confirm queue-wide scope; a third batch would only spend more preflight-failure
writes without changing the diagnosis). Not investigated: whether today's spike traces to a
specific change — the Open Questions entry's root cause (bulk-imported `cases.content` with
no `COURTLISTENER_SUBOPINION` markers) was diagnosed against the REBUILD queue, not the
triage queue, and the first 09-13 session flagged but didn't explain why triage specifically
went from passing (2026-09-06) to blocked. This session adds no new diagnosis, only breadth of
confirmation. The fix remains one of the two Open Questions options (backfill via
`fetch_courtlistener_document`, or relax the single-writing preflight branch) — recommend
whoever picks this up treats it as blocking both runbooks now, given two independent
same-day sessions both hit 100% on disjoint case sets.
Files touched: AI_COLLABORATION.md (this entry).
Deployment: none.
Commit: this entry only.

### Triage session 2026-09-13 (third run, same day): 0/3 — third independent confirmation, wall persists
Owner: Claude
Status: stopped early per runbook — no candidates saved; queue not exhausted
Ran `TRIAGE-BRIEFS.md` a third time today. `triage-list`'s 6-day rotation again returned a
disjoint set from both earlier 09-13 sessions' 26 cases: Rasoulzadeh v. Associated Press
(1866935), United States v. Contento-Pachon (428603), The Queen v. Dudley and Stephens
(manual-dudley-stephens), Richardson v. Chapman (2195023), Wagner v. International Railway
Co. (3607799), Carter v. Hinkle (6925878), People v. Chun (2506956) — all 7 probed refused at
`candidate-opinion` with the same two errors ("no verifiable opinion-part boundaries" /
"separate opinions but no explicit majority boundary"). Zero overlap with the 26 cases from
the first two sessions, so 33 distinct cases have now hit this wall today alone. Per step 5
these don't count against the 3-regeneration limit, so this reports 0/3.
Stopped after 7 rather than continuing to probe: the second 09-13 session already established
that further batches "only spend more preflight-failure writes without changing the
diagnosis," and this run adds only breadth, not new diagnosis. Did not touch
`opinion_boundary_preflight.py`/`opinion_passages.py`, per the same session's convention of
not debugging preflight from a content-generation session. Escalating: this is now three
same-day sessions unable to make progress on the triage queue at all. Recommend someone pick
up one of the two Open Questions fixes (backfill via `fetch_courtlistener_document`, or relax
the single-writing preflight branch) before running this runbook again — repeating it without
a fix will keep producing 0/3 sessions and burning through the queue's 6-day rotation window
for no gain.
Files touched: AI_COLLABORATION.md (this entry).
Deployment: none.
Commit: this entry only.

### Sunday source-brief batch 2026-09-13 (second session): 0/3 — fifth same-day confirmation
Owner: Claude
Status: stopped early per runbook — no candidates saved; queue not exhausted
Ran `SUNDAY-SOURCE-BRIEFS.md`. `candidate-list` returned Hawkins v. McGee (3574015), then
(after that one refused) Austin Instrument, Inc. v. Loral Corp. (5678730), Leonard v.
Pepsico, Inc. (2579076), and Mitchill v. Lath (3617659). All four refused at
`candidate-opinion` with "source has no verifiable opinion-part boundaries" — zero overlap
with the four cases the earlier session today logged against this same runbook (Angel v.
Murray, People v. Rizzo, Lefkowitz v. Great Minneapolis Surplus Store, Sherwood v. Walker),
and zero overlap with the 63+ REBUILD-queue cases logged refusing since 2026-08-30. Per
step 5 these don't count against the 3-regeneration limit, so this reports 0/3. Stopped
after 4 for the same reason as the earlier session today: the queue has already been
exhaustively sampled (0 of 506 REBUILD rows contain a `COURTLISTENER_SUBOPINION` marker,
per the 2026-09-06 direct-SQL check), so more probes add breadth, not new diagnosis. Did
not touch `opinion_boundary_preflight.py`/`opinion_passages.py`, per the standing
convention that the fix is out of scope for a content-generation session. This is the
fifth same-day confirmation (across both this runbook and `TRIAGE-BRIEFS.md`) that the wall
is unchanged. No new recommendation beyond what's already recorded: someone needs to pick
up one of the two Open Questions fixes before either runbook will produce a candidate.
Files touched: AI_COLLABORATION.md (this entry).
Deployment: none.
Commit: this entry only.

### Sunday source-brief batch 2026-09-13: 0/3 — REBUILD queue still 100% blocked, fourth same-day confirmation
Owner: Claude
Status: stopped early per runbook — no candidates saved; queue not exhausted
Ran `SUNDAY-SOURCE-BRIEFS.md`. `candidate-list` returned Angel v. Murray (2303115), then
(after that one refused) People v. Rizzo (1349311), Lefkowitz v. Great Minneapolis Surplus
Store (1289586), and Sherwood v. Walker (3532643). All four refused at `candidate-opinion`
with "source has no verifiable opinion-part boundaries" — zero overlap with the 63+
REBUILD-queue cases already logged refusing since 2026-08-30, and zero overlap with the 33
triage-queue cases the three earlier sessions today logged against `TRIAGE-BRIEFS.md`. Per
step 5 these don't count against the 3-regeneration limit, so this reports 0/3. Stopped
after 4 rather than spending the full probe budget: the 2026-09-06 session already queried
the REBUILD queue exhaustively via direct SQL and found 0 of 506 rows contain a
`COURTLISTENER_SUBOPINION` marker, so further sampling here could only add breadth, not
new diagnosis — and today's three triage sessions already established that a same-day
confirmation run doesn't need more than a handful of probes. Did not touch
`opinion_boundary_preflight.py`/`opinion_passages.py`, per the standing convention that the
fix (backfill via `fetch_courtlistener_document`, or relax the single-writing preflight
branch — see Open Questions) is out of scope for a content-generation session. Both
runbooks (`SUNDAY-SOURCE-BRIEFS.md` and `TRIAGE-BRIEFS.md`) are now confirmed still 100%
blocked as of today, a full week after the 2026-09-06 diagnosis with no fix landed
(`git log` since 09-06 on `opinion_passages.py`/`opinion_boundary_preflight.py`/
`sunday_briefs.py`/`fetch_full_opinions.py` shows nothing). Restating the same
recommendation as every session since 2026-08-30: someone needs to pick up one of the two
Open Questions fixes before either runbook will produce a candidate again.
Files touched: AI_COLLABORATION.md (this entry).
Deployment: none.
Commit: this entry only.

### Con Law shared collection Qdrant mirror (2026-09-05)
Owner: Codex
Status: completed and verified; future weekly metadata requires rerunning the sync
Created Qdrant collection `tortwell_con_law_15`, incrementally mirrored from public
Tortwell shared collection 15. The first sync indexed 23 cases; schedule reconciliation
found that principal Week 03(A) case *Simon v. Eastern Kentucky Welfare Rights
Organization* was missing, so case `109462` was appended to collection 15 and the corpus
now contains 24 cases / 1,081 paragraph-aware chunks. Every payload has case ID, week,
module, course role, topics, constitutional provisions, source, and local source links.
Five legacy S3 opinions with an exact 50k truncation signature are refreshed from
CourtListener v4 before embedding. An unchanged rerun writes zero points; semantic checks
rank *Linda R.S.* first for the child-support/prosecution hypothetical and *Simon* first
for the IRS/hospital hypothetical. Source schedules remain local to the law-school repo;
no copyrighted Chemerinsky text was uploaded.
Files: `/mnt/d/dev/law-school/fall-2026/con-law/materials/tortwell-qdrant/`, local opinion
exports under `materials/cases/tortwell/` (gitignored), and a link in the Con Law README.
Deployment: Qdrant collection live and green; database collection membership updated.
Commit: law-school repo `2fe653d` (pushed to `main`).

### Duncan Aviation v. Flexjet transfer ruling imported (2026-09-05)
Owner: Codex
Status: completed and verified in production; full-order source remains unavailable
Added `Duncan Aviation, Inc. v. Flexjet, LLC`, No. 4:24-cv-03004 (D. Neb.
June 24, 2025), as `recap-68140278-93`. It resolves at
`/cases/duncan-aviation-inc-v-flexjet-llc` and live search finds “Flexjet.” The stored
record has the docket-number column populated and is marked nonprecedential. The stored
text is deliberately limited to Filing 93's verified public docket entry: CourtListener
has docket 68140278, entry 429388267, and RECAP document 443642473, but marks the PDF
unavailable; the transferred SDNY docket's copy is also unavailable, and Justia exposes
only the docket disposition. Metadata records `source_text_status=verified_docket_entry_only`
and the page tells readers that it is not the full memorandum. Do not synthesize the
missing § 1404(a) reasoning. Replace this text if a verified Filing 93 PDF is later supplied.
Also created the missing federal `ned` court row (`D. Neb.`); the initial name fallback
incorrectly found the Nebraska Supreme Court, and the case was corrected before verification.
After the 1,155-character docket text correctly failed the 2,500-character generation
preflight, submitted free CourtListener RECAP prayer 53250 for the missing document and
recorded it in production metadata. `backend/main.py` now returns a precise 409 for any
verified docket-only source; `CaseDetailClient.tsx` hides the impossible Generate action,
shows the pending-document state, and links to the actual docket entry. Backend tests (54)
and frontend typecheck/build pass.
Deployment: backend `b5fc0c9b-bb12-4b4c-95e5-3c4368bef1a7`; frontend
`345a2099-d236-4802-8913-f9b4e6d1af29` (both successful). Live page returns 200,
shows the pending-document banner, and omits the Generate Summary action.
Commit: `2643b30`; existing unrelated working-tree changes preserved.

### Constitutional-law standing cases imported (2026-09-05)
Owner: Codex
Status: completed and verified in production; Diamond generation repaired
Imported and hydrated three Supreme Court cases from CourtListener's canonical opinion
records: Linda R. S. v. Richard D. (`8991786`, `410 U.S. 614`), Simon v. Eastern Kentucky
Welfare Rights Organization (`109462`, `426 U.S. 26`), and Diamond Alternative Energy, LLC
v. Environmental Protection Agency (`10776830`, `606 U.S. 100`). All three resolve through
their citation slugs, return HTTP 200 on Tortwell, and contain hashed opinion text with
canonical sub-opinion markers. The user-supplied Diamond DOCX is an edited class excerpt;
it was used to confirm the case but was not stored as the authoritative opinion. Diamond's
combined U.S. Reports source joined a counsel footnote directly to its majority heading
(`Washington.* Justice Kavanaugh ...`), so sentence splitting missed the majority boundary
while detecting the dissents and strict preflight refused generation. Bare star footnote
symbols after sentence punctuation are now removed before splitting; the exact Diamond shape
has a regression test. Production preflight passes with 290 majority and 267 dissent passages,
and a source-linked Opus brief was generated and saved as summary `1228`.
Deployment: backend `7c9ba9b4-4304-4d75-9dc0-27d8eb803154` successful.
Commit: `c237040`, pushed to main. Existing unrelated working-tree changes preserved.

### Warth token preflight failure (2026-09-05)
Owner: Codex
Status: fixed and verified in production
The unbounded Anthropic dependency installed SDK 1.2.0, whose httpcore2 transport calls
`anyio.Lock(fast_acquire=True)` against FastAPI 0.104.1's AnyIO 3.7.1. The resulting
TypeError is wrapped as APIConnectionError and surfaced as "AI token preflight is unavailable".
Pinned `backend/requirements.txt` to the locally tested SDK 0.116.0 instead of upgrading
the framework during the incident. A real token-count call from production with the pinned
SDK succeeded; 36 billing/stream-finalization tests passed. After deployment, Warth v.
Seldin (`109301`, `/cases/422-us-490`) generated successfully (HTTP 200) and was saved.
Deployment: backend `92574a62-0ac0-4814-870d-cb4d07f27326` successful.
Commit: `bf49fc9`, pushed to main. Existing unrelated working-tree changes preserved;
this handoff note remains with the already-uncommitted collaboration file.

### Triage session 2026-09-06 (second run): 3 regenerations, all clean content_hash — no remap needed
Owner: Claude
Status: completed 2026-09-06 — 3/3 candidates saved
Ran `TRIAGE-BRIEFS.md` again same day with a fresh 3-regeneration budget. Unlike the first
2026-09-06 session below, all three candidates' original content_hash matched the fresh
packet's hash exactly, so no passage-ID remap was needed — every fix was pure re-sourcing
or targeted rewrite against the existing passage set:
- **Gertz v. Robert Welch, Inc. (109091)**: rule[0] and majority_reasoning[1] made mirror-image
  claims (private-plaintiff voluntary-assumption-of-risk vs. public-figure access-to-rebuttal)
  but each cited only the other's supporting passages; fixed by sharing citations between the
  two claims (op-27e652/op-2f4500 added to rule[0], op-02e975 added to mr[1]) rather than
  rewriting either claim's text. rule[0]'s "short of strict liability" phrase was uncited in
  its own claim despite being supported by holding[0]'s passage (op-1b16efa9) — added that
  passage as a shared source. facts[0] named Nuccio as "a Chicago police officer" and the
  magazine as "American Opinion," both true but sourced only elsewhere in the brief (facts[1]
  and outside it) — found the packet actually contains passages saying both directly
  (op-002a8b71 "a Chicago policeman named Nuccio," op-b6ac73cc "Respondent publishes American
  Opinion") and re-sourced to them instead of deleting the specifics. majority_reasoning[2]
  quoted "public or general interest" when the passage reads "general or public interest" —
  fixed the word order. majority_reasoning[3] attributed the punish-unpopular-opinion risk to
  "presumed and punitive" damages when the cited passage supports presumed damages only —
  dropped "and punitive."
- **O'Connor v. Sullivan (564438)**: both holding claims (reversed / remanded) cited only the
  underlying rule/reasoning passages, none of which state a disposition — the opinion's actual
  disposition line ("REVERSED, AND REMANDED WITH DIRECTIONS," op-278d39a2) existed in the
  packet but had never been cited anywhere in the brief; added it to both holdings. holding[0]'s
  "diffusing-capacity test result alone satisfied that standard" was re-sourced by reusing
  op-3520254c/op-9c973a91, already cited under facts[1] and majority_reasoning[0].
- **Wal-Mart v. Dukes (219618)**: significance asserted "Justice Ginsburg's partial dissent
  argued the majority blurred commonality with predominance" — the packet contains no dissent
  passages at all (confirmed by grep), so unlike the other two fixes this couldn't be re-sourced;
  deleted the sentence per the runbook's delete option, since significance also cannot carry
  passage IDs even if a dissent passage had existed.

### Triage session 2026-09-06 (first run): 3 regenerations, all via passage-ID remap plus substantive re-sourcing
Owner: Claude
Status: completed 2026-09-06 — 3/3 candidates saved
Ran `TRIAGE-BRIEFS.md` with a fresh 3-regeneration budget. All three rejected candidates
predated their opinion's most recent passage rebuild, so every save needed a full ID sweep
(checking every cited ID against the fresh content_hash's passage set, pulling old passages
under the candidate's original content_hash, matching text against the new packet, verifying
by reading full text) in addition to fixing the reviewer's flagged claims:
- **City of Philadelphia v. New Jersey (109916)**: facts[2] attributed the NJ Supreme Court's
  reversal reasoning to two passages that turned out to be bare reporter-citation fragments
  ("Id., at 471-478...") — found the actual substantive holding a few passages away ("advanced
  vital health and environmental objectives with no economic discrimination against, and with
  little burden upon, interstate commerce") and re-sourced to it. facts[3] misattributed the
  pre-remand "no congressional intent to pre-empt" finding to the Resource Conservation and
  Recovery Act of 1976; the passages show that finding actually rested on the 1965 Solid Waste
  Disposal Act as amended by the 1970 Resource Recovery Act, while the 1976 RCRA was the basis
  for this Court's remand, not the state court's earlier reasoning — rewrote to keep the two
  statutes and their roles distinct rather than deleting the claim, since the packet fully
  supports the corrected (more precise) version. facts[0]'s undated "1973" claim was re-sourced
  to a passage stating the law "took effect in early 1974" as chapter 363 of the 1973 N.J. Laws.
  5 of 33 cited IDs were stale and remapped, none flagged by the reviewer.
- **Craig v. Boren (109570)**: majority_reasoning[0] said "the state accepted for purposes of
  discussion that traffic safety was the objective" — the cited passage actually reads "We
  accept... the District Court's identification of the objective," i.e., the Court accepted the
  District Court's framing, not a concession by the state; rewrote to attribute the acceptance
  correctly. majority_reasoning[3]'s Twenty-first-Amendment-history claim looked unsourced from
  its two cited bare-holding sentences, but a nearby passage the original draft never cited
  states nearly verbatim that "this Court's decisions since have confirmed that the Amendment
  primarily created an exception to the normal operation of the Commerce Clause" — re-sourced
  to it rather than deleting, since the claim was true and citable, just uncited. 7 of 28 cited
  IDs were stale and remapped, none flagged by the reviewer.
- **Baker v. Carr (106366)**: majority_reasoning[2] gave a textual-commitment-to-Congress
  rationale for Guaranty Clause nonjusticiability; the cited passage actually gives a
  standards-based rationale (the Clause "is not a repository of judicially manageable
  standards" for identifying a state's lawful government) — rewrote to match. dissent[0]
  dropped "industry location" and "preference for stability" from its cited passage's "geography
  and demography" list; both phrases turned out to be stated verbatim a few passages later in
  the same dissent (previously uncited) — re-sourced rather than trimmed. facts[2]'s named
  defendants ("Secretary of State, Attorney General, and other election officials") were cited
  only to a passage saying "the appellees," but the opinion separately and precisely names the
  defendants elsewhere — re-sourced to that passage. facts[0]'s "county voter population"
  formula was similarly uncited by its original passage (which only quoted the census-enumeration
  clause) but stated exactly two passages later ("Tennessee's standard for allocating legislative
  representation among her counties is the total number of qualified voters resident in the
  respective counties") — re-sourced. 5 of 35 cited IDs were stale and remapped, including two
  (Guaranty Clause rationale, defendant naming) that overlapped with the reviewer's flagged
  claims and three that didn't.

### Triage session 2026-08-30: 3 regenerations, all via passage-ID remap plus substantive re-sourcing
Owner: Claude
Status: completed 2026-08-30 — 3/3 candidates saved
Ran `TRIAGE-BRIEFS.md` with a fresh 3-regeneration budget. All three rejected candidates
predated the v9→v10 passage rebuild, so every case needed the full remap (pulling old
passages under the candidate's original content_hash, `difflib`-matching against the fresh
packet, verifying by reading full text) in addition to fixing the reviewer's flagged claims:
- **Martin v. Wilks (112275)**: majority_reasoning[3] cited two passages that are Stevens's
  dissent mislabeled `opinion_part: "opinion"` in the v10 combined/duplicate record (verified
  by finding the same sentence correctly labeled `dissent` elsewhere in the packet under a
  `-2` suffix ID) — the claim inverted the dissent's "no basis to reopen the judgment" into
  "no basis to bind the firefighters," so it was deleted rather than re-sourced, since citing
  the mislabeled-but-still-dissent passage would repeat the exact defect. facts[0] named
  "Black firefighters" as plaintiffs and stated the suit was "settled," neither actually
  stated by its cited passages; re-sourced to passages that name the true plaintiffs (NAACP's
  Ensley Branch + individuals) and the consent-decree settlement, and generalized "firefighters"
  since the original 1974 complaint covered "various public service jobs," not fire department
  specifically. rule[1]'s burden-of-joinder half was re-sourced to the passage the reviewer
  named (previously cited under holding[1] only). facts[1]'s "once promotions were made under
  the decrees" clause — unsupported by any of its three cited passages — was replaced with
  language the record actually states (the City/Board's own defense that the decisions were
  made pursuant to the decrees). 5 of 28 cited IDs were stale and remapped, including
  majority_reasoning[1]'s Provident Bank citation (unflagged by the reviewer, caught by a full
  ID sweep against the fresh content_hash — the runbook's warning that stale IDs aren't
  confined to the flagged claim held here too).
- **Teeters v. Currey (1715073)**: majority_reasoning[1] mischaracterized a 1969 Tennessee
  products-liability amendment as establishing "a discovery-based accrual date," but the
  quoted statutory text is date-of-injury accrual with a floor against barring claims before
  injury — rewrote to match the passage's actual text (guarantees one year from injury, not
  from the negligent act/sale) without touching the surrounding argument, which the reviewer
  didn't flag. significance asserted a concurrence's specific holding, but concurrence
  passages are structurally uncitable by any section in this schema (`UNCITABLE_PARTS` in
  `structured_briefs.py`) — no fix could source it, so the sentence was deleted rather than
  reworked. Also fixed the reviewer's "minor, not independently disqualifying" note on
  facts[3] (summary-judgment ground): re-sourced from the affidavit alone to passages
  explicitly stating the motion's brief was "devoted to... the running of the statute of
  limitations" and that the court read the ruling as "in effect, sustaining a plea of the
  statute of limitations" — both available in the packet but previously uncited. 3 of the
  ~50 cited IDs were stale (OCR/pagination-marker differences only; text unchanged) and
  remapped.
- **Western Union Telegraph Co. v. Hill (3225207)**: facts[0] was self-contradictory ("Mrs.
  Hill, plaintiff's wife, sued..." — she cannot be both plaintiff and plaintiff's wife); the
  opinion never names the plaintiff's first name/title, only "plaintiff" and, separately,
  "Mrs. Hill" as the wife who was assaulted, so rewrote to "Hill, the plaintiff... assault on
  his wife, Mrs. Hill" using only what the passages support. majority_reasoning[1] claimed
  the court "noted" a corporate-liability proposition was "already established in its earlier
  decision in Gassenheimer v. Western Ry.," but Gassenheimer is a bare supporting citation
  appended to the rule sentence (confirmed: the v10 reformat folded the citation fragment
  into the same passage as the rule statement itself) — not a separate holding, and not "its"
  (this court's) earlier decision. Deleted rather than re-sourced, since no passage supports
  the claim as framed. Also fixed the reviewer's "minor" note on majority_reasoning[0] by
  adding the actual reach-across-the-counter evidence passages (previously cited only under
  facts[3]) alongside the bare jury-question sentence it was citing. 3 of 27 cited IDs were
  stale; one (the Gassenheimer citation itself) turned out to be moot since its passage was
  being deleted anyway.
Files touched: none (three `candidate-save` writes to the DB only; no code changes).
Deployment: none.
Commit: N/A — documentation-only addition here (plus whatever unrelated changes were
already staged/modified in the working tree when this session started).

### Sunday source-brief batch 2026-08-30: 0/3 — 11 straight preflight refusals, queue may be exhausted of parseable sources
Owner: Claude
Status: stopped early per runbook — no candidates saved
Ran `SUNDAY-SOURCE-BRIEFS.md`. Every one of the 11 rebuild-queue cases probed this session
refused at `candidate-opinion` with "source has no verifiable opinion-part boundaries":
Corey v. Havener (6554250), Bristol-Myers Squibb v. Superior Court (2294163), McQuirter v.
State (1801433), Regina v. Cunningham (manual-cunningham), MacMunn v. Eli Lilly (2580870),
Parvi v. City of Kingston (5632396), Lucky Brand Dungarees v. Marcel Fashions (4753847),
Benn v. Thomas (1244600), Dobbs v. Jackson Women's Health (6481357), United States v.
Newbold (1141), NCNB Texas National Bank v. Johnson (6143). None count against the
3-candidate limit per the runbook, and the queue-rotation fix (`aeb89c4`) advanced past each
one automatically — but a 100% refusal rate is a step change from prior sessions (2026-08-16:
2/5 refused; 2026-08-23: 6/9 refused). No code changed between those sessions and this one
(last preflight-relevant commit is still `aeb89c4`, 2026-08-23), so this doesn't look like a
fresh regression — more likely the front of the REBUILD queue has rotated into a run of
sources this preflight format can't parse. Did not investigate `opinion_passages.py` further;
out of scope for a brief-writing session. Worth a look before next Sunday: either sample
further into the queue to see if the refusal rate recovers, or check whether a source-format
variant (pre-v10 ingestion? a specific court/reporter?) clusters in the cases listed above.
Files touched: none.
Deployment: none.
Commit: this entry only.

### Sunday source-brief batch 2026-08-30 (second session): 0/3 — confirms the wall, fully disjoint case set
Owner: Claude
Status: stopped early per runbook — no candidates saved
A second session ran `SUNDAY-SOURCE-BRIEFS.md` later the same day, unaware of the entry
above (found it only afterward, while updating this file — a session-collision case, not a
retry). All 7 rebuild-queue cases probed here also refused at `candidate-opinion` with the
identical "source has no verifiable opinion-part boundaries" error, and — notably — none of
these 7 overlap the 11 listed above: Hoffman v. Red Owl Stores (2161398), Angel v. Murray
(2303115), People v. Rizzo (1349311), Lefkowitz v. Great Minneapolis Surplus Store
(1289586), Sherwood v. Walker (3532643), Hawkins v. McGee (3574015), Austin Instrument v.
Loral Corp. (5678730). That's 18 distinct cases refused today across two independent
sessions with zero overlap, which weighs against "front of queue rotated into a bad patch"
and toward the queue being broadly saturated with this source shape right now — worth
prioritizing the "sample further / check for a clustering variant" follow-up above sooner
rather than at next Sunday's session.
Files touched: none.
Deployment: none.
Commit: this entry only.

### Sunday source-brief batch 2026-08-30 (third session): 0/3 — third straight 100% wall, still fully disjoint
Owner: Claude
Status: stopped early per runbook — no candidates saved
A third `SUNDAY-SOURCE-BRIEFS.md` session the same day, also unaware of the two entries
above until writing this one. `candidate-list 1` returned Leonard v. Pepsico (2579076),
which refused at `candidate-opinion` with "source has no verifiable opinion-part
boundaries"; `candidate-list 5` then returned five more (queue had rotated Leonard out of
the head already), and all five also refused: Mitchill v. Lath (3617659), Britton v. Turner
(8531446), Lenawee County Board of Health v. Messerly (1614330) — all three "no verifiable
opinion-part boundaries" — and Connecticut v. Doehr (112615), Buckley v. Valeo (109380),
both "source has separate opinions but no explicit majority boundary". 6 for 6 refused,
zero overlap with the 18 cases logged refusing in the two sessions above (29 distinct
REBUILD-queue cases now refused today across three source-brief sessions, plus the 22 and
9-of-12 refused in same-day triage sessions elsewhere in this file) — same-day evidence now
spans both queues and four independent sessions with no overlapping case ever passing
preflight. Did not touch `opinion_boundary_preflight.py`/`opinion_passages.py`/
`structured_briefs.py`; per the prior entries this is out of scope for a brief-writing
session and the more useful next step is what those entries already recommend — sample
deeper into the REBUILD queue or check for a source-format variant clustering at its
current head — rather than a fifth session re-confirming the same wall.
Files touched: none.
Deployment: none.
Commit: this entry only.

### Sunday source-brief batch 2026-08-30 (fourth session): 0/3 — fourth straight 100% wall, still no overlap
Owner: Claude
Status: stopped early per runbook — no candidates saved
A fourth `SUNDAY-SOURCE-BRIEFS.md` session the same day, found the three entries above only
while writing this one. `candidate-list 1` returned United States v. Nixon (19845, the 2000
CourtListener duplicate row, not the 1974 SCOTUS opinion), which refused at
`candidate-opinion` with "source has no verifiable opinion-part boundaries." The
queue-rotation fix advanced the queue automatically; the next two probes were Rucho v.
Common Cause (4633469, same "no verifiable opinion-part boundaries" error) and Miller v.
California (108838, "source has separate opinions but no explicit majority boundary"). All
three refused, zero overlap with the 32 REBUILD-queue cases already logged refusing in the
three sessions above — 35 distinct cases now refused today across four independent
source-brief sessions, with no case anywhere in that set passing preflight. Per the runbook's
instruction to stop early when something errors repeatedly, and per the prior sessions'
observation that a fifth same-day confirming pass adds nothing, stopped after 3 probes
without writing any candidate JSON. This now reads less like "front of queue rotated into a
bad patch" (35 disjoint cases across landmark, casebook-priority, and outline-linked rows all
failing) and more like something actually broke queue-wide; recommend the next session that
isn't running this runbook actually opens `opinion_boundary_preflight.py` /
`opinion_passages.py` and checks git blame / recent data changes around the refusal
predicates, rather than sampling further — four sessions of sampling already agree.
Files touched: none.
Deployment: none.
Commit: this entry only.

### Sunday source-brief batch 2026-08-30 (fifth session): 0/3 — fifth straight 100% wall, still no overlap
Owner: Claude
Status: stopped early per runbook — no candidates saved
A fifth `SUNDAY-SOURCE-BRIEFS.md` session the same day, found the four entries above only
while writing this one. All 3 probes refused at `candidate-opinion`, zero overlap with the 35
cases already logged today: Larry K. Howard v. Federal Crop Insurance Corp. (338519, "no
verifiable opinion-part boundaries"), United States ex rel. Coastal Steel Erectors v. Algernon
Blair (311461, same error), Klocek v. Gateway (2503865, same error). 38 distinct REBUILD-queue
cases now refused today across five independent sessions, still zero passes. Checked git log on
`backend/opinion_passages.py` — the most recent commit touching it is `f4851c2` (2026-08-12,
passage format v9→v10, folding contentless/citation-only passages), which predates every prior
Sunday session that saw a normal refusal rate (2026-08-16, 2026-08-23), so it isn't a same-day
regression either; nothing has touched preflight-relevant code today. Per the fourth session's
recommendation, did not re-sample further — that would just be a sixth confirming pass. The
open question is still unresolved: something about the current REBUILD queue itself (not a code
change) is producing near-100% preflight refusals where the same code previously passed cases
at a normal rate. Next non-runbook session should look at what's actually happening inside
`opinion_boundary_preflight.py`'s refusal predicate against a few of the 38 logged case IDs
directly, rather than running this runbook a sixth time.
Files touched: AI_COLLABORATION.md (this entry).
Deployment: none.
Commit: this entry only.

### Sunday source-brief batch 2026-08-30 (sixth session): 0/3 — sixth straight wall, still no overlap; stopped after 3 probes without a fourth
Owner: Claude
Status: stopped early per runbook — no candidates saved
A sixth `SUNDAY-SOURCE-BRIEFS.md` session the same day, found the five entries above only
while writing this one. `candidate-list 1` returned Walker v. Harrison (2409469), which
refused at `candidate-opinion` with "source has no verifiable opinion-part boundaries"; the
queue-rotation fix advanced past it automatically, and `candidate-list 5` then returned five
more with Walker already rotated out. Probed the next two — Groves v. John Wunder Co.
(3536897) and James Baird Co. v. Gimbel Bros. (1510721) — both refused with the identical
error. 41 distinct REBUILD-queue cases now refused today across six independent sessions,
still zero passes anywhere. Per the fourth and fifth sessions' explicit recommendation not to
keep sampling, stopped after 3 probes rather than confirming further with the remaining
candidates already returned (Neri v. Retail Marine, Van Wagner Advertising, Ardente v.
Horan — untried, listed here in case the next session wants to skip straight past them too).
Did not open `opinion_boundary_preflight.py` / `opinion_passages.py`; six same-day sessions
now agree this needs a code-level look, not another runbook pass. Recommend the next session
be explicitly told to investigate the refusal predicate directly rather than run this runbook
again until that happens.
Files touched: AI_COLLABORATION.md (this entry).
Deployment: none.
Commit: this entry only.

### Sunday source-brief batch 2026-08-30 (seventh session): 0/3 — root cause of the wall found, not fixed
Owner: Claude
Status: stopped early per runbook — no candidates saved; root cause documented in Open Questions
A seventh `SUNDAY-SOURCE-BRIEFS.md` session, found the six entries above only after already
probing. `candidate-list 1` refused four times running — People v. Staples (1675395), United
States v. Jones (538, the D.C. Cir. GPS-tracking opinion, not the 2012 SCOTUS cert grant),
Gruen v. Gruen (5688364), Jacque v. Steenberg Homes (1877286) — each with "source has no
verifiable opinion-part boundaries," each auto-rotated out of the queue by the existing 6-day
backoff. Rather than run a third round of identical probes (six prior same-day sessions already
established the 100% wall and asked for code investigation), wrote a standalone diagnostic
script (`/tmp/diag_boundary2.py`, not committed — reads case text via `sunday_briefs.read_full_opinion`
and calls `assess_opinion_boundaries` directly) against all four refused cases and found the
actual mechanism — full writeup moved into the Open Questions entry above rather than duplicated
here. Short version: the REBUILD queue's `content` was bulk-imported by
`scripts/fetch_full_opinions.py` with no opinion-part markers, ever; the only code path that
writes markers (`fetch_courtlistener_document`) is wired to an idempotent stub-only endpoint
that never touches cases with existing content. This was never a regression or a sign the queue
is unusually degraded — every case ingested this way was always going to refuse strict preflight,
so the 67%→100% climb over the past week is just the pre-marked stub cases (which pass) being
used up first. Recommend the next session skip the runbook entirely and either (a) relax the
single-writing preflight branch, or (b) write a backfill script over the ~890-case queue calling
`fetch_courtlistener_document` and overwriting `content` before preflight runs — see the Open
Questions entry for the tradeoffs. Did not attempt either fix: both are backend changes needing
their own review, out of scope for a content-generation session.
Files touched: AI_COLLABORATION.md (this entry + Open Questions). Diagnostic script left at
/tmp/diag_boundary2.py (not in repo).
Deployment: none.
Commit: this entry only.

### Sunday source-brief batch 2026-08-30 (eighth session): 0/3 — same wall, root cause already known, stopped after 6 probes
Owner: Claude
Status: stopped early per runbook and per the seventh session's explicit recommendation — no candidates saved
An eighth `SUNDAY-SOURCE-BRIEFS.md` session the same day. `candidate-list 1` returned Javins
v. First National Realty Corp. (8896568), which refused at `candidate-opinion` with "source
has no verifiable opinion-part boundaries"; `candidate-list 5` then returned five more (Javins
already rotated out by the existing backoff) — Prah v. Maretti (1585688), Ploof v. Putnam
(6705877), Moore v. Regents of University of California (2608931), United States v. Strouse
(27196, "source has separate opinions but no explicit majority boundary"), Nanakuli Paving &
Rock Co. v. Shell Oil Co. (8924868) — all six refused, zero overlap with the 45 cases already
logged refusing today. Did not sample further: the seventh session already found and
documented the root cause (see Open Questions — bulk-imported REBUILD `content` was never
marker-assembled, so strict preflight was always going to refuse it) and recommended the next
session skip this runbook entirely rather than re-confirm. A ninth same-day pass would add
nothing; the actual next step is the backend fix (relax the single-writing preflight branch,
or backfill markers via `fetch_courtlistener_document` over the queue), which is out of scope
for a content-generation session and needs its own review.
Files touched: AI_COLLABORATION.md (this entry).
Deployment: none.
Commit: this entry only.

### Sunday source-brief batch 2026-09-06: 0/3 — wall persists a week later, backfill still not run
Owner: Claude
Status: stopped early per runbook — no candidates saved
Ran `SUNDAY-SOURCE-BRIEFS.md` a week after the eight 2026-08-30 sessions that established
and diagnosed the 100% preflight-refusal wall (see Open Questions). All 12 REBUILD-queue
cases probed this session refused identically at `candidate-opinion` with "source has no
verifiable opinion-part boundaries": MacMunn v. Eli Lilly (2580870), Parvi v. City of
Kingston (5632396), Burdick v. Superior Court (2770126), Derdiarian v. Felix Contracting
(5684475), Kirby v. Foster (4104630), Corey v. Havener (6554250), Lucky Brand Dungarees v.
Marcel Fashions (4753847), Benn v. Thomas (1244600), Bristol-Myers Squibb v. Superior Court
(2294163), McQuirter v. State (1801433), Regina v. Cunningham (manual-cunningham), and
Dobbs v. Jackson Women's Health (6481357). Zero overlap with any of the 51 cases already
logged refusing across the eight 08-30 sessions. Confirmed via direct inspection (not just
re-running the runbook) that the diagnosed root cause is unchanged: Dobbs's S3-stored full
text (`read_full_opinion`) has zero `COURTLISTENER_SUBOPINION` or `===`-heading markers
despite genuinely having majority/concurrence/dissent structure, so it lands in the same
`counts == {"opinion": N}` / `canonical_marker_count != 1` refusal branch as every other
bulk-imported REBUILD case. The one preflight-relevant commit since 08-30 (`c237040`,
"Recognize majority headings after footnote symbols") is a heading-recognition heuristic,
not the backfill — consistent with it not helping any of these 12, all of which have no
headings to recognize at all. No backfill script or single-writing-branch relaxation has
landed (grepped `AI_COLLABORATION.md` and `git log` on `opinion_passages.py` /
`opinion_boundary_preflight.py` / `sunday_briefs.py` since 08-30: only `c237040`). Per the
eighth session's explicit recommendation, did not sample further once the pattern matched
the known wall exactly; stopped after confirming source rather than treating this as a
content-generation problem. Restating the actual next step since two Sundays have now
passed without it happening: someone needs to pick up option (b) from Open Questions (a
backfill script re-running `fetch_courtlistener_document` over the ~890-case queue,
rate-limited) or option (a) (relax the single-writing preflight branch) — this runbook will
keep returning 0/3 every week until one of those ships.

**Addendum, same day, second session:** 5 more probes, same wall, zero overlap with the 12
above or the 51 from 08-30 (63 distinct refused cases logged today plus that week):
Algernon Blair (311461), Klocek v. Gateway (2503865), Seaver v. Ransom (3607257), Mas v.
Perry (8904733), People v. Ceballos (2609526). Stopped after 5 rather than spending the
full 3-candidate budget probing a wall two same-day sessions had already fully diagnosed;
did not touch preflight code, per the standing recommendation that the fix is out of scope
for a content-generation session.
Files touched: AI_COLLABORATION.md (this entry).
Deployment: none.
Commit: this entry only.

**Addendum, same day, third session — queue queried exhaustively, not sampled: 0 of 506
can pass.** First candidate (Adarand-related item 4342450) refused with "source has
separate opinions but no explicit majority boundary"; the next 24 probes (Neri v. Retail
Marine, Van Wagner Advertising, Ardente v. Horan, then 21 more via `candidate-list 25`)
all refused with the same "no verifiable opinion-part boundaries" error, zero overlap with
any case logged in the entries above. Rather than add a fourth same-day sample, ran the
`candidate-list` SQL directly against production: **506 cases currently sit in the REBUILD
queue, 504 have `cases.content IS NULL` (S3-only), and 0 of the 506 contain a
`[[COURTLISTENER_SUBOPINION` marker anywhere.** Only two queue rows have non-null DB
`content` at all — Wood v. Lucy, Lady Duff-Gordon (3607750, 111 chars, below `MIN_OPINION`
so it falls through to the same markerless S3 text anyway) and Carroll v. Trump (9872801,
44,923 chars) — and `candidate-opinion 9872801` was tested directly: it refuses identically
("no verifiable opinion-part boundaries"), confirming the DB-content path is exactly as
blocked as the S3 path. This closes the open question from the 08-30 sessions about
whether sampling might eventually find a passing case: it cannot, by construction, until
one of the two Open Questions fixes ships. Did not implement either fix (backfill via
`fetch_courtlistener_document` or relaxing the single-writing preflight branch) — both are
backend changes to shared validation logic, out of scope for a content-generation session
and flagged to the user directly instead of guessed at.
Files touched: AI_COLLABORATION.md (this entry).
Deployment: none.
Commit: this entry only.

### Incident: Google sign-in silently broken for ~1 month (resolved 2026-08-17)
Owner: Sage (fix) / Claude (diagnosis)
Status: resolved 2026-08-17 ~14:22 UTC — verified by fresh session
Summary: Google OAuth sign-in on tortwell.com failed with "Unable to exchange external
code" from at latest 2026-07-16 (last successful Google sign-in) until today. Surfaced
accidentally while wiring local-dev auth; first misread as a localhost redirect issue
(adding http://localhost:3000/** to Supabase's redirect allow-list was needed for local
dev, but was not this bug). Diagnosis: probing Google's authorize endpoint with the
client ID returned a normal sign-in 302 — client alive, redirect URI authorized — which
isolated the fault to the CLIENT SECRET held by Supabase, since the code exchange is the
only step that uses it. Fix: new client secret minted in Google Cloud Console (project
number 616248408875, project id law-study-group, under sage@sagerock.com) and pasted
into Supabase Auth → Providers → Google. Root cause (Sage, 2026-08-18): he deleted the wrong client secret during an earlier
GCP credentials cleanup — human error, not expiry or Google-side action. Blast radius: 3 Google identities;
email/password sign-in unaffected throughout.
Done 2026-08-18: the auth canary now runs in sagerock/cron-monitor (job
tortwell-google-oauth-canary, commit 023a59a there) — authorize-endpoint probe plus a
secret-validity probe (invalid_grant-on-canary-code); reports 'partial' until
GOOGLE_OAUTH_CLIENT_SECRET is set on the monitor's Railway service. Originally noted:
(1) an auth canary — Supabase's log-query API 500'd throughout the
incident, and a monthly-broken login was invisible because sign-ins are rare; even a
weekly config-liveness probe of the authorize endpoint would have caught this in days;
(2) the Supabase auth logs backend error itself may be worth a support ticket; (3) the
OAuth consent screen may still say "Law Study Group" — rebrand to Tortwell is cosmetic
but user-visible on the Google prompt.
Deployment: none (Supabase dashboard + Google Console config only).
Commit: this entry only.


### Triage session 2026-08-17: 3 regenerations, all via passage-ID remap
Owner: Claude
Status: completed 2026-08-17 — 3/3 candidates saved
Ran `TRIAGE-BRIEFS.md` with a fresh 3-regeneration budget. All three queue items were
generated before their opinion's v9→v10 rebuild, so every save needed the full remap
(pulling old passages from `opinion_passages` under the candidate's original content_hash,
`difflib`-matching against the fresh packet, verifying by exact-substring check before
swapping IDs) — not just the flagged claim's citations, all of them:
- **Byrd v. Blue Ridge Rural Electric Cooperative (105689)**: three claims flagged.
  facts[2] asserted the Fourth Circuit "reversed the judgment for Byrd and directed entry
  of judgment for Blue Ridge" but cited passages about the unrelated Adams millinery-store
  case — the claim itself was true and directly stated in the packet, just cited wrong;
  re-sourced to the actual disposition passage and dropped an unsupported "relying on South
  Carolina's own allocation" clause the record didn't back. majority_reasoning[2]'s Herron
  "before Erie" / "constitutional provision" language and rule[0]'s "form or mode ... need
  not automatically be followed" language were both genuinely stated in the opinion, just
  under different passage IDs than the ones cited — both re-sourced, no wording changed.
  9 of 28 cited IDs were stale and remapped.
- **Conley v. Gibson (105573)**: single flagged claim (holding[0]'s "complaint was not
  properly dismissed" outcome lacked a source stating the outcome, citing only the
  no-set-of-facts standard). Fixed by attaching the reversal passage and the "adequately
  set forth a claim" passage the note pointed to. Heaviest drift of the session: 17 of 28
  cited IDs were stale, including two 3-way sentence-fragment merges from the old passage
  format.
- **Greenman v. Yuba Power Products (1168887)**: single flagged claim
  (majority_reasoning[2]'s "sound commercial rule between immediate parties" clause was
  unsupported — the note named the exact adjacent sentence in the Prosser quote that states
  it). Fixed by adding that sentence's passage as a source. 9 of 20 cited IDs were stale.
Files touched: none (three `candidate-save` writes to the DB only; no code changes).
Deployment: none.
Commit: N/A — documentation-only addition here (plus whatever unrelated changes were
already staged/modified in the working tree when this session started).

### Triage session 2026-08-16 (third pass): 3 regenerations, all via passage-ID remap
Owner: Claude
Status: completed 2026-08-16 — 3/3 candidates saved
Ran `TRIAGE-BRIEFS.md` with a fresh 3-regeneration budget. First queue item (Jordan,
cheng-ev-jordan-edny-2024) and the next (Rodriguez, cheng-ev-rodriguez-2022) both hit
`candidate-opinion`'s "source has no verifiable opinion-part boundaries" refusal —
reported per runbook step 5, not counted against the limit. The next three all fetched
cleanly but every one carried stale passage IDs from the v9→v10 rebuild (same failure
mode as the two sessions logged above), remapped via `difflib` against each candidate's
original content_hash before fixing the flagged claim:
- **City of Cleburne v. Cleburne Living Center (111507)**: majority_reasoning[3] claimed
  Council concern over "proximity to a junior high school" without a supporting citation
  — re-sourced by adding a passage that states this directly (it existed in the packet,
  just wasn't cited). rule[0] asserted the general rule yields to "a fundamental right,
  in which case courts apply strict or intermediate scrutiny," unsupported by either
  cited passage — generalized to only the race/alienage/national-origin exception the
  passages actually state. 6 of 22 cited IDs were stale and remapped.
- **Romer v. Evans (118027)**: facts[0] named "Aspen, Boulder, and Denver" ordinances
  without a passage naming any city — re-sourced with a passage that names all three.
  facts[1] asserted Amendment 2 was "self-executing... which the parties treated as" —
  the amendment's own text (in the packet) literally says it "shall be in all respects
  self-executing"; rewrote to quote that instead of attributing it to the parties. 17 of
  29 cited IDs were stale (the heaviest drift of any case triaged so far) and remapped.
- **Wickard v. Filburn (103716)**: facts[1] stated the "11.1-acre allotment" but the
  cited passage only gave the 23-acre sowing/11.9-acre-excess/239-bushel figures, not the
  allotment; re-sourced by adding the passage that states the 11.1-acre allotment
  directly (a separate sentence earlier in the opinion, not an arithmetic inference). 7 of
  23 cited IDs were stale and remapped.
Files touched: none (three `candidate-save` writes to the DB only; no code changes).
Deployment: none.
Commit: N/A — documentation-only addition here (plus whatever unrelated changes were
already staged/modified in the working tree when this session started).

### Memo Workbench rough-in (tool type #2)
Owner: Claude
Status: exercised end-to-end 2026-08-17 on the Jones project; local stack established
Update 2026-08-17: full loop run three times against a NATIVE local stack (Docker
Desktop's service wouldn't start headlessly; PostgreSQL 16 + pgvector now installed
in the Ubuntu WSL directly — user legal_user/legal_pass, db legal_research, schema
pulled from production via pg_dump --schema-only because migrations/ is incomplete
relative to prod; backend runs `uvicorn main:app --port 8001` with a LOCAL-ONLY
SUPABASE_JWT_SECRET and self-minted JWTs — no prod secrets involved; seed rows:
profiles 'local-dev-sage-0001', pool_ledger +$10).
Results: 8 documents uploaded and parsed, chart generated in ~100s for ~$0.17
(sonnet-4-6, ~31k in / ~4.8k out), all 7 answer-key arguments from the hand-built
Jones benchmark found, all 5 side calls correct. The loop caught two real defects:
(1) extract_text_from_pdf scrambled two-column Westlaw/Lexis printouts (pdfplumber
default interleaves columns line-by-line) — fixed with use_text_flow=True; affects
every upload path (BriefCheck, MSJ), not just memo; (2) verify_chart_quotes needed
typographic-punctuation and star-pagination normalization. The verifier's remaining
flags are true positives (model silently corrected a reporter's typo "controls fand";
paraphrased a Davis clause) — exactly the review UX intended. postprocess_generated
is now wired into the generate endpoint, so every chart persists chart_parsed +
quote_problems in document_metadata. Known open prompt issue: the chart still leans
on probable cause despite scope_notes excluding it; one scope-rule iteration added,
needs another pass.
Files: `backend/memo_builder.py`, `backend/test_memo_builder.py`, tool-dispatch and
link-case hunks in `backend/main.py`, `frontend/app/tools/memo/`,
`frontend/components/memo/MemoWorkbench.tsx`
Summary: second tool type on the generic legal-tools chassis (the ToolProjectCreate
comment always anticipated "memo"). Deliberately NOT a memo writer — Sage's direction:
collect the scenario, the record (transcripts), and the authorities, and help analyze
which cases help or hurt the client. Generation produces a CASE CHART (per-authority
helps/hurts/mixed with verbatim passages, fact comparisons, how-to-use-or-distinguish,
record gaps, suggested order) as JSON; the chat system prompt declines to draft the memo
and says why; closed-universe mode confines analysis to project authorities. Authorities
arrive by upload (doc_type 'case'/'statute') or the new
POST /tools/{type}/projects/{id}/link-case, which snapshots a Tortwell case's opinion
text (postgres → S3 → CourtListener) into tool_documents so downstream handling is
uniform. main.py now dispatches builder functions by convention
(build_{tool_type}_system_prompt / _generation_prompt) instead of hardcoded affidavit
names. memo_builder ships parse_memo_chart and verify_chart_quotes (brief-pipeline
verbatim discipline) — tested but NOT yet wired into the generate endpoint.
8 new tests; 208 pass; tsc clean.
Untested end-to-end: generate SSE with a real project, link-case against production,
frontend in a browser (DrvFs dev-server pain — see wsl-drvfs-dev-server memory). Test
corpus: the Jones/Super Hawk closed-universe memo (assigning memo + 2 depos + 4 cases +
R.C. 2935.041, /mnt/d/Downloads).
Context: the closed-world special case of Research Mode (see memo-benchmark memory and
the research-mode sketch); ships first because a memo project brings its own universe —
no embeddings or citator coverage required.
Next: exercise end-to-end with the Jones materials; wire verify_chart_quotes into
generate; decide whether memo chat needs a UI panel (the generic chat endpoint already
accepts tool_type memo); chart export.
Deployment: not deployed (local commit only)
Commit: `79223db`

### Triage session 2026-08-16: passage-ID drift after v10, and a boundary-preflight regression
Owner: Claude
Status: investigated and resolved 2026-08-16 — verdict: not a v10 regression; queue bug fixed
Resolution (Claude, same day): reproduced both named cases against the pre-v10 module
(`git show f4851c2~1`) — Parker (1453074) and Daimler (2649076) are refused IDENTICALLY
by v9 and v10, so the boundary assessment did not get stricter. The actual cause: these
candidates were generated 2026-07-12, nine days before strict source preflight shipped
(2026-07-21) — the gate is correctly refusing sources that were never held to its
standard. The real defect was in the queue: triage-list's two-strike rule counted only
semantic_review failures, so preflight-refused cases never rotated out and every session
re-attempted them (hence Parker's six same-day failure rows). Fixed by excluding cases
with a source_preflight failure in the last 6 days, mirroring candidate-list's window;
the live queue now serves 10 workable cases. The refused cases still need canonical
CourtListener re-ingestion (the Chemerinsky-handoff assembler path) to gain sub-opinion
markers — that remains human-scheduled work, per runbook step 5. The passage-ID remap
guidance in TRIAGE-BRIEFS.md stands unchanged.
Files: `citator/sunday_briefs.py`, `citator/TRIAGE-BRIEFS.md`, `backend/opinion_passages.py`
Summary: ran a normal `TRIAGE-BRIEFS.md` pass and hit two problems the runbook didn't
anticipate.
- **Stale citations across a format-version bump.** The three rejected candidates fixed
  this session (Seiler 481390, Jaffee 118042, In re Grand Jury Subpoena Miller 7914180)
  were generated 2026-07-12, before the passage-format v9→v10 rebuild (see the completed
  handoff below). Re-fetching each source packet today showed 4-12 of their ~30-35 cited
  passage IDs no longer exist under the current content_hash — v10 folds star-pagination
  and citation-only fragments into neighboring sentences, which merges or reshapes some
  passage boundaries even though the underlying opinion text is unchanged. `candidate-save`
  validates sources against the *current* content_hash's passages, so a triage fix that
  only edits the flagged claim's text (per the runbook's literal steps) will fail
  validation on every OTHER claim that happens to cite a since-merged passage — this isn't
  edge case, it hit 2 of 2 cases checked with non-trivial citation counts. Worked around it
  by pulling the old candidate's passages from `opinion_passages` under its original
  content_hash (still present, just under an old hash), matching each stale passage's text
  against the current packet (`difflib` ratio + manual verification — exact-substring
  matches were reliable, low-score matches needed eyeballing because two near-identical
  passages can appear in both `majority` and `dissent` parts), and remapping IDs before
  editing the flagged text. `TRIAGE-BRIEFS.md` should probably get a step for this — it
  currently assumes the packet handed back by `candidate-opinion` cites cleanly against
  the old candidate's IDs, which is only true when no format-version rebuild happened
  in between.
- **Boundary preflight is currently refusing most of the triage queue.** Of the 10 oldest
  rejected cases, `candidate-opinion` refused 7 outright: "source has no verifiable
  opinion-part boundaries" (5 cases) or "source has separate opinions but no explicit
  majority boundary" (Daimler AG v. Bauman, 2649076). `structured_summary_failures` shows
  the boundary error already logged 6 times today for Parker v. Twentieth Century-Fox Film
  Corp. (1453074) alone, from what looks like other automated attempts, so this isn't a
  one-off. These cases' briefs previously existed (they reached semantic review and were
  rejected on content grounds, not source grounds), so something about the v10 boundary
  assessment is now stricter than what originally ingested them. Left these for human
  attention per the runbook's step 5 rather than guessing at a fix; did not count them
  against the 3-regeneration session limit since no write was attempted. Worth checking
  whether `assess_opinion_boundaries`'s `require_explicit=True` path (backend/opinion_passages.py:615)
  got measurably stricter in the v10 change, or whether these specific opinions' stored
  text genuinely lost its part markers.
Deployment: none — documentation and one runbook clarification only.
Commit: none yet (uncommitted at session end).

### Triage session 2026-08-16 (second pass): 3 regenerations via passage-ID remap
Owner: Claude
Status: completed 2026-08-16 — 3/3 candidates saved, queue rotation fix confirmed separately
Ran `TRIAGE-BRIEFS.md` starting from a stale local view (before `aeb89c4` landed from a
concurrent session on this same machine — see the "Session collision" note in the dev-root
CLAUDE.md). Hit the identical wall documented in the entry above: `candidate-opinion`
refused every one of the first 10 queue items with the same two boundary-preflight errors
(Parker 1453074, Daimler 2649076, Obergefell 2812209, Biaggi 545489, Cosby 10315392, Gordon
277392, Rothlisberger 2621346, Elfgeeh 1386819, Grand Jury Proceedings 732430, McCray
7830390, Meza 273618 — 11 refused total across both sessions' attempts). None of these
count against the 3-regeneration limit (no candidate written). Working further down the
queue (items 11+, past what the two-strike/preflight-window queue bug had been silently
recycling) turned up 3 fetchable packets, each hit by the same stale-passage-ID drift from
the v9→v10 rebuild described above — remapped by pulling each candidate's original
content_hash from `opinion_passages`, `difflib`-matching stale IDs against the fresh
packet, and verifying full text (not just similarity score) before substituting:
- **Trammel v. United States (110212)**: rejected claim named three privileges
  (priest-penitent/attorney-client/physician-patient) and a "protect only confidential
  communications" comparison not in its cited passages; generalized to the actually-quoted
  "no other testimonial privilege sweeps so broadly." 22 of 30 cited passage IDs were stale
  and remapped (3 old IDs merged into 1 new passage in one case).
- **Monger v. Cessna Aircraft Co. (8957550)**: rejected claim characterized Exhibit 40 as
  "criticizing Cessna for past failures to identify safety problems" — passages support
  only that it might show improper FAA approval of the 210-J fuel system; rewrote to match.
  11 of 34 cited IDs were stale.
- **Michael H. v. Gerald D. (112295)**: two rejected claims (facts[2]'s "held Victoria out
  as his daughter" cohabitation detail, sourced only in a dissent passage; facts[0]'s
  wife-only two-year rebuttal window, omitting the natural-father-affidavit precondition).
  Both were re-sourceable: the majority's own fact recitation independently states Michael
  lived with Carole and Victoria and held her out as his daughter during an "ensuing eight
  months" period (ordinals 31-32, split across two passages by an "St. / Thomas" line
  break) — not just in White's dissent. 15 of 48 cited IDs were stale. Discovered a new
  failure mode along the way: one previously-approved claim (majority_reasoning[2], about
  Justice O'Connor and Kennedy declining to join footnote 6) cited a byline passage
  (op-3377454a98e8aca5) that is genuinely absent from the fresh packet — not merged
  elsewhere, just gone (packet `is_partial_packet: true`, 429/1139 passages selected;
  likely dropped in selection given how much of this case is dissent/concurrence). Also,
  `validate_structured_summary`'s `MAJORITY_SOURCE_SECTIONS` check
  (`backend/structured_briefs.py:120-125`) rejects `majority_reasoning` claims that cite
  `concurrence`-part passages — the original (rejected-for-other-reasons) candidate had
  apparently cited concurrence passages under `majority_reasoning` without this tripping,
  which only makes sense if the v9 pass labeled that content `opinion`/`majority` rather
  than `concurrence`. Fixed by dropping the claim (majority_reasoning's floor is 1; three
  remained) rather than guessing at a rewrite — the point survives in `significance`,
  which needs no passage support.
Files touched: none (three `candidate-save` writes to the DB only; no code changes).
Deployment: none.
Commit: N/A — no file changes to commit from this entry; documentation-only addition here.

### Triage session 2026-08-23: 3 regenerations, and the preflight-refusal rate is still high
Owner: Claude
Status: completed 2026-08-23 — 3/3 candidates saved
Ran `TRIAGE-BRIEFS.md`. The `aeb89c4` queue-rotation fix works as designed — each
`candidate-opinion` refusal writes a `source_preflight` failure row, and the very next
`triage-list` call excludes that case, so the live queue never re-served the same refused
case twice in this session. But the underlying refusal rate is still high: of 21 distinct
queue cases probed today, 16 refused at `candidate-opinion` (Parker 1453074, Daimler
2649076, Obergefell 2812209, Biaggi 545489, Cosby 10315392, Gordon 277392 — all six
carried over from 2026-08-16 and still unfixed at the source — plus newly-probed
Rothlisberger 2621346, Elfgeeh 1386819, Grand Jury Proceedings 732430, Jordan
cheng-ev-jordan-edny-2024, Rodriguez cheng-ev-rodriguez-2022, McCray 7830390, Meza 273618,
Ricketts v. Scothorn 6769658, Childress v. Taylor 569096, Osborn v. Bank 85451, Peoni
1485475, Tunkl 1149237, Liberty Mutual 109403, Tj Hooper 1542549, Walden v. Fiore 2654532).
None of these count against the 3-regeneration limit (no candidate written). The 5 that
passed preflight (Falcone 103400, Van Cauwenberghe 112092, Harris v. Jones 1560933, Taylor
v. Sturgell 145793, Freehe v. Freehe 2616799) supplied this session's 3 regenerations plus
2 left for a future session. This confirms the 2026-08-16 diagnosis (refusal is correctly
gating pre-v10 sources, not a new regression) but the volume says the "human-scheduled"
canonical re-ingestion work mentioned there hasn't started — roughly three-quarters of the
triage queue is currently unworkable until it does.

All 3 regenerated candidates hit the same stale-passage-ID pattern as 2026-08-16 (old
content_hash's fragment-level passages merged into fewer, fuller passages under the fresh
content_hash) — remapped by pulling each candidate's original content_hash from
`opinion_passages`, matching stale IDs against the fresh packet by substring, and verifying
full text before substituting:
- **United States v. Falcone (103400)**: rejected claim said sold materials "reached the
  possession and use of some of the distiller defendants" — flagged as unsupported because
  its cited passage was a stale OCR fragment truncating at "sold sugar, yeast or cans,".
  The fresh, fuller passage for the same sentence continues "...some of which found their
  way into the, possession and use of some of the distiller defendants" — full support, no
  wording change needed, pure ID remap. 13 of 21 cited IDs were stale.
- **Van Cauwenberghe v. Biard (112092)**: three flagged issues, all fixed by remap plus one
  re-source: (1) facts[3]'s "Mitchell v. Forsyth" citation — stale fragment truncated at
  "Cohen v."; fresh merged passage states both case names in full. (2) majority_reasoning[3]'s
  "28 U.S.C. § 1292(b)" — stale fragment truncated at "28 U."; fresh passage states the full
  citation. (3) facts[0]'s "townhouse complex" — not a stale-ID issue; the passage
  establishing it (op-554c5abd013c88bc, "renovating a townhouse complex outside Kansas City
  known as Concorde Bridge Townhouses") existed in the packet all along but was never cited
  under facts[0] — added it. 15 of 44 cited IDs were stale.
- **Harris v. Jones (1560933)**: rejected claim attributed the four-element IIED test to
  "Womack v. Eldridge," but cited passages were stale fragments that never named the case
  (one truncated at "the four elements outlined in"). The fresh merged passages state
  "Womack" by name in both the holding and majority-reasoning citations — pure ID remap, no
  wording change. 12 of 27 cited IDs were stale.
Files touched: none (three `candidate-save` writes to the DB only; no code changes).
Deployment: none.
Commit: N/A — no file changes to commit from this entry; documentation-only addition here.

### Triage session 2026-08-23 (second pass): 3 regenerations, mostly re-sourcing not rewriting
Owner: Claude
Status: completed 2026-08-23 — 3/3 candidates saved
Ran `TRIAGE-BRIEFS.md` again with a fresh 3-regeneration budget. All three queue items had
been generated before their opinion's v9→v10 passage rebuild, so every save needed the full
remap (pulling old passages from `opinion_passages` under the candidate's original
content_hash, matching stale IDs against the fresh packet by substring, verifying full text
before substituting) — not just the flagged claim's citations, all of them. In most of the
flagged claims, the underlying assertion was already true and already stated somewhere in
the fresh packet; the fix was adding the right citation, not rewriting the sentence:
- **Staples v. United States (1087954)**: three claims flagged. majority_reasoning[0] paired
  "hand grenades or food stamps" as if both were the suspect category, but Staples actually
  contrasts food stamps with hand grenades (per Liparota) — dropped the food-stamps clause
  and kept the hand-grenades/tradition-of-lawful-ownership claim the passages do support.
  rule[0] had cited the Government's characterization of precedent as the Court's own rule
  and asserted a "dangerous or deleterious devices" framing found nowhere in the majority's
  text — rewrote to only the "traditionally lawful conduct ... usual presumption" language
  the majority actually states, dropping the public-welfare framing entirely.
  majority_reasoning[1]'s "machineguns" quasi-suspect claim was rejected only because its
  cited passage was truncated right before the word; the fresh, untruncated passage states
  it in full — pure re-source, no wording change. 15 of 35 cited IDs were stale.
- **Davey v. Lockheed Martin Corp. (162516)**: four claims flagged, all fixable by
  re-sourcing rather than rewriting — the fresh, merged passages already state what the
  rejected claims asserted, they just weren't the ones cited. facts[0]'s "amended ... based
  on LMC's refusal to rehire her" is now one explicit sentence in the fresh packet. facts[2]'s
  "had not had an opportunity to conduct discovery" is now a direct paraphrase sentence.
  facts[3] and majority_reasoning[2] both leaned on an unverified "head nurse" job title
  (stated only by trial counsel's argument, never adopted by the court) — generalized to the
  district court's own language, that the juror had "worked as a nurse ... for ten years and
  supervised ... people." Heaviest remap of the session: 61 of 64 cited IDs were stale.
- **In re Recticel Foam Corp. (513181)**: three flagged claims plus one claim the note
  flagged as "minor," all fixed by citing passages that were already in the packet but never
  attached. facts[2]'s videotapes/photographs detail — added the two passages establishing
  that the shared "expense" was for producing those videotapes/photographs. majority_
  reasoning[0]'s "resembled discovery orders" / "remained subject to modification" — added
  the passages stating both (previously linked only under rule[0]). majority_reasoning[1]'s
  "reviewable ... after final judgment" and "reallocation of costs already paid" — added the
  post-judgment-appealability passage and the antecedent "motions for the reallocation of
  expenses" passage. holding[0]'s uncited "not final and fell within no exception" reasoning
  — added the opinion's closing-paragraph passage stating exactly that. 18 of 48 cited IDs
  were stale.
Files touched: none (three `candidate-save` writes to the DB only; no code changes).
Deployment: none.
Commit: N/A — no file changes to commit from this entry; documentation-only addition here.

### Triage session 2026-08-23 (third pass): 3 regenerations, one genuinely wrong claim (not just stale sourcing)
Owner: Claude
Status: completed 2026-08-23 — 3/3 candidates saved
Ran `TRIAGE-BRIEFS.md` a third time today with a fresh 3-regeneration budget. All three
queue items again predated their opinion's v9→v10 passage rebuild, so every save needed
the full remap (pulling the candidate's original content_hash from `opinion_passages`,
`difflib`-matching stale IDs against the fresh packet, verifying full text — not just
similarity score — before substituting, since near-duplicate fragments of the same citation
can recur multiple times in one opinion):
- **BMW of North America, Inc. v. Gore (118026)**: four claims flagged. facts[1]'s
  "suppression of a material fact" cause-of-action naming had no support in its cited
  passages — re-sourced with a passage that states it verbatim ("Dr. Gore alleged ... that
  the failure to disclose ... constituted suppression of a material fact"), which existed in
  the packet but wasn't cited. majority_reasoning[2]'s "though the Court declined to draw a
  bright mathematical line" was similarly re-sourced from an uncited passage that states it
  almost verbatim. issue[0]'s "based in part on the defendant's out-of-state conduct" and
  majority_reasoning[1]'s "rather than being treated as a recidivist wrongdoer" were both
  genuinely unsupported by any passage in the packet (not merely uncited) — dropped both
  clauses rather than guess at a rewrite. 14 of 40 cited IDs were stale.
- **O'Shea v. Welch (784334)**: heaviest remap of the session, 21 of 44 cited IDs stale,
  including one low-confidence `difflib` match (a fragment "within the scope of his
  employment when he attempted to turn into the service station" had been fully absorbed
  into a neighboring sentence rather than surviving as its own passage — confirmed by
  reading the merged passage's full text before treating it as the same source, not a loss).
  Five claims fixed: facts[0]'s "store manager" wording was generalized to "employee" to
  match its own cited passage (the manager detail is separately supported elsewhere in the
  brief). facts[2]'s "failed to yield" was changed to "allegedly failed to yield" — the
  opinion itself uses "allegedly," so matching it is accurate re-sourcing, not the
  hedge-while-still-unsupported pattern the runbook warns against. majority_reasoning[0]'s
  "the district court relied on" attribution and majority_reasoning[3]'s "deviation to drop
  off a prescription" detail were both re-sourced from passages that stated them verbatim
  but had never been cited. majority_reasoning[1] overstated "adopted slight-deviation
  analysis for third-party liability cases" when the opinion only calls the framework
  "compatible" and says Kansas had separately "adopted" it for workers'-comp cases —
  rewrote to track that distinction instead of dropping or re-sourcing.
- **Garratt v. Dailey (1415303)**: the one case this session where a flagged claim was
  substantively wrong, not just mis-cited. rule[0] had imported the "particular harmful
  contact" battery-intent formulation from *Garratt*'s famous 1955 opinion (46 Wn.2d 197) —
  a different content_hash, not part of this packet at all, which is the 1956 on-remand
  opinion. This opinion's own "such knowledge ... is sufficient to charge the defendant with
  intent to commit a battery" sentence has a different antecedent: the trial court's specific
  finding that the defendant knew the plaintiff would attempt to sit where the chair had
  been. Rewrote rule[0] to state that specific finding instead of the borrowed general
  formulation, and added the antecedent passage as a source. holding[0]'s "It finds ample
  support in the record" had the same missing-antecedent problem — added the same finding
  passage. 7 of 25 cited IDs were stale; three of those seven were fragments of the same
  "Garratt v. Dailey, 46 Wn.(2d) 197, 279 P.(2d) 1091" citation that had merged into one
  passage, and the opinion's passage-suffix numbering (`-2`/`-3` for repeated "Garratt v."
  fragments) shifted between old and new content hashes, so matching by suffix alone would
  have picked the wrong occurrence — resolved by reading surrounding context, not just
  string similarity.
Files touched: none (three `candidate-save` writes to the DB only; no code changes).
Deployment: none.
Commit: N/A — no file changes to commit from this entry; documentation-only addition here.

### Triage session 2026-08-23 (fourth pass): 6 of 9 probed cases refused at preflight, 3 regenerations
Owner: Claude
Status: completed 2026-08-23 — 3/3 candidates saved
Ran `TRIAGE-BRIEFS.md` a fourth time today. Preflight refusal rate was even worse than the
first pass's finding: of 9 distinct queue cases probed, 6 refused at `candidate-opinion`
(Iqbal v. Ashcroft 30747, Machuca Gonzalez v. Chrysler 28432, J. McIntyre Machinery v.
Nicastro 219733, Rasoulzadeh v. Associated Press 1866935, United States v. Contento-Pachon
428603, The Queen v. Dudley and Stephens manual-dudley-stephens) — none count against the
3-regeneration limit. Contento-Pachon's refusal message was a new variant not seen in prior
sessions' logs: "source declares concurrence material but parser found none" (the other five
were the familiar "no verifiable opinion-part boundaries") — worth a look if it recurs, since
it's a different failure mode than the pre-v10-source explanation already confirmed for the
boundary error. The queue-rotation fix (`aeb89c4`) again meant none of these six re-served
after their refusal was recorded.

The 3 that passed preflight all hit the same stale-passage-ID pattern (pre-v10 generation,
remapped by pulling the candidate's original content_hash from `opinion_passages`, matching
stale IDs against the fresh packet by substring, and verifying full text before
substituting):
- **Frier v. City of Vandalia (457114)**: two claims flagged. significance had asserted
  specific content of Judge Swygert's separate opinion (concurring in result only, would
  grant summary judgment under Mathews v. Eldridge) with no dissent/concurrence claims
  anywhere in the brief to source it — dropped the sentence rather than guess a citation.
  majority_reasoning[0]'s "no citation and no hearing on the parking violation" clause was
  genuinely stated in the packet, just uncited — re-sourced from the passage that says it
  almost verbatim. Heaviest remap of the session: 20 of 40 cited IDs were stale, including a
  three-way collapse where two old fragments ("Under 28 U.S.C." and "Sec.") both merged into
  one new passage, so both old IDs now point at the same new ID.
- **Neely v. Martin K. Eby Construction Co. (2764185)**: issue[0] framed the question as
  "consistent with... the Seventh Amendment's right to jury trial" but its cited passages
  never mention the Seventh Amendment — the passage that does (merged from two old fragments
  during the rebuild) was already cited under holding[0]/majority_reasoning[0]; attached it
  to issue[0] too. Also fixed the note's "minor" secondary point: majority_reasoning[0] names
  "28 U.S.C. Sec. 2106" but its passages only quoted the statute's text without the section
  number — added the adjacent passage that states "Section 2106 of Title 28 provides that,".
  12 of 44 cited IDs were stale.
- **McGuire v. Almy (6568714)**: two claims flagged, both re-sourcing, not rewrites. facts[2]
  said "the plaintiff's brother-in-law arrived" but its cited passage only said "When he
  arrived" — added the passage identifying Emerton as the brother-in-law (two old fragments
  merged into one during the rebuild). issue[0] named the cause of action "assault and
  battery" without citing the opinion's opening line stating exactly that — added it. Lightest
  remap of the session: 3 of 29 cited IDs were stale.
Files touched: none (three `candidate-save` writes to the DB only; no code changes).
Deployment: none.
Commit: N/A — no file changes to commit from this entry; documentation-only addition here.

### Triage session 2026-08-30: 22 of 22 probed cases refused at preflight, 0 regenerations
Owner: Claude
Status: stopped early — queue not exhausted, see Open Questions
Ran `TRIAGE-BRIEFS.md`. Every one of the 22 distinct queue cases probed refused at
`candidate-opinion`, all with the two familiar messages ("no verifiable opinion-part
boundaries" or "source has separate opinions but no explicit majority boundary" — split
roughly 20/2). None count against the 3-regeneration limit per runbook step 5; the
queue-rotation fix (`aeb89c4`) meant each refusal rotated that case out before the next
`triage-list` call, so no case repeated. Cases probed (all refused): Parker v. Twentieth
Century-Fox (1453074), Daimler AG v. Bauman (2649076), Obergefell v. Hodges (2812209),
United States v. Biaggi et al. (545489), Commonwealth v. Cosby (10315392), Morris W. Gordon
v. United States (277392), State v. Rothlisberger (2621346), United States v. Elfgeeh
(1386819), In Re Grand Jury Proceedings (732430), McCray v. State Farm (7830390), Sec'y of
HEW v. Meza (273618), United States v. Jordan (cheng-ev-jordan-edny-2024), People v.
Rodriguez (cheng-ev-rodriguez-2022), Ricketts v. Scothorn (6769658), Osborn v. Bank of the
United States (85451), Alice Childress v. Taylor et al. (569096), United States v. Peoni
(1485475), Tunkl v. Regents (1149237), Liberty Mutual v. Wetzel (109403), The T.J. Hooper
(1542549), Walden v. Fiore (2654532), Piesco v. Koch et al. (659320).

This is a materially worse refusal rate than any prior session — the worst previously
recorded was 6 of 9 (2026-08-23, fourth pass); this session's 22 of 22 is 100%, and the
queue still had 50+ untouched entries when I stopped (confirmed via `triage-list 50`), so
this isn't a small unlucky tail exhausting the backlog. I checked for a code regression
before concluding this was expected variance: `git log` on `opinion_boundary_preflight.py`,
`backend/opinion_passages.py`, and `backend/structured_briefs.py` shows no commits since
`f4851c2` (2026-08-12, the v9→v10 rebuild) — nothing changed recently that would explain a
jump from 67% to 100%. My read: this is the same accepted-risk backlog documented across
the 2026-08-16/17/23 sessions (pre-v10-generation and malformed-source cases genuinely
failing strict preflight, not a preflight bug), just concentrated at the current head of
the queue (`triage-list` orders oldest-rejected-first) — but I did not verify that
explanation the way the 2026-08-16 session verified its "not a regression" conclusion, so
flagging it as unconfirmed rather than asserting it.
Files touched: none (no candidate-opinion writes succeeded; only `source_preflight` failure
rows were recorded, which is `candidate-opinion`'s normal behavior on refusal).
Deployment: none.
Commit: N/A — documentation-only addition here.

### Triage session 2026-08-30 (second pass): 9 of 12 refused at preflight, 3 regenerations
Owner: Claude
Status: completed 2026-08-30 — 3/3 candidates saved
Ran `TRIAGE-BRIEFS.md` again later the same day as the "22 of 22" pass above. The
queue-rotation fix meant the head of the queue had moved on; this pass's preflight refusal
rate (9 of 12, 75%) was high but not total, and produced three savable regenerations before
hitting the limit. Refused at `candidate-opinion` (none count against the limit): Temple v.
Synthes Corp (112500), Iqbal v. Ashcroft (30747), Machuca Gonzalez v. Chrysler (28432), J.
McIntyre Machinery v. Nicastro (219733), Rasoulzadeh v. Associated Press (1866935), United
States v. Contento-Pachon (428603, the "declares concurrence material but parser found
none" variant), Richardson v. Chapman (2195023, same variant), Wagner v. International
Railway Co (3607799). All eight are repeats of cases already logged refusing in the
2026-08-16/23/30 sessions above — confirms the queue-rotation window (6 days) is working as
designed rather than silently reserving refused cases forever.

The 3 that passed preflight all carried stale passage IDs from the pre-v10 generation,
remapped by pulling each candidate's original content_hash from `opinion_passages`,
matching stale IDs against the fresh packet by substring, and verifying full text before
substituting:
- **Burnham v. Superior Court (112436)**: four issues. facts[0]'s "later moved to New
  Jersey" and "two children" were unsupported by the 3 cited passages — re-sourced by
  adding the one passage that states both directly ("the couple moved to New Jersey, where
  their two children were born"), previously uncited. majority_reasoning[0]'s "traced...to
  English common law" was unsupported by its 3 cited passages (which cover only 1868-era
  and post-1978 American practice) — re-sourced by adding the passage stating the rule's
  "antecedents in English common-law practice." majority_reasoning[3] misquoted the
  concurrence's phrase as "contemporary notions of fairness"; the opinion's actual phrase,
  used three times, is "contemporary notions of due process" — corrected the quote and
  added the passage where it appears. Minor: added the passage majority_reasoning[2] already
  cited to majority_reasoning[1] too, per the note. 9 of 25 cited IDs were stale and
  remapped.
- **Wallace v. Rosen (2079379)**: facts[0] claimed Rosen found "Wallace and two others"
  (a group of 3); one cited passage says "three or four people" without naming Wallace, and
  a passage cited elsewhere in the brief has the opinion's own words, "Wallace and three
  others" — fixed the count to match the opinion's own group-of-4 language and added that
  passage as a source. majority_reasoning[2]'s "pattern-instruction committee" attribution
  was unsupported by its cited passages — re-sourced with an uncited passage naming the
  "Civil Instruction Committee" in the pattern instruction's comment section. facts[2]'s
  "about ninety degrees" was sourced only to an ambiguous "Yeah, half that." fragment — added
  the passage with the court's own "90°" finding (already cited elsewhere in the brief).
  11 of 39 cited IDs were stale and remapped. Distinct new pattern: this source packet
  contains the full majority opinion text twice (a ~226-ordinal offset duplicate block with
  otherwise-identical text), so every passage had two valid IDs to choose from; picked the
  earlier-ordinal occurrence for consistency. Preflight passed regardless (both copies parse
  as majority), so this didn't block the fix, but it's a residual-risk shape not previously
  logged — worth a look if a future session finds contradictory-seeming duplicate citations.
- **Pipher v. Parsell (2330474)**: majority_reasoning[1] claimed the analogous Vermont case
  "held a driver liable," but its cited passages only establish that the passenger's prior
  conduct "should have forecast the peril...to a reasonably prudent driver" — the Vermont
  court's actual holding on liability isn't in the source. Reworded to the reviewer's own
  suggested fix ("held that peril was foreseeable to a reasonably prudent driver") rather
  than the unsupported liability claim. 16 of 33 cited IDs were stale — the heaviest drift
  of any case triaged so far — and several old IDs collapsed into single merged passages
  under the v10 rebuild (e.g., three separately-cited old sentences about the driver's duty
  of care now live in one merged "Duty of Driver" passage), so multiple old citations
  remapped to the same new ID.
Files touched: none (three `candidate-save` writes to the DB only; no code changes).
Deployment: none.
Commit: N/A — documentation-only addition here.

### Triage session 2026-08-30 (third pass): 3 regenerations, all via passage-ID remap
Owner: Claude
Status: completed 2026-08-30 — 3/3 candidates saved
Ran `TRIAGE-BRIEFS.md` a third time the same day, found the two entries above only while
writing this one. `triage-list 1` returned exactly one case per call each time (queue had
thinned to single-digit depth by this pass), so no preflight refusals to report this round
— all three probed cases fetched cleanly. All three still carried stale passage IDs from
the pre-v10 generation (each candidate's original content_hash differed from the fresh
packet's), remapped the same way as prior sessions: pulling the candidate's original
passages from `opinion_passages` under its own content_hash, matching stale IDs against the
fresh packet by substring, and verifying full text before substituting — every citation in
each fixed candidate re-checked against the fresh packet before saving, not just the flagged
claim's.
- **Murrell v. Goertz (1187453)**: single flagged claim (majority_reasoning[1] attributed
  the "no contact with the company" evidence to "Westbrook's affidavit and Goertz's
  deposition," but none of its three cited passages named an affidavit or deposition). The
  packet contains an uncited passage that states exactly this ("Appellee submits that the
  affidavit of Russell Westbrook and Goertz's deposition reveal that Goertz had no contact
  with appellee") — re-sourced by adding it rather than weakening the claim's language.
  8 of 26 cited IDs were stale and remapped, including a 3-way sentence-fragment merge
  (route/6-a.m./rubber-bands control factors, previously three separate old passages, now
  one).
- **Grable & Sons Metal Products v. Darue Engineering (799977)**: majority_reasoning[1]'s
  Government-interest-in-"clear terms of notice"/"good title" claim was flagged as
  unsupported by its cited passages — one of those two passages was itself stale, truncated
  under the old format at "United States v." before the notice/good-title language; the
  fresh, fuller v10 passage keeps going and states it directly, so re-sourcing to the fresh
  passage id resolved the flag without touching the claim's wording. Also fixed, per the
  note's secondary (non-holding) flag: majority_reasoning[3]'s closing clause ("that
  flood-of-cases concern is absent from Grable's case") wasn't supported by its four Merrell
  Dow sources and was redundant with majority_reasoning[2]'s already-sourced version of the
  same point — deleted the clause rather than re-source it. 5 of 29 cited IDs were stale and
  remapped.
- **Schlagenhauf v. Holder (106937)**: heaviest drift of the session, 16 of 49 cited IDs
  stale, and the note flagged three separate claims. facts[1] said the petition sought
  "nine physical and mental examinations" — the petition actually requested one specialist
  in each of four fields; nine was the number of physicians named to give the court a
  choice, and nine examinations was the District Court's order, not the petition (the
  brief's own facts[2] states the four-exam figure) — corrected the count and dropped an
  affidavit detail ("without slowing," "similar accident") not in the cited affidavit
  passage. facts[0] attributed the "not mentally or physically capable" allegation jointly
  to Contract Carriers and National Lead; the fresh packet shows it was Contract Carriers
  alone (via a letter treated as part of its answer) — corrected the attribution, and added
  a now-complete fresh passage (old version was split across two stale, separately-cited
  fragments) that names National Lead as the trailer's owner, which the claim needed anyway.
  rule[1]'s "Unlike the other discovery rules" comparative wasn't in either cited passage —
  dropped it, keeping the rest of the claim verbatim per the note. This packet also had the
  Wallace v. Rosen pattern from the prior session: the full majority opinion appears twice
  in the source (a ~216-ordinal-offset duplicate block), so several remaps had two valid
  target IDs; picked the earlier-ordinal occurrence for consistency.
Files touched: none (three `candidate-save` writes to the DB only; no code changes).
Deployment: none.
Commit: N/A — documentation-only addition here.

### Triage session 2026-08-30 (fourth pass): 3 regenerations; also mistakenly skipped 3 fixable cases as "source defects" before catching the Wallace v. Rosen precedent already logged above
Owner: Claude
Status: completed 2026-08-30 — 3/3 candidates saved; 3 additional queue cases left untouched
that should NOT be treated as blocked (see correction below)
Ran `TRIAGE-BRIEFS.md` a fourth time the same day, found the three passes above only while
writing this entry. `triage-list` returned single items at a time (queue thin), all
first-attempt rejects with real citation-sourcing notes — no preflight refusals this round.

**Regenerated (3/3, budget exhausted):**
- **Callanan v. United States (106152)**: rule[0] claimed the two Hobbs Act offenses "may
  be cumulatively punished," sourced only to the Pinkerton "separate and distinct offenses"
  quote, which stops short of the punishment consequence — added the adjacent passage
  stating that dislodging that "conventional consequence... would require specific language
  to the contrary" (the same pairing the reviewer already validated for
  majority_reasoning[2]'s American Tobacco characterization). Secondary: dissent[1] dated
  the legislative debates to "1946," a year none of its three cited passages state —
  generalized to "the legislative debates over the penalty increase," dropping the date
  rather than re-sourcing. 10 of 36 cited IDs were stale (candidate predates the v9→v10
  rebuild) and remapped.
- **Gunn v. Minton (820904)**: holding[1] summarized all three Grable factors
  ("necessarily raised and actually disputed... not substantial") but cited only a bare
  conclusion line and the reversal — re-sourced to the specific passages already used (and
  reviewer-validated) under majority_reasoning[0-2] for each factor. Secondary: issue[0]'s
  "hypothetical" characterization was unsupported by its two cited passages — added the
  passage majority_reasoning[2] already cites that uses the word directly. 1 of 26 cited
  IDs was stale and remapped.
- **Murphy v. Martin Oil Co. (2151622)**: two source-attachment gaps, no rewriting needed.
  rule[0]'s enumeration ("pain and suffering, lost wages, and property damage") was
  unsupported by its two cited passages — the exact disposition passage stating all three
  already existed in the candidate, cited under holding[0]; added it here too. issue[0]'s
  "survival statute" framing was unsupported by its one cited passage (which quotes the
  Wrongful Death Act) — added the passage already cited under facts[1] that names the
  survival statute. No stale IDs (content_hash differed from the stored candidate's, but
  every citation still resolved against the fresh packet).

**Skipped, then reconsidered — do NOT treat as blocked:**
Beacon Theatres v. Westover (105889), State v. Forrest (1239832), and Selders v. Armentrout
(1229086) all showed the same symptom: the fetched source packet contains the full opinion
text twice (a caption/opening-line reprint partway through the passage list — around
ordinal 140-230 depending on the case — with a few header lines at the seam mislabeled by
`opinion_part`). I read this as the "opinion text is defective" case in the runbook's step
5 and reported all three for human attention without regenerating — but the Wallace v.
Rosen (2079379) and Schlagenhauf v. Holder (106937) entries in the pass immediately above
already document this exact shape ("full majority opinion text twice... every passage had
two valid IDs to choose from; picked the earlier-ordinal occurrence for consistency.
Preflight passed regardless... so this didn't block the fix"). Boundary preflight
(`ok: true`, no errors/warnings) agreed for all three of mine too. This is the known
duplicate-block pattern, not a source defect — it should be triaged normally next session
(pick the earlier-ordinal occurrence when remapping, same as the two precedents). I'd
already spent the 3-regeneration budget on the cases above by the time I found the
precedent, so these three are untouched in the queue — not regenerated, and shouldn't count
against a future session's limit since no candidate was written for any of them.
Files touched: none (three `candidate-save` writes to the DB only; no code changes).
Deployment: none.
Commit: N/A — documentation-only addition here (plus whatever else was already
staged/modified in the working tree at session start).

### Source-brief yield: packet fix, repair-first burner, and the sonnet/opus experiment
Owner: Claude
Status: completed 2026-08-12
Files: `backend/opinion_passages.py`, `backend/test_opinion_passages.py`,
`citator/source_rebuild_burn.sh`, `citator/sunday_briefs.py`
Summary: pointing the rebuild burner at Con Law (casebook 1499) exposed the pipeline's
yield problem. Sonnet fresh generation went 0/8 at semantic review; opus went 4/12 (33%).
Reading all ten early rejection notes showed three failure classes: (1) claims citing
passages with no propositional content — star-page markers ("*518") and bare citation
stubs — a supply defect, not a drafting one; (2) accurate-but-unsourced details (training
knowledge leaking past source discipline); (3) genuine misreadings, the rarest (~3/10).
Every rejected brief failed on 1-3 claims of ~16, with the rest supported, often verbatim.
Fixes shipped, in priority order:
- Passage builder (format v9→v10): star pagination stripped; citation-only sentences fold
  into the sentence they support; section headings dropped; "Res." protected from splits.
  After the fix, rejection notes contain no contentless-passage complaints — remaining
  failures are claim-level re-sourcing, which triage repairs.
- Burner cycles are now triage → gen → review. Repair-with-notes approves at ~2x fresh
  generation (9/15 vs 90/282 observed), so it runs first. GEN_MODEL env picks the
  generation model (default sonnet; the Sunday cron is unchanged). PRIORITY_CASEBOOK_ID
  env aims a one-off run at a casebook without touching the cron.
- Today's 16 rejections sit in the triage queue with precise reviewer notes; the next
  burner run starts by repairing them.
Worth knowing: candidate-save validates against persisted passages by content hash, so a
format-version bump never strands an in-flight generation session. One-line dissent
notices embedded in a lead opinion are part-tagged "opinion", not "dissent" — a dissent
claim citing one fails validation (opus hit this on Poe and re-sourced around it).
Next: decide whether Con Law generation stays on GEN_MODEL=opus (33% vs 0% is decisive on
n=20, but post-fix sonnet has not been measured — cycle 4 on fixed packets went 2/3);
whether to raise Sunday cycles to clear the 1499 backlog; and whether the semantic-review
runbook should let the reviewer approve-with-edits for the accurate-but-unsourced class
instead of round-tripping through triage.
Deployment: none required — the passage builder ships with the next backend deploy; the
burner and queue changes are host-local.
Commit: `f4851c2` and `ebfc742`

### Constitutional Law cases grouped by doctrine
Owner: Claude
Status: completed 2026-08-12
Files: `scripts/classify_conlaw_topics.py`
Summary: textbook 1499 rendered as one flat alphabetical list of 299 cases because `chapter`
was null on every row. Rather than copy the book's chapter structure — the selection and
arrangement is the part of a casebook most plausibly protected — the cases are grouped under
Tortwell's own 13-topic doctrinal taxonomy, classified from each case's own holding using only
the case name, citation, and decision date already in our database. `sort_order` is topic rank
times 1000 plus alphabetical position, so groups render in teaching order (structure of
government before individual rights) and each group reads alphabetically.
`TextbookDetailClient.tsx` already groups when any case has a `chapter`, so no frontend change
was needed. `legal_concepts` now holds 2-4 doctrine tags per case; nothing renders them yet.
Production verified: 299/299 rows have a chapter, concept tags, and a distinct sort order, and
the live API serves the 13 groups in order.
Three things the next assistant should know about classifying with a model at this size: the
model twice answered a 25-case batch with a single entry (the script halves the batch and
retries), it title-cases connecting words past a schema enum — "Freedom Of Speech And The
Press" — which silently dropped 11 cases from the first plan until topics were canonicalized,
and `cases.id` is `text`, so coercing case IDs to int breaks the cache-reuse check. The run
caches its classification to JSON, so re-grouping under a revised taxonomy costs an `--apply`
and no tokens.
Next: the taxonomy is worth a second look — Freedom of Speech and the Press holds 70 cases (a
quarter of the book) and could split content-based/content-neutral, and Other Individual Rights
holds 5 that are really Second Amendment plus incorporation. Separately, 210 of the 299 still
have no AI brief; the list is navigable now, so that backlog is the bigger gap.
Deployment: production data operation; no redeploy needed (the textbook detail cache turned
over on its own TTL).
Commit: `3ab5407`

### Chemerinsky Constitutional Law 7th edition case-list verification
Owner: Sol
Status: completed 2026-08-11
Files: `scripts/sync_chemerinsky_casebook.py`
Summary: textbook 1499's Quimbee-derived mapping was replaced atomically with the 299
principal cases marked in the licensed 2024 book's table of cases. The private table and
page references were not copied into the repository or database. Four absent Supreme Court
case rows (Biden, Counterman, Horne, and Ex parte McCardle) were imported, and three existing
stubs (Janus, Bruen, and Slaughter-House) were hydrated through the canonical CourtListener
assembler. CFPB v. CFSA and Lindke v. Freed were removed from this textbook mapping because
they postdate the edition; their case rows were retained. The idempotent dry run resolves
299/299 with no removals, and the live page renders 299 flat cases.
Deployment: production data operation; frontend cache cleared by successful redeploy
`943ad1e5-b982-4bcb-bbed-4da6b029630c` of existing commit `893424a`.
Commit: not committed

### Mills RECAP opinion import
Owner: Sol
Status: completed 2026-08-03
Files: `scripts/import_mills_case.py`
Summary: Mills v. City of St. Louis is RECAP-only, so its bespoke importer originally stored raw
PDF text without canonical opinion-part metadata. Strict source preflight correctly rejected the
unmarked, non-CourtListener-ID source before spending. The importer now declares document 37 as
one verified majority writing and persists its matching content hash; the existing production row
was repaired idempotently. Exact production preflight found 186 majority passages with no errors,
and retrying generation created source-linked summary `1188` for $0.10455.
Next: none.
Deployment: n/a (offline data operation)
Commit: not committed

### Systemic CourtListener opinion assembly and preflight
Owner: Sol
Status: shipped 2026-07-21
Files: `backend/courtlistener_opinions.py`, `backend/opinion_passages.py`,
`backend/structured_briefs.py`, CourtListener/source-preflight hunks in `backend/main.py`,
`backend/webhooks.py`, `citator/{prefetch_opinions_local,upload_opinions_s3,sunday_briefs,
opinion_boundary_preflight}.py`, and focused tests
Summary: supersedes the shipped Chevron-only parser fix with canonical typed assembly across all
ingestion paths, strict pre-provider source checks, complete-cluster refusal on partial API fetches,
retryable Sunday preflight, durable webhook stub persistence, and compare-and-swap source repair.
Real API probes for Chevron (`108406`), Giles (`145781`), Stephens (`660220`), and cluster `7101`
all pass; full local Parquet probes pass, including cluster `7101` at 271 majority / 1 dissent
after fixing its inline colon-terminated circuit dissent heading. Exact staged snapshot: 131 passed;
the full working tree (including separate billing work) passes 161.
Focused review reports no remaining high/medium blocker.
Next: none. Legacy malformed stored packets remain blocked by preflight and repair from canonical
CourtListener data when generation is next requested; deployment verification made no paid AI call.
Deployment: backend `39fb3781-bbcf-438e-a412-0c715ecf4386`; frontend
`2d3ef5c1-a71f-4655-b711-d8b30b8f89e7` (both successful)
Commit: `06f137c`
Review (Claude, 2026-07-21): concurs — architecture is right (boundaries as ingestion metadata
via one canonical assembler; free preflight before paid generation; majority-only sourcing for
facts/issue/holding/rule). Independently verified: 157 backend tests pass; `cases.content_hash`
exists in prod (migration 030); live-API probe of 8 random stub clusters assembled 8/8.
Two watch items, neither blocking: (1) complete-cluster refusal treats a legitimately text-less
sub-opinion (empty remittitur/addendum record — normal data, not a failed fetch) like a partial
fetch and refuses the whole cluster — if "opinion unavailable" reports rise, require completeness
only for PRIMARY_TYPES; (2) the combined-record fallback can still wholesale-tag an embedded
dissent as majority when its heading format is unrecognized — residual failure class to expect
in future reports; preflight/validation contain it.

Follow-up fix (Claude, 2026-07-21, `efcdb61`): Sage hit "dissent[N] cites non-dissent passage"
on Chevron itself (404 U.S. 97) with the new pipeline live. Cause: the source introduces
Douglas's partial dissent with only "Mr. Justice Douglas." — no disposition word anywhere, and
cluster metadata carries none (judges list only) — so the bare-name-after-"It is so ordered."
heuristic's "concurrence" guess forced validation to reject the model's correct dissent claims.
Fix: such writings are now labeled `separate` (unknown disposition); majority sections still
cannot cite them, dissent claims may characterize them from content, the prompt explains the
tag, and preflight counts them as separate-opinion material. Passage format v6. This is not the
rejected "relax validation when the model disagrees with the parser" — there is nothing in the
source to parse; `separate` is the honest ingestion-time label.
Third fix (Claude, 2026-07-23, `5e286f4`): strict preflight refused State v. Mosley
(`10089542`, R.I. 2024) — a verified single-opinion case (one canonical combined sub-opinion,
no separate writings) — with "no verifiable opinion-part boundaries". Single-opinion cases have
no boundaries to find; demanding them refuses the most common shape in the catalog. Fixes:
(1) "Justice Goldberg, for the Court." recognized as an explicit majority heading (R.I. and
similar states); (2) a source whose canonical manifest declares exactly one sub-opinion counts
as a verified single writing under require_explicit (warning, not error). Unmarked legacy
all-opinion sources still fail strict preflight. Passage format v7. Residual accepted risk:
a lone combined record with an embedded separate writing in an unparseable heading format now
passes as all-majority — same class as watch item 2, contained by the review gate.
Third fix (Claude, 2026-07-23, `5e286f4`): strict preflight refused State v. Mosley
(`10089542`, R.I. 2024) — a verified single-opinion case (one canonical combined sub-opinion,
no separate writings) — with "no verifiable opinion-part boundaries". Single-opinion cases have
no boundaries to find; demanding them refuses the most common shape in the catalog. Fixes:
(1) "Justice Goldberg, for the Court." recognized as an explicit majority heading (R.I. and
similar states); (2) a source whose canonical manifest declares exactly one sub-opinion counts
as a verified single writing under require_explicit (warning, not error). Unmarked legacy
all-opinion sources still fail strict preflight. Passage format v7. Residual accepted risk:
a lone combined record with an embedded separate writing in an unparseable heading format now
passes as all-majority — same class as watch item 2, contained by the review gate.
Both follow-ups shipped (`c2756e1`, approved by Sage 2026-07-21): (1) generation-shaped probe
in `structured_briefs.generation_shape_report`, wired into `opinion_boundary_preflight` —
synthetic label-trusting candidate for hard errors, plus a >25%-uncitable-material warning
(the pre-fix Chevron signature, since a label-trusting probe alone can't see mislabels);
(2) one retry per CourtListener request in `fetch_courtlistener_document` so a transient
failure no longer refuses the whole cluster. The complete-cluster strictness (watch item 1)
was deliberately NOT loosened — no evidence it bites; revisit only if "opinion unavailable"
reports rise.
Fourth fix (Claude, 2026-07-26, `22b28ba`): Sage hit "dissent[N] cites non-dissent passage" ×4
on Smith v. Arizona (`10600062`, 602 U.S. 779). Unlike Chevron this was not a mislabel — the
parser was right. The case has no dissent: Kagan for the Court, Thomas and Gorsuch concurring
in part, Alito concurring in the judgment only (joined by Roberts). Alito rejects the
majority's Confrontation Clause reasoning, so it reads like a dissent and the model filed four
claims about it under `dissent` citing concurrence passages. The corrective retry cannot help
here — feeding the same error back does not change what the concurrence says. Cause: whether a
dissent exists is a deterministic fact about the packet's tags, but the prompt only said "use
an empty dissent array if the packet contains no dissent" and left the model to infer it from
tone. Fixes: (1) `build_structured_prompt` now states the packet inventory outright ("This
packet contains no (dissent) or (separate) passages, so "dissent" must be exactly []") and in
every case bars describing a concurrence under dissent; (2) `drop_uncitable_dissent`, a
pre-validation repair beside `repair_unknown_sources` — when a packet has no dissent/separate
material, dissent claims are dropped rather than 502ing. Deliberately narrow: where a real
dissent exists a miscite stays an error, since that is the near-miss the retry can fix. No
passage-format change; segmentation was never wrong. The `c2756e1` uncitable-material warning
predicted this on the live packet (789/2402, 33% concurrence) but it is a warning and is not
wired into the on-demand endpoint — worth reconsidering. Verified post-deploy: regeneration
returns 200, dissent `[]`, 648 words, Alito's disagreement captured in unsourced `significance`
where it belongs. Deployment: backend `af1faaa5-deb4-4bb3-96cb-d3e59957f103` (SUCCESS).
Fifth fix (Claude, 2026-07-26, `cd68b6c`): found while fixing the above — Smith is stored as a
U.S. Reports preliminary print, hard-wrapped at the typesetter's column, so blocks were
line-sized not sentence-sized: 2,655 passages for 95k chars (~36 each), citable as "To ad-" and
"Page Proof Pending Publication". `prepare_opinion_text` now rejoins wrapped lines,
de-hyphenates across the break, and drops page furniture. Smith 2,655→1,152 (median 32→42
chars, real sentences of 120-200 where there were clause fragments); State v. Mosley
2,267→711 (median 38→93). Gated on detection (40+ lines, median width ≤100, >50% of lines not
ending a sentence) because rejoining is wrong for the paragraph-per-line shape that dominates
the catalog: across a 14-case corpus (the `SOURCE_PILOT_IDS` set plus the case behind each
earlier boundary fix) 12/14 are byte-identical, only the two typeset sources change.
Three traps, all caught by measuring rather than reasoning: (1) a page break lands mid-sentence
as often as between paragraphs, so most form-feed lines in Mosley carry real content
("\fmale opened the barbershop door") — furniture is identified by content and alignment,
never by the break itself, since deleting body text is worse than the fragmentation; (2) the
blank lines padding a page break are typography, and letting them end a block stranded the
interrupted clause ("It re-"); (3) a centered section label glued onto the heading below it
("OPINION Justice Goldberg, for the Court.") hid it from `detect_opinion_marker` and Mosley
silently lost its majority boundary — visible only because the corpus diff reported part counts.
Passage format v8. Per the versioning contract, existing briefs keep their persisted v7 passage
sets (verified live: Smith still serves 2,655 passages, links intact); only new generations
re-segment. Smith and Mosley both have pre-fix cached briefs, so seeing v8 on either requires
clearing their `ai_summaries`/`structured_summary_candidates` rows — not done, Sage's call.
Accepted residuals: a compound broken at its own hyphen ("cross-"/"examine") loses it; footnote
text interleaved at a page foot still splits two Smith passages; one watermark interleaved
word-by-word into a body line by the upstream extractor survives.

### Sentence splitting fragmented citations (fixed 2026-07-26, `601a880`)
Owner: Claude
Status: shipped; deployed `f1fd9f9e`
Files: `backend/opinion_passages.py` (`split_sentences`, `CITATION_ABBREVIATIONS`, `SPACED_ELLIPSIS_RE`)
Summary: found while fixing `cd68b6c`, and the larger of the two problems — it affected the
whole catalog, not just typeset sources. `split_sentences` broke on any `[.!?]` + whitespace,
so citations shattered: "Crawford v. Washington, 541 U. S. 36, 53-54 (2004)." became four
passages — "Crawford v.", "Washington, 541 U.", "S.", "36, 53-54 (2004)." A source-linked brief
could pin a claim to a passage whose entire text was "S.", which occurred 1,127 times in the
14-case corpus. **9,438 of 20,024 passages (47%) contained no prose word at all; now 937 of
9,891 (9%).** Median passage length 17-138 chars → 101-195 (Erie 19→107, Roe 17→101,
Griswold 18→168). Three causes: (1) reporters print volume/series abbreviations spaced
("541 U. S. 36") so every single-letter token split — a lone letter before a period is an
initial or reporter abbreviation, never a word; (2) multi-letter legal abbreviations (Rev.,
Stat., Ann., Supp., No., Cir.) plus state abbreviations for the "Ariz. Rev. Stat. Ann."
statutory form; (3) spaced ellipses in quoted constitutional text ("the right . . . to be
confronted") read as three boundaries — 462 passages whose entire text was ".".
Part sets unchanged for all 14 corpus cases; preflight verdicts unchanged (Marbury still fails
strict preflight as an unmarked legacy all-opinion source, as before and unrelated).
Passage format v9. Where the rule is uncertain it errs toward protecting, because the failure
modes are asymmetric: an unprotected abbreviation fragments a citation into junk passages,
while an over-protected one merely joins two sentences into a passage that is still coherent
prose. Known gap left alone: a sentence ending in a closing quote ('it is so." We agree.')
never splits, since the boundary regex looks only at the character before the whitespace —
that over-merges rather than fragments, and adding it raised the corpus fragment rate.

### Re-segmentation reaches cached briefs only on force (mechanism shipped `91e911f`)
Owner: Sage (the spend decision); mechanism done
Status: force parameter shipped and deployed `15f7058a`; no backfill run
Summary: `cd68b6c` and `601a880` both bump `PASSAGE_FORMAT_VERSION`, and per the versioning
contract existing briefs keep their persisted passage sets — verified live (Smith still serves
its 2,655 v7 passages, zero dangling links). So existing briefs keep their old, fragmented
source links until regenerated, and `summarize_case` returned the cache unconditionally.
`POST /api/v1/cases/{id}/summarize?force=true` now bypasses the cache. Two things turned out
better than the earlier writeup assumed: regeneration needs **no deletion** — both the
`ai_summaries` and `structured_summary_candidates` writes are `ON CONFLICT DO UPDATE` upserts
inside one transaction, so a forced run replaces the brief in place and a failed run leaves the
existing one untouched. And the bypass is `require_admin`-gated, because it spends from the
shared Anthropic pool and would otherwise be a way to drain it by re-requesting one case in a
loop. Verified on production: force with no auth and force with a bad token both 401; a normal
cached read still 200s.
Not run, and deliberately: a catalog backfill is ~501 briefs × $0.034 ≈ **$17**, against
**$0.00 donations received** and the ~$23/month Sage already covers himself (`/transparency`,
2026-07-26). That is a spending decision, not a cleanup. Cheapest worthwhile subset is the two
known typeset cases, Smith `10600062` and Mosley `10089542`, ~$0.07 total — needs Sage's admin
JWT, which the agent does not have and should not.

### Backend saturation under Applebot crawl (resolved 2026-07-19)
Owner: Claude
Status: resolved; temporary crawl logging still in place (remove later)
Files: `backend/Dockerfile` (`4438261`), `frontend/middleware.ts` (`c4f7e47`)
Summary: for 6+ hours on 2026-07-19 the backend pegged one CPU and all requests queued
(30–280s responses, widespread 499 client aborts; Sage's Ask AI timed out). Cause: Applebot
(17.x.x.x, ~1 page/sec, with Googlebot and Meta alongside) sweeping the 219k-case catalog —
each SSR pageview fires ~6 backend calls with S3 opinion reads and 100–300KB payloads — while
uvicorn ran a single worker (hard one-core ceiling; Postgres and frontend were idle). Fix:
`--workers 3` in the Dockerfile CMD. Verified safe first: deployed billing/reservation state
is DB-backed, module-level state is only read-through TTL caches (per-worker duplication
harmless), 3 workers × pool max 10 = 30 connections vs Postgres max_connections=100. After
deploy: same crawl load, responses 4ms–1.5s, zero 499s. Crawler identified via temporary
`[crawl]` logging in frontend middleware — remove that block once no longer useful.
Not done (options if load returns): robots.txt `Crawl-delay` for Applebot (it honors
robots.txt; but this crawl is wanted — Apple search/AI surfacing); Next ISR caching of case
pages so a pageview stops costing six live API calls (the structural fix).
Commits: `4438261` (workers), `c4f7e47` (crawl logging)

### Lower-court dissent headings in passage segmentation
Owner: Claude
Status: shipped 2026-07-19 (`e3dc44a`); backend auto-deploying from main
Files: `backend/opinion_passages.py`, `backend/test_opinion_passages.py`
Summary: Stephens v. Miller (`660220`, 13 F.3d 998, 7th Cir. en banc) failed on-demand
generation with "dissent[N] cites non-dissent passage" ×4. Root cause: `detect_opinion_marker`
only knew bracketed CourtListener markers and SCOTUS "Justice X, dissenting." prose, so
circuit-style headings ("RIPPLE, Circuit Judge, dissenting." — all-caps surname, Judge not
Justice) were invisible and all 1,884 passages were tagged `opinion`; the model's correct
dissent claims then failed validation against wrong labels. This was the remaining format
family after Sol's 7/13–14 fixes (`c2a8959` SCOTUS headings, `6c6fd1a` HTML sections) — all
19 July-12/13 part-mismatch failures already have candidates; this class covers the F.2d/F.3d
and state-court cases that dominate the remaining backlog. Fix: recognize all-caps-author
headings (Judge/Justice titles, joined-by clauses, leading paragraph numbers, "(dissenting)"
parentheticals, "in part" forms; partial dissents tag as dissent). False-positive guards:
participles only (vote lines like "ANDREWS, J., dissents ... JJ., concur" use finite verbs),
all-caps names only (citation strings are mixed-case), strict end-of-sentence tail.
`PASSAGE_FORMAT_VERSION` bumped 2→3 per the `bfef03e` versioning contract — stored candidates
keep their own persisted passage sets; only new generations use the new segmentation.
Verified against production Stephens text: parts now majority=401/concurrence=359/dissent=1110
(that content is also messy — sub-opinions concatenated out of order plus a numbered duplicate
copy — worth a look if Stephens briefs read oddly). 134 backend tests pass.
Next: Sage retries the Stephens brief from the case page after deploy; watch
`structured_summary_failures` for residual "cites non-dissent" errors in the next batch run.
Commit: `e3dc44a`

### Long source-linked brief generation recovery
Owner: Sol
Status: shipped 2026-07-18
Files: `frontend/app/case/[id]/CaseDetailClient.tsx`
Summary: Palmer v. Hoffman (`103772`, `318 U.S. 109`) exposed Railway dropping the
synchronous generation response: the first request returned 502 at exactly 15 seconds and
later browser disconnects appeared as Firefox `Load failed`, while the backend continued and
saved valid summaries. The case page now treats body-less 5xx and fetch/network failures as a
possibly-running generation and polls the uncached summary endpoint for up to 90 seconds. It
waits specifically for a structured candidate when upgrading a legacy brief, so it cannot
mistake the old brief for the requested result. This also discourages duplicate clicks and
duplicate Opus spend while the first request is still running.
Verification: 8 frontend tests, TypeScript, production build, cached Palmer summary readback;
frontend deployment `dc949116-940b-4ebe-8bdd-df7ff13a9992` successful.
Next: none. A proper asynchronous generation-job API would be cleaner long-term, but polling
is the smallest fix compatible with the current endpoint and Railway behavior.
Commit: `2566c27`

### CourtListener webhook authentication
Owner: Sol (IP-allowlist design), Claude (Railway header fix 2026-07-16)
Status: fixed and deployed 2026-07-16; awaiting CourtListener's next automatic retry
Files: `backend/webhook_security.py`, `backend/webhooks.py`,
`backend/test_webhook_security.py`, `DEPLOYMENT.md`
Summary: production returned 401 for Search Alert deliveries because the July 10 security
change required an `X-Webhook-Secret` header that CourtListener explicitly does not support.
Sol's 2026-07-15 fix (`58c9790`) switched to verifying CourtListener's two documented static
sender IPs, but its nearest-public-`X-Forwarded-For` walk still 401'd every delivery: Railway
appends its own *public* edge-proxy hop to `X-Forwarded-For` (observed:
`'<client-ip>, 152.233.40.1'`), so the walk always found Railway's edge, never CourtListener.
Fix (`fee041e`): read Railway's `X-Real-IP` header as the authoritative source — verified live
that Railway overwrites a client-forged `X-Real-IP` with the true address, so it is
spoof-proof — keeping the `X-Forwarded-For` walk only as a non-Railway fallback, and log
rejected sources (search deploy logs for "Rejected webhook"). 9 webhook-security tests pass;
deployment `084eebef-cd08-46d7-8a76-ef6913404191` succeeded; forged-header and plain probes
both correctly 401 with correct source attribution in logs.
Next: confirm CourtListener's retry returns 2xx in Railway HTTP logs (failure count was 6 of 8
as of 03:51 UTC 2026-07-16; if it reaches 8 the webhook is disabled and must be re-enabled at
courtlistener.com/profile/webhooks — a manual test event from that panel confirms faster).
Deployment: production backend successful; provider delivery retry not yet observed
Commit: `fee041e`

### The Criminal Law Outline (canonical outline #3)
Owner: Claude
Status: shipped 2026-07-15 (v1 live: 18 sections / 45 sources; 70 key cases, 45 linked)
Files: `frontend/content/outlines/criminal-law.json`, `frontend/app/sitemap.ts`
Summary: authored from Sage's Spring 2026 notes (Professor Cole, Dressler casebook) — the
Notion master outline (24 units, distilled by three parallel agents from a 90KB fetch split
into thirds) plus his compiled "Criminal Law MAIN OUTLINE.pdf" (pulled from his MacBook),
whose Weeks 13-14 supplied the final-weeks units Notion never got: attempt's act tests and
impossibility, conspiracy's full doctrine, entrapment, and the entire accomplice-liability
section. Structure follows Cole's exam decision tree: building blocks (punishment, actus
reus, causation, mens rea, strict liability, mistakes) → homicide (PA model, voluntary
manslaughter's three frameworks, felony murder's four limitations) → defenses
(justification/excuse taxonomy, self-defense/BWS, retreat incl. ORC 2901.09, necessity,
duress, insanity/competency with all five tests) → inchoate (attempt, conspiracy,
accomplice). English staples link via manually-added records (manual-dudley-stephens,
manual-cunningham); 25 cases unlinked (crim state cases are spotty in CourtListener).
Known gap, deliberate: attempt abandonment/renunciation — absent from all of Sage's
materials, likely never covered in class. Verified live (200, correct title); 43/44 linked
cases entered the outline-priority rebuild queue.
Commits: c1c2112 (v1), 17efa2a (final-weeks fill)

### The Torts Outline (canonical outline #2) + Civ Pro v6
Owner: Claude
Status: shipped 2026-07-15; **v2 live same day** — Sage compiled his professor's complete
slide deck into a PDF (pulled from his MacBook via `scp macbook:...`) and asked for a
coverage check. Per the standing bright line the deck was used as a topic checklist ONLY —
no slide expression in the outline. Result: 14 of ~16 course units were already covered;
v2 (commit 063e017) adds a new Immunities section (id 17, after Defenses — from Sage's
Oct 29 notes + Reading Assignment 16: Freehe, Zellmer, Abernathy, Laird v. Nelms
(unlinked), Deuser, Lorman, Riss, DeLong), plus notes-sourced gap fills
(proximate-cause policy limits, seatbelt non-use, joint enterprise/bailments/negligent
entrustment, premises details, damages valuation, warning-defect satellites) and two
concepts written from general black-letter doctrine because his notes lack them
(professional malpractice standard, informed consent — flagged to Sage for possible
removal). v2 imported to production with Sage's explicit per-run authorization; live
totals 17 sections / 95 sources, 118 key cases / 95 linked. Gap report retained at the
session scratchpad (torts-gap-report.md).
Files: `frontend/content/outlines/torts.json`, `frontend/content/outlines/civil-procedure.json`,
`frontend/app/study/outlines/page.tsx`, `frontend/app/sitemap.ts`
Summary: Civ Pro reached v6 (Filing & Service and Appeal enriched from Sage's Notion notes;
Enforcement deliberately left thin — he has no notes on it, and the fidelity-first rule bars
inventing doctrine). The Torts Outline shipped as canonical outline #2: 16 doctrine sections
authored from Sage's Fall 2025 Torts notes (three parallel distillation agents produced
fidelity-first digests in the session scratchpad), 110 key cases with 88 linked to case pages
(court + date verified against production search; English cases and a handful missing from
CourtListener — Vaughan, Blyth, Byrne, Rylands, both Wagon Mounds, Cordas, Lyon v. Carey,
Indiana Harbor's 7th Cir. opinion, Erie v. Amazon, Montgomery Ward v. Anderson, Schott —
included unlinked). The study landing page now lists canonical outlines dynamically from
`GET /api/v1/canonical-outlines` (static Civ Pro fallback if the fetch fails), replacing the
hardcoded card whose section counts had gone stale; sitemap includes `/outlines/torts`.
Verification: 97 backend tests, 8 frontend tests, tsc typecheck, importer dry runs
(Civ Pro 15 sections / 158 sources; Torts 16 sections / 88 sources); both imported to
production and smoke-tested (list endpoint shows civil-procedure v6 + torts v1;
tortwell.com/outlines/torts returns 200 with correct title). Section-level votes/comments
work on Torts automatically — same canonical tables and UI.
Next: Crim Law outline (Sage's spring notes), then Evidence (target ~July 31). Torts
follow-ups if desired: link stragglers if the cases land in the DB later; premises-liability
section has only Rowland linked (his notes attribute little there).
Commit: 45eaf45 (Torts + landing page), e6b1a57 (Civ Pro v6)

### Canonical outlines v1 (Civ Pro)
Owner: Sol
Status: shipped
Files: `migrations/038_canonical_outlines.sql`, `scripts/import_canonical_outline.py`,
`scripts/privatize_outline_uploads.py`, `backend/main.py`,
`frontend/content/outlines/civil-procedure.json`, `frontend/app/outlines/[slug]/`,
`frontend/app/study/outlines/`, `frontend/app/outline/[id]/`
Summary: the existing eleven-stage Civ Pro timeline is now the single version-controlled
content source and validates to 69 case/rule/statute sources. A dedicated relational schema
separates stable section identity from immutable revision content and attaches signed-in
votes/comments to stable sections. `/outlines/civil-procedure` is an SSR public outline with
honey source links, section navigation, feedback totals, voting, and comments. The study
landing page now leads with the canonical outline and keeps uploads in a separate private
area; new and existing uploads are forced private, authenticated downloads work, and AI
conversation access now checks both conversation and outline ownership.
Verification: 93 backend/citator tests, 8 frontend tests, frontend typecheck, production
build, importer dry run (11 sections / 69 sources), and a two-pass code review all pass.
Production preparation (2026-07-14): migration 038 applied successfully; both legacy
outlines are private, database-backed files with zero remote public URLs to revoke; Civ Pro
version 1 imported with 11 active sections and 69 sources.
Production smoke test: backend health and canonical API pass with 11 sections / 69 sources;
anonymous SSR, study landing, source links, public comment reads, and auth rejection for
anonymous voting pass. Chunked sitemap routing passes; this commit fixes an existing strict
number comparison that omitted static pages from chunk 0 under Next.js 16 string route IDs.
Next: optional signed-in manual smoke test for voting, comments, private upload/download,
and AI study; these authenticated flows are covered by local automated checks but were not
exercised against a real production user session.
Deployment: backend and frontend canonical release deployed successfully; sitemap fix in
this commit
Commit: `cdaa964`

Version 2 — the jurisdictional half (Claude, 2026-07-14): Sage observed the shipped
outline was effectively his Civ Pro II course (the litigation process); the missing half
was Civ Pro I (Fed Juris). Four doctrine sections now lead the outline — Subject Matter
Jurisdiction, Personal Jurisdiction, Venue/Transfer/FNC, and Erie — authored from Sage's
own Notion course outlines (his "OUTLINE for X - COMPLETE" pages, the Civ Pro Triage
exam-flow doc, and the professor's four-column Erie chart), fetched via the new Notion MCP
connection. Design: new sections carry `kind: 'doctrine'` and ids 12-15, placed FIRST in
the sections array — process stages keep ids 1-11 so their `stage-NN` section_keys (and
live votes/comments) are untouched, and `timelineData.ts` filters doctrine sections out of
the /civpro chronological timeline. 45 doctrine case references were resolved to on-site
case IDs against the production search API; five search top-hits were lower-court
decisions with reversed captions (e.g. the 2d Cir. York) and were corrected to the SCOTUS
opinions by checking court + date — do the same when resolving future case links.
Three cases were added beyond Sage's notes as standard attributions of rules his notes
state anonymously (Gibbs for "common nucleus," Kroger for §1367(b), Van Dusen for
§1404's old-forum-law rule). Gibbs is since VERIFIED against Sage's compiled course
slides ("the Gibbs Standard (SCNOF Test)"); the slides also confirm St. Paul Mercury as
the named AIC legal-certainty test. Kroger and Van Dusen remain unverified — check the
casebook. Not in the DB (render unlinked): Price v. CTB, Atlantic Marine, SCOTUS
St. Paul Mercury.
Verified: typecheck, production build, 5/5 importer tests (one new: doctrine sections
link their case canon), version 2 imported to production (15 sections / 130 sources),
live page and timeline checked.
Follow-ups: trim Pre-Filing's now-redundant one-line §1331/§1332/venue entries; consider
importing Atlantic Marine and the SCOTUS St. Paul Mercury; Erie's modern refinements
(Gasperini, Semtek, Shady Grove) are absent because Sage's course notes don't cover them —
add only with a real source to cite.
Version 3 — Joinder upgrade (Claude, 2026-07-14, same day): the outline's thinnest
section (one concept, three cases) is now a full complex-joinder treatment — the
three-questions framework, compulsory/permissive counterclaims with their different SMJ
paths, crossclaims + Rule 18's open-door, Rule 19 three-step, Rule 24 intervention,
Rule 22 vs. statutory interpleader, and the two §1367(b) take-aways. Sage's 172-page
compiled slide document (`/mnt/d/Downloads/CONTENT FROM SLIDES.pdf`) served as the
coverage checklist; all prose is original (professor-materials copyright caution — the
doctrine isn't copyrightable, the professor's expression is; keep this discipline for
future cycles). Temple v. Synthes was added as the named attribution for the
joint-tortfeasor rule the slides state anonymously — on the casebook-check list with
Kroger and Van Dusen. King v. Blanton now links via its `manual-king-v-blanton` case ID.
Version 3 imported to production (15 sections / 134 sources) and verified live.
Still banked from the slide doc: the Mullane notice framework for Filing & Service.

Version 4 — Preclusion upgrade (Claude, 2026-07-14, same night): the outline's only
case-less section now carries its full canon (10/10 linked: Hansberry, Carter v. Hinkle,
Blonder-Tongue, Parklane, Frier, Martin v. Wilks, River Park, Semtek, Taylor v. Sturgell,
Lucky Brand) — authored from Sage's OWN 240-page Civ Pro II outline
(`/mnt/d/Downloads/MAIN OUTLINE CIV PRO II.pdf`; his authored work, so publishable-grade
source, unlike the professor-slide compilation). Adds choice-of-preclusion-law
(Art. IV/§1738/Semtek), the seven-step claim checklist, §24(2)'s six transactional
factors vs. same-evidence/primary-rights, counterclaim preclusion as rule preclusion,
Taylor's six exceptions, issue-preclusion elements (burden-of-proof transfer rule,
general-verdict problem, essential-as-factual-dicta), and Blonder-Tongue/Parklane
nonmutual preclusion. Semtek's inclusion also closes part of the flagged Erie-modern
gap. Live-verified after import (note: `/outlines/[slug]` has `revalidate: 300` — the
page can serve stale content for up to 5 minutes after an import; poll before declaring
a publish broken). Version 4 = 15 sections / 146 sources. Commit: `6700be0`.
Version 5 — Trial & Post-Trial enrichment (Claude, 2026-07-14, same night, commit
`5e3089a`): surgical rather than rewrite — these sections were already solid. Added
jury-control mechanisms (Rule 51 / Rule 49 verdict-form consistency options, with the
cross-link to issue preclusion's general-verdict problem), the JMOL evidence-viewing
rules, Trivedi v. Cooper (50(a)-waiver trap; remittitur with intertwined liability and
damages — links via manual id `lexis-trivedi-v-cooper-1996`), Wilson v. Vermont
Castings (internal vs. extraneous juror conduct under 606(b)), and the Piesco
credibility principle; linked the previously unlinked Dairy Queen, J.F. Edwards, Davey,
and Neely. Outline-wide: 83/103 key cases linked. Remaining from the CP2 outline:
a fuller Appeal treatment (currently 2 cases) — the last thin spot.

Multi-course roadmap (Sage, 2026-07-14): the same authoring pipeline extends to
**Criminal Law and Torts** (his 1L fall notes) and **Evidence** (in progress now; his
final is July 31) — explicitly NOT tonight; wait for Sage to start each. The pipeline
that worked for Civ Pro: pull Sage's own Notion course notes (Law School Hub →
semester → course; look for his "OUTLINE for X - COMPLETE" pages) via the Notion MCP →
distill faithfully → resolve case names against the production search API (beware
lower-court reversed-caption top hits — verify court + date) → author sections in the
canonical JSON → validate via importer tests → Sage approves the production import
per-run.
Deployment: v2 and v3 production imports complete 2026-07-14; frontend auto-deploys
from `main`
Commits: `10bf926` (v2), `8aa8f0a` (v3)

### Source-linked brief opinion-source repairs
Owner: Sol
Status: shipped
Files: `backend/main.py`, `backend/opinion_passages.py`, `backend/structured_briefs.py`,
`backend/test_opinion_passages.py`, `backend/test_structured_briefs.py`
Summary: two production generation failures exposed different source-shape defects. Mattox
v. United States (156 U.S. 237, case 94091) stores flattened reporter text whose old-style
`Mr. Justice Shiras dissenting` heading lacked the comma and block boundary expected by the
passage parser; inline single-sentence heading detection now labels its 140 dissent passages
without weakening source validation. Giles v. California (554 U.S. 353, case 145781) had a
truncated dissent-only S3 object; before spending an AI call, generation now detects packets
with no majority material and refreshes numeric cases from CourtListener. The fetcher prefers
CourtListener's combined record and otherwise joins every sub-opinion with explicit part
markers rather than returning only the first writing. Giles was verified locally against the
live CourtListener record: 118,226 characters with majority, concurrence, and dissent in the
selected packet. A Mattox retry then exposed historical passage rows sharing its text hash but
using the pre-fix IDs/ordinals. Passage content hashes are now namespaced by parser format
version, so parser changes create a new internally consistent set without deleting rows used
by older candidates. The strict validator remains unchanged. Verification: 97 backend/citator
tests pass; Mattox derives 359 v2 rows and its production v2 namespace is empty before retry.
Deployment: source repair deployed from `69b30c3`; passage-format fix auto-deploys from this
commit
Commits: `69b30c3`, this commit

### Practice Hypos feature — design parked, do not build yet
Owner: unassigned (design notes by Claude, from the law-school Evidence workspace)
Status: planned — **PARKED by Sage 2026-07-14; do not start until he says go**
Files: none yet (nothing built; no stubs exist beyond the homepage SOON chips)
Summary: turn the homepage "Practice hypos — SOON" chip into a real feature. Sage decided
the shape on 2026-07-14; he is mid-Evidence-semester (final July 31) and explicitly not
ready to build. Recording the design so whoever picks this up starts from decisions, not
research.
Decisions made (with Sage, 2026-07-14):
- **Content = original hypos, casebook-inspired.** Fresh fact patterns testing the same
  doctrine — NOT republished casebook problems. (Cheng's Evidence casebook is CC BY-NC-SA
  4.0, so republishing would be legal with attribution + ShareAlike, but Sage chose clean
  original IP. Fact patterns must not be recognizable derivatives — different actors,
  settings, evidentiary postures.)
- **Workflow: study there, publish here.** Sage's private Socratic problem-working stays in
  `/mnt/d/dev/law-school/summer-2026/evidence/`; polished originals flow into this repo.
  Authoring loop: after he works a topic privately, draft 2–3 original hypos → he answers
  them cold (doubles as exam prep) → reconcile → commit.
- **Scope: Evidence pilot first** (8–12 hypos across relevance/403, character, impeachment,
  hearsay, 801(d), 804/forfeiture), then Torts / Civ Pro / Crim Law from his prior-semester
  notes.
- **V1 experience = self-test, no accounts, no per-user cost:** fact pattern → call of the
  question → optional scratch textarea (client-side only) → "Reveal model answer" (full
  IRAC + takeaway + FRE rules cited) → possibly a client-side "did you spot these issues?"
  checklist (open question: include in v1 or ship bare reveal first). Model answer in a
  native `<details>`-style reveal so it stays in the DOM for SEO.
- **Phase 2 (later): AI-graded free-text answers** by cloning the Study Session engine
  (`migrations/018_study_sessions.sql`, `/api/v1/study/*` in `backend/main.py`,
  `frontend/components/study/QuizCard.tsx` + SSE grading flow). Per-answer API cost means
  it needs auth + quotas (reuse the textbook Q&A metering patterns). Flashcards chip can
  derive from the same content later.
Sketch of the v1 build (follow house patterns):
- Content: `content/hypos/evidence/*.md` with frontmatter (slug, subject, topic, title,
  rules[], difficulty, related_cases, status) + sections Facts / Question / Model Answer
  (IRAC) / Takeaway.
- `migrations/038_hypos.sql` (or next number): `hypos` table mirroring that frontmatter.
- `scripts/import_hypos.py`: idempotent upsert, `build_evidence_casebook.py` conventions.
- Backend: public `GET /api/v1/hypos?subject=` + `GET /api/v1/hypos/{slug}` (free SEO
  content, no auth).
- Frontend: `frontend/app/hypos/page.tsx` (index by subject→topic) +
  `frontend/app/hypos/[slug]/page.tsx` (SSR, `generateMetadata`); flip the SOON chip in
  `frontend/app/page.tsx` (~lines 242–253) to a linked chip; sitemap + optional Header nav.
  Visual identity rules apply (sage/cream, honey = source links only, no dark mode).
Next: nothing — wait for Sage. When he greenlights, the fuller planning notes (timing
around his July 31 exam, verification steps) are in
`/home/sage/.claude/plans/so-i-d-like-to-staged-creek.md`.
Deployment: not deployed
Commit: not committed

### Per-page social share images (dynamic OG cards)
Owner: Sol
Status: completed
Files: `frontend/app/api/og/cases/[id]/route.tsx`, `frontend/app/cases/[...slug]/page.tsx`,
`frontend/lib/case-data.ts`, `frontend/app/fonts/SourceSerif4-*.ttf`
Summary: generate a unique social share card per case page — case name as the hero, court +
year beneath, on the Tortwell turtle-card layout — so a shared case link previews as that case
rather than the generic brand card. Sage requested this 2026-07-14 after the site-wide default
shipped. Recommended approach (Claude): Next's built-in `ImageResponse` from `next/og` via a
route-level `opengraph-image.tsx` — renders JSX to PNG on request, cached, zero pre-generation,
scales to every case automatically. Rejected alternative: pre-generating static PNGs in batch
(storage + regeneration pipeline + repo/S3 bloat for a worse result). Start with case pages
only; statutes/rules/textbooks/`/shared/{id}` collections extend the same template later —
collections are the most share-shaped page, so they're the natural second target.
Context Sol needs:
- A site-wide default already ships (commit `b34bc5b`, 2026-07-14): `frontend/public/
  tortwell-social-featured.png` (1200×627) wired as `openGraph`/`twitter` images via the
  shared `SOCIAL_IMAGE` constant in `frontend/lib/site.ts`. It stays as the fallback for
  pages without their own card.
- Next.js metadata gotcha (hit while shipping the default): child segments REPLACE the parent
  `openGraph` object, they don't deep-merge. That's why six pages re-include `SOCIAL_IMAGE`
  today. A route-level `opengraph-image.tsx` takes precedence over the static images entry
  for that route — verify the case page's `generateMetadata` doesn't fight it (drop its
  `images: [SOCIAL_IMAGE]` line if the file route wins, keep behavior deterministic).
- Design constraints (see "Tortwell visual identity" above): cream background, sage-green
  turtle, Source Serif 4 for the wordmark/case name. `ImageResponse` cannot load webfonts —
  ship the font as a file (`next/font` already pulls Source Serif 4; the OG route needs its
  own ArrayBuffer load) and the turtle as inline SVG (mark lives in
  `components/TortoiseMark.tsx`). Honey stays reserved for source links — don't use it as
  the card accent. Match the reference card: `frontend/public/tortwell-social-featured.png`.
- Card copy: case name (truncate gracefully — captions can be very long), court + year if
  known (use structured fields; beware the UTC date pitfall recorded under Current Handoffs
  follow-ups — year must not render off-by-one), Tortwell wordmark + tagline as footer.
- Deliberately out of scope for v1 (banked ideas, don't build yet): citator treatment badge
  on the card (needs a DB hit from the image route), per-subject accent tinting.
Implementation (Sol, 2026-07-14): Next 16/Turbopack rejects metadata routes beneath a
catch-all segment because `opengraph-image` would illegally follow `[...slug]`. The card therefore
lives at the cached `/api/og/cases/{case_id}` endpoint, and case metadata explicitly points both
Open Graph and Twitter at it. This preserves dynamic generation without changing canonical URLs or
adding a second case lookup in the image request. The endpoint uses shipped Source Serif 4 files,
the inline tortoise mark, UTC-safe years, and deterministic truncation for extreme captions.
Verified with a production build, direct PNG request, generated metadata inspection, and both a
normal caption and a 6,188-character caption. Production verification confirmed the public PNG,
cache headers, and matching Open Graph/Twitter tags on the canonical Ince page.
Next: extend the template to `/shared/{id}` collections if desired.
Deployment: frontend `b5630f23-587b-49c8-9a0c-6477e00f9326` successful
Commit: `64aea27`

### Bruton source-linked brief generation
Owner: Sol
Status: completed
Files: `backend/main.py`, `backend/opinion_passages.py`, `backend/test_opinion_passages.py`
Summary: generation for Bruton (`107684`, `391 U.S. 123`) failed because the endpoint flattened
stored HTML into one line before passage parsing, erasing separate-opinion boundaries; the marker
parser also did not recognize old U.S. Reports headings such as `MR. JUSTICE WHITE, dissenting.`.
HTML-to-text conversion now preserves block boundaries inside the shared passage builder, old-style
Justice headings are recognized, and `NOTES` resets classification to neutral opinion text. On the
actual Bruton HTML the parser now finds 192 majority, 23 concurrence, 113 dissent, and 40 neutral
passages. Validation remains strict; no source rules were loosened.
Next: retry Bruton summary generation in production; the paid AI call was not triggered during
deployment verification.
Deployment: backend `8354b3e1-7a46-473d-be60-1d196d382f60` successful
Commit: `6c6fd1a`

### Multi-window auth deadlock
Owner: Sol
Status: completed
Files: `frontend/lib/auth-context.tsx`
Summary: the auth-state callback awaited `fetchProfile`, which makes another Supabase API call
while `onAuthStateChange` still holds the client auth lock. Supabase documents that pattern as a
deadlock: subsequent calls or tabs can hang, matching the gray profile placeholder reported when
opening cases side by side. Session/UI state now applies synchronously and profile loading is
deferred with `setTimeout(..., 0)` so the callback releases the lock first. The existing version
guard still prevents stale profile responses from winning.
Next: none; Sage confirmed the multi-window behavior works in production.
Deployment: frontend `d4395222-10ae-4375-8e5f-b60713008ca0` successful
Commit: `a6b98df`

### Albert v. McKay & Co. import
Owner: Sol
Status: completed
Files: `scripts/import_albert_mckay.py`
Summary: imported CourtListener cluster `3307250` into production with the complete opinion,
California Supreme Court association, docket `S. F. No. 7111.`, official citation
`174 Cal. 451`, and parallel citations. The idempotent script prefers CourtListener over the
user-supplied CaseMine mirror and decodes source HTML entities before storage.
Next: none; production search, case API, citation-slug resolver, and canonical page were verified.
Deployment: n/a (offline data operation)
Commit: `38d9ba2`

### AI billing protection Round 2
Owner: Sol
Status: deployed; production migration repaired 2026-07-27; local fallback hardening pending commit/deploy
Files: `backend/main.py`, `backend/ai_usage.py`, `backend/test_ai_usage.py`,
`backend/test_stream_finalization.py`, `migrations/039_ai_reservation_idempotency.sql`
Summary: migrated variable-prompt paths preflight and reserve bounded cost; textbook Q&A keeps its
bounded fixed reservation. Case Ask, study chat, MSJ chat/generation, and generic tool
chat/generation atomically persist output, usage, and settlement before SSE `done`; outline
conversation writes are atomic too. Ledger markers make reserve/settle/cancel retries idempotent,
and pending outline/study/case turns are not persisted on pool or token-count failure. MSJ prompt
inputs are deterministic; pricing and overrides fail closed. BYOK provider behavior is unchanged.
Production incident: generation for General Electric Co. v. Joiner (`118157`, canonical
`522-us-136`) returned 500 after Claude completed because commit `05d51d3` deployed before
migration 039 was applied. Settlement's partial-index `ON CONFLICT` therefore failed, rolling back
the brief write and leaving reservation `240` open. Migration 039 was applied and its exact marker
write passed a rollback-only production smoke test. Local defense-in-depth now writes terminal and
uncertain markers with the existing advisory lock plus `INSERT ... WHERE NOT EXISTS`, so delayed
index deployment cannot lose another paid response; the unique indexes remain the database guard.
All 190 backend/citator tests pass. Do not refund the open reservation automatically: the provider
completed but exact usage was lost, so retaining it follows the uncertain-outcome billing rule.
Next: commit and deploy the local two-file fallback hardening. Smoke-test the remaining Round 2
paths as previously planned; no second paid Joiner generation was triggered during this repair.
Deployment: backend `1ced97e5-fb0a-419e-9acc-f57acd044d94` (`6691425`) successful; migration 039
applied directly to production PostgreSQL and verified.
Commit: Round 2 `05d51d3`; fallback hardening uncommitted

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
scripts under `scripts/`. Initial verification passed all 80 tests. From Windows-hosted tools,
do not invoke bare `wsl.exe`: the default distribution can be `docker-desktop-data`. Use
`wsl.exe -d Ubuntu bash -lc "cd /mnt/d/dev/ai-law-research && make test-local"` (and the same
explicit `-d Ubuntu` form for other project commands). Verified 89 tests passing on 2026-07-13.

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

### Railway memory growth diagnosed 2026-09-01: not a code leak, Aug 17 commits exonerated
Owner: Claude
Status: diagnosis complete; fixes are Sage's call (all env-level, no code required)
Files: none changed; write-up at `/mnt/d/dev/ai-collab/2026-09-01-railway-memory-growth.md`
Summary: Both services climb for two weeks after each deploy (frontend to ~3 GB, backend to
~2.7 GB) and drop on restart. Inspected the running containers: cgroup `memory.max` is
24 GB and the hosts expose 32–48 CPUs, so nothing ever pressures memory back down, and
Railway's graph is `memory.current` (page cache included). Traffic is ~99% crawlers
(bingbot, SleepBot, Applebot, ChatGPT-User) sweeping `/cases/*` at ~30k unique URLs/day.
Frontend: Next's on-disk fetch cache holds ~52 KB per crawled page, never pruned —
9.7 GB / 309k files in the container — plus lazy V8 GC with a 4.5 GB heap ceiling; a local
2,000-page crawl of a production build plateaus at ~330 MB RSS and drops when idle, so
there is no JS-level leak. Backend: 3 workers × ~300 MB import baseline, then glibc
per-thread malloc arenas (54 threads/worker, 6–14 arena heaps each within 42 min)
fragmenting under the opinion-text churn of `get_case`. pdfplumber, `memo_builder`, and
the synthetic `get_case` allocation pattern all tested flat.
Done 2026-09-01 (Sage approved): backend `MALLOC_ARENA_MAX=2` and frontend
`NODE_OPTIONS=--max-old-space-size=512` set via CLI and both services redeployed; verified
in-container (backend worker env has the var; frontend V8 heap limit now 738 MB; the
rebuild reset `.next/cache` from 9.7 GB to 1.3 MB); all health checks 200. 30-day metrics
show the "leak" tracked a crawler wave that began Aug 17 (10k → 150k requests/day).
Also shipped (Sage approved): `cache: 'no-store'` on `resolveSlug`/`getCase` (and the
legacy `/case/[id]` resolve), plus `generateMetadata` returns early for non-canonical
slugs so a redirecting URL no longer fetches the full opinion. Verified on a production
build behind a counting proxy: canonical page = 1 resolve + 1 case fetch (memoization
holds), redirect = 2 resolves, zero files written to `.next/cache/fetch-cache`.
Next: (1) Sage sets Railway memory limits in the dashboard (CLI cannot; suggest 1 GB
frontend, 2 GB backend); (2) optional: uvicorn `--limit-max-requests` in the backend
Dockerfile; (3) re-check `railway metrics --all --memory --since 7d` in a week.
Deployment: Backend `ca84118b` (env only, commit `bb69698`); frontend `07cb66c9`
(SUCCESS, commit `c812926`) — post-deploy backend mix is 136 resolve : 130 case fetches,
i.e. the expected 1 + 1 per page; `.next/cache` is 20 KB in the new container
Commit: `c812926` (frontend only; this handoff entry itself is not yet committed)

## Deployment State

- Supreme Court separate-opinion heading parser: commit `c2a8959`; backend deployment
  `9dec83fc-7fd4-4897-b1f6-3c395d5cb31a` successful on 2026-07-13. The production
  health check passed with the database connected.
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
