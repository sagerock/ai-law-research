#!/home/sage/.venvs/lawdata/bin/python
"""stub_citers.py — create lightweight stub `cases` rows for a target's citers.

    python stub_citers.py <target_cluster_id> [<target_cluster_id> ...]

Reads the citers already in `case_authority_citers` (pushed by export_to_db.py) and inserts
a minimal stub row into `cases` for each one not already present. A stub carries only what we
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
            """SELECT citer_cluster_id, citer_name, citer_court_name, citer_date
               FROM case_authority_citers WHERE target_case_id = $1""", str(tid))
        created = skipped = 0
        for c in citers:
            cid = c["citer_cluster_id"]
            # metadata carries provenance + the court label so the stub page can show a court
            meta = f'{{"source": "citer_stub", "cl_court": {_json(c["citer_court_name"])}}}'
            status = await conn.execute(
                """INSERT INTO cases (id, title, decision_date, source_url, metadata, precedential)
                   VALUES ($1, $2, $3, $4, $5::jsonb, true)
                   ON CONFLICT (id) DO NOTHING""",
                cid, c["citer_name"], c["citer_date"], CL_OPINION.format(cid), meta)
            if status.endswith("1"):
                created += 1
            else:
                skipped += 1
        print(f"  target {tid}: {created} stubs created, {skipped} already present "
              f"({len(citers)} citers total)")
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
