#!/home/sage/.venvs/lawdata/bin/python
"""sunday_briefs.py — helper surface for the Sunday subscription-credit brief batch.

Each Sunday a scheduled Claude Code session generates AI case briefs using Sage's
LEFTOVER weekly subscription capacity (instead of metered API dollars) and stores
them exactly where the site's paid summarize endpoint would. The session drives
these subcommands; the MODEL writes the briefs, this script only moves data.

    sunday_briefs.py list [N]        next N un-briefed cases by priority (JSON)
    sunday_briefs.py opinion <id>    print the opinion text (S3, PG fallback), pre-truncated
    sunday_briefs.py save <id> <file> [model]   upsert brief into ai_summaries + usage log

Priority: (1) the 30 citator landmarks, (2) curated 1L cases (by casebook count),
(3) nothing yet — expand when tiers 1-2 run dry. Cost is logged as $0 with
source='subscription' so the transparency dashboard reflects reality.
"""
import asyncio, asyncpg, boto3, json, os, sys

HERE = os.path.dirname(__file__)
CURATED = "/mnt/d/backups/ai-law-research/data/1L_core_cases.json"
BUCKET = os.getenv("OPINIONS_BUCKET", "lawstudygroup-opinions")

# the 30 landmark targets (canonical cluster ids, 2026-07-05 run)
LANDMARKS = [
    "111722", "104200", "103012", "110170", "84759", "104357", "110586", "109964",
    "107082", "105221", "109469", "107024", "118144", "85412", "3602780", "96889",
    "107480", "118140", "105018", "130160", "96276", "118056", "3603427", "269048",
    "3632643", "3630485", "1320585", "1299375", "1305339", "8019723",
]


def prod_url():
    for path in ("/mnt/d/dev/ai-law-research/backend/.env", "/mnt/d/dev/ai-law-research/.env"):
        if os.path.exists(path):
            for line in open(path):
                if line.startswith("PROD_DATABASE_URL="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("PROD_DATABASE_URL not found")


def curated_ids():
    """Curated 1L case ids ordered by casebook count (desc), landmarks excluded."""
    d = json.load(open(CURATED))
    seen = {}
    for v in d.values():
        for c in v["cases"]:
            cid = c.get("courtlistener_id")
            if cid and (cid not in seen or c["casebook_count"] > seen[cid]):
                seen[cid] = c["casebook_count"]
    return [cid for cid, _ in sorted(seen.items(), key=lambda x: -x[1])
            if cid not in LANDMARKS]


async def cmd_list(n):
    conn = await asyncpg.connect(prod_url())
    queue, out = LANDMARKS + curated_ids(), []
    briefed = {r["case_id"] for r in await conn.fetch(
        "SELECT case_id FROM ai_summaries WHERE case_id = ANY($1)", queue)}
    exists = {r["id"]: r for r in await conn.fetch(
        "SELECT id, title, decision_date FROM cases WHERE id = ANY($1)", queue)}
    for cid in queue:
        if cid in briefed or cid not in exists:
            continue
        r = exists[cid]
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
    if not text:
        print(f"NO OPINION TEXT for {cid}", file=sys.stderr); sys.exit(1)
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
    else:
        print(__doc__); sys.exit(1)


if __name__ == "__main__":
    main()
