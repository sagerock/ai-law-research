#!/home/sage/.venvs/lawdata/bin/python
"""export_to_db.py — push a target case's authority-tier citers to the site database.

    python export_to_db.py <cluster_id> [<cluster_id> ...]

Runs the mechanical pipeline (trace -> resolve -> tier) for each target and upserts the
result into `case_authority_citers` in PROD_DATABASE_URL. Additive only; safe to re-run
(idempotent upsert per (target, citer)). The 320 GB corpus never leaves this machine —
only the small tiered result (a few dozen rows per case) is pushed.
"""
import asyncio, asyncpg, duckdb, os, sys, re, datetime
import citator_pipeline as P

HERE = os.path.dirname(__file__)
COURT_AUTH = os.path.join(HERE, "data", "court_authority.parquet")


def prod_url():
    for path in ("/mnt/d/dev/ai-law-research/backend/.env", "/mnt/d/dev/ai-law-research/.env"):
        if os.path.exists(path):
            for line in open(path):
                if line.startswith("PROD_DATABASE_URL="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("PROD_DATABASE_URL not found")


def court_labels():
    """court_id -> short display label (citation_string, e.g. '1st Cir.', 'D. Mass.', 'N.Y.')."""
    con = duckdb.connect(); con.execute("SET enable_progress_bar=false")
    out = {}
    for cid, cite, name in con.execute(
            f"select court_id, citation_string, court_name from read_parquet('{COURT_AUTH}')").fetchall():
        out[cid] = cite or name
    return out


SCHEMA = open(os.path.join(HERE, "..", "migrations", "006_authority_citers.sql")).read()


async def push(target_id, rows, labels):
    conn = await asyncpg.connect(prod_url())
    await conn.execute(SCHEMA)
    # replace this target's rows so re-runs reflect the latest computation
    await conn.execute("DELETE FROM case_authority_citers WHERE target_case_id = $1", str(target_id))
    n = 0
    for cid, name, court_id, date, tl, C in rows:
        d = None
        if date:
            try:
                d = datetime.date.fromisoformat(date[:10])
            except ValueError:
                d = None
        await conn.execute("""
            INSERT INTO case_authority_citers
              (target_case_id, citer_cluster_id, citer_name, citer_court_id,
               citer_court_name, citer_date, tier)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
            ON CONFLICT (target_case_id, citer_cluster_id) DO UPDATE SET
              citer_name=EXCLUDED.citer_name, citer_court_id=EXCLUDED.citer_court_id,
              citer_court_name=EXCLUDED.citer_court_name, citer_date=EXCLUDED.citer_date,
              tier=EXCLUDED.tier, run_date=CURRENT_DATE
        """, str(target_id), str(cid), name, court_id, labels.get(court_id), d, tl)
        n += 1
    await conn.close()
    return n


def main():
    if len(sys.argv) < 2:
        print("usage: export_to_db.py <cluster_id> [...]"); sys.exit(1)
    labels = court_labels()
    for arg in sys.argv[1:]:
        tid = int(arg)
        rows, T = P.run(tid)  # computes + writes the markdown report too
        n = asyncio.run(push(tid, rows, labels))
        print(f"  -> pushed {n} citer rows for {T['case_name']} (cluster {tid})")


if __name__ == "__main__":
    main()
