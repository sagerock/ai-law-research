"""Simplified and bullet-point versions of an approved source-linked brief.

A variant is a rewrite of the approved detailed brief, never a fresh reading of the
opinion. The model cites detailed-brief claims by reference ("holding[1]"), and the
server derives each line's passage sources from the claims it rewrites. That keeps the
majority/dissent split and the source links that the detailed brief already passed,
and makes dropped content mechanically detectable: every detailed claim must be covered
by at least one simplified line in its own section.
"""

from __future__ import annotations

import hashlib
import json
import re

VARIANT_PROMPT_VERSION = "v2"

SECTIONS = ("facts", "issue", "holding", "rule", "majority_reasoning", "dissent")
SECTION_LABELS = {
    "facts": "Facts",
    "issue": "Issue",
    "holding": "Holding",
    "rule": "Rule",
    "majority_reasoning": "Reasoning",
    "dissent": "Dissent",
}
# Bullet labels and the detailed-brief sections each may draw on. "Outcome" is the
# disposition (affirmed, reversed, vacated and remanded), which lives in the holding.
BULLET_SECTIONS = {
    "Facts": {"facts"},
    "Issue": {"issue"},
    "Holding": {"holding"},
    "Rule": {"rule"},
    "Reasoning": {"majority_reasoning"},
    "Outcome": {"holding"},
    "Dissent": {"dissent"},
}
MAX_SIMPLIFIED_WORDS = 400
# Sections whose every detailed claim must survive simplification. Dropping a holding (a
# partial remand) or half a rule changes the law; dropping a supporting fact or one of
# four reasoning points is the simplification. Other sections need at least one line.
FULL_COVERAGE_SECTIONS = ("issue", "holding", "rule")
MAX_BULLETS = 10
MAX_BULLET_WORDS = 40

_REF_RE = re.compile(r"^(facts|issue|holding|rule|majority_reasoning|dissent)\[(\d+)\]$")


def source_digest(summary: dict) -> str:
    """Fingerprint the detailed brief a variant was rewritten from."""
    canonical = json.dumps(
        {key: summary.get(key) for key in (*SECTIONS, "significance")},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _numbered_brief(summary: dict) -> str:
    lines = []
    for section in SECTIONS:
        claims = summary.get(section) or []
        if not claims:
            continue
        lines.append(f"{SECTION_LABELS[section].upper()}:")
        for index, claim in enumerate(claims):
            lines.append(f"  [{section}[{index}]] {claim['text']}")
    return "\n".join(lines)


def build_variant_prompt(case_name: str, summary: dict) -> str:
    has_dissent = bool(summary.get("dissent"))
    dissent_rule = (
        '- Include a "dissent" section and one "Dissent" bullet.'
        if has_dissent
        else '- This brief has no dissent: "dissent" must be [] and there is no "Dissent" bullet.'
    )
    limit = MAX_SIMPLIFIED_WORDS
    return f"""Rewrite this approved law-school case brief for {case_name} in two shorter forms.
Each detailed claim has a reference in brackets, like [holding[0]].

DETAILED BRIEF:
{_numbered_brief(summary)}

Return JSON only, with exactly this shape:
{{
  "simplified": {{
    "facts": [{{"text": "...", "from": ["facts[0]"]}}],
    "issue": [...], "holding": [...], "rule": [...],
    "majority_reasoning": [...], "dissent": [...]
  }},
  "bullets": [{{"label": "Holding", "text": "...", "from": ["holding[0]"]}}]
}}

SIMPLIFIED: the same sections, written for a reader who has never taken a law class and
is reading this before the case. Aim for about 250 words in total; the hard limit is
{limit} words. Brevity matters more than detail here: the detailed brief stays one click
away.
- Use everyday words. Replace legal and formal vocabulary ("wholesome", "nondiscriminatory",
  "appellant", "vacated") with plain words ("safe", "treating everyone the same", "Dean
  Milk", "sent back"). Keep the name of a legal test only if you explain it in the same
  sentence.
- Short sentences that each say who did what. Reread every sentence: it must make sense
  on its own and say exactly what its claims say, not the opposite.
- At most 2 lines per section, each 1-3 short sentences. Merge related claims into one line
  and keep only the point each claim makes, not its supporting detail (exact dollar
  figures, statistics, and record citations usually go).
- Each line lists in "from" the detailed claims it rewrites, all from the same section.
- Every issue, holding, and rule claim must appear in the "from" of some line. In facts,
  reasoning, and dissent, keep only the claims a beginner needs to follow the case
  (usually 1-2 lines per section) and leave the rest to the detailed brief. Each kept
  line may say only what its cited claims say.

BULLETS: 5-8 one-line points, each at most 30 words. "label" is one of: Facts, Issue,
Holding, Rule, Reasoning, Outcome, Dissent. Include at least Holding, Rule, and Outcome.
Outcome states the disposition, including any part vacated or remanded.
Bullets are for exam review, so unlike Simplified they keep the court's own doctrinal
terms and tests word for word (for example "clearly excessive", "virtually per se
invalid", "substantial reason"), each with a short plain explanation if it needs one.
Keep the elements of a multi-part test; do not paraphrase a test into vaguer words. Each bullet's
"from" may cite only claims from its label's section (Outcome cites holding claims).
{dissent_rule}

Accuracy rules for both forms:
- Plain words, same law. Restate the legal test the court applied so its meaning does not
  change: "discriminates against out-of-state businesses" may become "treats out-of-state
  businesses worse", but never a looser or different standard such as "makes it too hard".
  Never describe a test with the vocabulary of a different doctrine.
- Keep every part of the outcome, including partial dispositions.
- Name the specific alternatives, factors, or exceptions the brief names; do not
  generalize them into vaguer words.
- Keep modal force: "may" stays permissive and "must" stays mandatory.
- Use only what the detailed brief states. Add no facts, names, votes, quotations, later
  history, or doctrine from outside it."""


def _variant_lines(candidate: dict):
    for section in SECTIONS:
        for index, line in enumerate(candidate["simplified"].get(section, [])):
            yield f"simplified.{section}[{index}]", line
    for index, bullet in enumerate(candidate["bullets"]):
        yield f"bullets[{index}] ({bullet['label']})", bullet


def build_fidelity_prompt(case_name: str, summary: dict, candidate: dict) -> str:
    """Ask a separate reviewer whether each rewritten line says what its claims say.

    Structural validation proves each line cites real claims from the right section; it
    cannot tell whether the plain-English sentence still means the same thing. A context
    that wrote a sentence is the worst judge of that, so this runs as its own call.
    """
    claims = {
        f"{section}[{index}]": claim["text"]
        for section in SECTIONS
        for index, claim in enumerate(summary.get(section) or [])
    }
    rows = []
    for where, line in _variant_lines(candidate):
        cited = "\n".join(f"    {ref}: {claims.get(ref.strip(), '(unknown)')}" for ref in line["from"])
        rows.append(f"{where}: {line['text']}\n  CITED CLAIMS:\n{cited}")
    lines_block = "\n\n".join(rows)
    return f"""You are checking a plain-English rewrite of an approved case brief for {case_name}.
For each rewritten line below, compare it only with the detailed claims it cites.

Flag a line if it:
- says something the cited claims do not say, or the opposite of what they say;
- is garbled or self-contradictory;
- changes the legal test, its strength, or its modal force (may/must), or swaps in a
  different doctrine's vocabulary (for example calling a discrimination holding a burden);
- leaves out part of the outcome that the cited claims state; or
- adds a fact, name, number, or vote that the cited claims do not contain.

Do not flag simplification itself: dropping supporting detail and using everyday words are
the point of the rewrite.

REWRITTEN LINES:
{lines_block}

Rate each problem's severity:
- "wrong": a student relying on the line would misstate the case, its outcome, or its rule.
- "minor": imprecise or incomplete wording that still points the student the right way.

Decide before you write. Return one JSON object and nothing else:
{{"problems": [{{"line": "simplified.dissent[0]", "severity": "wrong", "problem": "..."}}]}}
Return {{"problems": []}} if every line is faithful."""


def parse_fidelity_response(text: str) -> list[str]:
    """Return reviewer problems as validation-style error strings."""
    value = _last_json_object(text)
    problems = value.get("problems") if isinstance(value, dict) else None
    if not isinstance(problems, list):
        raise ValueError("fidelity response lacks a problems list")
    errors = []
    for problem in problems:
        if not isinstance(problem, dict) or not problem.get("problem"):
            continue
        # Minor imprecision is the cost of simplifying; only misstatements block.
        if problem.get("severity", "wrong") != "wrong":
            continue
        errors.append(f"{problem.get('line', 'a line')}: {problem['problem']}")
    return errors


def correction_message(errors: list[str], fidelity: bool) -> str:
    """The follow-up turn for a failed attempt."""
    if fidelity:
        return (
            "A reviewer found these lines misstate the detailed brief: " + "; ".join(errors)
            + ". Rewrite only the named lines so each says exactly what its cited claims say."
            " Copy every other line unchanged. Return the complete corrected JSON only."
        )
    return (
        "That response failed validation: " + "; ".join(errors)
        + ". Return the corrected JSON only, following every requirement in the original"
        " instructions."
    )


def _last_json_object(text: str):
    """The final JSON object in the text: a reviewer that revises itself ends with its answer."""
    decoder = json.JSONDecoder()
    last = None
    index = text.find("{")
    while index != -1:
        try:
            value, end = decoder.raw_decode(text, index)
        except json.JSONDecodeError:
            index = text.find("{", index + 1)
            continue
        last = value
        index = text.find("{", end)
    if last is None:
        raise ValueError("no JSON object in response")
    return last


def parse_variant_response(text: str) -> dict:
    value = text.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.I)
        value = re.sub(r"\s*```$", "", value)
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        # Models occasionally wrap the object in a sentence; take the outermost braces.
        start, end = value.find("{"), value.rfind("}")
        if start == -1 or end <= start:
            raise
        return json.loads(value[start:end + 1])


def _resolve_ref(ref, summary: dict):
    if not isinstance(ref, str):
        return None
    match = _REF_RE.match(ref.strip())
    if not match:
        return None
    section, index = match.group(1), int(match.group(2))
    claims = summary.get(section) or []
    if index >= len(claims):
        return None
    return section, index


def _word_count(text: str) -> int:
    return len(text.split())


def validate_variants(candidate: dict, summary: dict) -> list[str]:
    """Return every reason the candidate cannot be published; empty means valid."""
    errors: list[str] = []
    if not isinstance(candidate, dict):
        return ["response is not a JSON object"]
    simplified = candidate.get("simplified")
    bullets = candidate.get("bullets")
    if not isinstance(simplified, dict):
        errors.append("simplified must be an object")
        simplified = {}
    if not isinstance(bullets, list):
        errors.append("bullets must be a list")
        bullets = []

    total_words = 0
    for section in SECTIONS:
        lines = simplified.get(section, [])
        detailed = summary.get(section) or []
        if not isinstance(lines, list):
            errors.append(f"simplified.{section} must be a list")
            continue
        if not detailed and lines:
            errors.append(f"simplified.{section} must be empty; the detailed brief has none")
            continue
        covered: set[int] = set()
        for position, line in enumerate(lines):
            where = f"simplified.{section}[{position}]"
            if not isinstance(line, dict) or not isinstance(line.get("text"), str) or not line["text"].strip():
                errors.append(f"{where} needs text")
                continue
            total_words += _word_count(line["text"])
            refs = line.get("from")
            if not isinstance(refs, list) or not refs:
                errors.append(f"{where} must cite at least one detailed claim")
                continue
            for ref in refs:
                resolved = _resolve_ref(ref, summary)
                if resolved is None:
                    errors.append(f"{where} cites unknown claim {ref!r}")
                elif resolved[0] != section:
                    errors.append(f"{where} cites {ref!r} from another section")
                else:
                    covered.add(resolved[1])
        if not detailed:
            continue
        if section in FULL_COVERAGE_SECTIONS:
            missing = [f"{section}[{index}]" for index in range(len(detailed)) if index not in covered]
            if missing:
                errors.append(f"simplified.{section} drops detailed claims: {', '.join(missing)}")
        elif not covered:
            errors.append(f"simplified.{section} needs at least one line")
    if total_words > MAX_SIMPLIFIED_WORDS:
        errors.append(f"simplified is {total_words} words; the limit is {MAX_SIMPLIFIED_WORDS}")

    if len(bullets) > MAX_BULLETS:
        errors.append(f"{len(bullets)} bullets; the limit is {MAX_BULLETS}")
    labels = []
    for position, bullet in enumerate(bullets):
        where = f"bullets[{position}]"
        if not isinstance(bullet, dict) or not isinstance(bullet.get("text"), str) or not bullet["text"].strip():
            errors.append(f"{where} needs text")
            continue
        label = bullet.get("label")
        if label not in BULLET_SECTIONS:
            errors.append(f"{where} has unknown label {label!r}")
            continue
        labels.append(label)
        if _word_count(bullet["text"]) > MAX_BULLET_WORDS:
            errors.append(f"{where} exceeds {MAX_BULLET_WORDS} words")
        refs = bullet.get("from")
        if not isinstance(refs, list) or not refs:
            errors.append(f"{where} must cite at least one detailed claim")
            continue
        for ref in refs:
            resolved = _resolve_ref(ref, summary)
            if resolved is None:
                errors.append(f"{where} cites unknown claim {ref!r}")
            elif resolved[0] not in BULLET_SECTIONS[label]:
                errors.append(f"{where} ({label}) cannot cite {ref!r}")
    for required in ("Holding", "Rule", "Outcome"):
        if required not in labels:
            errors.append(f"bullets need a {required} bullet")
    if summary.get("dissent") and "Dissent" not in labels:
        errors.append("bullets need a Dissent bullet")
    if not summary.get("dissent") and "Dissent" in labels:
        errors.append("bullets include a Dissent bullet but the brief has no dissent")
    return errors


def _sources_for(refs: list, summary: dict) -> list[str]:
    sources: list[str] = []
    for ref in refs:
        resolved = _resolve_ref(ref, summary)
        if resolved is None:
            continue
        section, index = resolved
        for passage_id in summary[section][index].get("sources", []):
            if passage_id not in sources:
                sources.append(passage_id)
    return sources


def attach_sources(candidate: dict, summary: dict) -> dict:
    """Return the publishable variant: normalized refs plus derived passage sources."""
    simplified = {}
    for section in SECTIONS:
        simplified[section] = [
            {
                "text": line["text"].strip(),
                "from": [ref.strip() for ref in line["from"]],
                "sources": _sources_for(line["from"], summary),
            }
            for line in candidate["simplified"].get(section, [])
        ]
    bullets = [
        {
            "label": bullet["label"],
            "text": bullet["text"].strip(),
            "from": [ref.strip() for ref in bullet["from"]],
            "sources": _sources_for(bullet["from"], summary),
        }
        for bullet in candidate["bullets"]
    ]
    return {"simplified": simplified, "bullets": bullets}
