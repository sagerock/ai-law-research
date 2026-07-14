#!/usr/bin/env python3
"""Import Albert v. McKay & Co., 174 Cal. 451 (1917), from CourtListener."""

import asyncio
import html
import json
import os
import re
import urllib.request
from datetime import date

import asyncpg


CLUSTER_ID = "3307250"
CLUSTER_URL = f"https://www.courtlistener.com/api/rest/v4/clusters/{CLUSTER_ID}/"


def courtlistener_get(url):
    token = os.environ["COURTLISTENER_API_KEY"]
    request = urllib.request.Request(url, headers={"Authorization": f"Token {token}"})
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def strip_html(value):
    value = re.sub(r"</?(?:p|div|h[1-6]|blockquote|li|br)[^>]*>", "\n", value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[ \t]+", " ", value)
    return html.unescape(re.sub(r"\n\s*\n+", "\n\n", value)).strip()


def citation_text(citation):
    return " ".join(
        str(citation.get(field) or "").strip()
        for field in ("volume", "reporter", "page")
    ).strip()


def fetch_case():
    cluster = courtlistener_get(CLUSTER_URL)
    opinions = [courtlistener_get(url) for url in cluster.get("sub_opinions", [])]
    content = "\n\n".join(
        strip_html(
            opinion.get("html_with_citations")
            or opinion.get("html_columbia")
            or opinion.get("html")
            or opinion.get("plain_text")
        )
        for opinion in opinions
    ).strip()
    citations = [citation_text(citation) for citation in cluster.get("citations", [])]
    citations = [citation for citation in citations if citation]
    reporter_cite = next((citation for citation in citations if " Cal." in citation), citations[0])

    docket = courtlistener_get(cluster["docket"])
    return {
        "title": cluster["case_name"],
        "decision_date": date.fromisoformat(cluster["date_filed"]),
        "reporter_cite": reporter_cite,
        "docket_number": docket.get("docket_number"),
        "content": content,
        "source_url": "https://www.courtlistener.com" + cluster["absolute_url"],
        "metadata": json.dumps(
            {
                "cl_court": "Cal.",
                "docket_number": docket.get("docket_number"),
                "parallel_citations": citations,
                "import_source": "CourtListener",
            }
        ),
    }


async def main():
    database_url = os.getenv("DATABASE_PUBLIC_URL") or os.getenv("PROD_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    case = fetch_case()
    if not case["content"]:
        raise RuntimeError("CourtListener returned an empty opinion")

    connection = await asyncpg.connect(database_url)
    try:
        court_id = await connection.fetchval(
            "SELECT id FROM courts WHERE name IN ('Supreme Court of California', 'California Supreme Court') "
            "ORDER BY CASE WHEN name = 'Supreme Court of California' THEN 0 ELSE 1 END LIMIT 1"
        )
        if court_id is None:
            court_id = await connection.fetchval(
                "INSERT INTO courts (name, jurisdiction, level) VALUES ($1, $2, $3) RETURNING id",
                "Supreme Court of California",
                "state",
                "supreme",
            )

        await connection.execute(
            """
            INSERT INTO cases (
                id, title, docket_number, decision_date, court_id, reporter_cite,
                content, source_url, metadata, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                docket_number = EXCLUDED.docket_number,
                decision_date = EXCLUDED.decision_date,
                court_id = EXCLUDED.court_id,
                reporter_cite = EXCLUDED.reporter_cite,
                content = EXCLUDED.content,
                source_url = EXCLUDED.source_url,
                metadata = COALESCE(cases.metadata, '{}'::jsonb) || EXCLUDED.metadata,
                updated_at = NOW()
            """,
            CLUSTER_ID,
            case["title"],
            case["docket_number"],
            case["decision_date"],
            court_id,
            case["reporter_cite"],
            case["content"],
            case["source_url"],
            case["metadata"],
        )
        print(
            f"Imported {case['title']} ({CLUSTER_ID}) | {case['reporter_cite']} | "
            f"{len(case['content']):,} characters"
        )
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
