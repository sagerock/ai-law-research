import json
import re

from opinion_passages import build_opinion_passages


SECTION_LIMITS = {
    "facts": 4,
    "issue": 1,
    "holding": 2,
    "rule": 2,
    "majority_reasoning": 4,
    "dissent": 4,
}


def has_majority_source_material(passages: list[dict]) -> bool:
    """Return whether a packet can support the required majority sections."""
    return any(
        passage.get("opinion_part") in {"opinion", "majority"}
        for passage in passages
    )


def validate_structured_summary(candidate: dict, passages: list[dict]) -> list[str]:
    errors = []
    allowed = set(SECTION_LIMITS) | {"significance"}
    if not isinstance(candidate, dict):
        return ["top level must be an object"]
    if set(candidate) != allowed:
        errors.append(f"keys must be exactly {sorted(allowed)}")

    passage_by_id = {
        passage.get("passage_id", passage.get("id")): passage
        for passage in passages
    }
    for section, maximum in SECTION_LIMITS.items():
        claims = candidate.get(section)
        minimum = 0 if section == "dissent" else 1
        if not isinstance(claims, list) or not minimum <= len(claims) <= maximum:
            errors.append(f"{section} must contain {minimum}-{maximum} claims")
            continue
        for index, claim in enumerate(claims):
            if not isinstance(claim, dict) or set(claim) != {"text", "sources"}:
                errors.append(f"{section}[{index}] must contain only text and sources")
                continue
            if not isinstance(claim["text"], str) or not claim["text"].strip():
                errors.append(f"{section}[{index}] has invalid text")
            sources = claim["sources"]
            if not isinstance(sources, list) or not sources or len(sources) != len(set(sources)):
                errors.append(f"{section}[{index}] has missing or duplicate sources")
                continue
            unknown = [source for source in sources if source not in passage_by_id]
            if unknown:
                errors.append(f"{section}[{index}] has unknown sources: {unknown}")
                continue
            parts = {passage_by_id[source]["opinion_part"] for source in sources}
            if section == "majority_reasoning":
                if "dissent" in parts:
                    errors.append(f"{section}[{index}] cites dissent")
                elif any(part not in {"opinion", "majority"} for part in parts):
                    errors.append(f"{section}[{index}] cites non-majority passage")
            if section == "dissent" and any(part != "dissent" for part in parts):
                errors.append(f"{section}[{index}] cites non-dissent passage")

    significance = candidate.get("significance")
    if not isinstance(significance, str) or not significance.strip() or re.search(r"op-[0-9a-f]", significance):
        errors.append("significance must be unsourced editorial text")
    words = len(re.findall(r"\b\w+\b", " ".join(
        [
            claim.get("text", "")
            for section in SECTION_LIMITS
            for claim in candidate.get(section, [])
            if isinstance(claim, dict)
        ] + ([significance] if isinstance(significance, str) else [])
    )))
    if not 400 <= words <= 800:
        errors.append(f"candidate must contain 400-800 words, got {words}")
    return errors


def repair_unknown_sources(candidate: dict, passages: list[dict]) -> None:
    """Fix near-miss passage IDs in place before validation.

    Models occasionally emit a real passage ID with a character added or dropped
    at the end. When exactly one known ID is a prefix of the cited ID (or vice
    versa), the intended passage is unambiguous, so repairing it locally is
    cheaper than a regeneration round-trip.
    """
    if not isinstance(candidate, dict):
        return
    known = {
        passage.get("passage_id", passage.get("id"))
        for passage in passages
    }
    for claims in candidate.values():
        if not isinstance(claims, list):
            continue
        for claim in claims:
            if not isinstance(claim, dict) or not isinstance(claim.get("sources"), list):
                continue
            sources = claim["sources"]
            for index, source in enumerate(sources):
                if not isinstance(source, str) or source in known:
                    continue
                matches = [
                    passage_id for passage_id in known
                    if isinstance(passage_id, str)
                    and (passage_id.startswith(source) or source.startswith(passage_id))
                ]
                if len(matches) == 1 and matches[0] not in sources:
                    sources[index] = matches[0]


def build_source_packet(text: str, max_leading_chars: int = 65000, max_trailing_chars: int = 15000):
    content_hash, passages = build_opinion_passages(text)
    selected, chars = [], 0
    for passage in passages:
        if chars + len(passage["text"]) > max_leading_chars:
            break
        selected.append(passage)
        chars += len(passage["text"])
    if len(selected) < len(passages):
        tail, tail_chars = [], 0
        for passage in reversed(passages):
            if tail_chars + len(passage["text"]) > max_trailing_chars:
                break
            tail.append(passage)
            tail_chars += len(passage["text"])
        selected_ids = {passage["id"] for passage in selected}
        selected.extend(passage for passage in reversed(tail) if passage["id"] not in selected_ids)
    return content_hash, passages, selected


def build_structured_prompt(case_name: str, court: str, date: str, passages: list[dict]) -> str:
    source_packet = "\n".join(
        f'[{passage["id"]}] ({passage["opinion_part"]}) {passage["text"]}'
        for passage in passages
    )
    return f"""Create a source-linked law-school case brief for {case_name} ({court}, {date}).

Return JSON only, with exactly this shape:
{{
  "facts": [{{"text": "...", "sources": ["op-id"]}}],
  "issue": [{{"text": "...", "sources": ["op-id"]}}],
  "holding": [{{"text": "...", "sources": ["op-id"]}}],
  "rule": [{{"text": "...", "sources": ["op-id"]}}],
  "majority_reasoning": [{{"text": "...", "sources": ["op-id"]}}],
  "dissent": [{{"text": "...", "sources": ["op-id"]}}],
  "significance": "..."
}}

Requirements:
- Write 400-800 words total.
- Use 1-4 facts, exactly 1 issue, 1-2 holdings, 1-2 rules, 1-4 majority-reasoning claims, and 0-4 dissent claims.
- Every claim must cite one or more passage IDs that directly support the complete claim.
- Cite only opinion/majority passages for majority reasoning and only dissent passages for dissent.
- Use an empty dissent array if the packet contains no dissent.
- Significance is concise editorial context and has no source IDs.
- Do not invent facts, procedure, quotations, rules, or later history.

PASSAGE-TAGGED OPINION:
{source_packet}"""


def parse_structured_response(text: str) -> dict:
    value = text.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.I)
        value = re.sub(r"\s*```$", "", value)
    return json.loads(value)


def structured_summary_to_text(summary: dict) -> str:
    sections = [
        ("📋 Facts", "facts"),
        ("⚖️ Issue(s)", "issue"),
        ("📚 Holding", "holding"),
        ("📏 Rule", "rule"),
        ("💡 Reasoning", "majority_reasoning"),
        ("🗣️ Dissent", "dissent"),
    ]
    output = []
    for heading, key in sections:
        claims = summary[key]
        if claims:
            output.append(f"**{heading}**\n" + "\n\n".join(claim["text"] for claim in claims))
    output.append(f'**🎯 Significance**\n{summary["significance"]}')
    return "\n\n".join(output)
