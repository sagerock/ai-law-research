#!/usr/bin/env python3
"""Subscription path for Simplified/Bullets brief versions (see backend/brief_variants.py).

Internal backfills run in Claude Code sessions on the subscription, not on the site's
API key and community pool; the site endpoint stays for visitors' first-open requests.
Same gates as the endpoint, split across sessions so the writer never reviews itself:

  writer:   queue -> fetch -> stage   (deterministic validation runs at stage)
  reviewer: review-list -> review-fetch -> review-save approve|hold

Approval publishes to `brief_variants` through `railway ssh` (citator/railway_db.py), where
the deployed module re-validates before writing. A hold keeps the candidate staged with the
reviewer's notes; the next writer pass repairs only the named lines. Two holds hand the case
to a human. Staging lives outside the repo in ~/.local/state/tortwell/brief-variants/.

Usage (python = /home/sage/.venvs/lawdata/bin/python or the repo .venv):
  brief_variant_batch.py queue [N] [--collection ID]
  brief_variant_batch.py fetch <case_id>
  brief_variant_batch.py stage <case_id> <candidate.json> "<model-id>"
  brief_variant_batch.py review-list [N]
  brief_variant_batch.py review-fetch <case_id>
  brief_variant_batch.py review-save <case_id> <verdict.json>
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "backend"))

import railway_db  # noqa: E402
from brief_variants import (  # noqa: E402
    build_fidelity_prompt,
    build_variant_prompt,
    source_digest,
    validate_variants,
)

API = "https://backend-production-8940.up.railway.app"
STAGING = Path.home() / ".local/state/tortwell/brief-variants"
MAX_STRIKES = 2


# ---------------------------------------------------------------- data access

def _get(path: str) -> dict:
    with urllib.request.urlopen(f"{API}{path}", timeout=60) as response:
        return json.load(response)


def approved_brief(case_id: str):
    """(title, provider, summary) for the brief the case page shows, via the public API."""
    quoted = urllib.parse.quote(case_id, safe="")
    candidates = _get(f"/api/v1/cases/{quoted}/summary").get("structured_candidates") or []
    if not candidates:
        return None
    case = _get(f"/api/v1/cases/{quoted}")
    title = (case.get("case") or case).get("title") or case_id
    return title, candidates[0]["provider"], candidates[0]["summary"]


def staged_path(case_id: str) -> Path:
    return STAGING / f"{case_id}.json"


def load_staged(case_id: str) -> dict | None:
    path = staged_path(case_id)
    return json.loads(path.read_text()) if path.exists() else None


def write_staged(case_id: str, record: dict) -> None:
    STAGING.mkdir(parents=True, exist_ok=True)
    staged_path(case_id).write_text(json.dumps(record, indent=1))


def all_staged() -> list[dict]:
    if not STAGING.exists():
        return []
    return [json.loads(path.read_text()) for path in sorted(STAGING.glob("*.json"))]


# ---------------------------------------------------------------- remote jobs

QUEUE_SNIPPET = '''
from brief_variants import source_digest
async def job(conn, payload):
    collection = payload.get("collection")
    if collection is not None:
        rows = await conn.fetch("""
            SELECT DISTINCT ON (cc.case_id) cc.case_id AS id, c.title, cc.position
            FROM collection_cases cc
            JOIN cases c ON c.id = cc.case_id
            JOIN structured_summary_candidates s
              ON s.case_id = cc.case_id AND s.review_status = 'approved'
            WHERE cc.collection_id = $1
            ORDER BY cc.case_id""", int(collection))
        rows = sorted(rows, key=lambda r: r["position"] or 0)
    else:
        rows = await conn.fetch("""
            SELECT DISTINCT s.case_id AS id, c.title, 0 AS position
            FROM structured_summary_candidates s JOIN cases c ON c.id = s.case_id
            WHERE s.review_status = 'approved'""")
    ids = [r["id"] for r in rows]
    briefs = {}
    for r in await conn.fetch("""
            SELECT DISTINCT ON (case_id) case_id, summary
            FROM structured_summary_candidates
            WHERE case_id = ANY($1::text[]) AND review_status = 'approved'
            ORDER BY case_id, CASE provider WHEN 'claude' THEN 1 WHEN 'openai' THEN 2 ELSE 3 END""",
            ids):
        summary = r["summary"]
        briefs[r["case_id"]] = json.loads(summary) if isinstance(summary, str) else summary
    variants = {r["case_id"]: r["source_digest"] for r in await conn.fetch(
        "SELECT case_id, source_digest FROM brief_variants WHERE case_id = ANY($1::text[])", ids)}
    out = []
    for r in rows:
        digest = source_digest(briefs[r["id"]])
        if variants.get(r["id"]) != digest:
            out.append({"id": r["id"], "title": r["title"],
                        "state": "stale" if r["id"] in variants else "missing"})
    return out
'''

PUBLISH_SNIPPET = '''
from brief_variants import VARIANT_PROMPT_VERSION, attach_sources, source_digest, validate_variants
async def job(conn, payload):
    case_id = payload["case_id"]
    row = await conn.fetchrow("""
        SELECT provider, summary FROM structured_summary_candidates
        WHERE case_id = $1 AND review_status = 'approved'
        ORDER BY CASE provider WHEN 'claude' THEN 1 WHEN 'openai' THEN 2 ELSE 3 END
        LIMIT 1""", case_id)
    if not row:
        return {"ok": False, "error": "no approved brief"}
    summary = json.loads(row["summary"]) if isinstance(row["summary"], str) else row["summary"]
    digest = source_digest(summary)
    if digest != payload["digest"]:
        return {"ok": False, "error": "the detailed brief changed after this candidate was written"}
    errors = validate_variants(payload["candidate"], summary)
    if errors:
        return {"ok": False, "error": "; ".join(errors)}
    published = attach_sources(payload["candidate"], summary)
    await conn.execute("""
        INSERT INTO brief_variants
          (case_id, source_provider, source_digest, simplified, bullets, model,
           prompt_version, input_tokens, output_tokens, cost, key_source, created_at)
        VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6, $7, 0, 0, 0, 'subscription', NOW())
        ON CONFLICT (case_id) DO UPDATE SET
          source_provider = EXCLUDED.source_provider, source_digest = EXCLUDED.source_digest,
          simplified = EXCLUDED.simplified, bullets = EXCLUDED.bullets, model = EXCLUDED.model,
          prompt_version = EXCLUDED.prompt_version, input_tokens = 0, output_tokens = 0,
          cost = 0, key_source = 'subscription', created_at = NOW()""",
        case_id, row["provider"], digest, json.dumps(published["simplified"]),
        json.dumps(published["bullets"]), payload["model"], VARIANT_PROMPT_VERSION)
    return {"ok": True}
'''


# ---------------------------------------------------------------- commands

def cmd_queue(n: int, collection: str | None) -> list[dict]:
    """Cases needing a variant: held candidates awaiting repair first, then fresh work."""
    staged = {record["case_id"]: record for record in all_staged()}
    repairs = [
        {"id": r["case_id"], "title": r["title"], "state": "repair", "notes": r["holds"][-1]}
        for r in staged.values() if r["status"] == "held"
    ]
    remote = railway_db.run(QUEUE_SNIPPET, {"collection": collection})
    fresh = [
        item for item in remote
        if staged.get(item["id"], {}).get("status") not in {"pending", "held", "needs-human"}
    ]
    return (repairs + fresh)[:n]


def cmd_fetch(case_id: str) -> dict:
    brief = approved_brief(case_id)
    if not brief:
        return {"case_id": case_id, "error": "no approved source-linked brief"}
    title, _provider, summary = brief
    result = {
        "case_id": case_id,
        "title": title,
        "digest": source_digest(summary),
        # The same instructions the site endpoint sends, so both paths write to one spec.
        "instructions": build_variant_prompt(title, summary),
    }
    staged = load_staged(case_id)
    if staged and staged["status"] == "held":
        result["repair"] = {
            "previous_candidate": staged["candidate"],
            "reviewer_notes": staged["holds"][-1],
            "instruction": "Rewrite only the lines the reviewer named; copy every other line unchanged.",
        }
    return result


def cmd_stage(case_id: str, candidate_path: str, model: str) -> dict:
    brief = approved_brief(case_id)
    if not brief:
        return {"ok": False, "errors": ["no approved source-linked brief"]}
    title, _provider, summary = brief
    try:
        candidate = json.loads(Path(candidate_path).read_text())
    except (OSError, json.JSONDecodeError) as error:
        return {"ok": False, "errors": [f"could not read candidate: {error}"]}
    errors = validate_variants(candidate, summary)
    if errors:
        return {"ok": False, "errors": errors}
    previous = load_staged(case_id) or {}
    if previous.get("status") == "needs-human":
        return {"ok": False, "errors": ["held twice; a human must clear this case first"]}
    write_staged(case_id, {
        "case_id": case_id,
        "title": title,
        "digest": source_digest(summary),
        "candidate": candidate,
        "model": model,
        "status": "pending",
        "holds": previous.get("holds", []),
        "staged_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True, "status": "pending review"}


def cmd_review_list(n: int) -> list[dict]:
    pending = [r for r in all_staged() if r["status"] == "pending"]
    return [{"id": r["case_id"], "title": r["title"], "model": r["model"]} for r in pending[:n]]


def cmd_review_fetch(case_id: str) -> dict:
    staged = load_staged(case_id)
    if not staged or staged["status"] != "pending":
        return {"case_id": case_id, "error": "no pending candidate"}
    brief = approved_brief(case_id)
    if not brief or source_digest(brief[2]) != staged["digest"]:
        return {"case_id": case_id, "error": "the detailed brief changed; this candidate is stale"}
    return {
        "case_id": case_id,
        "title": staged["title"],
        "review_material": build_fidelity_prompt(staged["title"], brief[2], staged["candidate"]),
    }


def cmd_review_save(case_id: str, verdict_path: str) -> dict:
    staged = load_staged(case_id)
    if not staged or staged["status"] != "pending":
        return {"ok": False, "error": "no pending candidate"}
    verdict = json.loads(Path(verdict_path).read_text())
    problems = [p for p in verdict.get("problems", []) if p.get("severity", "wrong") == "wrong"]
    decision = verdict.get("verdict")
    if decision not in {"approve", "hold"}:
        return {"ok": False, "error": 'verdict must be "approve" or "hold"'}
    if decision == "approve" and problems:
        return {"ok": False, "error": "cannot approve with wrong-severity problems listed"}
    if decision == "hold" and not problems:
        return {"ok": False, "error": "a hold must list the wrong lines and why"}

    if decision == "hold":
        notes = [f"{p.get('line', 'a line')}: {p.get('problem', '')}" for p in problems]
        staged["holds"] = staged.get("holds", []) + [notes]
        staged["status"] = "needs-human" if len(staged["holds"]) >= MAX_STRIKES else "held"
        write_staged(case_id, staged)
        return {"ok": True, "status": staged["status"]}

    result = railway_db.run(PUBLISH_SNIPPET, {
        "case_id": case_id,
        "digest": staged["digest"],
        "candidate": staged["candidate"],
        "model": f"{staged['model']} (subscription)",
    })
    if not result.get("ok"):
        return {"ok": False, "error": result.get("error")}
    staged["status"] = "published"
    staged["published_at"] = datetime.now(timezone.utc).isoformat()
    write_staged(case_id, staged)
    return {"ok": True, "status": "published"}


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in {"-h", "--help"}:
        print(__doc__)
        return 0
    command, args = argv[1], argv[2:]
    if command == "queue":
        collection = None
        if "--collection" in args:
            index = args.index("--collection")
            collection = args[index + 1]
            args = args[:index] + args[index + 2:]
        result = cmd_queue(int(args[0]) if args else 10, collection)
    elif command == "fetch" and len(args) == 1:
        result = cmd_fetch(args[0])
    elif command == "stage" and len(args) == 3:
        result = cmd_stage(*args)
    elif command == "review-list":
        result = cmd_review_list(int(args[0]) if args else 10)
    elif command == "review-fetch" and len(args) == 1:
        result = cmd_review_fetch(args[0])
    elif command == "review-save" and len(args) == 2:
        result = cmd_review_save(*args)
    else:
        print(__doc__)
        return 2
    if isinstance(result, dict) and "review_material" in result:
        print(result["review_material"])
    else:
        print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
