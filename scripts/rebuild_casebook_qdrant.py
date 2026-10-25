#!/usr/bin/env python3
"""Rebuild a casebook's "Ask this textbook" Qdrant collection from casebook_content.

Written 2026-10-25 after the Qdrant General wipe (the original ingest script for
evidence_cheng_v38 was never committed). The reader table already holds the whole
book in order with para_ordinal = the Qdrant "para" field, so it is the source.

Payload per point: text, case (the case heading the passage sits under, matching
casebook_cases.case_name_in_book), chapter (chapter title), section, para (first
paragraph ordinal in the chunk, for reader deep links).

Runs where DATABASE_URL, QDRANT_URL, QDRANT_API_KEY and OPENAI_API_KEY are set,
e.g. on the Backend service:  python3 rebuild_casebook_qdrant.py --casebook-id 2467
"""
import argparse, asyncio, html as htmlmod, json, os, re, uuid
import asyncpg, httpx

MAX_CHARS = 1500
SKIP = {"image", "diagram", "divider"}
RESET_CASE = {"chapter-title", "section", "subsection"}


def plain(h):
    return htmlmod.unescape(re.sub(r"<[^>]+>", " ", h or "")).replace("\xa0", " ").strip()


def build_chunks(rows):
    chunks, cur = [], None
    chapter = section = case = None

    def flush():
        nonlocal cur
        if cur and cur["text"].strip():
            chunks.append(cur)
        cur = None

    for r in rows:
        bt = r["block_type"]
        if bt in SKIP:
            continue
        text = plain(r["html"])
        if not text:
            continue
        if bt == "chapter-title":
            flush(); chapter = r["chapter_title"]; section = None; case = None
        elif bt in RESET_CASE:
            flush(); section = text; case = None
        elif bt == "case":
            flush(); case = text
        chapter = r["chapter_title"] or chapter
        if cur and len(cur["text"]) + len(text) > MAX_CHARS:
            flush()
        if cur is None:
            cur = {"text": "", "case": case, "chapter": chapter, "section": section, "para": r["para_ordinal"]}
        if cur["para"] is None:
            cur["para"] = r["para_ordinal"]
        cur["text"] += ("\n" if cur["text"] else "") + text
    flush()
    return chunks


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--casebook-id", type=int, required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    db = await asyncpg.connect(os.environ["DATABASE_URL"])
    md = await db.fetchval("SELECT metadata FROM casebooks WHERE id=$1", a.casebook_id)
    md = json.loads(md) if isinstance(md, str) else (md or {})
    collection = md.get("qdrant_collection")
    if not collection:
        raise SystemExit("casebook has no metadata.qdrant_collection")
    rows = await db.fetch("SELECT block_type, html, chapter_title, para_ordinal FROM casebook_content "
                          "WHERE casebook_id=$1 ORDER BY sort_order", a.casebook_id)
    chunks = build_chunks(rows)
    print(f"{collection}: {len(rows)} blocks -> {len(chunks)} chunks, "
          f"{sum(1 for c in chunks if c['case'])} under a case")
    if a.dry_run:
        for c in chunks[200:203]:
            print(json.dumps({k: (v[:120] if isinstance(v, str) else v) for k, v in c.items()}))
        return
    q, qk, ok = os.environ["QDRANT_URL"].rstrip("/"), os.environ["QDRANT_API_KEY"], os.environ["OPENAI_API_KEY"]
    async with httpx.AsyncClient(timeout=120) as http:
        h = {"api-key": qk}
        await http.delete(f"{q}/collections/{collection}", headers=h)
        r = await http.put(f"{q}/collections/{collection}", headers=h,
                           json={"vectors": {"size": 1536, "distance": "Cosine"}})
        r.raise_for_status()
        for i in range(0, len(chunks), 100):
            batch = chunks[i:i + 100]
            e = await http.post("https://api.openai.com/v1/embeddings", headers={"Authorization": f"Bearer {ok}"},
                                json={"model": "text-embedding-3-small", "input": [c["text"] for c in batch]})
            e.raise_for_status()
            vecs = [d["embedding"] for d in e.json()["data"]]
            points = [{"id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{collection}/{i + j}")), "vector": v, "payload": c}
                      for j, (c, v) in enumerate(zip(batch, vecs))]
            u = await http.put(f"{q}/collections/{collection}/points?wait=true", headers=h, json={"points": points})
            u.raise_for_status()
        info = (await http.get(f"{q}/collections/{collection}", headers=h)).json()["result"]
        print(f"done: {info['points_count']} points in {collection}")


if __name__ == "__main__":
    asyncio.run(main())
