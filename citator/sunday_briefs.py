#!/home/sage/.venvs/lawdata/bin/python
"""sunday_briefs.py — helper surface for the Sunday subscription-credit brief batch.

Each Sunday a scheduled Claude Code session generates AI case briefs using Sage's
LEFTOVER weekly subscription capacity (instead of metered API dollars) and stores
them exactly where the site's paid summarize endpoint would. The session drives
these subcommands; the MODEL writes the briefs, this script only moves data.

    sunday_briefs.py list [N]        next N un-briefed cases by priority (JSON)
    sunday_briefs.py opinion <id>    print the opinion text (S3, PG fallback), pre-truncated
    sunday_briefs.py save <id> <file> [model]   upsert brief into ai_summaries + usage log
    sunday_briefs.py candidate-list [N]         next source-linked pilot cases
    sunday_briefs.py candidate-opinion <id>     persist + print passage-tagged opinion JSON
    sunday_briefs.py candidate-save <id> <file> <model> <content-hash>

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
    conn = await asyncpg.connect(prod_url())
    try:
        completed = {row["case_id"] for row in await conn.fetch(
            """SELECT case_id FROM structured_summary_candidates
               WHERE provider = $1 AND case_id = ANY($2)""",
            SOURCE_PROVIDER, SOURCE_PILOT_IDS,
        )}
        rows = await conn.fetch(
            """SELECT c.id, c.title, c.decision_date
               FROM cases c JOIN ai_summaries s ON s.case_id = c.id
               WHERE c.id = ANY($1)""",
            SOURCE_PILOT_IDS,
        )
        by_id = {row["id"]: row for row in rows}
        queue = [
            {
                "id": cid,
                "title": by_id[cid]["title"],
                "date": by_id[cid]["decision_date"].isoformat() if by_id[cid]["decision_date"] else None,
            }
            for cid in SOURCE_PILOT_IDS
            if cid in by_id and cid not in completed and cid not in skiplist()
        ][:n]
        print(json.dumps(queue, indent=1))
    finally:
        await conn.close()


async def cmd_candidate_opinion(cid):
    if cid not in SOURCE_PILOT_IDS:
        raise SystemExit(f"{cid} is not in the source-linked pilot allowlist")
    text, source = await asyncio.to_thread(read_full_opinion, cid)
    conn = await asyncpg.connect(prod_url())
    try:
        if not text:
            text = await conn.fetchval("SELECT content FROM cases WHERE id = $1", cid)
            source = "database"
        if not text or len(text) < MIN_OPINION:
            raise SystemExit(f"Opinion for {cid} is missing or too short ({len(text or '')} chars)")
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
    errors = []
    limits = {"facts": 4, "issue": 1, "holding": 2, "rule": 2,
              "majority_reasoning": 4, "dissent": 4}
    allowed = set(limits) | {"significance"}
    if not isinstance(candidate, dict):
        return ["top level must be an object"]
    if set(candidate) != allowed:
        errors.append(f"keys must be exactly {sorted(allowed)}")
    passage_by_id = {p["passage_id"]: p for p in passages}
    for section, maximum in limits.items():
        claims = candidate.get(section)
        minimum = 0 if section == "dissent" else 1
        if not isinstance(claims, list) or not minimum <= len(claims) <= maximum:
            errors.append(f"{section} must contain {minimum}-{maximum} claims")
            continue
        for index, claim in enumerate(claims):
            if not isinstance(claim, dict) or set(claim) != {"text", "sources"}:
                errors.append(f"{section}[{index}] must contain only text and sources")
                continue
            if not isinstance(claim["text"], str) or not claim["text"].strip():
                errors.append(f"{section}[{index}] has invalid text")
            sources = claim["sources"]
            if not isinstance(sources, list) or not sources or len(sources) != len(set(sources)):
                errors.append(f"{section}[{index}] has missing or duplicate sources")
                continue
            unknown = [source for source in sources if source not in passage_by_id]
            if unknown:
                errors.append(f"{section}[{index}] has unknown sources: {unknown}")
                continue
            parts = {passage_by_id[source]["opinion_part"] for source in sources}
            if section == "majority_reasoning" and "dissent" in parts:
                errors.append(f"{section}[{index}] cites dissent")
            if section == "dissent" and any(part != "dissent" for part in parts):
                errors.append(f"{section}[{index}] cites non-dissent passage")
    significance = candidate.get("significance")
    if not isinstance(significance, str) or not significance.strip() or re.search(r"op-[0-9a-f]", significance):
        errors.append("significance must be unsourced editorial text")
    words = len(re.findall(r"\b\w+\b", " ".join(
        [claim.get("text", "") for section in limits for claim in candidate.get(section, []) if isinstance(claim, dict)]
        + ([significance] if isinstance(significance, str) else [])
    )))
    if not 400 <= words <= 800:
        errors.append(f"candidate must contain 400-800 words, got {words}")
    return errors


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
                    validation_version, created_at)
                   VALUES ($1, $2, $3, $4::jsonb, $5, $6::jsonb, 'v1', NOW())
                   ON CONFLICT (case_id, provider) DO UPDATE SET
                       model = EXCLUDED.model,
                       summary = EXCLUDED.summary,
                       content_hash = EXCLUDED.content_hash,
                       generation_metadata = EXCLUDED.generation_metadata,
                       validation_version = EXCLUDED.validation_version,
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
    else:
        print(__doc__); sys.exit(1)


if __name__ == "__main__":
    main()
