import json
import re

from opinion_passages import build_opinion_passages


# Multi-issue cases (Sage, 2026-11-07): Buckley v. Valeo decides First Amendment,
# disclosure, public-financing, and Appointments Clause questions, and a con law
# class reads it for the last one. "Exactly 1 issue" forced the brief to drop all
# but one. Most cases still have one issue; the higher caps are room, not a target.
SECTION_LIMITS = {
    "facts": 5,
    "issue": 4,
    "holding": 4,
    "rule": 4,
    "majority_reasoning": 8,
    "dissent": 4,
}
MAJORITY_SOURCE_SECTIONS = frozenset({
    "facts", "issue", "holding", "rule", "majority_reasoning"
})


def has_majority_source_material(passages: list[dict]) -> bool:
    """Return whether a packet can support the required majority sections."""
    return any(
        passage.get("opinion_part") in {"opinion", "majority"}
        for passage in passages
    )


# Parts no brief section is permitted to cite. Concurrences are excluded from
# briefs by design; "other" covers remittiturs, addenda, and similar.
UNCITABLE_PARTS = frozenset({"concurrence", "other"})


def generation_shape_report(passages: list[dict]) -> tuple[list[str], list[str]]:
    """Check that a source packet's labels and the validation rules can both
    be satisfied by a well-formed candidate — without any AI call.

    Errors mean generation is guaranteed to fail validation regardless of
    claim quality. Warnings flag packets where a content-reading model is
    likely to collide with the labels: when a large share of the packet is
    material no section may cite (pre-fix Chevron: a dissent mislabeled
    "concurrence" was 51% of the packet), the model tends to describe it
    under dissent and fail.
    """
    def first_id(parts):
        for passage in passages:
            if passage.get("opinion_part") in parts:
                return passage.get("passage_id", passage.get("id"))
        return None

    warnings: list[str] = []
    majority_id = first_id({"opinion", "majority"})
    if not majority_id:
        return ["generation-shape: no majority/opinion passage available to cite"], warnings

    dissent_id = first_id({"dissent", "separate"})
    filler = " ".join(["synthetic"] * 70)
    candidate = {
        section: [{"text": filler, "sources": [majority_id]}]
        for section in MAJORITY_SOURCE_SECTIONS
    }
    candidate["dissent"] = (
        [{"text": filler, "sources": [dissent_id]}] if dissent_id else []
    )
    candidate["significance"] = filler
    errors = [
        f"generation-shape: {error}"
        for error in validate_structured_summary(candidate, passages)
    ]

    uncitable = sum(
        1 for passage in passages if passage.get("opinion_part") in UNCITABLE_PARTS
    )
    if len(passages) > 10 and uncitable / len(passages) > 0.25:
        parts_found = ", ".join(sorted({
            passage["opinion_part"] for passage in passages
            if passage.get("opinion_part") in UNCITABLE_PARTS
        }))
        warnings.append(
            f"generation-shape: {uncitable}/{len(passages)} passages "
            f"({uncitable / len(passages):.0%}) are uncitable parts ({parts_found}) "
            "— a content-reading model may describe them under dissent and fail validation"
        )
    return errors, warnings


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
            if section in MAJORITY_SOURCE_SECTIONS:
                if section == "majority_reasoning" and "dissent" in parts:
                    errors.append(f"{section}[{index}] cites dissent")
                elif any(part not in {"opinion", "majority"} for part in parts):
                    errors.append(f"{section}[{index}] cites non-majority passage")
            # "separate" marks a writing whose disposition the source never
            # states (e.g. a bare "Mr. Justice Douglas." heading). Dissent
            # claims may characterize it from its content; majority sections
            # are still barred from citing it by the check above.
            if section == "dissent" and any(
                part not in {"dissent", "separate"} for part in parts
            ):
                errors.append(f"{section}[{index}] cites non-dissent passage")

    significance = candidate.get("significance")
    if not isinstance(significance, str) or not significance.strip() or re.search(r"op-[0-9a-f]", significance):
        errors.append("significance must be unsourced editorial text")
    # No word budget: a brief runs as long as the case needs. A fixed 400-800
    # band rejected multi-opinion cases like United States v. Guest for going
    # a few words over (removed at Sage's direction 2026-09-26).
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


def has_dissent_source_material(passages: list[dict]) -> bool:
    """Return whether a packet contains anything a dissent claim may cite."""
    return any(
        passage.get("opinion_part") in {"dissent", "separate"}
        for passage in passages
    )


def drop_uncitable_dissent(candidate: dict, passages: list[dict]) -> None:
    """Empty the dissent section when the packet holds no dissent material.

    An opinion concurring only in the judgment rejects the majority's reasoning
    and so reads like a dissent — Alito's writing in Smith v. Arizona, joined by
    the Chief Justice, is the type case. A content-reading model files it under
    dissent and fails validation, twice, because feeding "cites non-dissent
    passage" back does not change what the concurrence says. Concurrences are
    excluded from briefs by design and the dissent section is optional, so
    dropping those claims yields the brief the source actually supports instead
    of a 502. The repair is deliberately narrow: when real dissent passages do
    exist, a miscited claim is a near-miss the retry round-trip can fix.
    """
    if not isinstance(candidate, dict) or not isinstance(candidate.get("dissent"), list):
        return
    if has_dissent_source_material(passages):
        return
    candidate["dissent"] = []


# Packet budgets, in characters of passage text. Nearly every opinion fits whole
# (a 239-case benchmark averaged 32k chars; 6 ran over 100k). Before 2026-11-07
# the packet was the first 65k + last 15k chars, which cut Buckley v. Valeo's
# Appointments Clause part (it starts ~142k into a 530k-char opinion) and with it
# a holding con law classes read the case for.
MAJORITY_BUDGET_CHARS = 150_000
DISSENT_BUDGET_CHARS = 30_000
MAJORITY_PARTS = frozenset({"opinion", "majority"})
DISSENT_PARTS = frozenset({"dissent", "separate"})
# A head/tail split per majority segment: the head states the part's question and
# analysis, the tail usually holds its conclusion ("We therefore hold...").
SEGMENT_HEAD_SHARE = 0.7
FALLBACK_SEGMENTS = 8

_CAPS_HEADING_RE = re.compile(
    r"^(?:\[\d+\]\s*)?(?:[IVX]{1,5}\.?\s+)?([A-Z][A-Z'’,&-]+(?:\s+[A-Z][A-Z'’,&-]+)+)"
)
_NUMERAL_HEADING_RE = re.compile(r"^(?:\[\d+\]\s*)?[IVX]{1,5}\.?$")
_ONE_WORD_HEADING_RE = re.compile(
    r"^(?:\[\d+\]\s*)?(?:[IVX]{1,5}\.?\s+)?(?:CONCLUSION|BACKGROUND|DISCUSSION|INTRODUCTION)\b"
)
# Statutory text or data reprinted after the opinion (Buckley's runs ~100k chars).
# Dropped first when a packet must be trimmed; the omission marker says so.
_APPENDIX_RE = re.compile(r"(?:^|\.\s+)APPENDIX\b")


def _is_section_heading(text: str) -> bool:
    """Heuristic: a passage that opens a top-level part of an opinion.

    CourtListener text keeps headings inline ("REPORTING AND DISCLOSURE
    REQUIREMENTS Unlike the limitations..." or "[11] I. CONTRIBUTION AND...").
    A false positive only adds a segment boundary, which costs nothing.
    """
    stripped = text.strip()
    if _NUMERAL_HEADING_RE.match(stripped) or _ONE_WORD_HEADING_RE.match(stripped):
        return True
    match = _CAPS_HEADING_RE.match(stripped)
    return bool(match and len(match.group(1)) >= 15)


def _take_head(passages: list[dict], budget: int) -> list[dict]:
    taken, chars = [], 0
    for passage in passages:
        if taken and chars + len(passage["text"]) > budget:
            break
        taken.append(passage)
        chars += len(passage["text"])
    return taken


def _take_tail(passages: list[dict], budget: int) -> list[dict]:
    taken, chars = [], 0
    for passage in reversed(passages):
        if chars + len(passage["text"]) > budget:
            break
        taken.append(passage)
        chars += len(passage["text"])
    return list(reversed(taken))


def _segments(passages: list[dict]) -> list[list[dict]]:
    """Split passages into top-level parts, or equal slices if there are no
    detectable headings."""
    total = sum(len(passage["text"]) for passage in passages)
    raw: list[list[dict]] = []
    for passage in passages:
        if raw and not _is_section_heading(passage["text"]):
            raw[-1].append(passage)
        else:
            raw.append([passage])
    # Fold tiny segments into a neighbor: a caption joins the first part, and a
    # short CONCLUSION becomes the tail of the last part, which the tail share
    # then keeps whole.
    min_size = total / 24
    segments: list[list[dict]] = []
    for segment in raw:
        if segments and sum(len(p["text"]) for p in segment) < min_size:
            segments[-1].extend(segment)
        elif segments and sum(len(p["text"]) for p in segments[-1]) < min_size:
            segments[-1].extend(segment)
        else:
            segments.append(segment)
    if len(segments) >= 3:
        return segments
    target = total / FALLBACK_SEGMENTS
    segments, chars = [[]], 0
    for passage in passages:
        if segments[-1] and chars >= target * len(segments):
            segments.append([])
        segments[-1].append(passage)
        chars += len(passage["text"])
    return segments


def _spread_sample(passages: list[dict], budget: int) -> list[dict]:
    total = sum(len(passage["text"]) for passage in passages)
    if total <= budget:
        return list(passages)
    selected = []
    for segment in _segments(passages):
        size = sum(len(passage["text"]) for passage in segment)
        allocation = budget * size / total
        head = _take_head(segment, int(allocation * SEGMENT_HEAD_SHARE))
        head_ids = {passage["id"] for passage in head}
        tail = _take_tail(segment[len(head):], int(allocation - sum(len(p["text"]) for p in head)))
        selected.extend(head)
        selected.extend(passage for passage in tail if passage["id"] not in head_ids)
    return selected


def select_packet_passages(
    passages: list[dict],
    majority_budget: int = MAJORITY_BUDGET_CHARS,
    dissent_budget: int = DISSENT_BUDGET_CHARS,
) -> list[dict]:
    """Choose the passages a brief is written from.

    Whole opinion when it fits. Otherwise every top-level part of the majority
    is represented (head and tail of each, proportional to its length), and
    the dissent material is spread the same way. Concurrences and "other" parts are dropped
    first when trimming: no brief section may cite them.
    """
    total = sum(len(passage["text"]) for passage in passages)
    if total <= majority_budget + dissent_budget:
        return list(passages)
    majority = [p for p in passages if p.get("opinion_part") in MAJORITY_PARTS]
    appendix_at = next(
        (index for index, p in enumerate(majority) if _APPENDIX_RE.search(p["text"])),
        None,
    )
    if appendix_at is not None:
        # Keep the passage that opens the appendix: it often ends the opinion
        # proper ("MR. JUSTICE STEVENS took no part... APPENDIX TO ...").
        majority = majority[: appendix_at + 1]
    dissents = [p for p in passages if p.get("opinion_part") in DISSENT_PARTS]
    majority_chars = sum(len(p["text"]) for p in majority)
    dissent_chars = sum(len(p["text"]) for p in dissents)
    # Unused budget on one side goes to the other.
    if majority_chars < majority_budget:
        dissent_budget += majority_budget - majority_chars
    elif dissent_chars < dissent_budget:
        majority_budget += dissent_budget - dissent_chars
    chosen = {
        passage["id"]
        for passage in (
            _spread_sample(majority, majority_budget)
            # Separate writings often arrive as one unbroken "dissent" run with
            # no author lines (Buckley's five), so spread across it rather than
            # taking its opening, which would be one Justice's.
            + _spread_sample(dissents, dissent_budget)
        )
    }
    return [passage for passage in passages if passage["id"] in chosen]


def build_source_packet(text: str):
    content_hash, passages = build_opinion_passages(text)
    return content_hash, passages, select_packet_passages(passages)


def format_source_packet(passages: list[dict]) -> tuple[str, bool]:
    """Render passages one per line, marking any gap in ordinals so the model
    knows the packet skips text. Returns (text, whether anything was omitted)."""
    lines, previous, omitted = [], None, False
    for passage in passages:
        ordinal = passage.get("ordinal")
        if previous is not None and ordinal is not None and ordinal > previous + 1:
            lines.append(f"[... {ordinal - previous - 1} passages omitted ...]")
            omitted = True
        lines.append(f'[{passage["id"]}] ({passage["opinion_part"]}) {passage["text"]}')
        if ordinal is not None:
            previous = ordinal
    return "\n".join(lines), omitted


def build_structured_prompt(case_name: str, court: str, date: str, passages: list[dict]) -> str:
    source_packet, omitted = format_source_packet(passages)
    excerpt_rule = (
        "\n- This opinion is long, so the packet is an excerpt: every part of the majority is represented, with gaps marked \"passages omitted\". Brief what the packet shows and never describe omitted text."
        if omitted else ""
    )
    # Whether a dissent exists is a fact about the packet's tags, not a judgment
    # call about tone, so state it rather than leaving the model to infer it
    # from a concurrence that happens to reject the majority's reasoning.
    dissent_rules = (
        """- Cite only (dissent) or (separate) passages for dissent.
- A (separate) tag marks a separate writing whose type the source does not state. If its content is a dissent, describe it under dissent; never cite it for the majority sections."""
        if has_dissent_source_material(passages)
        else """- This packet contains no (dissent) or (separate) passages, so "dissent" must be exactly []."""
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
- Write as much as a complete, useful brief needs and no more. Be concise; a case with several separate opinions may need more room than a short one.
- Use 1-5 facts, 1-4 issues, 1-4 holdings, 1-4 rules, 1-8 majority-reasoning claims, and 0-4 dissent claims.
- Most cases decide one question; use one issue for them. When the court decides several distinct questions, often under separate headings (for example a First Amendment challenge and an Appointments Clause challenge), give each its own issue, holding, rule, and reasoning, in the same order, and do not drop any of them. A student may be assigned the case for any one of its holdings.{excerpt_rule}
- Every claim must cite one or more passage IDs that directly support the complete claim.
- Cite only opinion/majority passages for facts, issue, holding, rule, and majority reasoning.
{dissent_rules}
- Passages tagged (concurrence) are excluded from these briefs by design. Never cite them in any section, and never describe one under dissent: an opinion concurring in the judgment may reject the majority's reasoning, but it is a concurrence, not a dissent.
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
