import hashlib
import html
import re


ABBREVIATIONS = ("Mrs.", "Mr.", "Ms.", "Dr.", "Ch. J.", "J.", "Co.", "R.R.", "U.S.")
JUSTICE_PREFIX = r"(?:(?:The|Mr\.|Ms\.|Mrs\.)\s+)?(?:(?:Chief|Associate)\s+)?Justice\b"
PASSAGE_FORMAT_VERSION = "3"

# Lower courts introduce separate writings surname-first ("RIPPLE, Circuit
# Judge, dissenting."), unlike the Supreme Court's "Justice Kagan, dissenting."
# The author name is required to be ALL CAPS and the disposition to be a
# participle: citation strings ("Cudahy, J., dissenting, at 1012-14") use mixed
# case, and end-of-opinion vote lines ("ANDREWS, J., dissents ... JJ., concur")
# use finite verbs, so both fail these anchors.
LOWER_COURT_AUTHOR = (
    r"(?:[A-Z]\.\s+)*(?:(?:Mc|Mac|O'|D')?[A-Z][A-Z'\-]+)"
    r"(?:\s+(?:[A-Z]\.|(?:Mc|Mac|O'|D')?[A-Z][A-Z'\-]+))*"
)
LOWER_COURT_TITLE = (
    r"(?:(?:Chief|Circuit|District|Senior|Presiding)\s+)*"
    r"(?:Judges?|Justices?|C\.\s?J\.|Ch\.\s?J\.|JJ?\.)"
)
LOWER_COURT_HEADING = re.compile(
    rf"(?:\d{{1,4}}\s+)?{LOWER_COURT_AUTHOR},\s*{LOWER_COURT_TITLE}"
    r"(?:,[^.;]*?)?"  # optional "joined by ..." / "with whom ..." clause
    r",?\s+\(?(?:dissenting|concurring)"
    r"(?:\s+in\s+part)?(?:\s+and\s+(?:dissenting|concurring)(?:\s+in\s+part)?)*"
    r"(?:\s+in\s+the\s+(?:judgment|result))?"
    r"(?:\s+from\b[^.;]*)?"
    r"\)?\s*\."
)
LOWER_COURT_MAJORITY = re.compile(
    rf"(?:\d{{1,4}}\s+)?{LOWER_COURT_AUTHOR}"
    r",\s*(?:(?:Chief|Circuit|District|Senior|Presiding)\s+)*Judges?"
    r"(?:,(?![^.;]*(?:dissent|concurr))[^.;]*?)?"
    r"(?:[:.]|,?\s+deliver\w+\s+the\s+opinion\b[^.;]*\.)"
)


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

    is_justice_intro = bool(re.match(rf"^{JUSTICE_PREFIX}", block, re.I))
    is_lower_court_intro = bool(
        re.match(rf"^(?:\d{{1,4}}\s+)?{LOWER_COURT_AUTHOR},", block)
    )
    if not is_justice_intro and not is_lower_court_intro:
        return None, 0

    # Opinion introductions in reporter text commonly wrap after one or two
    # short lines. Requiring a sentence-ending period avoids treating a partial
    # first line as a marker and leaving its continuation as opinion text.
    for consumed in range(1, min(3, len(blocks) - index) + 1):
        candidate = normalize_opinion_text(" ".join(blocks[index:index + consumed]))
        if not candidate.endswith("."):
            continue
        boundary_check = candidate
        for abbreviation in ABBREVIATIONS:
            boundary_check = re.sub(
                re.escape(abbreviation),
                abbreviation.replace(".", "<DOT>"),
                boundary_check,
                flags=re.I,
            )
        if len(re.findall(r"[.!?](?:\s+|$)", boundary_check)) != 1:
            continue
        if re.fullmatch(
            rf"{JUSTICE_PREFIX}.*(?:,\s*|\s+)dissenting"
            r"(?:\s+from\b[^.]*)?(?:,\s*with whom concurred\b.*)?\.",
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
        if is_lower_court_intro:
            if LOWER_COURT_HEADING.fullmatch(candidate):
                # A partial dissent ("concurring in part and dissenting in
                # part") reads as dissent so dissent claims may cite it.
                part = "dissent" if "dissent" in candidate.lower() else "concurrence"
                return part, consumed
            if LOWER_COURT_MAJORITY.fullmatch(candidate):
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
    # This identifies the derived passage set, not only the source text. Bump
    # the format version whenever parsing changes can alter IDs or ordinals so
    # existing candidates retain their original, internally consistent set.
    content_hash = hashlib.sha256(
        f"{PASSAGE_FORMAT_VERSION}\0{normalized}".encode("utf-8")
    ).hexdigest()
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
        for sentence in split_sentences(block):
            # Some plain-text opinions flatten separate-writing headings into
            # the surrounding paragraph instead of preserving line breaks.
            marker_part, _ = detect_opinion_marker([sentence], 0)
            if marker_part:
                opinion_part = marker_part
                continue
            sentences.append((opinion_part, sentence))
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
