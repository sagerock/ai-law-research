#!/home/sage/.venvs/lawdata/bin/python
"""prefetch_opinions_local.py — graduate a target's citer stubs from the LOCAL opinion corpus.

Replaces the CourtListener /fetch-opinion round-trips with a single scan of the opinions Parquet
(`text_clean`, already cleaned) and a direct DB write. One corpus scan covers the whole batch,
so 200 citers and 20,000 citers cost roughly the same wall-clock — no API in the loop.

    python prefetch_opinions_local.py <target_cluster_id> [<target_cluster_id> ...]

Run after export_to_db.py + stub_citers.py (the stub rows must exist to graduate).
"""
import asyncio, asyncpg, duckdb, hashlib, os, sys

BACKEND = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend")
sys.path.insert(0, BACKEND)
from courtlistener_opinions import SubOpinion, assemble_sub_opinions

OPINIONS = "/mnt/d/backups/ai-law-research/data/courtlistener/parquet/opinions_text/*.parquet"

def prod_url():
    for path in ("/mnt/d/dev/ai-law-research/backend/.env", "/mnt/d/dev/ai-law-research/.env"):
        if os.path.exists(path):
            for line in open(path):
                if line.startswith("PROD_DATABASE_URL="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("PROD_DATABASE_URL not found")


async def citer_ids(target_ids):
    conn = await asyncpg.connect(prod_url())
    ids = set()
    for tid in target_ids:
        rows = await conn.fetch(
            "SELECT citer_cluster_id FROM case_authority_citers WHERE target_case_id = $1", str(tid))
        ids |= {int(r["citer_cluster_id"]) for r in rows}
    await conn.close()
    return sorted(ids)


def stitch_opinions(cluster_ids):
    """One scan of the corpus -> {cluster_id: stitched opinion text}."""
    con = duckdb.connect(); con.execute("SET enable_progress_bar=false")
    con.execute("SET threads=4"); con.execute("SET memory_limit='8GB'")
    con.execute("CREATE TEMP TABLE want(cluster_id BIGINT)")
    con.executemany("INSERT INTO want VALUES (?)", [(c,) for c in cluster_ids])
    rows = con.execute(f"""
        SELECT o.opinion_id, o.cluster_id, o.type, o.author_str, o.text_source, o.text_clean
        FROM read_parquet('{OPINIONS}') o JOIN want w ON w.cluster_id = o.cluster_id
        WHERE o.text_clean IS NOT NULL AND length(o.text_clean) > 100
        ORDER BY o.cluster_id, o.type, o.opinion_id
    """).fetchall()
    by_cluster = {}
    for opinion_id, cid, otype, author, text_source, text in rows:
        by_cluster.setdefault(cid, []).append(
            (opinion_id, otype, author, text_source, text)
        )
    out = {}
    for cid, parts in by_cluster.items():
        document = assemble_sub_opinions(cid, [
            SubOpinion(str(opinion_id), otype, author, text, text_source or "text_clean")
            for opinion_id, otype, author, text_source, text in parts
        ])
        if document:
            out[cid] = document.text
    return out


async def push(texts):
    conn = await asyncpg.connect(prod_url())
    graduated = 0
    for cid, text in texts.items():
        # only graduate stubs; never overwrite a real case that already has content
        status = await conn.execute(
            """UPDATE cases SET content = $1, content_hash = $2, updated_at = NOW()
               WHERE id = $3 AND (content IS NULL OR length(content) < 200)""",
            text, hashlib.sha256(text.encode("utf-8")).hexdigest(), str(cid))
        if status.endswith("1"):
            graduated += 1
    await conn.close()
    return graduated


def main():
    targets = sys.argv[1:]
    if not targets:
        print("usage: prefetch_opinions_local.py <target_cluster_id> [...]"); sys.exit(1)
    ids = asyncio.run(citer_ids(targets))
    print(f"{len(ids)} citer stubs; scanning local corpus for opinion text...", flush=True)
    texts = stitch_opinions(ids)
    print(f"  found opinion text for {len(texts)}/{len(ids)} citers", flush=True)
    graduated = asyncio.run(push(texts))
    no_text = len(ids) - len(texts)
    print(f"DONE: {graduated} stubs graduated from local corpus, "
          f"{no_text} had no opinion text in the corpus", flush=True)


if __name__ == "__main__":
    main()
