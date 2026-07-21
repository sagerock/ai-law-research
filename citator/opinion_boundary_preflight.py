#!/home/sage/.venvs/lawdata/bin/python
"""Audit stored opinion boundaries without making any AI/provider calls.

Examples:
    python opinion_boundary_preflight.py 108406 660220
    python opinion_boundary_preflight.py --brief-eligible --limit 500

The command emits one JSON object per case and exits nonzero if any source is
missing, too short, or structurally inconsistent.
"""

import argparse
import asyncio
import json
import os
import sys

import asyncpg
import boto3

HERE = os.path.dirname(__file__)
BACKEND = os.path.join(os.path.dirname(HERE), "backend")
sys.path.insert(0, BACKEND)

from opinion_passages import assess_opinion_boundaries
from structured_briefs import (
    build_source_packet,
    generation_shape_report,
    has_majority_source_material,
)


BUCKET = os.getenv("OPINIONS_BUCKET", "lawstudygroup-opinions")
MIN_OPINION = 2500


def database_url():
    value = os.getenv("PROD_DATABASE_URL") or os.getenv("DATABASE_URL")
    if value:
        return value
    for path in (
        "/mnt/d/dev/ai-law-research/backend/.env",
        "/mnt/d/dev/ai-law-research/.env",
    ):
        if not os.path.exists(path):
            continue
        for line in open(path):
            if line.startswith("PROD_DATABASE_URL="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("PROD_DATABASE_URL not found")


def read_s3(case_id):
    try:
        response = boto3.client("s3").get_object(
            Bucket=BUCKET, Key=f"opinions/{case_id}.txt"
        )
        return response["Body"].read().decode("utf-8")
    except Exception:
        return None


async def select_cases(conn, explicit_ids, brief_eligible, limit):
    if explicit_ids:
        rows = await conn.fetch(
            "SELECT id, title, content FROM cases WHERE id = ANY($1) ORDER BY id",
            explicit_ids,
        )
        found = {row["id"] for row in rows}
        missing = sorted(set(explicit_ids) - found)
        if missing:
            raise SystemExit(f"case IDs not found: {', '.join(missing)}")
        return rows
    if not brief_eligible:
        raise SystemExit("provide case IDs or --brief-eligible")
    return await conn.fetch(
        """SELECT c.id, c.title, c.content
           FROM cases c
           WHERE (
                 EXISTS (SELECT 1 FROM ai_summaries s WHERE s.case_id = c.id)
                 OR EXISTS (SELECT 1 FROM casebook_cases cc WHERE cc.case_id = c.id)
                 OR EXISTS (
                     SELECT 1
                     FROM canonical_outline_section_sources src
                     JOIN canonical_outline_section_revisions sr
                       ON sr.id = src.section_revision_id
                     JOIN canonical_outline_revisions rev ON rev.id = sr.revision_id
                     JOIN canonical_outlines o ON o.id = rev.outline_id
                          AND o.current_version = rev.version AND o.is_published
                     WHERE src.target_type = 'case' AND src.target_ref = c.id
                 )
             )
             AND NOT EXISTS (
                 SELECT 1 FROM structured_summary_candidates k
                 WHERE k.case_id = c.id AND k.provider = 'claude'
             )
           ORDER BY (SELECT COUNT(*) FROM citations x WHERE x.target_case_id = c.id) DESC
           LIMIT $1""",
        limit,
    )


async def run(args):
    conn = await asyncpg.connect(database_url())
    try:
        rows = await select_cases(conn, args.case_ids, args.brief_eligible, args.limit)
    finally:
        await conn.close()

    failed = 0
    for row in rows:
        text = row["content"]
        source = "database" if text else "s3"
        if not text:
            text = await asyncio.to_thread(read_s3, row["id"])
        if text:
            content_hash, passages, selected = build_source_packet(text)
            assessment = assess_opinion_boundaries(
                text, passages, min_chars=MIN_OPINION, require_explicit=True
            )
            errors = list(assessment.errors)
            if not has_majority_source_material(selected):
                errors.append("selected source packet has no majority material")
            # Generation-shaped probe: would a well-formed candidate that
            # trusts the packet's labels survive validation? Runs on the
            # selected packet (what generation actually sends), no AI call.
            shape_errors, shape_warnings = generation_shape_report(selected)
            errors.extend(shape_errors)
            result = {
                "case_id": row["id"],
                "title": row["title"],
                "source": source,
                "content_hash": content_hash,
                "total_passages": len(passages),
                "selected_passages": len(selected),
                **assessment.as_dict(),
                "ok": not errors,
                "errors": errors,
                "warnings": list(assessment.warnings) + shape_warnings,
            }
        else:
            result = {
                "case_id": row["id"],
                "title": row["title"],
                "source": None,
                "ok": False,
                "errors": ["opinion text is unavailable"],
                "warnings": [],
                "part_counts": {},
            }
        failed += not result["ok"]
        print(json.dumps(result, ensure_ascii=False))

    print(f"audited={len(rows)} failed={failed}", file=sys.stderr)
    return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("case_ids", nargs="*")
    parser.add_argument("--brief-eligible", action="store_true")
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
