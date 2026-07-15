#!/home/sage/.venvs/lawdata/bin/python
"""sunday_briefs.py — helper surface for the Sunday subscription-credit brief batch.

Each Sunday a scheduled Claude Code session generates AI case briefs using Sage's
LEFTOVER weekly subscription capacity (instead of metered API dollars) and stores
them exactly where the site's paid summarize endpoint would. The session drives
these subcommands; the MODEL writes the briefs, this script only moves data.

    sunday_briefs.py list [N]        next N un-briefed cases by priority (JSON)
    sunday_briefs.py opinion <id>    print the opinion text (S3, PG fallback), pre-truncated
    sunday_briefs.py save <id> <file> [model]   upsert brief into ai_summaries + usage log
    sunday_briefs.py candidate-list [N]         next rebuild cases (legacy brief, no structured)
    sunday_briefs.py candidate-opinion <id>     persist + print passage-tagged opinion JSON
    sunday_briefs.py candidate-save <id> <file> <model> <content-hash>
    sunday_briefs.py triage-list [N]            rejected cases + notes, one retry each (two-strike)
    sunday_briefs.py review-list [N]            pending candidates awaiting semantic review
    sunday_briefs.py review-fetch <id>          candidate claims with cited passage texts
    sunday_briefs.py review-save <id> <file>    apply {"verdict": "approve"|"hold", "notes"}

Priority: (1) the 30 citator landmarks, (2) curated 1L cases (by casebook count),
(3) nothing yet — expand when tiers 1-2 run dry. Cost is logged as $0 with
source='subscription' so the transparency dashboard reflects reality.
"""
import asyncio, asyncpg, boto3, json, os, re, sys

HERE = os.path.dirname(__file__)
CURATED = "/mnt/d/backups/ai-law-research/data/1L_core_cases.json"
BUCKET = os.getenv("OPINIONS_BUCKET", "lawstudygroup-opinions")
# cases with no briefable opinion (table affirmances, cert grants, wrong-cluster ids):
# `opinion` auto-appends here, `list` excludes — otherwise they clog every batch
SKIPLIST = os.path.join(HERE, "data", "briefs_skiplist.txt")
MIN_OPINION = 2500  # chars; below this it's a procedural order, not an opinion
BACKEND = os.path.join(os.path.dirname(HERE), "backend")
sys.path.insert(0, BACKEND)
from opinion_passages import build_opinion_passages
from structured_briefs import validate_structured_summary

# Diverse, hand-verified pilot: civil procedure, constitutional law, and jurisdiction;
# modern/older OCR opinions; majority-only and separate-opinion cases.
SOURCE_PILOT_IDS = [
    "111722",  # Celotex
    "104200",  # International Shoe
    "103012",  # Erie
    "84759",   # Marbury
    "104357",  # Hickman
    "107082",  # Griswold
    "105221",  # Brown
    "107024",  # Hanna
    "118144",  # Glucksberg
    "96889",   # Mottley
]
SOURCE_PROVIDER = "claude"
SOURCE_PACKET_CHARS = 80000
PRIORITY_CASEBOOK_ID = 2467


def skiplist():
    if not os.path.exists(SKIPLIST):
        return set()
    return {ln.split("\t")[0].strip() for ln in open(SKIPLIST) if ln.strip()}

# the 30 landmark targets (canonical cluster ids, 2026-07-05 run)
LANDMARKS = [
    "111722", "104200", "103012", "110170", "84759", "104357", "110586", "109964",
    "107082", "105221", "109469", "107024", "118144", "85412", "3602780", "96889",
    "107480", "118140", "105018", "130160", "96276", "118056", "3603427", "269048",
    "3632643", "3630485", "1320585", "1299375", "1305339", "8019723",
]


def prod_url():
    if os.getenv("PROD_DATABASE_URL") or os.getenv("DATABASE_URL"):
        return os.getenv("PROD_DATABASE_URL") or os.getenv("DATABASE_URL")
    for path in ("/mnt/d/dev/ai-law-research/backend/.env", "/mnt/d/dev/ai-law-research/.env"):
        if os.path.exists(path):
            for line in open(path):
                if line.startswith("PROD_DATABASE_URL="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("PROD_DATABASE_URL not found")


def curated_ids():
    """Curated 1L cases [(id, name, date)] by casebook count (desc), landmarks excluded."""
    d = json.load(open(CURATED))
    seen = {}
    for v in d.values():
        for c in v["cases"]:
            cid = c.get("courtlistener_id")
            if cid and (cid not in seen or c["casebook_count"] > seen[cid][2]):
                seen[cid] = (c["name"], c.get("date_filed"), c["casebook_count"])
    return [(cid, nm, dt) for cid, (nm, dt, _) in sorted(seen.items(), key=lambda x: -x[1][2])
            if cid not in LANDMARKS]


def _sides(name):
    """Distinctive tokens for (plaintiff side, defendant side) of a caption."""
    sys.path.insert(0, HERE)
    from citator_pipeline import distinctive_parties
    import re
    parts = re.split(r"\s+v\.?\s+", name, maxsplit=1, flags=re.I)
    if len(parts) != 2:
        return None
    return distinctive_parties(parts[0]), distinctive_parties(parts[1])


def identity_matches(curated_name, stored_title):
    """The curated JSON's CL ids are unreliable (famous-name mismatches: its 'Brown v.
    Board' was Brown & Root v. NLRB; 'Brown v. Kendall' points at a Kendall Brown habeas).
    Its dates/citations for bad entries come from the wrong cluster itself, so the NAME is
    the only ground truth. Match ORDER-AWARE: plaintiff-side tokens must overlap the
    stored plaintiff side, defendant-side the defendant side — coincidental shared
    surnames on the wrong side ('Kendall Brown v. Wilmot') then fail."""
    sys.path.insert(0, HERE)
    from citator_pipeline import distinctive_parties
    ca, sa = _sides(curated_name), _sides(stored_title)
    if ca and sa:
        (cp, cd), (sp, sd) = ca, sa
        p_ok = not cp or not sp or bool(cp & sp)
        d_ok = not cd or not sd or bool(cd & sd)
        return p_ok and d_ok
    a, b = distinctive_parties(curated_name), distinctive_parties(stored_title)
    if not a or not b:  # single-generic-name captions (e.g. "In re Baby M") — let through
        return True
    return bool(a & b)


async def cmd_list(n):
    conn = await asyncpg.connect(prod_url())
    queue = [(c, None, None) for c in LANDMARKS] + curated_ids()  # landmarks hand-verified
    out, skip = [], skiplist()
    ids = [c for c, _, _ in queue]
    briefed = {r["case_id"] for r in await conn.fetch(
        "SELECT case_id FROM ai_summaries WHERE case_id = ANY($1)", ids)}
    exists = {r["id"]: r for r in await conn.fetch(
        "SELECT id, title, decision_date FROM cases WHERE id = ANY($1)", ids)}
    for cid, curated_name, curated_date in queue:
        if cid in briefed or cid not in exists or cid in skip:
            continue
        r = exists[cid]
        if curated_name and not identity_matches(curated_name, r["title"]):
            print(f"  ! id mismatch, skipping {cid}: curated {curated_name!r} "
                  f"vs stored {r['title'][:50]!r} ({r['decision_date']})",
                  file=sys.stderr)
            continue
        out.append({"id": cid, "title": r["title"],
                    "date": r["decision_date"].isoformat() if r["decision_date"] else None})
        if len(out) >= n:
            break
    await conn.close()
    print(json.dumps(out, indent=1))


async def cmd_opinion(cid):
    text = None
    try:
        obj = boto3.client("s3").get_object(Bucket=BUCKET, Key=f"opinions/{cid}.txt")
        text = obj["Body"].read().decode("utf-8")
    except Exception:
        pass
    if not text:
        conn = await asyncpg.connect(prod_url())
        text = await conn.fetchval("SELECT content FROM cases WHERE id = $1", cid)
        await conn.close()
    if not text or len(text) < MIN_OPINION:
        # table affirmance / cert grant / wrong cluster — blacklist so it stops
        # reappearing in every batch; a human should re-resolve or exclude it
        with open(SKIPLIST, "a") as f:
            f.write(f"{cid}\t{len(text or '')} chars, auto-skipped {__import__('datetime').date.today()}\n")
        print(f"SKIPPED {cid}: opinion text is {len(text or '')} chars — procedural order or "
              f"missing, added to {os.path.basename(SKIPLIST)}", file=sys.stderr)
        sys.exit(1)
    # same truncation the paid endpoint uses: first 18k + last 2k
    if len(text) > 20000:
        text = text[:18000] + "\n\n[...middle section omitted...]\n\n" + text[-2000:]
    print(text)


async def cmd_save(cid, path, model):
    summary = open(path).read().strip()
    if len(summary) < 500 or "📋" not in summary or "🎯" not in summary:
        print(f"REFUSING to save: brief looks malformed ({len(summary)} chars)", file=sys.stderr)
        sys.exit(1)
    # rough token estimate for the log (chars/4); cost is genuinely $0 (subscription)
    in_est, out_est = 20000 // 4, len(summary) // 4
    conn = await asyncpg.connect(prod_url())
    await conn.execute("""
        INSERT INTO ai_summaries (case_id, summary, model, input_tokens, output_tokens, cost)
        VALUES ($1, $2, $3, $4, $5, 0)
        ON CONFLICT (case_id) DO UPDATE
        SET summary = EXCLUDED.summary, model = EXCLUDED.model,
            input_tokens = EXCLUDED.input_tokens, output_tokens = EXCLUDED.output_tokens,
            cost = 0, created_at = CURRENT_TIMESTAMP
    """, cid, summary, model, in_est, out_est)
    await conn.execute("""
        INSERT INTO api_usage_log (usage_date, usage_type, call_count, input_tokens,
                                   output_tokens, estimated_cost, source, updated_at)
        VALUES (CURRENT_DATE, 'ai_summary', 1, $1, $2, 0, 'subscription', CURRENT_TIMESTAMP)
        ON CONFLICT (usage_date, usage_type) DO UPDATE SET
            call_count = api_usage_log.call_count + 1,
            input_tokens = api_usage_log.input_tokens + EXCLUDED.input_tokens,
            output_tokens = api_usage_log.output_tokens + EXCLUDED.output_tokens,
            updated_at = CURRENT_TIMESTAMP
    """, in_est, out_est)
    await conn.close()
    print(f"saved brief for {cid} ({len(summary)} chars, model {model})")


def read_full_opinion(cid):
    try:
        obj = boto3.client("s3").get_object(Bucket=BUCKET, Key=f"opinions/{cid}.txt")
        return obj["Body"].read().decode("utf-8"), "s3"
    except Exception:
        return None, None


async def cmd_candidate_list(n):
    """Source-linked queue: priority casebook cases, then the existing rebuild pool.

    The 10-case pilot (SOURCE_PILOT_IDS) graduated 2026-07-12: 5 approved, 5 held
    at semantic review. Queue priority mirrors the legacy batch — landmarks first
    (most-visited pages), curated 1L cases next, everything else by citation count.
    Cases held at semantic review stay excluded until a human clears the failure row.

    Cases linked from a published canonical outline (tortwell.com/outlines/*) rank
    just below the priority casebook and are admitted even without a legacy brief —
    the outlines send readers straight to these pages, so they convert first
    (Sage, 2026-07-15).
    """
    outline_case_sql = """SELECT 1
                     FROM canonical_outline_section_sources src
                     JOIN canonical_outline_section_revisions sr ON sr.id = src.section_revision_id
                     JOIN canonical_outline_revisions rev ON rev.id = sr.revision_id
                     JOIN canonical_outlines o ON o.id = rev.outline_id
                          AND o.current_version = rev.version AND o.is_published
                     WHERE src.target_type = 'case' AND src.target_ref = c.id"""
    conn = await asyncpg.connect(prod_url())
    try:
        rows = await conn.fetch(
            f"""SELECT c.id AS case_id, c.title, c.decision_date,
                      (SELECT COUNT(*) FROM citations t
                       WHERE t.target_case_id = c.id) AS cites,
                      EXISTS (SELECT 1 FROM casebook_cases cc
                              WHERE cc.case_id = c.id AND cc.casebook_id = $2) AS priority_casebook,
                      EXISTS ({outline_case_sql}) AS outline_case,
                      (SELECT cc.sort_order FROM casebook_cases cc
                       WHERE cc.case_id = c.id AND cc.casebook_id = $2
                       LIMIT 1) AS priority_order
               FROM cases c
               WHERE (EXISTS (SELECT 1 FROM ai_summaries s WHERE s.case_id = c.id)
                      OR EXISTS (SELECT 1 FROM casebook_cases cc
                                 WHERE cc.case_id = c.id AND cc.casebook_id = $2)
                      OR EXISTS ({outline_case_sql}))
                 AND NOT EXISTS (SELECT 1 FROM structured_summary_candidates k
                                  WHERE k.case_id = c.id AND k.provider = $1)
                  AND NOT EXISTS (SELECT 1 FROM structured_summary_failures f
                                  WHERE f.case_id = c.id AND f.provider = $1
                                    AND f.stage = 'semantic_review')""",
            SOURCE_PROVIDER, PRIORITY_CASEBOOK_ID,
        )
        skip = skiplist()
        landmark_rank = {cid: i for i, cid in enumerate(LANDMARKS)}
        curated_rank = {cid: i for i, (cid, _, _) in enumerate(curated_ids())}

        def rank(row):
            cid = row["case_id"]
            if row["priority_casebook"]:
                return (0, row["priority_order"] or 999999)
            if row["outline_case"]:
                return (1, -row["cites"])
            if cid in landmark_rank:
                return (2, landmark_rank[cid])
            if cid in curated_rank:
                return (3, curated_rank[cid])
            return (4, -row["cites"])

        queue = [
            {
                "id": row["case_id"],
                "title": row["title"],
                "date": row["decision_date"].isoformat() if row["decision_date"] else None,
            }
            for row in sorted(rows, key=rank)
            if row["case_id"] not in skip
        ][:n]
        print(json.dumps(queue, indent=1))
    finally:
        await conn.close()


async def cmd_candidate_opinion(cid):
    text, source = await asyncio.to_thread(read_full_opinion, cid)
    conn = await asyncpg.connect(prod_url())
    try:
        if not text:
            text = await conn.fetchval("SELECT content FROM cases WHERE id = $1", cid)
            source = "database"
        if not text or len(text) < MIN_OPINION:
            with open(SKIPLIST, "a") as f:
                f.write(f"{cid}\t{len(text or '')} chars, auto-skipped (candidate) "
                        f"{__import__('datetime').date.today()}\n")
            raise SystemExit(f"SKIPPED {cid}: opinion is missing or too short "
                             f"({len(text or '')} chars) — added to skiplist")
        title = await conn.fetchval("SELECT title FROM cases WHERE id = $1", cid)
        content_hash, passages = build_opinion_passages(text)
        async with conn.transaction():
            await conn.executemany(
                """INSERT INTO opinion_passages
                   (case_id, content_hash, passage_id, ordinal, opinion_part, text)
                   VALUES ($1, $2, $3, $4, $5, $6)
                   ON CONFLICT (case_id, content_hash, passage_id) DO UPDATE SET
                       ordinal = EXCLUDED.ordinal,
                       opinion_part = EXCLUDED.opinion_part,
                       text = EXCLUDED.text""",
                [
                    (cid, content_hash, p["id"], p["ordinal"], p["opinion_part"], p["text"])
                    for p in passages
                ],
            )

        selected, chars = [], 0
        for passage in passages:
            if chars + len(passage["text"]) > 65000:
                break
            selected.append(passage)
            chars += len(passage["text"])
        if len(selected) < len(passages):
            tail, tail_chars = [], 0
            for passage in reversed(passages):
                if tail_chars + len(passage["text"]) > 15000:
                    break
                tail.append(passage)
                tail_chars += len(passage["text"])
            selected_ids = {p["id"] for p in selected}
            selected.extend(p for p in reversed(tail) if p["id"] not in selected_ids)
        packet = {
            "case_id": cid,
            "title": title,
            "content_hash": content_hash,
            "source": source,
            "is_partial_packet": len(selected) < len(passages),
            "total_passages": len(passages),
            "passages": selected,
        }
        print(json.dumps(packet, ensure_ascii=False))
    finally:
        await conn.close()


def validate_candidate(candidate, passages):
    return validate_structured_summary(candidate, passages)


async def record_candidate_failure(conn, cid, content_hash, stage, error):
    await conn.execute(
        """INSERT INTO structured_summary_failures
           (case_id, provider, content_hash, stage, error)
           VALUES ($1, $2, $3, $4, $5)""",
        cid, SOURCE_PROVIDER, content_hash, stage, error[:4000],
    )


async def cmd_candidate_save(cid, path, model, content_hash):
    conn = await asyncpg.connect(prod_url())
    try:
        try:
            candidate = json.load(open(path))
        except Exception as error:
            await record_candidate_failure(conn, cid, content_hash, "parse", str(error))
            raise SystemExit(f"REFUSING candidate: invalid JSON: {error}")
        passages = await conn.fetch(
            """SELECT passage_id, opinion_part, text FROM opinion_passages
               WHERE case_id = $1 AND content_hash = $2""",
            cid, content_hash,
        )
        if not passages:
            await record_candidate_failure(conn, cid, content_hash, "stale_source", "No passages for content hash")
            raise SystemExit("REFUSING candidate: content hash is stale or unknown")
        errors = validate_candidate(candidate, passages)
        if errors:
            message = "; ".join(errors)
            await record_candidate_failure(conn, cid, content_hash, "validation", message)
            raise SystemExit(f"REFUSING candidate: {message}")
        output_chars = len(json.dumps(candidate))
        input_chars = sum(len(row["text"]) for row in passages)
        metadata = {
            "source": "subscription",
            "schema_version": "v1",
            "input_tokens_estimate": input_chars // 4,
            "output_tokens_estimate": output_chars // 4,
        }
        async with conn.transaction():
            await conn.execute(
                """INSERT INTO structured_summary_candidates
                   (case_id, provider, model, summary, content_hash, generation_metadata,
                    validation_version, review_status, created_at)
                   VALUES ($1, $2, $3, $4::jsonb, $5, $6::jsonb, 'v1', 'pending', NOW())
                   ON CONFLICT (case_id, provider) DO UPDATE SET
                       model = EXCLUDED.model,
                       summary = EXCLUDED.summary,
                       content_hash = EXCLUDED.content_hash,
                       generation_metadata = EXCLUDED.generation_metadata,
                       validation_version = EXCLUDED.validation_version,
                       review_status = 'pending',
                       reviewed_at = NULL,
                       review_notes = NULL,
                       created_at = NOW()""",
                cid, SOURCE_PROVIDER, model, json.dumps(candidate), content_hash, json.dumps(metadata),
            )
            await conn.execute(
                """INSERT INTO api_usage_log
                   (usage_date, usage_type, call_count, input_tokens, output_tokens,
                    estimated_cost, source, updated_at)
                   VALUES (CURRENT_DATE, 'structured_summary', 1, $1, $2, 0,
                           'subscription', CURRENT_TIMESTAMP)
                   ON CONFLICT (usage_date, usage_type) DO UPDATE SET
                       call_count = api_usage_log.call_count + 1,
                       input_tokens = api_usage_log.input_tokens + EXCLUDED.input_tokens,
                       output_tokens = api_usage_log.output_tokens + EXCLUDED.output_tokens,
                       updated_at = CURRENT_TIMESTAMP""",
                input_chars // 4, output_chars // 4,
            )
        print(f"saved structured candidate for {cid} ({model}, {content_hash[:12]})")
    finally:
        await conn.close()


async def cmd_triage_list(n):
    """Rejected cases eligible for ONE corrective regeneration (two-strike rule).

    Returns each case with its latest rejection note so the regenerating session
    addresses the reviewer's specific findings instead of rolling the dice again.
    A case rejected twice stays out permanently — it needs a human. Re-saving via
    candidate-save resets the candidate to 'pending', so the corrected brief goes
    back through the same review gate; triage never bypasses review.
    """
    conn = await asyncpg.connect(prod_url())
    try:
        rows = await conn.fetch(
            """SELECT f.case_id, c.title,
                      COUNT(*) AS attempts,
                      (ARRAY_AGG(f.error ORDER BY f.created_at DESC))[1] AS latest_note
               FROM structured_summary_failures f
               JOIN cases c ON c.id = f.case_id
               WHERE f.provider = $1 AND f.stage = 'semantic_review'
                 AND NOT EXISTS (SELECT 1 FROM structured_summary_candidates k
                                 WHERE k.case_id = f.case_id AND k.provider = $1
                                   AND k.review_status IN ('approved', 'pending'))
               GROUP BY f.case_id, c.title
               HAVING COUNT(*) < 2
               ORDER BY MAX(f.created_at)
               LIMIT $2""",
            SOURCE_PROVIDER, n,
        )
        print(json.dumps([
            {"id": r["case_id"], "title": r["title"], "attempts": r["attempts"],
             "rejection_note": r["latest_note"]}
            for r in rows
        ], ensure_ascii=False, indent=1))
    finally:
        await conn.close()


async def cmd_review_list(n):
    """Pending structured candidates awaiting semantic review, oldest first."""
    conn = await asyncpg.connect(prod_url())
    try:
        rows = await conn.fetch(
            """SELECT k.case_id, c.title, k.model, k.created_at
               FROM structured_summary_candidates k
               JOIN cases c ON c.id = k.case_id
               WHERE k.provider = $1 AND k.review_status = 'pending'
               ORDER BY k.created_at
               LIMIT $2""",
            SOURCE_PROVIDER, n,
        )
        print(json.dumps([
            {"id": r["case_id"], "title": r["title"], "model": r["model"],
             "created_at": r["created_at"].isoformat()}
            for r in rows
        ], indent=1))
    finally:
        await conn.close()


async def cmd_review_fetch(cid):
    """Print a pending candidate with each claim's cited passage texts for review."""
    conn = await asyncpg.connect(prod_url())
    try:
        row = await conn.fetchrow(
            """SELECT summary, content_hash, model FROM structured_summary_candidates
               WHERE case_id = $1 AND provider = $2 AND review_status = 'pending'""",
            cid, SOURCE_PROVIDER,
        )
        if not row:
            raise SystemExit(f"No pending candidate for {cid}")
        candidate = json.loads(row["summary"])
        passages = {
            p["passage_id"]: p for p in await conn.fetch(
                """SELECT passage_id, opinion_part, text FROM opinion_passages
                   WHERE case_id = $1 AND content_hash = $2""",
                cid, row["content_hash"],
            )
        }
        title = await conn.fetchval("SELECT title FROM cases WHERE id = $1", cid)
        claims = []
        for section, value in candidate.items():
            if not isinstance(value, list):
                continue
            for index, claim in enumerate(value):
                claims.append({
                    "section": section,
                    "index": index,
                    "text": claim["text"],
                    "sources": [
                        {"id": sid,
                         "opinion_part": passages[sid]["opinion_part"] if sid in passages else "MISSING",
                         "text": passages[sid]["text"] if sid in passages else "MISSING"}
                        for sid in claim["sources"]
                    ],
                })
        print(json.dumps({
            "case_id": cid,
            "title": title,
            "model": row["model"],
            "content_hash": row["content_hash"],
            "significance": candidate.get("significance"),
            "claims": claims,
        }, ensure_ascii=False, indent=1))
    finally:
        await conn.close()


async def cmd_review_save(cid, path):
    """Apply a review verdict: {"verdict": "approve"|"hold", "notes": "..."}.

    Approve publishes the candidate (the frontend only shows approved ones).
    Hold records a semantic_review failure, which also removes the case from the
    rebuild queue until a human clears it — deliberate: a brief that failed human-level
    review should not be silently regenerated and re-approved by the same pipeline.
    """
    verdict = json.load(open(path))
    if verdict.get("verdict") not in ("approve", "hold") or not str(verdict.get("notes", "")).strip():
        raise SystemExit('Verdict file must be {"verdict": "approve"|"hold", "notes": "<specific reasons>"}')
    notes = str(verdict["notes"])[:4000]
    conn = await asyncpg.connect(prod_url())
    try:
        row = await conn.fetchrow(
            """SELECT content_hash FROM structured_summary_candidates
               WHERE case_id = $1 AND provider = $2 AND review_status = 'pending'""",
            cid, SOURCE_PROVIDER,
        )
        if not row:
            raise SystemExit(f"No pending candidate for {cid}")
        async with conn.transaction():
            status = "approved" if verdict["verdict"] == "approve" else "rejected"
            await conn.execute(
                """UPDATE structured_summary_candidates
                   SET review_status = $3, reviewed_at = NOW(), review_notes = $4
                   WHERE case_id = $1 AND provider = $2""",
                cid, SOURCE_PROVIDER, status, notes,
            )
            if status == "rejected":
                await record_candidate_failure(conn, cid, row["content_hash"], "semantic_review", notes)
        print(f"{status} candidate for {cid}")
    finally:
        await conn.close()


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "list":
        asyncio.run(cmd_list(int(sys.argv[2]) if len(sys.argv) > 2 else 25))
    elif cmd == "opinion":
        asyncio.run(cmd_opinion(sys.argv[2]))
    elif cmd == "save":
        model = sys.argv[4] if len(sys.argv) > 4 else "claude-sunday-batch"
        asyncio.run(cmd_save(sys.argv[2], sys.argv[3], model))
    elif cmd == "candidate-list":
        asyncio.run(cmd_candidate_list(int(sys.argv[2]) if len(sys.argv) > 2 else 10))
    elif cmd == "candidate-opinion" and len(sys.argv) == 3:
        asyncio.run(cmd_candidate_opinion(sys.argv[2]))
    elif cmd == "candidate-save" and len(sys.argv) == 6:
        asyncio.run(cmd_candidate_save(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]))
    elif cmd == "triage-list":
        asyncio.run(cmd_triage_list(int(sys.argv[2]) if len(sys.argv) > 2 else 10))
    elif cmd == "review-list":
        asyncio.run(cmd_review_list(int(sys.argv[2]) if len(sys.argv) > 2 else 10))
    elif cmd == "review-fetch" and len(sys.argv) == 3:
        asyncio.run(cmd_review_fetch(sys.argv[2]))
    elif cmd == "review-save" and len(sys.argv) == 4:
        asyncio.run(cmd_review_save(sys.argv[2], sys.argv[3]))
    else:
        print(__doc__); sys.exit(1)


if __name__ == "__main__":
    main()
