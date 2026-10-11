#!/usr/bin/env python3
"""Tag a shared collection's cases with doctrine topics from a fixed taxonomy.

Pilot for topic tags (Sage, 2026-10-11). Every tag must come from the subject's
taxonomy file in data/topics/, so the model can't invent near-duplicate tags. Inputs
are public: the collection's cases and notes, and each case's cached brief, read from
the production API. Nothing is written to the database. The output is a review file
(JSON plus a Markdown digest) for Sage to correct before anything is imported.

Example:
    .venv/bin/python scripts/tag_collection_topics.py --collection-id 15 \
        --taxonomy data/topics/con_law.json --out data/topics/review/collection-15

Re-tag some cases against the full opinion text, merging into an existing review file:
    ... --with-opinion --only 145831,217515
With --with-opinion the model must quote a sentence from the opinion supporting the primary
tag, and the quote is checked against the text (`evidence_verified`).
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import urllib.request

import anthropic
from dotenv import load_dotenv


API = "https://backend-production-8940.up.railway.app/api/v1"
MODEL = "claude-opus-5-5"
BRIEF_CHARS = 12000
OPINION_CHARS = 400_000  # ~100k tokens; longer opinions are cut and the prompt says so

SYSTEM_PROMPT = """You tag court cases with doctrinal topics for Tortwell, a free study \
site for law students. Tags let a student filter a reading list ("show me the ripeness \
cases") and jump from a case to related ones.

You get one case: its name and citation, the instructor-facing course note attached to it \
in the reading list, Tortwell's AI brief of the opinion, and sometimes the opinion text \
itself. When the opinion is given, it is the authority: judge the holding from it. Pick tags \
only from the doctrine list provided, using the exact slugs.

- `primary`: the doctrine the case is principally taught for in this collection. The \
course note is the best evidence of why it was assigned; the brief tells you what the \
Court actually held. When they point different ways, follow the holding and say so in \
the rationale.
- `secondary`: other doctrines the opinion genuinely decides or substantially discusses, \
at most three. Leave it empty rather than padding it. A doctrine only mentioned in passing \
does not count. If the course note assigns the case for a doctrine other than your \
primary, include that doctrine here: students filter the list by it.
- `rationale`: one sentence a student could check against the brief.
- `confidence`: "high" when the holding plainly turns on the primary doctrine, "medium" \
when the case straddles doctrines, "low" when the inputs are thin (no brief) or nothing \
in the list fits well.
- `evidence`: when opinion text is given, one sentence copied character for character from \
the Court's opinion (not the syllabus, headnotes, or brief) that shows why the primary tag \
fits. Copy it exactly; it is checked mechanically. Empty string when no opinion is given.
- `gap`: if a doctrine the case is clearly about is missing from the list, name it here \
in a few words; otherwise an empty string."""


def fetch_json(url: str):
    with urllib.request.urlopen(url, timeout=90) as response:
        return json.load(response)


def fetch_brief(case_id: str) -> str:
    try:
        return fetch_json(f"{API}/cases/{case_id}/summary").get("summary") or ""
    except Exception:
        return ""


def fetch_opinion(case_id: str) -> str:
    """Opinion text, repairing the legacy exact-50k truncation from CourtListener."""
    try:
        text = fetch_json(f"{API}/cases/{case_id}").get("content") or ""
    except Exception:
        return ""
    if case_id.isdigit() and 49_950 <= len(text) <= 50_050:
        import asyncio
        import os

        key = os.environ.get("COURTLISTENER_API_KEY") or os.environ.get("COURTLISTENER_TOKEN")
        backend = str(Path(__file__).resolve().parent.parent / "backend")
        if key:
            if backend not in sys.path:
                sys.path.insert(0, backend)
            from courtlistener_opinions import fetch_courtlistener_document

            document = asyncio.run(fetch_courtlistener_document(case_id, key))
            if document and len(document.text) > len(text):
                print(f"  refreshed truncated opinion {case_id}: {len(text):,} -> "
                      f"{len(document.text):,} chars", file=sys.stderr)
                text = document.text
    return text


def _normalize(text: str) -> str:
    import re

    text = re.sub(r"<[^>]+>", " ", text).replace("\u00ad", "")
    text = re.sub(r"(\w)- (\w)", r"\1\2", text)  # line-break hyphens ("ac- tors")
    for a, b in (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'),
                 ("\u2014", "-"), ("\u2013", "-")):
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).strip().lower()


def evidence_found(evidence: str, opinion: str) -> bool:
    # Compare with whitespace removed: stored opinions break words across lines
    # ("anticom mandeering"), with or without a hyphen.
    quote = _normalize(evidence).strip('"').rstrip(".")
    return len(quote) >= 40 and quote.replace(" ", "") in _normalize(opinion).replace(" ", "")


def load_taxonomy(path: Path) -> tuple[dict, dict[str, tuple[str, str]]]:
    taxonomy = json.loads(path.read_text())
    doctrines = {
        d["slug"]: (topic["topic"], d["label"])
        for topic in taxonomy["topics"]
        for d in topic["doctrines"]
    }
    return taxonomy, doctrines


def doctrine_listing(taxonomy: dict) -> str:
    lines = []
    for topic in taxonomy["topics"]:
        lines.append(topic["topic"])
        lines.extend(f"  - {d['slug']}: {d['label']}" for d in topic["doctrines"])
    return "\n".join(lines)


def result_schema(slugs: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "primary": {"type": "string", "enum": slugs},
            "secondary": {"type": "array", "items": {"type": "string", "enum": slugs}},
            "rationale": {"type": "string"},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "evidence": {"type": "string"},
            "gap": {"type": "string"},
        },
        "required": ["primary", "secondary", "rationale", "confidence", "evidence", "gap"],
        "additionalProperties": False,
    }


def tag_case(client, system: str, schema: dict, case: dict, brief: str,
             opinion: str = "") -> dict:
    brief_text = brief[:BRIEF_CHARS] if brief else "(No Tortwell brief exists for this case yet.)"
    prompt = (
        f"Case: {case['title']}, {case.get('reporter_cite') or 'no reporter cite'} "
        f"({(case.get('decision_date') or 'n.d.')[:4]})\n\n"
        f"Course note:\n{(case.get('notes') or '').strip() or '(none)'}\n\n"
        f"Brief:\n{brief_text}"
    )
    if opinion:
        cut = len(opinion) > OPINION_CHARS
        prompt += (
            "\n\nOpinion text"
            + (f" (first {OPINION_CHARS:,} of {len(opinion):,} characters)" if cut else "")
            + f":\n{opinion[:OPINION_CHARS]}"
        )
    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=system,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": prompt}],
        extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
        extra_body={"fallbacks": "default"},
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"{case['title']}: refused ({response.stop_details})")
    text = next(b.text for b in response.content if b.type == "text")
    result = json.loads(text)
    result["secondary"] = [s for s in dict.fromkeys(result["secondary"]) if s != result["primary"]][:3]
    result["evidence_verified"] = bool(opinion) and evidence_found(result["evidence"], opinion)
    return result


def write_digest(path: Path, title: str, rows: list[dict], doctrines: dict) -> None:
    def label(slug: str) -> str:
        return doctrines[slug][1]

    order = list(doctrines)
    lines = [f"# Topic tags for review: {title}", "",
             f"{len(rows)} cases. Grouped by primary doctrine, in taxonomy order. "
             "Low-confidence tags and taxonomy gaps are listed first.", ""]
    flagged = [r for r in rows if r["confidence"] == "low" or r["gap"]
               or (r.get("evidence") and not r.get("evidence_verified"))]
    if flagged:
        lines += ["## Check these first", ""]
        for r in flagged:
            extra = f"; gap: {r['gap']}" if r["gap"] else ""
            if r.get("evidence") and not r.get("evidence_verified"):
                extra += "; quote not found in opinion"
            lines.append(f"- **{r['title']}** ({r['confidence']}{extra}): {label(r['primary'])}")
        lines.append("")
    current_topic = None
    for slug in order:
        group = [r for r in rows if r["primary"] == slug]
        if not group:
            continue
        topic = doctrines[slug][0]
        if topic != current_topic:
            lines += [f"## {topic}", ""]
            current_topic = topic
        lines += [f"### {label(slug)}", ""]
        for r in sorted(group, key=lambda r: r["position"]):
            also = ", ".join(label(s) for s in r["secondary"])
            lines.append(f"- **{r['title']}** ({r['year']}) [{r['confidence']}]"
                         + (f". Also: {also}" if also else ""))
            lines.append(f"  {r['rationale']}")
            if r.get("evidence_verified"):
                lines.append(f"  > {r['evidence']}")
        lines.append("")
    path.write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--collection-id", required=True)
    parser.add_argument("--taxonomy", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="output path without extension")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--only", help="comma-separated case ids; merge into the existing review file")
    parser.add_argument("--with-opinion", action="store_true",
                        help="send the opinion text and require a verified supporting quote")
    args = parser.parse_args()

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    taxonomy, doctrines = load_taxonomy(args.taxonomy)
    collection = fetch_json(f"{API}/shared/{args.collection_id}")
    positions = {c["id"]: c.get("position", 0) for c in collection["cases"]}
    cases = collection["cases"]
    if args.only:
        wanted = set(args.only.split(","))
        cases = [c for c in cases if c["id"] in wanted]
        missing = wanted - {c["id"] for c in cases}
        if missing:
            parser.error(f"not in collection {args.collection_id}: {sorted(missing)}")
    with ThreadPoolExecutor(args.workers) as pool:
        briefs = list(pool.map(lambda c: fetch_brief(c["id"]), cases))
        opinions = (list(pool.map(lambda c: fetch_opinion(c["id"]), cases))
                    if args.with_opinion else [""] * len(cases))

    client = anthropic.Anthropic()
    system = SYSTEM_PROMPT + "\n\nDoctrine list:\n" + doctrine_listing(taxonomy)
    schema = result_schema(list(doctrines))

    def run(triple):
        case, brief, opinion = triple
        result = tag_case(client, system, schema, case, brief, opinion)
        print(f"  {case['title']}: {result['primary']}", file=sys.stderr)
        return {
            "case_id": case["id"],
            "title": case["title"],
            "year": (case.get("decision_date") or "")[:4],
            "position": case.get("position", 0),
            "has_brief": bool(brief),
            "used_opinion": bool(opinion),
            **result,
        }

    with ThreadPoolExecutor(args.workers) as pool:
        rows = list(pool.map(run, zip(cases, briefs, opinions)))

    out_json = args.out.with_suffix(".json")
    if args.only and out_json.exists():
        retagged = {r["case_id"] for r in rows}
        previous = json.loads(out_json.read_text())["cases"]
        rows = [r for r in previous if r["case_id"] not in retagged] + rows
    for r in rows:
        r["position"] = positions.get(r["case_id"], r["position"])
    rows.sort(key=lambda r: r["position"])

    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "collection_id": args.collection_id,
        "collection_name": collection.get("name"),
        "taxonomy": str(args.taxonomy),
        "model": MODEL,
        "status": "unreviewed",
        "cases": rows,
    }
    args.out.with_suffix(".json").write_text(json.dumps(payload, indent=2) + "\n")
    write_digest(args.out.with_suffix(".md"), collection.get("name") or args.collection_id,
                 rows, doctrines)
    print(f"Wrote {args.out}.json and .md ({len(rows)} cases)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
