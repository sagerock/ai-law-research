#!/home/sage/.venvs/lawdata/bin/python
"""Populate authority and outgoing-citation data for every case in a casebook.

    python export_casebook_citations.py <casebook_id>

Existing targets with both data sets are skipped. Work is committed per target so an interrupted
run can be safely restarted without discarding completed cases.
"""
import asyncio
import sys

import asyncpg

import citator_pipeline as P
import export_cited_cases as outgoing
import export_to_db as authority


async def run(casebook_id):
    conn = await asyncpg.connect(authority.prod_url())
    try:
        targets = await conn.fetch(
            """SELECT cc.case_id, c.title,
                      EXISTS (SELECT 1 FROM case_authority_citers ac
                              WHERE ac.target_case_id = cc.case_id) AS has_authority,
                      EXISTS (SELECT 1 FROM citations ci
                              WHERE ci.source_case_id = cc.case_id) AS has_outgoing
               FROM casebook_cases cc
               JOIN cases c ON c.id = cc.case_id
               WHERE cc.casebook_id = $1
               ORDER BY cc.sort_order NULLS LAST, c.title""",
            casebook_id,
        )
    finally:
        await conn.close()

    labels = authority.court_labels()
    courts = outgoing.court_metadata()
    conn = await asyncpg.connect(authority.prod_url())
    try:
        for index, target in enumerate(targets, 1):
            case_id = target["case_id"]
            if not case_id.isdigit():
                print(f"[{index}/{len(targets)}] {case_id} is not a CourtListener cluster; skipping",
                      flush=True)
                continue
            if target["has_authority"] and target["has_outgoing"]:
                print(f"[{index}/{len(targets)}] {case_id} complete; skipping", flush=True)
                continue
            print(f"[{index}/{len(targets)}] {case_id} {target['title']}", flush=True)
            if not target["has_authority"]:
                rows, _ = P.run(int(case_id))
                count = await authority.push(int(case_id), rows, labels)
                print(f"  authority: {count}", flush=True)
            if not target["has_outgoing"]:
                cited_ids = P.trace_cited(int(case_id))
                metadata = P.resolve(cited_ids)
                _, count = await outgoing.export_target(
                    conn, int(case_id), cited_ids, metadata, courts,
                )
                print(f"  outgoing: {count}", flush=True)
    finally:
        await conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: export_casebook_citations.py <casebook_id>")
        raise SystemExit(1)
    asyncio.run(run(int(sys.argv[1])))
