#!/home/sage/.venvs/lawdata/bin/python
"""Export a target case's outgoing citation edges to the production site database.

    python export_cited_cases.py <cluster_id> [<cluster_id> ...]

The CourtListener citation map is opinion-level. This uses the pipeline's local lookup to
convert both sides to clusters, creates minimal stubs for missing cited cases, and inserts only
missing cluster-level edges. Existing case records are never overwritten.
"""
import asyncio
import datetime
import json
import os
import sys

import asyncpg
import duckdb

import citator_pipeline as P


HERE = os.path.dirname(__file__)
COURT_AUTH = os.path.join(HERE, "data", "court_authority.parquet")
CL_OPINION = "https://www.courtlistener.com/opinion/{}/"


def prod_url():
    for path in ("/mnt/d/dev/ai-law-research/backend/.env", "/mnt/d/dev/ai-law-research/.env"):
        if os.path.exists(path):
            for line in open(path):
                if line.startswith("PROD_DATABASE_URL="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("PROD_DATABASE_URL not found")


def court_metadata():
    con = duckdb.connect(); con.execute("SET enable_progress_bar=false")
    rows = con.execute(
        f"SELECT court_id, court_name, citation_string FROM read_parquet('{COURT_AUTH}')"
    ).fetchall()
    return {court_id: (name or court_id, citation or name or court_id)
            for court_id, name, citation in rows}


async def export_target(conn, target_id, cited_ids, metadata, courts):
    async with conn.transaction():
        await conn.execute("SELECT pg_advisory_xact_lock(hashtext($1))", f"cited-cases:{target_id}")
        if not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM cases WHERE id = $1)", str(target_id)):
            raise ValueError(f"target case {target_id} is not in the production database")

        court_ids = {}
        for court_id in {m.get("court_id") for m in metadata.values() if m.get("court_id")}:
            name, abbreviation = courts.get(court_id, (court_id, court_id))
            site_id = await conn.fetchval(
                """INSERT INTO courts (name, abbreviation)
                   VALUES ($1, $2)
                   ON CONFLICT (name) DO UPDATE SET abbreviation = COALESCE(courts.abbreviation, EXCLUDED.abbreviation)
                   RETURNING id""",
                name, abbreviation,
            )
            court_ids[court_id] = site_id

        stubs = []
        for cited_id in cited_ids:
            item = metadata.get(cited_id)
            if not item:
                continue
            title = item.get("case_name") or f"CourtListener case {cited_id}"
            if len(title) > 300:
                title = title[:300].rsplit(" ", 1)[0] + " ..."
            decision_date = item.get("date_filed")
            if isinstance(decision_date, str):
                decision_date = datetime.date.fromisoformat(decision_date[:10])
            provenance = json.dumps({"source": "outgoing_citation_stub"})
            stubs.append((str(cited_id), court_ids.get(item.get("court_id")), title,
                          decision_date, CL_OPINION.format(cited_id), provenance))

        await conn.executemany(
            """INSERT INTO cases
                 (id, court_id, title, decision_date, source_url, metadata, precedential)
               VALUES ($1, $2, $3, $4, $5, $6::jsonb, true)
               ON CONFLICT (id) DO NOTHING""",
            stubs,
        )

        existing = {row["target_case_id"] for row in await conn.fetch(
            "SELECT DISTINCT target_case_id FROM citations WHERE source_case_id = $1",
            str(target_id),
        )}
        edges = [(str(target_id), str(cited_id)) for cited_id in cited_ids
                 if cited_id in metadata and str(cited_id) not in existing]
        await conn.executemany(
            """INSERT INTO citations (source_case_id, target_case_id, confidence)
               VALUES ($1, $2, 1.0)""",
            edges,
        )
    return len(stubs), len(edges)


async def run(target_ids):
    courts = court_metadata()
    conn = await asyncpg.connect(prod_url())
    try:
        for target_id in target_ids:
            cited_ids = P.trace_cited(target_id)
            metadata = P.resolve(cited_ids)
            stubs, edges = await export_target(conn, target_id, cited_ids, metadata, courts)
            print(f"target {target_id}: {len(cited_ids)} cited clusters, "
                  f"{stubs} stubs considered, {edges} edges inserted")
    finally:
        await conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: export_cited_cases.py <cluster_id> [...]")
        raise SystemExit(1)
    asyncio.run(run([int(arg) for arg in sys.argv[1:]]))
