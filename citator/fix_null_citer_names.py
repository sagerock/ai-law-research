#!/home/sage/.venvs/lawdata/bin/python
"""fix_null_citer_names.py — one-time repair for the case_name coalescing bug.

build_cluster_court.py originally took only `case_name` from the clusters CSV, but ~50k
CL clusters store their name only in case_name_full/_short — so export_to_db.py pushed
NULL citer_names and stub_citers.py fell back to generic "<court> case (<year>)" titles.
The parquet is rebuilt with COALESCE; this backfills the rows already in prod:

  1. case_authority_citers.citer_name  where NULL/empty
  2. cases.title                       where it's a citer_stub with the generic fallback

Only updates rows whose cluster_id now has a real name in the parquet. --dry-run to preview.
"""
import asyncio, asyncpg, duckdb, os, sys

HERE = os.path.dirname(__file__)
CLUSTER_COURT = os.path.join(HERE, "data", "cluster_court.parquet")
from stub_citers import prod_url


def parquet_names(cluster_ids):
    if not cluster_ids:
        return {}
    con = duckdb.connect(); con.execute("SET enable_progress_bar=false")
    con.execute("CREATE TEMP TABLE want(cluster_id BIGINT)")
    con.executemany("INSERT INTO want VALUES (?)", [(int(c),) for c in cluster_ids])
    return dict(con.execute(f"""
        SELECT cc.cluster_id, cc.case_name
        FROM read_parquet('{CLUSTER_COURT}') cc JOIN want w USING (cluster_id)
        WHERE cc.case_name IS NOT NULL""").fetchall())


async def run(dry):
    conn = await asyncpg.connect(prod_url())

    # 1. authority rows with no citer name
    rows = await conn.fetch("""SELECT DISTINCT citer_cluster_id FROM case_authority_citers
                               WHERE citer_name IS NULL OR citer_name = ''""")
    auth_ids = [r[0] for r in rows]
    # 2. stub cases that got the generic fallback title
    stubs = await conn.fetch("""SELECT id, title FROM cases
                                WHERE metadata->>'source' = 'citer_stub'
                                  AND title LIKE '% case (%'""")
    print(f"case_authority_citers null/empty citer_name: {len(auth_ids)} cluster_ids")
    print(f"cases with generic stub title:               {len(stubs)}")

    names = parquet_names(sorted({*[int(c) for c in auth_ids], *[int(s['id']) for s in stubs]}))
    print(f"names recovered from rebuilt parquet:        {len(names)}")

    fixed_auth = fixed_stub = 0
    for cid in auth_ids:
        name = names.get(int(cid))
        if not name:
            print(f"  ! still nameless in corpus: {cid}"); continue
        if not dry:
            await conn.execute("""UPDATE case_authority_citers SET citer_name = $1
                                  WHERE citer_cluster_id = $2
                                    AND (citer_name IS NULL OR citer_name = '')""", name, cid)
        fixed_auth += 1
    for s in stubs:
        name = names.get(int(s["id"]))
        if not name:
            print(f"  ! still nameless in corpus: {s['id']} ({s['title']})"); continue
        if not dry:
            await conn.execute("UPDATE cases SET title = $1 WHERE id = $2 AND title = $3",
                               name, s["id"], s["title"])
        fixed_stub += 1
        print(f"  {s['id']}: {s['title']!r} -> {name[:80]!r}")

    verb = "would fix" if dry else "fixed"
    print(f"\n{verb}: {fixed_auth} citer_name rows, {fixed_stub} stub titles")
    await conn.close()


if __name__ == "__main__":
    asyncio.run(run(dry="--dry-run" in sys.argv))
