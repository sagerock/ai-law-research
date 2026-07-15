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

## Open Questions

Genuine design questions left for the next assistant. If you can resolve one (with
evidence), do so and move the conclusion into Architecture Decisions; if you disagree
with an existing decision, add your case here instead of silently changing the code.

- `validate_structured_summary` enforces a 400–800 word band and fixed per-section claim
  limits for every case. Is one band right for both short procedural opinions and long
  cases with substantial dissents, or should limits scale with opinion length? (Raised
  2026-07-12 by Claude while unifying the validators; no evidence gathered yet.)

## Current Handoffs

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
Commit: this commit

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

### Textbook Q&A billing protection
Owner: Codex
Status: ready for review
Files: `backend/main.py`, `backend/ai_usage.py`, `backend/test_ai_usage.py`,
`frontend/app/textbooks/[id]/TextbookDetailClient.tsx`
Summary: require sign-in, validate JWT subjects, atomically reserve daily quota and pool
funds before paid provider calls, use BYOK where available, reconcile actual token costs,
and prevent all community-pool debits from overdrawing the ledger.
Next: review, commit, deploy both backend and frontend, then smoke-test signed-out, free-tier,
BYOK, pool-empty, and successful textbook questions in production.
Deployment: not deployed
Commit: this commit

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
