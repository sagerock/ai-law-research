#!/usr/bin/env python3
"""Publish a validated structured-summary artifact without replacing the original brief."""

import argparse
import asyncio
import json
import os
from pathlib import Path

import asyncpg


async def publish(path: Path, provider: str):
    artifact = json.loads(path.read_text(encoding="utf-8"))
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        result = await conn.execute(
            """INSERT INTO structured_summary_candidates
               (case_id, provider, model, summary, created_at)
               VALUES ($1, $2, $3, $4::jsonb, NOW())
               ON CONFLICT (case_id, provider) DO UPDATE SET
                   model = EXCLUDED.model,
                   summary = EXCLUDED.summary,
                   created_at = NOW()""",
            artifact["case_id"], provider, artifact["model"], json.dumps(artifact["candidate"]),
        )
        print(f"published_case_id={artifact['case_id']} provider={provider} result={result}")
    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--provider", required=True)
    args = parser.parse_args()
    asyncio.run(publish(args.artifact, args.provider))


if __name__ == "__main__":
    main()
