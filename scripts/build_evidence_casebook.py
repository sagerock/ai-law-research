#!/usr/bin/env python3
"""
Create the Evidence Draft Text casebook on Tortwell and link its cases.

- Creates (or reuses) a `casebooks` row.
- For each resolved case: ensures it exists in `cases` (imports opinion text from
  CourtListener if missing), then links it via `casebook_cases` (chapter, sort_order,
  case_name_in_book, citation_in_book).
- Unresolved cases go to `casebook_pending_imports`.

Run via: railway run --service Backend -- <venv>/bin/python scripts/build_evidence_casebook.py
"""
import asyncio, os, re, json
import asyncpg, httpx
from datetime import datetime

SCRATCH = "/tmp/claude-1000/-mnt-d-dev-law-hub/84984383-e5c4-4692-a046-88a81d9ac4d5/scratchpad"
DB_URL = (os.getenv("DATABASE_PUBLIC_URL")
          or os.getenv("DATABASE_URL", "").replace(
              "postgres.railway.internal:5432", "switchyard.proxy.rlwy.net:22438"))
TOKEN = os.getenv("COURTLISTENER_API_KEY") or os.getenv("COURTLISTENER_TOKEN")
CLH = {"Authorization": f"Token {TOKEN}"} if TOKEN else {}

# --- Casebook metadata (confirm before publishing) ---
CB_TITLE = "Evidence (Cheng, Draft v38 — Open Source)"
CB_AUTHORS = "Edward K. Cheng"
CB_SUBJECT = "evidence"
CB_EDITION = "Draft v38"
CB_YEAR = 2025


async def fetch_opinion(client, cluster_id):
    """cluster -> first sub_opinion -> text (correct path, not the buggy /opinions/{cluster})."""
    try:
        c = await client.get(f"https://www.courtlistener.com/api/rest/v4/clusters/{cluster_id}/",
                             headers=CLH, timeout=30)
        if c.status_code != 200:
            return None, None, None
        cl = c.json()
        cites = cl.get("citations") or []
        cite = None
        if cites and isinstance(cites[0], dict):
            x = cites[0]; cite = f"{x.get('volume','')} {x.get('reporter','')} {x.get('page','')}".strip()
        date = cl.get("date_filed")
        text = ""
        subs = cl.get("sub_opinions") or []
        if subs:
            o = await client.get(subs[0], headers=CLH, timeout=30)
            if o.status_code == 200:
                od = o.json()
                text = od.get("plain_text") or ""
                if not text:
                    for f in ("html_with_citations", "html", "html_lawbox", "html_columbia"):
                        h = od.get(f) or ""
                        if h:
                            text = re.sub(r"<[^>]+>", " ", h); text = re.sub(r"\s+", " ", text).strip(); break
        return cl.get("case_name"), cite, (date, text)
    except Exception as e:
        print(f"    fetch error {cluster_id}: {repr(e)[:80]}")
        return None, None, None


async def ensure_case(conn, client, cluster_id):
    """Return True if the case is present in `cases` (importing if needed)."""
    row = await conn.fetchrow("SELECT id, (content IS NOT NULL) AS has FROM cases WHERE id=$1", str(cluster_id))
    if row:
        return True
    name, cite, dt = await fetch_opinion(client, cluster_id)
    if not name:
        return False
    date, text = dt or (None, "")
    decision_date = None
    if date:
        try: decision_date = datetime.strptime(date, "%Y-%m-%d").date()
        except (ValueError, TypeError): pass
    await conn.execute("""
        INSERT INTO cases (id, title, decision_date, court_id, reporter_cite, content, source_url, created_at)
        VALUES ($1,$2,$3,NULL,$4,$5,$6,NOW())
        ON CONFLICT (id) DO UPDATE SET content=COALESCE(EXCLUDED.content, cases.content), updated_at=NOW()
    """, str(cluster_id), name, decision_date, cite, text or None,
        f"https://www.courtlistener.com/opinion/{cluster_id}/")
    return True


async def main():
    resolved = json.load(open(f"{SCRATCH}/evidence_resolved.json"))
    conn = await asyncpg.connect(DB_URL)

    # 1) casebook row (reuse if same title exists)
    cb = await conn.fetchrow("SELECT id FROM casebooks WHERE title=$1", CB_TITLE)
    if cb:
        cb_id = cb["id"]
    else:
        cb_id = await conn.fetchval("""
            INSERT INTO casebooks (title, edition, subject, authors, year, metadata, created_at, updated_at)
            VALUES ($1,$2,$3,$4,$5,$6,NOW(),NOW()) RETURNING id
        """, CB_TITLE, CB_EDITION, CB_SUBJECT, CB_AUTHORS, CB_YEAR,
            json.dumps({"source": "Evidence Draft Text v38.docx", "open_source": True}))
    print(f"Casebook id={cb_id}: {CB_TITLE}")

    # clean prior links/pending for idempotent re-runs
    await conn.execute("DELETE FROM casebook_cases WHERE casebook_id=$1", cb_id)
    await conn.execute("DELETE FROM casebook_pending_imports WHERE casebook_id=$1", cb_id)

    linked = pending = 0
    async with httpx.AsyncClient() as client:
        for i, c in enumerate(resolved, 1):
            cid = c.get("cluster_id")
            good = cid and c.get("confidence") in ("citation", "name")
            if good and await ensure_case(conn, client, cid):
                await conn.execute("""
                    INSERT INTO casebook_cases
                        (casebook_id, case_id, chapter, sort_order, case_name_in_book, citation_in_book, created_at, updated_at)
                    VALUES ($1,$2,$3,$4,$5,$6,NOW(),NOW())
                """, cb_id, str(cid), c["chapter"], i, c["caption"], c.get("parsed_cite"))
                linked += 1
                print(f"  [{i}/75] LINK  {c['parsed_name'][:38]:38s} -> cluster {cid}")
            else:
                await conn.execute("""
                    INSERT INTO casebook_pending_imports
                        (casebook_id, case_name, citation, chapter, courtlistener_id, match_confidence, import_status, created_at, updated_at)
                    VALUES ($1,$2,$3,$4,$5,$6,'pending',NOW(),NOW())
                """, cb_id, c["parsed_name"], c.get("parsed_cite") or "(no citation)", c["chapter"],
                    str(cid) if cid else None, c.get("confidence"))
                pending += 1
                print(f"  [{i}/75] PEND  {c['parsed_name'][:38]:38s} ({c.get('confidence')})")
    await conn.close()
    print(f"\nLinked: {linked}  Pending: {pending}  (casebook id {cb_id})")


if __name__ == "__main__":
    asyncio.run(main())
