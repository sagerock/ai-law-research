#!/usr/bin/env python3
"""Synchronize Chemerinsky Constitutional Law principal cases to a Tortwell textbook.

The source is a private, locally extracted table of cases. Only italicized principal
case captions and citations are parsed; page references and other book text are never
stored. The default mode is a read-only resolution report. Use --apply only after the
report resolves every principal case without ambiguity.

Example:
    railway run --service Postgres -- python3 scripts/sync_chemerinsky_casebook.py \
        --source /path/to/table-of-cases.md
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import unicodedata

import asyncpg
import httpx
from dotenv import load_dotenv


CITATION_RE = re.compile(
    r"(?P<volume>\d+)\s+(?P<reporter>U\.S\.|S\. Ct\.)\s+"
    r"(?:\([^)]+\)\s+)?(?P<page>\d+)",
    re.IGNORECASE,
)
NAME_STOP_WORDS = {
    "and", "association", "board", "city", "co", "commission", "county",
    "department", "district", "inc", "of", "school", "state", "the", "town",
    "united", "university", "v", "village",
}
COURTLISTENER_OVERRIDES = {
    # These principal cases were absent from the textbook mapping. Some were absent
    # from the cases table and others were unhydrated stubs. Bound-volume Supreme
    # Court clusters are preferred over duplicate slip-opinion clusters.
    "143:sct:2355": ("10049655", "600 U.S. 477"),  # Biden v. Nebraska
    "600:us:66": ("10049662", "600 U.S. 66"),  # Counterman v. Colorado
    "576:us:350": ("2811848", "576 U.S. 350"),  # Horne v. Department of Agriculture
    "138:sct:2448": ("4511640", "585 U.S. 878"),  # Janus v. AFSCME
    "74:us:506": ("88034", "74 U.S. 506"),  # Ex parte McCardle
    "142:sct:2111": ("6480696", "597 U.S. 1"),  # New York State Rifle v. Bruen
    "83:us:36": ("88661", "83 U.S. 36"),  # Slaughter-House Cases
}


@dataclass(frozen=True)
class PrincipalCase:
    caption: str
    citation: str


def parse_principal_cases(source: Path) -> list[PrincipalCase]:
    cases: list[PrincipalCase] = []
    for line in source.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("*") or line.startswith("**"):
            continue
        citation_match = CITATION_RE.search(line)
        if citation_match:
            caption_source = line[:citation_match.start()].rstrip(" ,")
            citation = citation_match.group(0)
        elif line.startswith("*Goldberg v. Kelly*"):
            caption_source = "*Goldberg v. Kelly*"
            citation = ""
        else:
            continue
        caption = caption_source.replace("*", "").strip()
        cases.append(PrincipalCase(caption=caption, citation=citation))
    if not cases:
        raise ValueError(f"No italicized principal cases found in {source}")
    keys = [citation_key(case.citation) for case in cases if case.citation]
    if len(set(keys)) != len(keys):
        raise ValueError("Principal-case citations are not unique; review the source parser")
    return cases


def citation_key(value: str | None) -> str:
    match = CITATION_RE.search(value or "")
    if not match:
        return ""
    reporter = re.sub(r"[^a-z]", "", match.group("reporter").lower())
    return f"{match.group('volume')}:{reporter}:{match.group('page')}"


def citation_query(value: str) -> str:
    match = CITATION_RE.search(value)
    if not match:
        return ""
    return f"{match.group('volume')} {match.group('reporter')} {match.group('page')}"


def uninvert_caption(value: str) -> str:
    if ";" in value and value.rstrip().endswith(" v."):
        party, plaintiff = (part.strip() for part in value.split(";", 1))
        return f"{plaintiff} {party}"
    match = re.match(
        r"^(.+?),\s+(City|County|Town|Village) of,\s+v\.\s+(.+)$",
        value,
        re.IGNORECASE,
    )
    if match:
        return f"{match.group(2)} of {match.group(1)} v. {match.group(3)}"
    return value


def normalized_name(value: str | None) -> str:
    value = uninvert_caption(value or "")
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = value.lower().replace("&", " and ")
    replacements = {
        "assn": "association",
        "commn": "commission",
        "dept": "department",
        "intl": "international",
        "natl": "national",
        "soc y": "society",
    }
    words = re.findall(r"[a-z0-9]+", value)
    return " ".join(replacements.get(word, word) for word in words)


def name_score(expected: str, row: asyncpg.Record) -> float:
    wanted = normalized_name(expected)
    names = [row["title"], row.get("case_name_in_book")]
    return max(
        SequenceMatcher(None, wanted, normalized_name(name)).ratio()
        for name in names if name
    )


def search_tokens(caption: str) -> list[str]:
    words = normalized_name(caption).split()
    useful = [word for word in words if word not in NAME_STOP_WORDS and len(word) >= 4]
    return sorted(set(useful), key=lambda word: (-len(word), words.index(word)))[:3]


async def title_candidates(conn: asyncpg.Connection, case: PrincipalCase) -> list[asyncpg.Record]:
    tokens = search_tokens(case.caption)
    if not tokens:
        return []
    clauses = [f"lower(c.title) LIKE ${index + 1}" for index in range(len(tokens))]
    return await conn.fetch(
        f"""
        SELECT c.id, c.title, c.reporter_cite, NULL::text AS case_name_in_book
        FROM cases c
        WHERE {' AND '.join(clauses)}
        LIMIT 30
        """,
        *(f"%{token}%" for token in tokens),
    )


async def resolve_cases(
    conn: asyncpg.Connection,
    principals: list[PrincipalCase],
    casebook_id: int,
) -> tuple[list[tuple[PrincipalCase, asyncpg.Record, str]], list[str]]:
    current = await conn.fetch(
        """
        SELECT c.id, c.title, c.reporter_cite, cc.case_name_in_book,
               cc.sort_order, cc.citation_in_book
        FROM casebook_cases cc
        JOIN cases c ON c.id = cc.case_id
        WHERE cc.casebook_id = $1
        ORDER BY cc.sort_order NULLS LAST, c.title
        """,
        casebook_id,
    )
    citations = [citation_query(case.citation) for case in principals if case.citation]
    exact_rows = await conn.fetch(
        """
        SELECT c.id, c.title, c.reporter_cite, NULL::text AS case_name_in_book
        FROM cases c
        WHERE EXISTS (
            SELECT 1 FROM unnest($1::text[]) AS wanted(citation)
            WHERE c.reporter_cite ILIKE wanted.citation || '%'
        )
        """,
        citations,
    )
    override_rows = await conn.fetch(
        """
        SELECT c.id, c.title, c.reporter_cite, NULL::text AS case_name_in_book
        FROM cases c
        WHERE c.id = ANY($1::text[])
        """,
        [cluster_id for cluster_id, _ in COURTLISTENER_OVERRIDES.values()],
    )
    override_by_id = {row["id"]: row for row in override_rows}
    by_citation: dict[str, list[asyncpg.Record]] = {}
    for row in exact_rows:
        by_citation.setdefault(citation_key(row["reporter_cite"]), []).append(row)

    used_ids: set[str] = set()
    resolved: list[tuple[PrincipalCase, asyncpg.Record, str]] = []
    errors: list[str] = []
    current_by_id = {row["id"]: row for row in current}

    for case in principals:
        override = COURTLISTENER_OVERRIDES.get(citation_key(case.citation))
        override_row = override_by_id.get(override[0]) if override else None
        if override_row and override_row["id"] not in used_ids:
            candidates = [override_row]
            method = "verified-id"
        else:
            candidates = [
                row for row in by_citation.get(citation_key(case.citation), [])
                if row["id"] not in used_ids
            ]
            method = "citation"
        if not candidates:
            scored_current = sorted(
                (
                    (name_score(case.caption, row), row)
                    for row in current if row["id"] not in used_ids
                ),
                reverse=True,
                key=lambda item: item[0],
            )
            if scored_current and scored_current[0][0] >= 0.78:
                best_score, best = scored_current[0]
                next_score = scored_current[1][0] if len(scored_current) > 1 else 0.0
                if best_score - next_score >= 0.05:
                    candidates = [best]
                    method = f"current-name:{best_score:.2f}"
        if not candidates:
            title_rows = await title_candidates(conn, case)
            scored_titles = sorted(
                ((name_score(case.caption, row), row) for row in title_rows),
                reverse=True,
                key=lambda item: item[0],
            )
            if scored_titles and scored_titles[0][0] >= 0.78:
                best_score, best = scored_titles[0]
                next_score = scored_titles[1][0] if len(scored_titles) > 1 else 0.0
                if best_score - next_score >= 0.05:
                    candidates = [best]
                    method = f"database-name:{best_score:.2f}"
        if len(candidates) > 1:
            candidates.sort(
                key=lambda row: (row["id"] in current_by_id, name_score(case.caption, row)),
                reverse=True,
            )
            top_score = name_score(case.caption, candidates[0])
            second_score = name_score(case.caption, candidates[1])
            if candidates[0]["id"] not in current_by_id and top_score - second_score < 0.05:
                errors.append(
                    f"AMBIGUOUS {case.caption} | {case.citation}: "
                    + "; ".join(f"{row['id']} {row['title']}" for row in candidates[:5])
                )
                continue
            candidates = [candidates[0]]
        if not candidates:
            errors.append(f"UNRESOLVED {case.caption} | {case.citation}")
            continue

        row = current_by_id.get(candidates[0]["id"], candidates[0])
        used_ids.add(row["id"])
        resolved.append((case, row, method))

    extras = [row for row in current if row["id"] not in used_ids]
    for row in extras:
        errors.append(
            f"REMOVE {row['id']} | {row['case_name_in_book'] or row['title']} | "
            f"{row['reporter_cite']}"
        )
    return resolved, errors


async def fetch_override_case(case: PrincipalCase) -> dict:
    override = COURTLISTENER_OVERRIDES[citation_key(case.citation)]
    cluster_id, reporter_cite = override
    api_key = os.getenv("COURTLISTENER_API_KEY")
    if not api_key:
        raise RuntimeError("COURTLISTENER_API_KEY is required to import missing opinions")

    backend_dir = Path(__file__).resolve().parents[1] / "backend"
    sys.path.insert(0, str(backend_dir))
    from courtlistener_opinions import fetch_courtlistener_document

    headers = {"Authorization": f"Token {api_key}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://www.courtlistener.com/api/rest/v4/clusters/{cluster_id}/",
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        cluster = response.json()
        document = await fetch_courtlistener_document(
            cluster_id, api_key, client=client
        )
    if not document:
        raise RuntimeError(f"CourtListener cluster {cluster_id} has no complete opinion document")

    metadata = {
        "citation_count": cluster.get("citation_count", 0),
        "courtlistener_document": document.manifest(),
        "judges": cluster.get("judges"),
        "precedential_status": cluster.get("precedential_status"),
        "source": "courtlistener_api",
    }
    return {
        "id": cluster_id,
        "title": cluster.get("case_name") or uninvert_caption(case.caption),
        "decision_date": (
            date.fromisoformat(cluster["date_filed"])
            if cluster.get("date_filed") else None
        ),
        "reporter_cite": reporter_cite,
        "content": document.text,
        "content_hash": hashlib.sha256(document.text.encode("utf-8")).hexdigest(),
        "metadata": json.dumps(metadata),
        "source_url": "https://www.courtlistener.com" + (cluster.get("absolute_url") or ""),
    }


async def insert_override_cases(
    conn: asyncpg.Connection,
    rows: list[dict],
) -> None:
    court_id = await conn.fetchval(
        "SELECT id FROM courts WHERE court_listener_id = 'scotus' LIMIT 1"
    )
    for row in rows:
        await conn.execute(
            """
            INSERT INTO cases
                (id, title, court_id, decision_date, reporter_cite, content,
                 content_hash, metadata, source_url, created_at, updated_at)
            VALUES ($1, $2, $3, $4::date, $5, $6, $7, $8::jsonb, $9, NOW(), NOW())
            ON CONFLICT (id) DO UPDATE SET
                title = EXCLUDED.title,
                court_id = COALESCE(cases.court_id, EXCLUDED.court_id),
                decision_date = COALESCE(cases.decision_date, EXCLUDED.decision_date),
                reporter_cite = COALESCE(cases.reporter_cite, EXCLUDED.reporter_cite),
                content = CASE
                    WHEN cases.content IS NULL OR length(cases.content) < 200
                    THEN EXCLUDED.content ELSE cases.content END,
                content_hash = CASE
                    WHEN cases.content IS NULL OR length(cases.content) < 200
                    THEN EXCLUDED.content_hash ELSE cases.content_hash END,
                metadata = COALESCE(cases.metadata, '{}'::jsonb) || EXCLUDED.metadata,
                source_url = COALESCE(cases.source_url, EXCLUDED.source_url),
                updated_at = NOW()
            """,
            row["id"],
            row["title"],
            court_id,
            row["decision_date"],
            row["reporter_cite"],
            row["content"],
            row["content_hash"],
            row["metadata"],
            row["source_url"],
        )


async def synchronize(args: argparse.Namespace) -> int:
    principals = parse_principal_cases(args.source)
    database_url = (
        os.getenv("DATABASE_PUBLIC_URL")
        or os.getenv("PROD_DATABASE_URL")
        or os.getenv("DATABASE_URL")
    )
    if not database_url:
        raise RuntimeError("DATABASE_PUBLIC_URL, PROD_DATABASE_URL, or DATABASE_URL is required")

    conn = await asyncpg.connect(database_url)
    try:
        resolved, report = await resolve_cases(conn, principals, args.casebook_id)
        blockers = [line for line in report if not line.startswith("REMOVE ")]
        removals = [line for line in report if line.startswith("REMOVE ")]
        unresolved_by_caption = {
            case.caption: case
            for case in principals
            if any(
                line.startswith(f"UNRESOLVED {case.caption} |")
                for line in blockers
            )
        }
        importable = [
            case for case in unresolved_by_caption.values()
            if citation_key(case.citation) in COURTLISTENER_OVERRIDES
        ]
        importable_blockers = {
            f"UNRESOLVED {case.caption} | {case.citation}" for case in importable
        }
        hard_blockers = [line for line in blockers if line not in importable_blockers]
        method_counts: dict[str, int] = {}
        for _, _, method in resolved:
            method_counts[method.split(":", 1)[0]] = method_counts.get(method.split(":", 1)[0], 0) + 1

        print(f"Principal cases: {len(principals)}")
        print(f"Resolved: {len(resolved)} ({json.dumps(method_counts, sort_keys=True)})")
        print(f"Authoritative removals: {len(removals)}")
        for line in blockers + removals:
            print(line)
        for case in importable:
            cluster_id, _ = COURTLISTENER_OVERRIDES[citation_key(case.citation)]
            print(f"IMPORT {cluster_id} | {case.caption} | {case.citation}")

        if not args.apply:
            print("DRY RUN: no database changes made")
            return 1 if hard_blockers else 0
        if hard_blockers:
            print("REFUSED: all principal cases must resolve before --apply")
            return 1

        imported_rows = await asyncio.gather(
            *(
                fetch_override_case(case)
                for case in principals
                if citation_key(case.citation) in COURTLISTENER_OVERRIDES
            )
        )

        async with conn.transaction():
            await insert_override_cases(conn, imported_rows)
            resolved, post_import_report = await resolve_cases(
                conn, principals, args.casebook_id
            )
            post_import_blockers = [
                line for line in post_import_report if not line.startswith("REMOVE ")
            ]
            if post_import_blockers or len(resolved) != len(principals):
                raise RuntimeError(
                    "Post-import resolution failed: " + "; ".join(post_import_blockers)
                )
            book = await conn.fetchrow("SELECT id, metadata FROM casebooks WHERE id = $1 FOR UPDATE", args.casebook_id)
            if not book:
                raise ValueError(f"Textbook {args.casebook_id} does not exist")
            raw_metadata = book["metadata"] or {}
            metadata = (
                json.loads(raw_metadata)
                if isinstance(raw_metadata, str)
                else dict(raw_metadata)
            )
            metadata["case_list_verification"] = {
                "edition": 7,
                "principal_case_count": len(principals),
                "scope": "principal_cases",
                "verified_on": date.today().isoformat(),
                "year": 2024,
            }
            await conn.execute(
                """
                UPDATE casebooks
                SET edition = '7th', authors = 'Erwin Chemerinsky',
                    publisher = 'Aspen Publishing', year = 2024, metadata = $2::jsonb,
                    updated_at = NOW()
                WHERE id = $1
                """,
                args.casebook_id,
                json.dumps(metadata),
            )
            await conn.execute("DELETE FROM casebook_pending_imports WHERE casebook_id = $1", args.casebook_id)
            await conn.execute("DELETE FROM casebook_cases WHERE casebook_id = $1", args.casebook_id)
            await conn.executemany(
                """
                INSERT INTO casebook_cases
                    (casebook_id, case_id, case_name_in_book, citation_in_book,
                     sort_order, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
                """,
                [
                    (
                        args.casebook_id,
                        row["id"],
                        row["case_name_in_book"] or row["title"],
                        case.citation or row["reporter_cite"],
                        index,
                    )
                    for index, (case, row, _) in enumerate(resolved)
                ],
            )
        print(f"APPLIED: textbook {args.casebook_id} now has {len(resolved)} principal cases")
        return 0
    finally:
        await conn.close()


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--casebook-id", type=int, default=1499)
    parser.add_argument("--apply", action="store_true")
    return asyncio.run(synchronize(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
