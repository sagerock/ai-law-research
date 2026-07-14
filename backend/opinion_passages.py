import hashlib
import html
import re


ABBREVIATIONS = ("Mrs.", "Mr.", "Ms.", "Dr.", "Ch. J.", "J.", "Co.", "R.R.", "U.S.")
JUSTICE_PREFIX = r"(?:(?:The|Mr\.|Ms\.|Mrs\.)\s+)?(?:(?:Chief|Associate)\s+)?Justice\b"


def prepare_opinion_text(text: str) -> str:
    """Convert stored opinion HTML to text without losing block boundaries."""
    if "<" not in text or ">" not in text:
        return html.unescape(text)
    value = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
    value = re.sub(
        r"(?i)</?(?:p|div|h[1-6]|blockquote|li|br|section|article|table|tr)[^>]*>",
        "\n",
        value,
    )
    value = re.sub(r"<[^>]+>", " ", value)
    lines = [normalize_opinion_text(line) for line in html.unescape(value).splitlines()]
    return "\n".join(line for line in lines if line)


def detect_opinion_marker(blocks: list[str], index: int) -> tuple[str | None, int]:
    """Return an opinion part and number of marker blocks consumed.

    CourtListener's hand-curated opinions use bracketed markers such as
    ``[Dissent by Andrews]``. Official U.S. Reports text instead introduces a
    separate writing with prose such as ``Justice Kagan, ... dissenting.``;
    those introductions are often wrapped across two lines. Running page
    headers (for example, ``Kagan, J., dissenting``) are deliberately ignored
    because they can appear above the final text of the preceding opinion.
    """
    block = blocks[index]
    marker = re.fullmatch(r"\[(?:(Dissent|Concurrence)\s+by|by)\s+[^]]+\]", block, re.I)
    if marker:
        return (marker.group(1) or "majority").lower(), 1

    if re.fullmatch(r"per\s+curiam\.?", block, re.I):
        return "majority", 1

    if re.fullmatch(r"(?:notes|footnotes)", block, re.I):
        return "opinion", 1

    if not re.match(rf"^{JUSTICE_PREFIX}", block, re.I):
        return None, 0

    # Opinion introductions in reporter text commonly wrap after one or two
    # short lines. Requiring a sentence-ending period avoids treating a partial
    # first line as a marker and leaving its continuation as opinion text.
    for consumed in range(1, min(3, len(blocks) - index) + 1):
        candidate = normalize_opinion_text(" ".join(blocks[index:index + consumed]))
        if not candidate.endswith("."):
            continue
        if re.fullmatch(
            rf"{JUSTICE_PREFIX}.*,\s*dissenting"
            r"(?:\s+from\b[^.]*)?\.",
            candidate,
            re.I,
        ):
            return "dissent", consumed
        if re.fullmatch(
            rf"{JUSTICE_PREFIX}.*,\s*concurring\b[^.]*\.",
            candidate,
            re.I,
        ):
            return "concurrence", consumed
        if re.fullmatch(
            rf"{JUSTICE_PREFIX}.*"
            r"(?:delivered\s+(?:the|an)\s+opinion\s+of\s+the\s+Court|"
            r"announced\s+the\s+judgment\s+of\s+the\s+Court)[^.]*\.",
            candidate,
            re.I,
        ):
            return "majority", consumed
    return None, 0


def normalize_opinion_text(text: str) -> str:
    text = text.translate(str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "—": "-"}))
    return re.sub(r"\s+", " ", text.replace("&amp;", "&")).strip()


def split_sentences(text: str) -> list[str]:
    protected = normalize_opinion_text(text)
    for abbreviation in ABBREVIATIONS:
        protected = protected.replace(abbreviation, abbreviation.replace(".", "<DOT>"))
    return [
        part.replace("<DOT>", ".").strip()
        for part in re.split(r"(?<=[.!?])\s+", protected)
        if part.strip()
    ]


def build_opinion_passages(text: str, sentences_per_passage: int = 1) -> tuple[str, list[dict]]:
    prepared = prepare_opinion_text(text)
    normalized = normalize_opinion_text(prepared)
    content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    opinion_part = "opinion"
    sentences: list[tuple[str, str]] = []
    blocks = [block.strip() for block in prepared.splitlines() if block.strip()]
    index = 0
    while index < len(blocks):
        marker_part, consumed = detect_opinion_marker(blocks, index)
        if marker_part:
            opinion_part = marker_part
            index += consumed
            continue
        block = blocks[index]
        sentences.extend((opinion_part, sentence) for sentence in split_sentences(block))
        index += 1

    passages = []
    passage_id_counts: dict[str, int] = {}
    for ordinal, start in enumerate(range(0, len(sentences), sentences_per_passage)):
        group = sentences[start:start + sentences_per_passage]
        passage_text = normalize_opinion_text(" ".join(sentence for _, sentence in group))
        if not passage_text:
            continue
        base_id = "op-" + hashlib.sha256(passage_text.encode("utf-8")).hexdigest()[:16]
        occurrence = passage_id_counts.get(base_id, 0) + 1
        passage_id_counts[base_id] = occurrence
        passage_id = base_id if occurrence == 1 else f"{base_id}-{occurrence}"
        passages.append({
            "id": passage_id,
            "ordinal": ordinal,
            "opinion_part": group[0][0],
            "text": passage_text,
        })
    return content_hash, passages
