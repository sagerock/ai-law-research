#!/usr/bin/env python3
"""Report completion and validation metadata for the 10-case source-link pilot."""

import asyncio
import json
import os

import asyncpg


PILOT_IDS = [
    "111722", "104200", "103012", "84759", "104357",
    "107082", "105221", "107024", "118144", "96889",
]


async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        rows = await conn.fetch(
            """SELECT c.id, c.title, s.model, s.content_hash, s.created_at,
                      (SELECT COUNT(*) FROM opinion_passages p
                       WHERE p.case_id = c.id AND p.content_hash = s.content_hash) AS passages
               FROM cases c
               JOIN structured_summary_candidates s
                 ON s.case_id = c.id AND s.provider = 'claude'
               WHERE c.id = ANY($1)
               ORDER BY array_position($1, c.id)""",
            PILOT_IDS,
        )
        failures = await conn.fetch(
            """SELECT case_id, stage, error, created_at
               FROM structured_summary_failures
               WHERE case_id = ANY($1)
               ORDER BY created_at""",
            PILOT_IDS,
        )
        print(json.dumps({
            "completed": [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "model": row["model"],
                    "content_hash": row["content_hash"],
                    "passages": row["passages"],
                    "created_at": row["created_at"].isoformat(),
                }
                for row in rows
            ],
            "failures": [
                {
                    "case_id": row["case_id"],
                    "stage": row["stage"],
                    "error": row["error"],
                    "created_at": row["created_at"].isoformat(),
                }
                for row in failures
            ],
        }, indent=2))
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
