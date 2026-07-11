#!/usr/bin/env python3
"""Publish a validated structured-summary artifact without replacing the original brief."""

import argparse
import asyncio
import json
import os
from pathlib import Path

import asyncpg


async def publish(path: Path):
    artifact = json.loads(path.read_text(encoding="utf-8"))
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        result = await conn.execute(
            """UPDATE ai_summaries
               SET structured_summary = $1::jsonb,
                   structured_model = $2,
                   structured_created_at = NOW()
               WHERE case_id = $3""",
            json.dumps(artifact["candidate"]), artifact["model"], artifact["case_id"],
        )
        if result != "UPDATE 1":
            raise RuntimeError(f"Expected one summary update, got {result}")
        print(f"published_case_id={artifact['case_id']}")
    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    asyncio.run(publish(args.artifact))


if __name__ == "__main__":
    main()
