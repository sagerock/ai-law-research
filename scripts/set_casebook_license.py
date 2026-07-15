"""Set the content-license metadata on a casebook.

Full text (reader / Q&A corpus) may only be loaded for casebooks whose license
permits it; the license stored here is surfaced by the textbook API and rendered
as attribution on the textbook pages.

Usage:
    python scripts/set_casebook_license.py --database-url <url> [--casebook-id 2467]
"""

import argparse
import asyncio
import json
import os

import asyncpg

CHENG_LICENSE = {
    "name": "CC BY-NC-SA 4.0",
    "url": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
    "attribution": (
        "Full text of “Evidence” (Draft v38) by Edward K. Cheng, "
        "reformatted for the web by Tortwell, licensed under"
    ),
}


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--casebook-id", type=int, default=2467)
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL or --database-url is required")

    conn = await asyncpg.connect(args.database_url)
    try:
        row = await conn.fetchrow(
            "SELECT title, metadata FROM casebooks WHERE id = $1", args.casebook_id
        )
        if row is None:
            raise SystemExit(f"casebook {args.casebook_id} not found")
        metadata = row["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata) if metadata else {}
        metadata = metadata or {}
        metadata["license"] = CHENG_LICENSE
        await conn.execute(
            "UPDATE casebooks SET metadata = $2::jsonb WHERE id = $1",
            args.casebook_id,
            json.dumps(metadata),
        )
        print(f"license set on casebook {args.casebook_id}: {row['title']}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
