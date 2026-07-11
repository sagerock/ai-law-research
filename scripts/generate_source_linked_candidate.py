#!/usr/bin/env python3
"""Generate and validate a non-destructive source-linked Palsgraf brief candidate."""

import json
import os
import re
import urllib.request
import urllib.error
from pathlib import Path


API_URL = "https://backend-production-8940.up.railway.app"
CASE_ID = "3602780"
MODEL = "claude-opus-4-8"
ROOT = Path(__file__).resolve().parents[1]
JSON_OUTPUT = ROOT / "docs" / "prototypes" / "palsgraf-source-linked-candidate.json"
MARKDOWN_OUTPUT = ROOT / "docs" / "prototypes" / "palsgraf-source-linked-candidate.md"
REQUIRED_SECTIONS = ("facts", "issue", "holding", "rule", "majority_reasoning", "dissent")


def request_json(url, *, headers=None, body=None):
    request = urllib.request.Request(
        url,
        headers=headers or {},
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Remote API returned HTTP {error.code}: {detail}") from error


def extract_json(text):
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Model did not return a JSON object")
    return json.loads(text[start:end + 1])


def validate(candidate, passage_ids):
    errors = []
    for section in REQUIRED_SECTIONS:
        claims = candidate.get(section)
        if not isinstance(claims, list) or not claims:
            errors.append(f"{section}: missing claims")
            continue
        for index, claim in enumerate(claims):
            if not isinstance(claim.get("text"), str) or not claim["text"].strip():
                errors.append(f"{section}[{index}]: missing text")
            sources = claim.get("sources")
            if not isinstance(sources, list) or not sources:
                errors.append(f"{section}[{index}]: missing sources")
            else:
                unknown = [source for source in sources if source not in passage_ids]
                if unknown:
                    errors.append(f"{section}[{index}]: unknown sources {unknown}")
    significance = candidate.get("significance")
    if not isinstance(significance, str) or not significance.strip():
        errors.append("significance: missing editorial synthesis")
    return errors


def render_markdown(candidate, passages, usage):
    labels = {
        "facts": "Facts",
        "issue": "Issue",
        "holding": "Holding",
        "rule": "Rule",
        "majority_reasoning": "Majority Reasoning",
        "dissent": "Dissent",
    }
    lines = [
        "# Citation-Aware Palsgraf Candidate",
        "",
        f"Model: `{MODEL}` | Input tokens: {usage.get('input_tokens', 0):,} | Output tokens: {usage.get('output_tokens', 0):,}",
        "",
        "This is an A/B candidate. It has not replaced the production summary.",
        "",
    ]
    for section in REQUIRED_SECTIONS:
        lines.extend([f"## {labels[section]}", ""])
        for claim in candidate[section]:
            source_links = ", ".join(f"`{source}`" for source in claim["sources"])
            lines.extend([f"{claim['text']} [{source_links}]", ""])
            for source in claim["sources"]:
                lines.append(f"> {passages[source]['text']}")
                lines.append("")
    lines.extend([
        "## Significance",
        "",
        candidate["significance"],
        "",
        "*Editorial synthesis; intentionally not represented as language from the opinion.*",
    ])
    return "\n".join(lines)


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY is required")

    summary = request_json(f"{API_URL}/api/v1/cases/{CASE_ID}/summary")
    passages = {passage["id"]: passage for passage in summary["opinion_passages"]}
    passage_text = "\n".join(
        f"[{passage['id']}] ({passage['opinion_part']}) {passage['text']}"
        for passage in summary["opinion_passages"]
    )
    prompt = f"""Create a concise, accurate law-school case brief for Palsgraf v. Long Island Railroad Co. Target 550-700 total words including significance. Synthesize rather than cataloging every sentence. Use at most four Facts claims, one Issue claim, two Holding claims, two Rule claims, four Majority Reasoning claims, and four Dissent claims. Keep Significance under 90 words.

Use only the numbered opinion sentences below for Facts, Issue, Holding, Rule, Majority Reasoning, and Dissent. Return valid JSON only. Each section must be an array of atomic claims. Every claim must have exactly this shape: {{"text": "one supported proposition", "sources": ["op-valid-id"]}}. Cite the smallest set of sentences that directly supports the claim. Never invent an ID. Separate Cardozo's majority from Andrews's dissent. The significance field must be a plain string clearly written as editorial synthesis and must not contain source IDs.

Required object keys: facts, issue, holding, rule, majority_reasoning, dissent, significance.

OPINION SENTENCES:
{passage_text}
"""
    claim_item_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["text", "sources"],
        "properties": {
            "text": {"type": "string"},
            "sources": {
                "type": "array",
                "minItems": 1,
                "items": {"type": "string"},
            },
        },
    }

    def claim_schema(max_items):
        return {
            "type": "array",
            "minItems": 1,
            "maxItems": max_items,
            "items": claim_item_schema,
        }
    brief_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [*REQUIRED_SECTIONS, "significance"],
        "properties": {
            "facts": claim_schema(4),
            "issue": claim_schema(1),
            "holding": claim_schema(2),
            "rule": claim_schema(2),
            "majority_reasoning": claim_schema(4),
            "dissent": claim_schema(4),
            "significance": {"type": "string"},
        },
    }
    response = request_json(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        body={
            "model": MODEL,
            "max_tokens": 3200,
            "messages": [{"role": "user", "content": prompt}],
            "tools": [{
                "name": "save_case_brief",
                "description": "Save the complete citation-aware case brief.",
                "input_schema": brief_schema,
            }],
            "tool_choice": {"type": "tool", "name": "save_case_brief"},
        },
    )
    tool_blocks = [block for block in response.get("content", []) if block.get("type") == "tool_use"]
    if not tool_blocks:
        raise ValueError("Model did not return the required case brief tool payload")
    candidate = tool_blocks[0]["input"]
    errors = validate(candidate, set(passages))
    if errors:
        raise ValueError("Candidate validation failed:\n" + "\n".join(errors))

    artifact = {
        "case_id": CASE_ID,
        "model": response.get("model", MODEL),
        "usage": response.get("usage", {}),
        "candidate": candidate,
    }
    JSON_OUTPUT.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    MARKDOWN_OUTPUT.write_text(
        render_markdown(candidate, passages, response.get("usage", {})),
        encoding="utf-8",
    )
    print(MARKDOWN_OUTPUT)


if __name__ == "__main__":
    main()
