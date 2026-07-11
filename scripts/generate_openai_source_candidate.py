#!/usr/bin/env python3
"""Generate a validated OpenAI source-linked Palsgraf brief candidate."""

import json
import os
from pathlib import Path

from generate_source_linked_candidate import (
    API_URL,
    CASE_ID,
    REQUIRED_SECTIONS,
    request_json,
    validate,
)


MODEL = "gpt-5.6-sol"
ROOT = Path(__file__).resolve().parents[1]
JSON_OUTPUT = ROOT / "docs" / "prototypes" / "palsgraf-openai-source-candidate.json"
MARKDOWN_OUTPUT = ROOT / "docs" / "prototypes" / "palsgraf-openai-source-candidate.md"


def claim_schema(max_items):
    return {
        "type": "array",
        "minItems": 1,
        "maxItems": max_items,
        "items": {
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
        },
    }


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
        "# OpenAI Citation-Aware Palsgraf Candidate",
        "",
        f"Model: `{MODEL}` | Input tokens: {usage.get('input_tokens', 0):,} | Output tokens: {usage.get('output_tokens', 0):,}",
        "",
        "This candidate has not replaced either production brief.",
        "",
    ]
    for section in REQUIRED_SECTIONS:
        lines.extend([f"## {labels[section]}", ""])
        for claim in candidate[section]:
            source_list = ", ".join(f"`{source}`" for source in claim["sources"])
            lines.extend([f"{claim['text']} [{source_list}]", ""])
            for source in claim["sources"]:
                lines.extend([f"> {passages[source]['text']}", ""])
    lines.extend([
        "## Significance",
        "",
        candidate["significance"],
        "",
        "*Editorial synthesis; intentionally not represented as language from the opinion.*",
    ])
    return "\n".join(lines)


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required")

    summary = request_json(f"{API_URL}/api/v1/cases/{CASE_ID}/summary")
    passages = {passage["id"]: passage for passage in summary["opinion_passages"]}
    passage_text = "\n".join(
        f"[{passage['id']}] ({passage['opinion_part']}) {passage['text']}"
        for passage in summary["opinion_passages"]
    )
    schema = {
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
    prompt = f"""Create a concise, accurate law-school case brief for Palsgraf v. Long Island Railroad Co. Target 550-700 total words including significance. Synthesize rather than cataloging every sentence. Use at most four Facts claims, one Issue claim, two Holding claims, two Rule claims, four Majority Reasoning claims, and four Dissent claims. Keep Significance under 90 words.

Use only the numbered opinion sentences below for Facts, Issue, Holding, Rule, Majority Reasoning, and Dissent. Every claim must cite the smallest set of sentence IDs that directly supports it. Never invent an ID. Separate Cardozo's majority from Andrews's dissent. Significance must be editorial synthesis and contain no source IDs.

OPINION SENTENCES:
{passage_text}
"""
    response = request_json(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        body={
            "model": MODEL,
            "input": prompt,
            "reasoning": {"effort": "medium"},
            "max_output_tokens": 4000,
            "text": {
                "verbosity": "medium",
                "format": {
                    "type": "json_schema",
                    "name": "citation_aware_case_brief",
                    "strict": True,
                    "schema": schema,
                },
            },
        },
    )
    output_text = "".join(
        content.get("text", "")
        for item in response.get("output", []) if item.get("type") == "message"
        for content in item.get("content", []) if content.get("type") == "output_text"
    )
    candidate = json.loads(output_text)
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
        render_markdown(candidate, passages, response.get("usage", {})), encoding="utf-8"
    )
    print(MARKDOWN_OUTPUT)


if __name__ == "__main__":
    main()
