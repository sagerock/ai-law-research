#!/usr/bin/env python3
"""Import a version-controlled canonical outline into the relational schema."""

import argparse
import asyncio
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import asyncpg


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTENT = ROOT / "frontend" / "content" / "outlines" / "civil-procedure.json"


def section_key(stage: dict[str, Any]) -> str:
    return f"stage-{int(stage['id']):02d}"


def section_slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not slug:
        raise ValueError("section title must produce a non-empty slug")
    return slug


def build_section(stage: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
    lines = [stage["subtitle"].strip()]
    sources: list[dict[str, str]] = []
    seen_sources: set[tuple[str, str]] = set()

    def add_source(target_type: str, target_ref: str, label: str) -> None:
        key = (target_type, target_ref)
        if key not in seen_sources:
            seen_sources.add(key)
            sources.append({"target_type": target_type, "target_ref": target_ref, "label": label})

    rules = stage.get("rules") or []
    if rules:
        lines.extend(["", "### Rules and authorities"])
        for rule in rules:
            label = rule["rule"].strip()
            if rule.get("slug"):
                reference = f"[{label}](/rules/{rule['slug']})"
                add_source("rule", rule["slug"], label)
            else:
                reference = label
                if "USC" in label:
                    add_source("statute", label, label)
            lines.append(f"- **{reference}** — {rule['description'].strip()}")
            if rule.get("timing"):
                lines.append(f"  - **Timing:** {rule['timing'].strip()}")

    concepts = stage.get("concepts") or []
    if concepts:
        lines.extend(["", "### Core concepts"])
        for concept in concepts:
            lines.append(f"- **{concept['name'].strip()}** — {concept['description'].strip()}")

    tools = stage.get("discoveryTools") or []
    if tools:
        lines.extend(["", "### Discovery tools"])
        for tool in tools:
            lines.append(f"- **{tool['name'].strip()}** — {tool['description'].strip()}")

    cases = stage.get("keyCases") or []
    if cases:
        lines.extend(["", "### Key cases"])
        for case in cases:
            label = case["name"].strip()
            if case.get("caseId"):
                reference = f"[{label}](/case/{case['caseId']})"
                add_source("case", str(case["caseId"]), label)
            else:
                reference = label
            holding = case.get("holding", "").strip()
            lines.append(f"- **{reference}**{f' — {holding}' if holding else ''}")

    branches = stage.get("branches") or []
    if branches:
        lines.extend(["", "### Procedural branches"])
        for branch in branches:
            rules_text = f" ({', '.join(branch.get('rules') or [])})" if branch.get("rules") else ""
            lines.append(f"- **{branch['label'].strip()}**{rules_text} — {branch['description'].strip()}")

    return "\n".join(lines).strip(), sources


def load_outline(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = ("slug", "subject", "title", "description", "version", "sections")
    missing = [field for field in required if not data.get(field)]
    if missing:
        raise ValueError(f"missing outline fields: {', '.join(missing)}")
    if int(data["version"]) < 1:
        raise ValueError("outline version must be positive")
    if not data["sections"]:
        raise ValueError("outline must contain sections")

    keys = [section_key(stage) for stage in data["sections"]]
    slugs = [section_slug(stage["title"]) for stage in data["sections"]]
    if len(keys) != len(set(keys)) or len(slugs) != len(set(slugs)):
        raise ValueError("section keys and slugs must be unique")
    return data


def outline_content_hash(data: dict[str, Any]) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def import_outline(data: dict[str, Any], database_url: str) -> tuple[int, int]:
    conn = await asyncpg.connect(database_url)
    try:
        async with conn.transaction():
            outline_id = await conn.fetchval(
                """
                INSERT INTO canonical_outlines (slug, subject, title, description, current_version, is_published)
                VALUES ($1, $2, $3, $4, $5, TRUE)
                ON CONFLICT (slug) DO UPDATE SET
                    subject = EXCLUDED.subject,
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    current_version = EXCLUDED.current_version,
                    is_published = TRUE,
                    updated_at = NOW()
                RETURNING id
                """,
                data["slug"], data["subject"], data["title"], data["description"], int(data["version"]),
            )
            content_hash = outline_content_hash(data)
            revision_id = await conn.fetchval(
                """
                INSERT INTO canonical_outline_revisions
                    (outline_id, version, content_hash, revision_note, published_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (outline_id, version) DO NOTHING
                RETURNING id
                """,
                outline_id, int(data["version"]), content_hash,
                data.get("revision_note") or "Initial canonical outline",
            )
            if revision_id is None:
                existing_revision = await conn.fetchrow(
                    """
                    SELECT id, content_hash FROM canonical_outline_revisions
                    WHERE outline_id = $1 AND version = $2
                    """,
                    outline_id, int(data["version"]),
                )
                if existing_revision["content_hash"] != content_hash:
                    raise ValueError(
                        f"version {data['version']} is already published with different content; increment version"
                    )
                revision_id = existing_revision["id"]

            active_keys: list[str] = []
            source_count = 0
            for order, stage in enumerate(data["sections"]):
                key = section_key(stage)
                active_keys.append(key)
                stable_section_id = await conn.fetchval(
                    """
                    INSERT INTO canonical_outline_sections
                        (outline_id, section_key, slug, sort_order, is_active)
                    VALUES ($1, $2, $3, $4, TRUE)
                    ON CONFLICT (outline_id, section_key) DO UPDATE SET
                        slug = EXCLUDED.slug,
                        sort_order = EXCLUDED.sort_order,
                        is_active = TRUE,
                        updated_at = NOW()
                    RETURNING id
                    """,
                    outline_id, key, section_slug(stage["title"]), order,
                )
                body, sources = build_section(stage)
                section_revision_id = await conn.fetchval(
                    """
                    INSERT INTO canonical_outline_section_revisions (revision_id, section_id, title, body)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (revision_id, section_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        body = EXCLUDED.body
                    RETURNING id
                    """,
                    revision_id, stable_section_id, stage["title"].strip(), body,
                )
                await conn.execute(
                    "DELETE FROM canonical_outline_section_sources WHERE section_revision_id = $1",
                    section_revision_id,
                )
                for source_order, source in enumerate(sources):
                    await conn.execute(
                        """
                        INSERT INTO canonical_outline_section_sources
                            (section_revision_id, target_type, target_ref, label, sort_order)
                        VALUES ($1, $2, $3, $4, $5)
                        """,
                        section_revision_id, source["target_type"], source["target_ref"],
                        source["label"], source_order,
                    )
                source_count += len(sources)

            await conn.execute(
                """
                UPDATE canonical_outline_sections
                SET is_active = FALSE, updated_at = NOW()
                WHERE outline_id = $1 AND NOT (section_key = ANY($2::text[]))
                """,
                outline_id, active_keys,
            )
        return len(data["sections"]), source_count
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--content", type=Path, default=DEFAULT_CONTENT)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data = load_outline(args.content)
    rendered = [build_section(stage) for stage in data["sections"]]
    if args.dry_run:
        print(f"Validated {data['title']}: {len(rendered)} sections, {sum(len(s[1]) for s in rendered)} sources")
        return
    if not args.database_url:
        raise SystemExit("DATABASE_URL or --database-url is required")

    section_count, source_count = asyncio.run(import_outline(data, args.database_url))
    print(f"Imported {data['title']}: {section_count} sections, {source_count} sources")


if __name__ == "__main__":
    main()
