#!/usr/bin/env python3
"""Build a read-only example linking an existing case brief to opinion passages."""

import json
import math
import re
import urllib.request
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path


API_URL = "https://backend-production-8940.up.railway.app"
CASE_ID = "3602780"
OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "prototypes" / "palsgraf-summary-links.md"
SECTION_RE = re.compile(r"\*\*([^*]+)\*\*\s*\n+(.*?)(?=\n\*\*|\Z)", re.S)
WORD_RE = re.compile(r"[a-z][a-z'-]{2,}")
STOPWORDS = {
    "and", "are", "but", "for", "from", "had", "has", "have", "her", "his",
    "its", "not", "that", "the", "their", "there", "they", "this", "was", "were",
    "which", "who", "with", "would",
}


def fetch_json(path):
    with urllib.request.urlopen(f"{API_URL}{path}", timeout=30) as response:
        return json.load(response)


def normalize(text):
    text = text.translate(str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "—": "-"}))
    return re.sub(r"\s+", " ", text.replace("&amp;", "&")).strip()


def split_sentences(text):
    protected = normalize(text)
    for abbreviation in ("Mrs.", "Mr.", "Ch. J.", "J.", "Co.", "R.R.", "U.S."):
        protected = protected.replace(abbreviation, abbreviation.replace(".", "<DOT>"))
    return [part.replace("<DOT>", ".") for part in re.split(r"(?<=[.!?])\s+", protected)]


def words(text):
    return [word for word in WORD_RE.findall(text.lower()) if word not in STOPWORDS]


def cosine(left, right):
    a, b = Counter(words(left)), Counter(words(right))
    common = set(a) & set(b)
    numerator = sum(a[word] * b[word] for word in common)
    denominator = math.sqrt(sum(value * value for value in a.values())) * math.sqrt(
        sum(value * value for value in b.values())
    )
    return numerator / denominator if denominator else 0


def passages(opinion):
    labeled = opinion.replace("[by Cardozo]", "\nMAJORITY\n").replace(
        "[Dissent by Andrews]", "\nDISSENT\n"
    )
    result = []
    opinion_part = "opinion"
    sentences = []
    for block in labeled.splitlines():
        block = normalize(block)
        if not block:
            continue
        if block in {"MAJORITY", "DISSENT"}:
            opinion_part = block.lower()
            continue
        sentences.extend((opinion_part, sentence) for sentence in split_sentences(block))

    for index in range(0, len(sentences), 2):
        part = sentences[index][0]
        window = normalize(" ".join(sentence for _, sentence in sentences[index:index + 3]))
        if len(window) >= 80:
            result.append({"id": f"op-{index + 1:03d}", "part": part, "text": window})
    return result


def section_claims(summary):
    for heading, body in SECTION_RE.findall(summary):
        section = re.sub(r"^[^A-Za-z]+", "", heading).strip()
        claims = [normalize(claim) for claim in split_sentences(body)]
        claims.extend(normalize(quote) for quote in re.findall(r'"([^"]{30,})"', normalize(body)))
        yield section, list(dict.fromkeys(claim for claim in claims if len(claim) >= 30))


def score_match(claim, passage):
    lexical = cosine(claim, passage)
    sequence = SequenceMatcher(None, claim.lower(), passage.lower()).ratio()
    quoted = re.findall(r'"([^"]{18,})"', claim)
    quote_match = max(
        (SequenceMatcher(None, quote.lower(), passage.lower()).ratio() for quote in quoted),
        default=0,
    )
    return min(1.0, 0.62 * lexical + 0.18 * sequence + 0.35 * quote_match)


def confidence(score):
    if score >= 0.58:
        return "high"
    if score >= 0.42:
        return "medium"
    return "low"


def build_report(case, summary):
    opinion_passages = passages(case["content"])
    lines = [
        f"# Source-linked brief prototype: {case['title']}",
        "",
        f"Case: `{case['reporter_cite']}` | Production case ID: `{case['id']}`",
        "",
        "This is a read-only similarity prototype. Links marked low confidence would not be shown to users.",
        "Passage IDs are generated deterministically from the current opinion text and are not yet persisted.",
        "",
    ]

    for section, claims in section_claims(summary["summary"]):
        candidates = []
        for claim in claims:
            best = max(opinion_passages, key=lambda item: score_match(claim, item["text"]))
            candidates.append((score_match(claim, best["text"]), claim, best))

        selected = []
        seen = set()
        for match in sorted(candidates, reverse=True, key=lambda item: item[0]):
            if match[2]["id"] not in seen:
                selected.append(match)
                seen.add(match[2]["id"])
            if len(selected) == 2:
                break

        visible = [match for match in selected if confidence(match[0]) != "low"]
        lines.extend([f"## {section}", ""])
        if not visible:
            lines.extend(["No passage met the display threshold.", ""])
        for score, claim, passage in visible:
            lines.extend([
                f"**Suggested link:** `{passage['id']}` ({passage['part']}, {confidence(score)} confidence, {score:.2f})",
                "",
                f"> Brief claim: {claim}",
                "",
                f"> Opinion passage: {passage['text']}",
                "",
            ])

    return "\n".join(lines)


def main():
    case = fetch_json(f"/api/v1/cases/{CASE_ID}")
    summary = fetch_json(f"/api/v1/cases/{CASE_ID}/summary")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(build_report(case, summary), encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
