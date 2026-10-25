#!/usr/bin/env python3
"""Rebuild the Qdrant collection behind the Cheng Evidence casebook's AI Q&A.

The original `evidence_cheng_v38` collection was lost when the shared Qdrant instance
restarted on ephemeral storage (2026-10-25); no builder had been committed. This rebuilds it
from the reader rows in `casebook_content` (casebook 2467), whose `para_ordinal` is the docx
paragraph index the textbook Q&A endpoint deep-links with.

Payload per chunk (what /api/v1/textbooks/{id}/ask reads): `text`, `chapter`, `case`
(the excerpted case's heading, matched to `casebook_cases.case_name_in_book`, or null),
`para` (first paragraph index in the chunk). Also `section`, `chapter_slug`.
Chunks never cross a chapter, section, or case boundary.

Run from repo root:  .venv/bin/python scripts/build_cheng_qdrant.py [--dry-run]
Reads QDRANT_URL / QDRANT_API_KEY / OPENAI_API_KEY from the Railway Backend service.
Idempotent: deterministic point IDs; --recreate drops the collection first.
"""
import html as htmllib
import json
import re
import subprocess
import sys
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "citator"))
import railway_db  # noqa: E402

CASEBOOK_ID = 2467
COLLECTION = "evidence_cheng_v38"
MODEL = "text-embedding-3-small"
TARGET_CHARS = 1400
BOUNDARY_TYPES = {"chapter-title", "section", "subsection", "case"}
# Notes / Problem / Rule label lines start the commentary after an excerpt: they end the case.
CASE_END_TYPES = BOUNDARY_TYPES | {"note", "problem", "rule"}
SKIP_TYPES = {"divider", "image"}
NS = uuid.UUID("5b0c1d1e-c4e9-4d38-9a1e-2467e0000038")

FETCH = '''
async def job(conn, payload):
    rows = await conn.fetch("""SELECT sort_order, chapter_slug, chapter_title, section, block_type,
                                      html, para_ordinal
                                 FROM casebook_content WHERE casebook_id = $1 ORDER BY sort_order""",
                            payload["id"])
    return [dict(r) for r in rows]
'''


def config():
    out = subprocess.run([railway_db.RAILWAY, "variables", "--service", "Backend", "--json"],
                         capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL)
    v = json.loads(out.stdout)
    return v["QDRANT_URL"].rstrip("/"), v["QDRANT_API_KEY"], v["OPENAI_API_KEY"]


def plain(fragment: str) -> str:
    text = re.sub(r"<br\s*/?>|</p>|</li>|</tr>", "\n", fragment or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = htmllib.unescape(text)
    return re.sub(r"[ \t ]+", " ", re.sub(r"\n\s*\n+", "\n", text)).strip()


def chunk(rows):
    chunks, buf, start = [], [], None
    chapter = case = slug = section = None

    def flush():
        nonlocal buf, start
        if buf:
            chunks.append({"text": "\n".join(buf), "chapter": chapter, "chapter_slug": slug,
                           "section": section, "case": case, "para": start})
        buf, start = [], None

    for r in rows:
        btype, text = r["block_type"], plain(r["html"])
        if btype in SKIP_TYPES or not text:
            continue
        moved = r["chapter_title"] != chapter or r["section"] != section
        if moved or btype in CASE_END_TYPES:
            flush()
            chapter, slug, section = r["chapter_title"], r["chapter_slug"], r["section"]
            if btype == "case":
                case = text
            elif moved or btype in CASE_END_TYPES:
                case = None
        if buf and sum(len(b) for b in buf) + len(text) > TARGET_CHARS:
            flush()
        if start is None:
            start = r["para_ordinal"]
        buf.append(text)
    flush()
    return chunks


def call(url, key, path, body=None, method=None):
    req = urllib.request.Request(
        url + path, data=json.dumps(body).encode() if body is not None else None,
        headers={"api-key": key, "Content-Type": "application/json"},
        method=method or ("POST" if body is not None else "GET"))
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)


def embed(openai_key, texts):
    req = urllib.request.Request(
        "https://api.openai.com/v1/embeddings",
        data=json.dumps({"model": MODEL, "input": texts}).encode(),
        headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.load(resp)
    return [d["embedding"] for d in sorted(data["data"], key=lambda d: d["index"])]


def main():
    dry = "--dry-run" in sys.argv
    rows = railway_db.run(FETCH, {"id": CASEBOOK_ID}, timeout=300)
    chunks = chunk(rows)
    with_case = sum(1 for c in chunks if c["case"])
    print(f"{len(rows)} blocks -> {len(chunks)} chunks ({with_case} inside case excerpts), "
          f"{sum(len(c['text']) for c in chunks):,} chars")
    if dry:
        for c in chunks[:3] + [c for c in chunks if c["case"]][:2]:
            print(json.dumps({k: (v[:120] if isinstance(v, str) else v) for k, v in c.items()}))
        return
    url, qkey, okey = config()
    if "--recreate" in sys.argv:
        try:
            call(url, qkey, f"/collections/{COLLECTION}", method="DELETE")
        except Exception:
            pass
    try:
        call(url, qkey, f"/collections/{COLLECTION}")
    except Exception:
        call(url, qkey, f"/collections/{COLLECTION}",
             {"vectors": {"size": 1536, "distance": "Cosine"}}, method="PUT")
    for i in range(0, len(chunks), 96):
        batch = chunks[i:i + 96]
        vectors = embed(okey, [c["text"] for c in batch])
        points = [{"id": str(uuid.uuid5(NS, f"{CASEBOOK_ID}:{c['para']}:{n}")), "vector": v, "payload": c}
                  for n, (c, v) in enumerate(zip(batch, vectors), start=i)]
        call(url, qkey, f"/collections/{COLLECTION}/points?wait=true", {"points": points}, method="PUT")
        print(f"upserted {i + len(batch)}/{len(chunks)}")
    info = call(url, qkey, f"/collections/{COLLECTION}")["result"]
    print(json.dumps({"collection": COLLECTION, "status": info.get("status"),
                      "points_count": info.get("points_count")}))


if __name__ == "__main__":
    main()
