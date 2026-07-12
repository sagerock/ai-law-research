#!/home/sage/.venvs/lawdata/bin/python
"""stub_citers.py — create lightweight stub `cases` rows for a target's citers.

    python stub_citers.py <target_cluster_id> [<target_cluster_id> ...]

Reads the newest 100 citers per authority tier (the same cap exposed by the API) and inserts a
minimal stub row into `cases` for each one not already present. A stub carries only what we
already computed (id = CL cluster_id, title, date, court label, CourtListener source link) and
NO opinion text — so the site's existing lazy-fetch "graduates" it to a full case on first visit
(main.py get_case). ON CONFLICT DO NOTHING: never touches a real, already-imported case.

Effect: the authority endpoint's LEFT JOIN to `cases` now sees these citers, so `in_site` flips
true and the panel links to them internally — no frontend change needed for the linking itself.
"""
import asyncio, asyncpg, os, sys

CL_OPINION = "https://www.courtlistener.com/opinion/{}/"  # CL redirects to the canonical slug


def prod_url():
    for path in ("/mnt/d/dev/ai-law-research/backend/.env", "/mnt/d/dev/ai-law-research/.env"):
        if os.path.exists(path):
            for line in open(path):
                if line.startswith("PROD_DATABASE_URL="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("PROD_DATABASE_URL not found")


async def run(target_ids):
    conn = await asyncpg.connect(prod_url())
    for tid in target_ids:
        citers = await conn.fetch(
            """WITH ranked AS (
                   SELECT citer_cluster_id, citer_name, citer_court_name, citer_date,
                          ROW_NUMBER() OVER (
                              PARTITION BY tier ORDER BY citer_date DESC NULLS LAST
                          ) AS rn
                   FROM case_authority_citers
                   WHERE target_case_id = $1
               )
               SELECT citer_cluster_id, citer_name, citer_court_name, citer_date
               FROM ranked WHERE rn <= 100""",
            str(tid),
        )
        # skip ids already present so the executemany batch is pure inserts
        existing = {r["id"] for r in await conn.fetch(
            "SELECT id FROM cases WHERE id = ANY($1)",
            [c["citer_cluster_id"] for c in citers])}
        records = []
        for c in citers:
            cid = c["citer_cluster_id"]
            if cid in existing:
                continue
            # metadata carries provenance + the court label so the stub page can show a court
            meta = f'{{"source": "citer_stub", "cl_court": {_json(c["citer_court_name"])}}}'
            # a few corpus clusters have no case_name — cases.title is NOT NULL, so fall back
            # to court + year (e.g. "8th Cir. case (1989)") rather than crash
            title = c["citer_name"]
            if not title:
                yr = f" ({c['citer_date'].year})" if c["citer_date"] else ""
                title = f"{c['citer_court_name'] or 'Court'} case{yr}"
            # consolidated-appeal names from case_name_full can run >2700 bytes, which
            # overflows the btree cap on idx_cases_title — truncate at a word boundary
            if len(title) > 300:
                title = title[:300].rsplit(" ", 1)[0] + " …"
            records.append((cid, title, c["citer_date"], CL_OPINION.format(cid), meta))
        # executemany pipelines the batch (row-by-row was one ~50ms round trip per citer;
        # landmark targets have 100k+); ON CONFLICT still guards against races
        await conn.executemany(
            """INSERT INTO cases (id, title, decision_date, source_url, metadata, precedential)
               VALUES ($1, $2, $3, $4, $5::jsonb, true)
               ON CONFLICT (id) DO NOTHING""", records)
        print(f"  target {tid}: {len(records)} stubs created, {len(existing)} already present "
              f"({len(citers)} citers total)", flush=True)
    await conn.close()


def _json(s):
    if s is None:
        return "null"
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def main():
    if len(sys.argv) < 2:
        print("usage: stub_citers.py <target_cluster_id> [...]"); sys.exit(1)
    asyncio.run(run([int(a) for a in sys.argv[1:]]))


if __name__ == "__main__":
    main()
