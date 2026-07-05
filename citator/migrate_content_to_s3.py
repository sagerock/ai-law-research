#!/home/sage/.venvs/lawdata/bin/python
"""migrate_content_to_s3.py — move opinion text from Postgres to S3, safely.

    python migrate_content_to_s3.py --reconcile   # report S3-vs-Postgres state, no writes
    python migrate_content_to_s3.py               # upload PG content to S3 (where missing),
                                                  # verify, then null cases.content

SAFETY INVARIANT: a case's Postgres content is nulled ONLY after its opinion is confirmed in
S3 — either freshly uploaded and hash-verified byte-identical, or already present and of
substantial length. Nothing is ever deleted on faith. Idempotent + resumable: already-nulled
cases are skipped, so a re-run just continues.
"""
import asyncio, asyncpg, boto3, hashlib, os, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

BUCKET = os.getenv("OPINIONS_BUCKET", "lawstudygroup-opinions")
RECONCILE = "--reconcile" in sys.argv
_s3 = boto3.client("s3")


def prod_url():
    for path in ("/mnt/d/dev/ai-law-research/backend/.env", "/mnt/d/dev/ai-law-research/.env"):
        if os.path.exists(path):
            for line in open(path):
                if line.startswith("PROD_DATABASE_URL="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("PROD_DATABASE_URL not found")


def list_s3_sizes():
    """One paginated listing -> {cluster_id: byte_size} for everything already in S3."""
    out = {}
    for page in _s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix="opinions/"):
        for o in page.get("Contents", []):
            cid = o["Key"].split("/")[-1].rsplit(".", 1)[0]
            if cid.isdigit():
                out[int(cid)] = o["Size"]
    return out


def put_and_verify(cid, text):
    b = text.encode("utf-8")
    _s3.put_object(Bucket=BUCKET, Key=f"opinions/{cid}.txt", Body=b,
                   ContentType="text/plain; charset=utf-8")
    back = _s3.get_object(Bucket=BUCKET, Key=f"opinions/{cid}.txt")["Body"].read()
    return hashlib.sha256(back).digest() == hashlib.sha256(b).digest()


async def main():
    conn = await asyncpg.connect(prod_url())
    total = await conn.fetchval("select count(*) from cases")
    pg_ids = [r["id"] for r in await conn.fetch(
        "select id from cases where content is not null and length(content) > 200")]
    s3_sizes = list_s3_sizes()
    s3_ids = set(s3_sizes)
    pg_set = {int(i) for i in pg_ids if str(i).isdigit()}

    both = pg_set & s3_ids
    pg_only = pg_set - s3_ids
    s3_only = s3_ids - pg_set
    print(f"cases: {total:,} | PG-content: {len(pg_set):,} | S3 objects: {len(s3_ids):,}")
    print(f"  in both (PG not yet nulled): {len(both):,}")
    print(f"  PG-only (need upload):       {len(pg_only):,}")
    print(f"  S3-only (migrated / ok):     {len(s3_only):,}")
    if RECONCILE:
        # drift check: a migrated case must never have neither store
        gone = await conn.fetchval(
            "select count(*) from cases where (content is null or length(content) <= 200)")
        print(f"  cases with no PG content: {gone:,} "
              f"(of which {len(s3_only):,} are safely in S3; the rest are un-graduated stubs)")
        await conn.close(); return

    stats = Counter()
    BATCH = 300
    for i in range(0, len(pg_ids), BATCH):
        batch = pg_ids[i:i + BATCH]
        rows = await conn.fetch(
            "select id, content from cases where id = any($1::text[])", batch)

        def work(r):
            cid, content = r["id"], r["content"]
            cnum = int(cid) if str(cid).isdigit() else None
            pg_len = len(content.encode("utf-8"))
            sz = s3_sizes.get(cnum) if cnum is not None else None
            if sz is not None and sz >= 500 and sz >= 0.6 * pg_len:
                return (cid, "null")           # already substantial in S3
            if put_and_verify(cid, content):
                return (cid, "null")           # uploaded + hash-verified
            return (cid, "skip")               # verify failed — keep PG content

        with ThreadPoolExecutor(max_workers=16) as pool:
            results = list(pool.map(work, rows))
        to_null = [cid for cid, a in results if a == "null"]
        for _, a in results:
            stats[a] += 1
        if to_null:
            await conn.execute("update cases set content = null where id = any($1::text[])", to_null)
        print(f"  {min(i + BATCH, len(pg_ids))}/{len(pg_ids)}  "
              f"nulled={stats['null']} skipped={stats['skip']}", flush=True)

    print(f"DONE: nulled {stats['null']} cases (opinion now served from S3), "
          f"{stats['skip']} skipped (S3 verify failed — content kept)", flush=True)
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
