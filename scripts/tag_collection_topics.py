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

SYSTEM_PROMPT = """You tag court cases with doctrinal topics for Tortwell, a free study \
site for law students. Tags let a student filter a reading list ("show me the ripeness \
cases") and jump from a case to related ones.

You get one case: its name and citation, the instructor-facing course note attached to it \
in the reading list, and Tortwell's AI brief of the opinion. Pick tags only from the \
doctrine list provided, using the exact slugs.

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
            "gap": {"type": "string"},
        },
        "required": ["primary", "secondary", "rationale", "confidence", "gap"],
        "additionalProperties": False,
    }


def tag_case(client, system: str, schema: dict, case: dict, brief: str) -> dict:
    brief_text = brief[:BRIEF_CHARS] if brief else "(No Tortwell brief exists for this case yet.)"
    prompt = (
        f"Case: {case['title']}, {case.get('reporter_cite') or 'no reporter cite'} "
        f"({(case.get('decision_date') or 'n.d.')[:4]})\n\n"
        f"Course note:\n{(case.get('notes') or '').strip() or '(none)'}\n\n"
        f"Brief:\n{brief_text}"
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
    return result


def write_digest(path: Path, title: str, rows: list[dict], doctrines: dict) -> None:
    def label(slug: str) -> str:
        return doctrines[slug][1]

    order = list(doctrines)
    lines = [f"# Topic tags for review: {title}", "",
             f"{len(rows)} cases. Grouped by primary doctrine, in taxonomy order. "
             "Low-confidence tags and taxonomy gaps are listed first.", ""]
    flagged = [r for r in rows if r["confidence"] == "low" or r["gap"]]
    if flagged:
        lines += ["## Check these first", ""]
        for r in flagged:
            extra = f"; gap: {r['gap']}" if r["gap"] else ""
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
        lines.append("")
    path.write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--collection-id", required=True)
    parser.add_argument("--taxonomy", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="output path without extension")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    taxonomy, doctrines = load_taxonomy(args.taxonomy)
    collection = fetch_json(f"{API}/shared/{args.collection_id}")
    cases = collection["cases"]
    with ThreadPoolExecutor(args.workers) as pool:
        briefs = list(pool.map(lambda c: fetch_brief(c["id"]), cases))

    client = anthropic.Anthropic()
    system = SYSTEM_PROMPT + "\n\nDoctrine list:\n" + doctrine_listing(taxonomy)
    schema = result_schema(list(doctrines))

    def run(pair):
        case, brief = pair
        result = tag_case(client, system, schema, case, brief)
        print(f"  {case['title']}: {result['primary']}", file=sys.stderr)
        return {
            "case_id": case["id"],
            "title": case["title"],
            "year": (case.get("decision_date") or "")[:4],
            "position": case.get("position", 0),
            "has_brief": bool(brief),
            **result,
        }

    with ThreadPoolExecutor(args.workers) as pool:
        rows = list(pool.map(run, zip(cases, briefs)))

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
