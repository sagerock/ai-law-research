#!/usr/bin/env python3
"""Blindly compare structured-brief candidates against their cited sources."""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from eval_structured_brief_models import call_model, case_packet, load_env  # noqa: E402


DEFAULT_JUDGE = "gpt-6-astra"
RUBRIC = {
    "legal_accuracy": "Correctly states the facts, issue, holdings, rules, and reasoning.",
    "citation_support": "Each sourced claim is entailed by the passages it cites.",
    "opinion_attribution": "Keeps majority, separate opinions, and dissent positions distinct.",
    "writing": "Clear, precise, economical prose without repetition or inflated claims.",
    "teaching_value": "Useful to a law student studying doctrine and procedural posture.",
}


def parse_json_response(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def judge_prompt(
    case_title: str,
    passages: list[dict[str, Any]],
    candidates: dict[str, dict[str, Any]],
) -> str:
    labels = list(candidates)
    evaluation_template = {
        "scores": {dimension: 1 for dimension in RUBRIC},
        "specific_errors": [
            {
                "claim": "brief quotation or paraphrase",
                "problem": "...",
                "source_ids": ["..."],
            }
        ],
        "strengths": ["..."],
    }
    result_template = {
        "case_title": "...",
        "evaluations": {
            label: evaluation_template
            for label in labels
        },
        "ranking": labels,
        "ranking_reason": "...",
    }
    source_packet = [
        {
            "id": passage.get("id"),
            "opinion_part": passage.get("opinion_part"),
            "text": passage.get("text"),
        }
        for passage in passages
    ]
    return f"""You are evaluating source-linked law-school case briefs for {case_title}.

Use only the supplied opinion passages. Do not rely on outside knowledge. Check the
substance of each claim and inspect the exact passage IDs cited in its `sources`
array. A citation earns credit only when that passage actually supports the claim.
Pay special attention to procedural posture, the precise holding, majority versus
dissent attribution, and claims in the uncited significance paragraph.

Score each candidate from 1 (poor) to 5 (excellent) on every rubric dimension:
{json.dumps(RUBRIC, indent=2)}

Return JSON with exactly these candidate labels and this top-level shape:
{json.dumps(result_template, indent=2)}

Give concrete errors rather than general impressions. Do not infer the models from
their style. Do not include markdown or text outside the JSON.

OPINION PASSAGES:
{json.dumps(source_packet, ensure_ascii=False)}

BLINDED CANDIDATES:
{json.dumps(candidates, ensure_ascii=False)}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--judge-model", default=DEFAULT_JUDGE)
    parser.add_argument("--seed", type=int, default=20260906)
    parser.add_argument("--max-output-tokens", type=int, default=12_000)
    args = parser.parse_args()

    load_env(ROOT / ".env")
    output = args.output or args.input / f"judgments-{args.judge_model}.json"
    grouped: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(args.input.glob("*.json")):
        if path.name == "report.json" or path.name.startswith("judgments-"):
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("candidate"):
            grouped.setdefault(str(record["case_id"]), []).append(record)

    rng = random.Random(args.seed)
    judgments = []
    for case_id, records in sorted(grouped.items()):
        detail, passages, _ = case_packet(case_id)
        shuffled = records[:]
        rng.shuffle(shuffled)
        labels = [chr(ord("A") + index) for index in range(len(shuffled))]
        mapping = {label: record["model"] for label, record in zip(labels, shuffled)}
        candidates = {
            label: record["candidate"] for label, record in zip(labels, shuffled)
        }
        print(f"Judging {case_id} with {args.judge_model}...", flush=True)
        started = time.perf_counter()
        raw, usage, provider = call_model(
            args.judge_model,
            judge_prompt(detail.get("title") or case_id, passages, candidates),
            max_output_tokens=args.max_output_tokens,
        )
        judgment = parse_json_response(raw)
        judgments.append({
            "case_id": case_id,
            "case_title": detail.get("title"),
            "blind_mapping": mapping,
            "judge_model": args.judge_model,
            "latency_seconds": round(time.perf_counter() - started, 3),
            "usage": usage,
            "provider": provider,
            "judgment": judgment,
        })
        output.write_text(
            json.dumps({"judgments": judgments}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    print(json.dumps({"judgments": judgments}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
