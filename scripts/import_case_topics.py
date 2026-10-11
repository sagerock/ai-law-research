#!/usr/bin/env python3
"""Load a subject taxonomy and a tag review file into topic_doctrines / case_topics.

Inputs are the files written by scripts/tag_collection_topics.py: the taxonomy
(data/topics/<subject>.json) and its review output (data/topics/review/*.json).
Runs in one transaction; --dry-run rolls back after reporting what would change.

AI tags are replaced on re-import. A case with any reviewed tag (reviewed_at set) in
this subject is left alone, so hand corrections are never overwritten.

Local or proxied database:
    python3 scripts/import_case_topics.py --taxonomy data/topics/con_law.json \
        --review data/topics/review/collection-15.json --database-url "$URL" --dry-run

Production has no public Postgres proxy; run it inside the backend container instead:
    python3 scripts/import_case_topics.py --taxonomy ... --review ... --bundle \
        | railway ssh -s Backend -- python -          # add DRY_RUN=0 to apply
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys


def doctrine_rows(taxonomy: dict) -> list[tuple]:
    subject_slug = taxonomy["subject_slug"]
    rows = []
    order = 0
    for topic_rank, topic in enumerate(taxonomy["topics"]):
        for doctrine in topic["doctrines"]:
            rows.append((
                f"{subject_slug}:{doctrine['slug']}", taxonomy["subject"], topic["topic"],
                doctrine["label"], topic_rank, order,
            ))
            order += 1
    return rows


def tag_rows(taxonomy: dict, review: dict) -> list[tuple]:
    subject_slug = taxonomy["subject_slug"]
    known = {row[0] for row in doctrine_rows(taxonomy)}
    rows = []
    for case in review["cases"]:
        slugs = [case["primary"], *case["secondary"]]
        for index, slug in enumerate(dict.fromkeys(slugs)):
            doctrine_id = f"{subject_slug}:{slug}"
            if doctrine_id not in known:
                raise ValueError(f"{case['title']}: {slug!r} is not in the taxonomy")
            rows.append((
                case["case_id"], doctrine_id, index == 0, case["confidence"],
                case["rationale"] if index == 0 else None, review["model"],
            ))
    return rows


async def apply(conn, taxonomy: dict, review: dict, dry_run: bool) -> None:
    doctrines = doctrine_rows(taxonomy)
    tags = tag_rows(taxonomy, review)
    case_ids = sorted({row[0] for row in tags})
    transaction = conn.transaction()
    await transaction.start()
    try:
        await conn.executemany(
            """
            INSERT INTO topic_doctrines (id, subject, topic, label, topic_rank, sort_order)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (id) DO UPDATE SET subject = EXCLUDED.subject, topic = EXCLUDED.topic,
                label = EXCLUDED.label, topic_rank = EXCLUDED.topic_rank,
                sort_order = EXCLUDED.sort_order
            """,
            doctrines,
        )
        reviewed = {
            r["case_id"] for r in await conn.fetch(
                """
                SELECT DISTINCT ct.case_id FROM case_topics ct
                JOIN topic_doctrines d ON d.id = ct.doctrine_id
                WHERE d.subject = $1 AND ct.reviewed_at IS NOT NULL AND ct.case_id = ANY($2)
                """,
                taxonomy["subject"], case_ids,
            )
        }
        replaceable = [c for c in case_ids if c not in reviewed]
        deleted = await conn.execute(
            """
            DELETE FROM case_topics ct USING topic_doctrines d
            WHERE d.id = ct.doctrine_id AND d.subject = $1 AND ct.case_id = ANY($2)
            """,
            taxonomy["subject"], replaceable,
        )
        new_tags = [row for row in tags if row[0] not in reviewed]
        await conn.executemany(
            """
            INSERT INTO case_topics (case_id, doctrine_id, is_primary, confidence, rationale,
                                     source, model)
            VALUES ($1, $2, $3, $4, $5, 'ai', $6)
            """,
            new_tags,
        )
        print(f"doctrines upserted: {len(doctrines)}")
        print(f"cases tagged: {len(replaceable)} (skipped as reviewed: {len(reviewed)})")
        print(f"tags inserted: {len(new_tags)}; previous AI tags removed: {deleted.split()[-1]}")
    except BaseException:
        await transaction.rollback()
        raise
    if dry_run:
        await transaction.rollback()
        print("dry run: rolled back")
    else:
        await transaction.commit()
        print("committed")


async def run(database_url: str, taxonomy: dict, review: dict, dry_run: bool) -> None:
    import asyncpg

    conn = await asyncpg.connect(database_url)
    try:
        await apply(conn, taxonomy, review, dry_run)
    finally:
        await conn.close()


def bundle(taxonomy: dict, review: dict) -> str:
    """A self-contained program for `python -` inside the backend container."""
    source = Path(__file__).read_text()
    return (
        source
        + f"\nTAXONOMY = json.loads({json.dumps(json.dumps(taxonomy))})"
        + f"\nREVIEW = json.loads({json.dumps(json.dumps(review))})"
        + "\nasyncio.run(run(os.environ['DATABASE_URL'], TAXONOMY, REVIEW,"
        + " os.environ.get('DRY_RUN', '1') != '0'))\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--taxonomy", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--database-url")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--bundle", action="store_true",
                        help="print a self-contained program to pipe into the backend container")
    args = parser.parse_args()
    taxonomy = json.loads(args.taxonomy.read_text())
    review = json.loads(args.review.read_text())
    tag_rows(taxonomy, review)  # validate before doing anything
    if args.bundle:
        sys.stdout.write(bundle(taxonomy, review))
        return 0
    if not args.database_url:
        parser.error("--database-url is required unless --bundle is given")
    asyncio.run(run(args.database_url, taxonomy, review, args.dry_run))
    return 0


if __name__ == "__main__" and sys.argv[0] != "-":
    sys.exit(main())
