#!/usr/bin/env python3
"""Move legacy public outline objects into PostgreSQL and revoke public storage URLs."""

import argparse
import asyncio
import os
from urllib.parse import quote, unquote, urlparse

import asyncpg
import httpx


def supabase_storage_path(file_url: str) -> str | None:
    marker = "/storage/v1/object/public/outlines/"
    path = urlparse(file_url).path
    if marker not in path:
        return None
    return unquote(path.split(marker, 1)[1]).lstrip("/") or None


async def privatize(database_url: str, supabase_url: str, service_key: str, dry_run: bool) -> int:
    conn = await asyncpg.connect(database_url)
    try:
        rows = await conn.fetch("""
            SELECT id, file_url, original_file IS NOT NULL AS has_original
            FROM outlines
            WHERE file_url IS NOT NULL AND btrim(file_url) <> ''
            ORDER BY id
        """)
        if dry_run:
            for row in rows:
                print(f"outline {row['id']}: {'already copied' if row['has_original'] else 'copy required'}")
            return len(rows)

        headers = {"Authorization": f"Bearer {service_key}", "apikey": service_key}
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            for row in rows:
                storage_path = supabase_storage_path(row["file_url"])
                if not storage_path:
                    raise ValueError(f"outline {row['id']} has an unsupported public file URL")

                if not row["has_original"]:
                    response = await client.get(row["file_url"])
                    response.raise_for_status()
                    if len(response.content) > 25 * 1024 * 1024:
                        raise ValueError(f"outline {row['id']} exceeds the 25MB migration limit")
                    await conn.execute("""
                        UPDATE outlines
                        SET original_file = $1,
                            original_content_type = COALESCE(original_content_type, $2),
                            updated_at = NOW()
                        WHERE id = $3
                    """, response.content, response.headers.get("content-type"), row["id"])

                delete_url = f"{supabase_url.rstrip('/')}/storage/v1/object/outlines/{quote(storage_path, safe='/')}"
                deleted = await client.delete(delete_url, headers=headers)
                if deleted.status_code not in (200, 404):
                    raise RuntimeError(
                        f"could not revoke public object for outline {row['id']}: HTTP {deleted.status_code}"
                    )
                await conn.execute(
                    "UPDATE outlines SET file_url = NULL, updated_at = NOW() WHERE id = $1",
                    row["id"],
                )
                print(f"outline {row['id']}: copied and public object revoked")
        return len(rows)
    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--supabase-url", default=os.getenv("SUPABASE_URL"))
    parser.add_argument("--service-role-key", default=os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("DATABASE_URL or --database-url is required")
    if not args.dry_run and (not args.supabase_url or not args.service_role_key):
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required to revoke public objects")

    count = asyncio.run(privatize(
        args.database_url,
        args.supabase_url or "",
        args.service_role_key or "",
        args.dry_run,
    ))
    print(f"Processed {count} legacy outline uploads")


if __name__ == "__main__":
    main()
