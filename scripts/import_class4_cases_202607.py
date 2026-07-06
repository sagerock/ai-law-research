#!/usr/bin/env python3
"""
Import the two Summer 2026 Evidence off-book cases missing from production:

  - Carroll v. Trump, 660 F. Supp. 3d 196 (S.D.N.Y. Mar. 10, 2023)  [cluster 9882744]
    (the motion-in-limine ruling — FRE 415/413(d)/403, Access Hollywood tape;
    distinct from the 2022 anti-SLAPP opinion already in the DB as id 9872801)
  - Stephens v. Miller, 13 F.3d 998 (7th Cir. 1994) (en banc)        [cluster 660220]

Samia v. United States, 599 U.S. 635 (2023) is already present (id 10049665).

Follows the same cases-table insert as scripts/import_evidence_cases.py, but
fetches text straight from the CourtListener v4 API (these two aren't in the
law-hub cache). court_id left NULL; metadata.cl_court carries the court label
the way citator/stub_citers.py does.

Run from repo root:  python scripts/import_class4_cases_202607.py
Requires PROD_DATABASE_URL and COURTLISTENER_API_KEY in .env / environment.
"""

import asyncio
import json
import os
import re
import urllib.request

import asyncpg

CL_BASE = "https://www.courtlistener.com/api/rest/v4"

CASES = [
    {
        "cluster_id": "9882744",
        "title": "Carroll v. Trump",
        "reporter_cite": "660 F. Supp. 3d 196",
        "cl_court": "S.D.N.Y.",
    },
    {
        "cluster_id": "660220",
        "title": "Stephens v. Miller",
        "reporter_cite": "13 F.3d 998",
        "cl_court": "7th Cir.",
    },
]


def load_env():
    if os.path.exists(".env"):
        for line in open(".env"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v)


def cl_get(path_or_url):
    url = path_or_url if path_or_url.startswith("http") else f"{CL_BASE}{path_or_url}"
    req = urllib.request.Request(
        url, headers={"Authorization": f"Token {os.environ['COURTLISTENER_API_KEY']}"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def strip_html(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", s).strip()


def fetch_case(spec):
    cluster = cl_get(f"/clusters/{spec['cluster_id']}/")
    opinions = cl_get(f"/opinions//?cluster={spec['cluster_id']}".replace("//", "/"))
    texts = []
    for op in opinions["results"]:
        text = op.get("plain_text") or ""
        html = strip_html(op.get("html_with_citations") or op.get("html") or "")
        texts.append(html if len(html) > len(text) else text)
    content = "\n\n".join(t for t in texts if t).strip() or None
    return {
        "id": spec["cluster_id"],
        "title": spec["title"],
        "decision_date": cluster.get("date_filed"),  # 'YYYY-MM-DD'
        "reporter_cite": spec["reporter_cite"],
        "content": content,
        "source_url": "https://www.courtlistener.com" + (cluster.get("absolute_url") or ""),
        "metadata": json.dumps({"cl_court": spec["cl_court"]}),
    }


async def main():
    load_env()
    db_url = os.getenv("PROD_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: PROD_DATABASE_URL not set")
        return

    rows = [fetch_case(spec) for spec in CASES]
    for r in rows:
        print(f"fetched: {r['title']} | {r['reporter_cite']} | "
              f"{len(r['content'] or ''):,} chars | filed {r['decision_date']}")

    conn = await asyncpg.connect(db_url)
    try:
        for r in rows:
            exists = await conn.fetchrow("SELECT id, title FROM cases WHERE id = $1", r["id"])
            if exists:
                print(f"  skip (exists): {r['title']} ({r['id']})")
                continue
            from datetime import date
            dd = date.fromisoformat(r["decision_date"]) if r["decision_date"] else None
            await conn.execute(
                """
                INSERT INTO cases (id, title, decision_date, court_id, reporter_cite,
                                   content, source_url, metadata, created_at)
                VALUES ($1, $2, $3, NULL, $4, $5, $6, $7, NOW())
                """,
                r["id"], r["title"], dd, r["reporter_cite"],
                r["content"], r["source_url"], r["metadata"],
            )
            print(f"  imported: {r['title']} ({r['id']})")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
