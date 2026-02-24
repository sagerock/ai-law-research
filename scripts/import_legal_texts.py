#!/usr/bin/env python3
"""
Import legal texts (Constitution, FRCP, Federal Statutes) from JSON into the database.

Reads the 3 JSON files from data/ and populates legal_documents + legal_text_items tables.
Uses ON CONFLICT for idempotent re-runs.

Usage:
    python scripts/import_legal_texts.py
    python scripts/import_legal_texts.py --dry-run
"""

import asyncio
import argparse
import json
import os
import sys
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DATA_DIR = Path("data")


def flatten_text(item: dict) -> str:
    """Recursively flatten all text from an item and its subsections into a single string."""
    parts = []
    if item.get("text"):
        parts.append(item["text"])
    for sub in item.get("subsections", []):
        parts.append(flatten_text(sub))
    for sub in item.get("sections", []):
        parts.append(flatten_text(sub))
    return "\n".join(parts)


def extract_number_from_id(item_id: str, doc_type: str) -> str | None:
    """Extract a display number from an item ID."""
    if doc_type == "frcp":
        # rule-12 -> 12, rule-4-1 -> 4.1, rule-a -> A
        num = item_id.replace("rule-", "")
        if num.replace("-", "").isdigit():
            return num.replace("-", ".")
        return num.upper()
    elif doc_type == "constitution":
        if item_id.startswith("article-"):
            num = item_id.replace("article-", "")
            roman = {"1": "I", "2": "II", "3": "III", "4": "IV", "5": "V", "6": "VI", "7": "VII"}
            return roman.get(num, num)
        elif item_id.startswith("amendment-"):
            num = item_id.replace("amendment-", "")
            roman = {
                "1": "I", "2": "II", "3": "III", "4": "IV", "5": "V",
                "6": "VI", "7": "VII", "8": "VIII", "9": "IX", "10": "X",
                "11": "XI", "12": "XII", "13": "XIII", "14": "XIV", "15": "XV",
                "16": "XVI", "17": "XVII", "18": "XVIII", "19": "XIX", "20": "XX",
                "21": "XXI", "22": "XXII", "23": "XXIII", "24": "XXIV", "25": "XXV",
                "26": "XXVI", "27": "XXVII",
            }
            return roman.get(num, num)
    return None


async def run_migration(conn: asyncpg.Connection):
    """Run the migration SQL to create tables if needed."""
    migration_path = Path("migrations/015_legal_texts.sql")
    if migration_path.exists():
        sql = migration_path.read_text()
        await conn.execute(sql)
        print("Migration applied.")
    else:
        print("Warning: migration file not found, tables must already exist.")


async def import_constitution(conn: asyncpg.Connection, dry_run: bool = False) -> int:
    """Import Constitution data."""
    path = DATA_DIR / "constitution.json"
    if not path.exists():
        print(f"  Skipping: {path} not found")
        return 0

    data = json.loads(path.read_text())
    doc_id = "constitution"
    metadata = {"preamble": data.get("preamble", "")}

    if not dry_run:
        await conn.execute("""
            INSERT INTO legal_documents (id, title, doc_type, metadata)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (id) DO UPDATE SET title = $2, metadata = $4
        """, doc_id, data["title"], doc_id, json.dumps(metadata))

    count = 0
    for i, section in enumerate(data["sections"]):
        slug = section["id"]  # article-1, amendment-14
        title = section["title"]
        number = extract_number_from_id(slug, "constitution")
        body = flatten_text(section)
        content = json.dumps(section)

        if dry_run:
            print(f"  [DRY] {slug}: {title}")
        else:
            await conn.execute("""
                INSERT INTO legal_text_items (document_id, slug, title, number, body, content, sort_order)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (document_id, slug) DO UPDATE
                SET title = $3, number = $4, body = $5, content = $6, sort_order = $7
            """, doc_id, slug, title, number, body, content, i)
        count += 1

    return count


async def import_frcp(conn: asyncpg.Connection, dry_run: bool = False) -> int:
    """Import FRCP data."""
    path = DATA_DIR / "frcp.json"
    if not path.exists():
        print(f"  Skipping: {path} not found")
        return 0

    data = json.loads(path.read_text())
    doc_id = "frcp"
    metadata = {"effective_date": data.get("effective_date", "")}

    if not dry_run:
        await conn.execute("""
            INSERT INTO legal_documents (id, title, doc_type, metadata)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (id) DO UPDATE SET title = $2, metadata = $4
        """, doc_id, data["title"], doc_id, json.dumps(metadata))

    count = 0
    for i, rule in enumerate(data["rules"]):
        slug = rule["id"]  # rule-12
        title = rule.get("title", "")
        number = rule.get("number", extract_number_from_id(slug, "frcp"))
        body = flatten_text(rule)
        content = json.dumps(rule)

        if dry_run:
            print(f"  [DRY] {slug}: Rule {number} - {title}")
        else:
            await conn.execute("""
                INSERT INTO legal_text_items (document_id, slug, title, number, body, content, sort_order)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (document_id, slug) DO UPDATE
                SET title = $3, number = $4, body = $5, content = $6, sort_order = $7
            """, doc_id, slug, title, number, body, content, i)
        count += 1

    return count


async def import_statutes(conn: asyncpg.Connection, dry_run: bool = False) -> int:
    """Import Federal Statutes data."""
    path = DATA_DIR / "federal_statutes.json"
    if not path.exists():
        print(f"  Skipping: {path} not found")
        return 0

    data = json.loads(path.read_text())
    doc_id = "federal_statutes"

    if not dry_run:
        await conn.execute("""
            INSERT INTO legal_documents (id, title, doc_type, metadata)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (id) DO UPDATE SET title = $2, metadata = $4
        """, doc_id, data["title"], doc_id, json.dumps({}))

    count = 0
    for i, statute in enumerate(data["statutes"]):
        slug = statute["id"]  # 28-usc-1332
        title = statute.get("title", "")
        citation = statute.get("citation", "")
        body = flatten_text(statute)
        content = json.dumps(statute)

        if dry_run:
            print(f"  [DRY] {slug}: {citation} - {title}")
        else:
            await conn.execute("""
                INSERT INTO legal_text_items (document_id, slug, title, citation, body, content, sort_order)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (document_id, slug) DO UPDATE
                SET title = $3, citation = $4, body = $5, content = $6, sort_order = $7
            """, doc_id, slug, title, citation, body, content, i)
        count += 1

    return count


async def main():
    parser = argparse.ArgumentParser(description="Import legal texts into database")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be imported without writing")
    args = parser.parse_args()

    if not DATABASE_URL:
        print("Error: DATABASE_URL not set")
        sys.exit(1)

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        if not args.dry_run:
            await run_migration(conn)

        print("Importing Constitution...")
        n = await import_constitution(conn, args.dry_run)
        print(f"  {n} items (7 articles + 27 amendments)")

        print("Importing FRCP...")
        n = await import_frcp(conn, args.dry_run)
        print(f"  {n} rules")

        print("Importing Federal Statutes...")
        n = await import_statutes(conn, args.dry_run)
        print(f"  {n} statutes")

        # Verify counts
        if not args.dry_run:
            docs = await conn.fetchval("SELECT COUNT(*) FROM legal_documents")
            items = await conn.fetchval("SELECT COUNT(*) FROM legal_text_items")
            print(f"\nTotal: {docs} documents, {items} items")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
