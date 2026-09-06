#!/usr/bin/env python3
"""Compare source-linked case-brief generation across model providers.

This script is intentionally read-only with respect to Tortwell. It reuses the
production prompt and deterministic validator, then writes candidates and a
machine-readable report to a local output directory.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

import httpx


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from structured_briefs import (  # noqa: E402
    build_source_packet,
    build_structured_prompt,
    drop_uncitable_dissent,
    generation_shape_report,
    parse_structured_response,
    repair_unknown_sources,
    validate_structured_summary,
)


TORTWELL_API = "https://backend-production-8940.up.railway.app"
DEFAULT_CASES = ["106282", "107451", "109117"]
DEFAULT_MODELS = ["claude-opus-5", "claude-fable-5-1", "gpt-5.6-sol"]
MODEL_PRICING = {
    "claude-opus-5": (5.0, 25.0),
    "claude-fable-5": (10.0, 50.0),
    "claude-fable-5-1": (10.0, 50.0),
    "gpt-5.6-sol": (4.0, 20.0),
}


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def get_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url, headers={"User-Agent": "Tortwell structured-brief model eval/1.0"}
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.load(response)


def select_passages(
    passages: list[dict[str, Any]],
    max_leading_chars: int = 65_000,
    max_trailing_chars: int = 15_000,
) -> list[dict[str, Any]]:
    """Apply the same leading-plus-trailing packet selection as production."""
    normalized = [
        {
            "id": passage.get("id") or passage.get("passage_id"),
            "ordinal": passage.get("ordinal", index),
            "opinion_part": passage.get("opinion_part"),
            "text": passage.get("text") or "",
        }
        for index, passage in enumerate(passages)
    ]
    selected: list[dict[str, Any]] = []
    chars = 0
    for passage in normalized:
        if chars + len(passage["text"]) > max_leading_chars:
            break
        selected.append(passage)
        chars += len(passage["text"])
    if len(selected) < len(normalized):
        tail: list[dict[str, Any]] = []
        tail_chars = 0
        for passage in reversed(normalized):
            if tail_chars + len(passage["text"]) > max_trailing_chars:
                break
            tail.append(passage)
            tail_chars += len(passage["text"])
        selected_ids = {passage["id"] for passage in selected}
        selected.extend(
            passage for passage in reversed(tail) if passage["id"] not in selected_ids
        )
    return selected


def case_packet(case_id: str) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    detail = get_json(f"{TORTWELL_API}/api/v1/cases/{case_id}")
    summary = get_json(f"{TORTWELL_API}/api/v1/cases/{case_id}/summary")
    passages = summary.get("opinion_passages") or []
    content_hash = summary.get("opinion_content_hash")
    if passages:
        selected = select_passages(passages)
    else:
        content_hash, _, selected = build_source_packet(detail.get("content") or "")
    if not selected:
        raise RuntimeError(f"Case {case_id} produced no source passages")
    return detail, selected, content_hash or "unknown"


def extract_openai_text(response: dict[str, Any]) -> str:
    for item in response.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return content["text"]
    raise RuntimeError("OpenAI response contained no output text")


def extract_gemini_text(response: dict[str, Any]) -> str:
    parts = (
        response.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [])
    )
    text = "".join(
        str(part.get("text") or "")
        for part in parts
        if isinstance(part, dict)
    )
    if text:
        return text
    raise RuntimeError("Gemini response contained no output text")


def call_model(
    model: str,
    prompt: str,
    max_output_tokens: int = 8_000,
) -> tuple[str, dict[str, int], dict[str, Any]]:
    if model.startswith("claude-"):
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": max_output_tokens,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=180,
        )
        response.raise_for_status()
        data = response.json()
        text = next(
            block["text"] for block in data.get("content", [])
            if block.get("type") == "text"
        )
        usage = data.get("usage") or {}
        return text, {
            "input_tokens": int(usage.get("input_tokens", 0)),
            "output_tokens": int(usage.get("output_tokens", 0)),
        }, {"stop_reason": data.get("stop_reason")}

    if model.startswith("gpt-"):
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        response = httpx.post(
            "https://api.openai.com/v1/responses",
            headers={
                "authorization": f"Bearer {key}",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "input": prompt,
                "max_output_tokens": max_output_tokens,
                "reasoning": {"effort": "high"},
            },
            timeout=300,
        )
        response.raise_for_status()
        data = response.json()
        usage = data.get("usage") or {}
        return extract_openai_text(data), {
            "input_tokens": int(usage.get("input_tokens", 0)),
            "output_tokens": int(usage.get("output_tokens", 0)),
        }, {
            "status": data.get("status"),
            "incomplete_details": data.get("incomplete_details"),
        }

    if model.startswith("gemini-"):
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={
                "x-goog-api-key": key,
                "content-type": "application/json",
            },
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": max_output_tokens,
                    "responseMimeType": "application/json",
                },
            },
            timeout=300,
        )
        response.raise_for_status()
        data = response.json()
        usage = data.get("usageMetadata") or {}
        candidates = data.get("candidates") or [{}]
        output_tokens = int(usage.get("candidatesTokenCount", 0))
        output_tokens += int(usage.get("thoughtsTokenCount", 0))
        return extract_gemini_text(data), {
            "input_tokens": int(usage.get("promptTokenCount", 0)),
            "output_tokens": output_tokens,
        }, {
            "finish_reason": candidates[0].get("finishReason"),
            "thoughts_tokens": int(usage.get("thoughtsTokenCount", 0)),
            "cached_content_tokens": int(usage.get("cachedContentTokenCount", 0)),
        }

    raise RuntimeError(f"Unsupported model provider for {model}")


def estimated_cost(model: str, usage: dict[str, int]) -> float | None:
    rates = MODEL_PRICING.get(model)
    if not rates:
        return None
    return (
        usage["input_tokens"] * rates[0]
        + usage["output_tokens"] * rates[1]
    ) / 1_000_000


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", nargs="+", default=DEFAULT_CASES)
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument(
        "--pairs",
        nargs="+",
        metavar="CASE:MODEL",
        help="Evaluate only the listed case/model pairs",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=8_000,
        help="Provider output-token allowance; includes Gemini thinking tokens",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "tmp" / "model-evals")
    args = parser.parse_args()

    load_env(ROOT / ".env")
    args.output.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    if args.pairs:
        work = []
        for pair in args.pairs:
            case_id, separator, model = pair.partition(":")
            if not separator or not case_id or not model:
                parser.error(f"invalid --pairs value {pair!r}; expected CASE:MODEL")
            work.append((case_id, model))
    else:
        work = [
            (str(case_id), model)
            for case_id in args.cases
            for model in args.models
        ]

    case_cache: dict[str, tuple[dict[str, Any], list[dict[str, Any]], str]] = {}
    for case_id, model in work:
        if case_id not in case_cache:
            case_cache[case_id] = case_packet(case_id)
        detail, passages, content_hash = case_cache[case_id]
        shape_errors, shape_warnings = generation_shape_report(passages)
        if shape_errors:
            raise RuntimeError(f"Case {case_id} has unusable source packet: {shape_errors}")
        prompt = build_structured_prompt(
            detail.get("title") or str(case_id),
            detail.get("court_name") or "Unknown Court",
            detail.get("decision_date") or "Unknown Date",
            passages,
        )
        print(f"Generating {case_id} with {model}...", flush=True)
        started = time.perf_counter()
        record: dict[str, Any] = {
            "case_id": str(case_id),
            "case_title": detail.get("title"),
            "model": model,
            "content_hash": content_hash,
            "source_passages": len(passages),
            "source_chars": sum(len(p["text"]) for p in passages),
            "source_shape_warnings": shape_warnings,
        }
        try:
            raw, usage, provider = call_model(
                model,
                prompt,
                max_output_tokens=args.max_output_tokens,
            )
            latency = time.perf_counter() - started
            record.update({
                "raw_response": raw,
                "usage": usage,
                "provider": provider,
                "estimated_cost_usd": estimated_cost(model, usage),
            })
            candidate = parse_structured_response(raw)
            repair_unknown_sources(candidate, passages)
            drop_uncitable_dissent(candidate, passages)
            errors = validate_structured_summary(candidate, passages)
            words = len(re.findall(
                r"\b\w+\b",
                " ".join(
                    claim.get("text", "")
                    for section in (
                        "facts", "issue", "holding", "rule",
                        "majority_reasoning", "dissent",
                    )
                    for claim in candidate.get(section, [])
                ) + " " + str(candidate.get("significance", "")),
            ))
            record.update({
                "valid": not errors,
                "validation_errors": errors,
                "word_count": words,
                "latency_seconds": round(latency, 3),
                "candidate": candidate,
            })
        except Exception as exc:
            record.update({
                "valid": False,
                "validation_errors": [f"provider_or_parse_error: {exc}"],
                "latency_seconds": round(time.perf_counter() - started, 3),
            })
        filename = f"{case_id}-{slug(model)}.json"
        (args.output / filename).write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        results.append({
            key: value
            for key, value in record.items()
            if key not in {"candidate", "raw_response"}
        })

    report = {
        "cases": sorted({case_id for case_id, _ in work}),
        "models": sorted({model for _, model in work}),
        "production_prompt": "backend/structured_briefs.py:build_structured_prompt",
        "production_validator": "backend/structured_briefs.py:validate_structured_summary",
        "writes_to_tortwell": False,
        "results": results,
    }
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if all(result["valid"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
