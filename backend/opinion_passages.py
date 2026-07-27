from collections import Counter
from dataclasses import dataclass
import hashlib
import html
import json
import re


ABBREVIATIONS = ("Mrs.", "Mr.", "Ms.", "Dr.", "Ch. J.", "J.", "Co.", "R.R.", "U.S.")
JUSTICE_PREFIX = r"(?:(?:The|Mr\.|Ms\.|Mrs\.)\s+)?(?:(?:Chief|Associate)\s+)?Justice\b"
PASSAGE_FORMAT_VERSION = "8"
CANONICAL_MARKER_RE = re.compile(r"\[\[COURTLISTENER_SUBOPINION\s+(.+)\]\]")
EXTRACTOR_MARKER_RE = re.compile(
    r"={3,}\s*(Lead Opinion|Majority|Opinion|Plurality|Concurrence(?: in Part)?|Dissent)\s*={3,}",
    re.I,
)
EXTRACTOR_PARTS = {
    "lead opinion": "majority",
    "majority": "majority",
    "opinion": "majority",
    "plurality": "majority",
    "concurrence": "concurrence",
    "concurrence in part": "concurrence",
    "dissent": "dissent",
}

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
LOWER_COURT_HEADING_BODY = (
    rf"(?:\d{{1,4}}\s+)?{LOWER_COURT_AUTHOR},\s*{LOWER_COURT_TITLE}"
    r"(?:,[^.;]*?)?"  # optional "joined by ..." / "with whom ..." clause
    r",?\s+\(?(?:dissenting|concurring)"
    r"(?:\s+in\s+part)?(?:\s+and\s+(?:dissenting|concurring)(?:\s+in\s+part)?)*"
    r"(?:\s+in\s+the\s+(?:judgment|result))?"
    r"(?:\s+from\b[^.;]*)?"
)
LOWER_COURT_HEADING = re.compile(LOWER_COURT_HEADING_BODY + r"\)?\s*[:.]")
LOWER_COURT_INLINE_HEADING = re.compile(
    rf"(?m)(^|[.!?][ \t]+)({LOWER_COURT_HEADING_BODY}\)?\s*:)[ \t]+(?=\S)"
)
LOWER_COURT_MAJORITY = re.compile(
    rf"(?:\d{{1,4}}\s+)?{LOWER_COURT_AUTHOR}"
    r",\s*(?:(?:Chief|Circuit|District|Senior|Presiding)\s+)*Judges?"
    r"(?:,(?![^.;]*(?:dissent|concurr))[^.;]*?)?"
    r"(?:[:.]|,?\s+deliver\w+\s+the\s+opinion\b[^.;]*\.)"
)


# Typeset reporter text (U.S. Reports preliminary prints, state slip opinions)
# arrives hard-wrapped at the column the typesetter used, so a sentence spans
# many source lines and every line ends mid-clause. Blocks are then line-sized
# rather than sentence-sized and passages cite fragments like "To ad-".
# Unwrapping is gated on detection because most of the catalog stores one
# paragraph — or the whole opinion — per line, where rejoining would be wrong.
WRAP_MIN_LINES = 40
WRAP_MAX_MEDIAN_WIDTH = 100
WRAP_MIN_UNTERMINATED = 0.5
# Above this share, blank lines are line spacing (double-spaced slip opinions),
# not paragraph separators, so they must not end a block.
WRAP_BLANK_SPACING_RATIO = 0.35
LINE_TERMINALS = ('.', '!', '?', '"', "'", ':', ';', '”', '’')
# A short line set this far in is centered — a section label ("OPINION", "II"),
# not a wrapped clause. Block quotes indent perhaps half as far. These stay in
# the text but end their block: glued onto the writing heading that follows
# ("OPINION Justice Goldberg, for the Court.") they hide it from marker
# detection and the opinion silently loses its majority boundary.
CENTERED_INDENT = 20
CENTERED_MAX_WIDTH = 60

# Page furniture, recognized by content wherever it appears in a wrapped source.
PAGE_FURNITURE_RE = re.compile(
    r"""
      Page\s+Proof\s+Pending\s+Publication   # preliminary-print watermark
    | -\s*\d{1,4}\s*-                        # centered page number: -12-
    """,
    re.X | re.I,
)
# Section labels a reporter repeats under the running head of every page. Only
# consulted directly beneath a page break, so "Syllabus" as a body word is safe.
PAGE_HEADER_RE = re.compile(
    r"""
      Cite\s+as:.*
    | (?:[A-Z][a-z]+\s+)?TERM,?\s*\d{4}.*
    | Syllabus
    | Counsel
    | Per\s+Curiam
    | Opinion\s+of\s+(?:the\s+Court|[A-Z][A-Za-z'.-]+,?\s*JJ?\.)
    | Reporter'?s\s+Note
    | [A-Z][A-Za-z'.\ -]{1,40},\s*(?:C\.\s*)?JJ?\.,\s*(?:concurring|dissenting)[^.]*
    """,
    re.X,
)
PAGE_BREAK = "\f"


def _is_page_header(line: str) -> bool:
    """Whether a page-break line is a running head rather than body text.

    A page break lands mid-sentence as often as it lands between paragraphs, so
    the text riding on it is usually real content ("\fmale opened the barbershop
    door") and deleting it would be far worse than the fragmentation being
    fixed. Running heads are distinguishable: centered or right-aligned, short,
    shouted or drawn from the reporter's fixed label vocabulary, never ending a
    sentence.
    """
    if len(line) - len(line.lstrip()) >= 20:
        return True
    value = line.strip()
    if not value or len(value) > 80 or value.endswith("."):
        return False
    # Strip a leading or trailing page number: "782   SMITH v. ARIZONA".
    value = re.sub(r"^\d{1,4}\s{2,}", "", value)
    value = re.sub(r"\s{2,}\d{1,4}$", "", value).strip()
    if not value:
        return True
    letters = [character for character in value if character.isalpha()]
    if letters and sum(character.isupper() for character in letters) / len(letters) >= 0.6:
        return True
    return bool(PAGE_HEADER_RE.fullmatch(value))


def looks_hard_wrapped(lines: list[str]) -> bool:
    """Whether these lines were broken by a typesetter rather than an author."""
    body = [line.strip() for line in lines if line.strip()]
    if len(body) < WRAP_MIN_LINES:
        return False
    widths = sorted(len(line) for line in body)
    if widths[len(widths) // 2] > WRAP_MAX_MEDIAN_WIDTH:
        return False
    unterminated = sum(1 for line in body if not line.endswith(LINE_TERMINALS))
    return unterminated / len(body) > WRAP_MIN_UNTERMINATED


def unwrap_typeset_lines(text: str) -> str:
    """Rejoin typesetter-wrapped lines into blocks, dropping page furniture.

    Left alone unless the source is detected as hard-wrapped, so the paragraph-
    per-line and whole-opinion-per-line shapes that dominate the catalog keep
    their existing segmentation exactly.
    """
    lines = text.split("\n")
    if not looks_hard_wrapped(lines):
        return text

    blank_ratio = sum(1 for line in lines if not line.strip()) / max(len(lines), 1)
    blank_separates = blank_ratio <= WRAP_BLANK_SPACING_RATIO

    blocks: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current.strip():
            blocks.append(current.strip())
        current = ""

    def append(fragment: str) -> None:
        nonlocal current
        if not current:
            current = fragment
        elif current.endswith("-"):
            # Syllabic hyphenation is overwhelmingly the reason a justified line
            # ends in a hyphen ("de-" / "fendant"), so the hyphen goes. A true
            # compound broken at its hyphen ("cross-" / "examine") loses it too;
            # accepted, since the alternative mangles far more words.
            current = current[:-1] + fragment if fragment[:1].islower() else current + fragment
        else:
            current += " " + fragment

    # A page break is padded with blank lines above and below its running head.
    # Those blanks are typography, not paragraph breaks: letting them end a
    # block strands the clause the page interrupted ("It re-").
    in_page_break = False
    for line in lines:
        if not line.strip():
            if blank_separates and not in_page_break:
                flush()
            continue
        if PAGE_BREAK in line:
            line = line.replace(PAGE_BREAK, "")
            if not line.strip() or _is_page_header(line):
                in_page_break = True
                continue
        elif in_page_break and PAGE_HEADER_RE.fullmatch(line.strip()):
            # The label repeated beneath every running head, on its own line.
            continue
        in_page_break = False
        stripped = line.strip()
        if PAGE_FURNITURE_RE.fullmatch(stripped):
            continue
        if (
            len(line) - len(line.lstrip()) >= CENTERED_INDENT
            and len(stripped) <= CENTERED_MAX_WIDTH
            and not stripped.endswith(LINE_TERMINALS)
        ):
            flush()
            blocks.append(stripped)
            continue
        # Structural markers must survive as standalone blocks or the opinion
        # boundaries they declare are lost inside a joined paragraph.
        if (
            CANONICAL_MARKER_RE.fullmatch(stripped)
            or EXTRACTOR_MARKER_RE.fullmatch(stripped)
        ):
            flush()
            blocks.append(stripped)
            continue
        append(stripped)
    flush()
    return "\n".join(blocks)


def prepare_opinion_text(text: str) -> str:
    """Convert stored opinion HTML to text without losing block boundaries."""
    if "<" not in text or ">" not in text:
        prepared = unwrap_typeset_lines(html.unescape(text))
        return LOWER_COURT_INLINE_HEADING.sub(r"\1\n\2\n", prepared)
    value = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
    value = re.sub(
        r"(?i)</?(?:p|div|h[1-6]|blockquote|li|br|section|article|table|tr)[^>]*>",
        "\n",
        value,
    )
    value = re.sub(r"<[^>]+>", " ", value)
    lines = [normalize_opinion_text(line) for line in html.unescape(value).splitlines()]
    prepared = unwrap_typeset_lines("\n".join(line for line in lines if line))
    return LOWER_COURT_INLINE_HEADING.sub(r"\1\n\2\n", prepared)


def detect_opinion_marker(
    blocks: list[str], index: int, previous_text: str | None = None
) -> tuple[str | None, int]:
    """Return an opinion part and number of marker blocks consumed.

    CourtListener's hand-curated opinions use bracketed markers such as
    ``[Dissent by Andrews]``. Official U.S. Reports text instead introduces a
    separate writing with prose such as ``Justice Kagan, ... dissenting.``;
    those introductions are often wrapped across two lines. Running page
    headers (for example, ``Kagan, J., dissenting``) are deliberately ignored
    because they can appear above the final text of the preceding opinion.
    """
    block = blocks[index]
    canonical = CANONICAL_MARKER_RE.fullmatch(block)
    if canonical:
        try:
            metadata = json.loads(canonical.group(1))
        except (json.JSONDecodeError, TypeError):
            return "other", 1
        part = metadata.get("part")
        return (part if part in {"opinion", "majority", "concurrence", "dissent", "other"} else "other"), 1

    extractor = EXTRACTOR_MARKER_RE.fullmatch(block)
    if extractor:
        return EXTRACTOR_PARTS[extractor.group(1).lower()], 1

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
        colon_heading = candidate.endswith(":")
        if not candidate.endswith((".", ":")):
            continue
        boundary_check = candidate
        for abbreviation in ABBREVIATIONS:
            boundary_check = re.sub(
                re.escape(abbreviation),
                abbreviation.replace(".", "<DOT>"),
                boundary_check,
                flags=re.I,
            )
        boundaries = len(re.findall(r"[.!?](?:\s+|$)", boundary_check))
        if boundaries + int(colon_heading) != 1:
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
            return ("dissent" if "dissent" in candidate.lower() else "concurrence"), consumed
        if re.fullmatch(
            rf"{JUSTICE_PREFIX}.*"
            r"(?:delivered\s+(?:the|an)\s+opinion\s+of\s+the\s+Court|"
            r"announced\s+the\s+judgment\s+of\s+the\s+Court)[^.]*\.",
            candidate,
            re.I,
        ):
            return "majority", consumed
        # Rhode Island (and similar) style: "Justice Goldberg, for the Court."
        if re.fullmatch(
            rf"{JUSTICE_PREFIX}[^.]*,\s*for\s+the\s+Court\.",
            candidate,
            re.I,
        ):
            return "majority", consumed
        # Some older U.S. Reports opinions omit the disposition from a separate
        # writing's heading entirely — Chevron Oil v. Huson introduces Douglas's
        # partial dissent with only "Mr. Justice Douglas." A bare justice name
        # immediately after the Court's terminal disposition still marks a new
        # writing, but its type is genuinely unknowable from the text, so label
        # it "separate" (unknown disposition) rather than guessing concurrence:
        # validation forbids majority sections from citing it either way, and
        # dissent claims are allowed to characterize it from its content.
        if (
            previous_text
            and re.fullmatch(r"it\s+is\s+so\s+ordered\.", previous_text, re.I)
            and re.fullmatch(
                rf"{JUSTICE_PREFIX}\s+[A-Z][A-Za-z'.-]*"
                r"(?:\s+[A-Z][A-Za-z'.-]*)*\.",
                candidate,
                re.I,
            )
        ):
            return "separate", consumed
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
    opinion_part = "opinion"
    sentences: list[tuple[str, str]] = []
    blocks = [block.strip() for block in prepared.splitlines() if block.strip()]
    index = 0
    while index < len(blocks):
        previous_text = sentences[-1][1] if sentences else None
        marker_part, consumed = detect_opinion_marker(blocks, index, previous_text)
        if marker_part:
            opinion_part = marker_part
            index += consumed
            continue
        block = blocks[index]
        for sentence in split_sentences(block):
            # Some plain-text opinions flatten separate-writing headings into
            # the surrounding paragraph instead of preserving line breaks.
            previous_text = sentences[-1][1] if sentences else None
            marker_part, _ = detect_opinion_marker([sentence], 0, previous_text)
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
    # Hash the derived passage representation, including boundaries. Two source
    # texts with identical words but different heading line breaks can classify
    # passages differently and therefore must not share a namespace.
    passage_material = "\n".join(
        f'{passage["ordinal"]}\0{passage["id"]}\0{passage["opinion_part"]}\0{passage["text"]}'
        for passage in passages
    )
    content_hash = hashlib.sha256(
        f"{PASSAGE_FORMAT_VERSION}\0{passage_material}".encode("utf-8")
    ).hexdigest()
    return content_hash, passages


@dataclass(frozen=True)
class BoundaryAssessment:
    ok: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    part_counts: dict[str, int]

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "part_counts": self.part_counts,
            "passage_format_version": PASSAGE_FORMAT_VERSION,
        }


def assess_opinion_boundaries(
    text: str,
    passages: list[dict],
    *,
    min_chars: int = 0,
    require_explicit: bool = False,
) -> BoundaryAssessment:
    """Check deterministic source-boundary invariants before paid generation."""
    errors: list[str] = []
    warnings: list[str] = []
    counts = dict(Counter(passage.get("opinion_part", "unknown") for passage in passages))

    if len(text.strip()) < min_chars:
        errors.append(f"opinion text is too short ({len(text.strip())} chars; minimum {min_chars})")
    if not passages:
        errors.append("opinion produced no passages")

    expected_parts: set[str] = set()
    for match in CANONICAL_MARKER_RE.finditer(text):
        try:
            part = json.loads(match.group(1)).get("part")
        except (json.JSONDecodeError, TypeError):
            errors.append("canonical sub-opinion marker contains invalid JSON")
            continue
        if part in {"majority", "concurrence", "dissent"}:
            expected_parts.add(part)
    expected_parts.update(
        EXTRACTOR_PARTS[match.group(1).lower()]
        for match in EXTRACTOR_MARKER_RE.finditer(text)
    )
    for part in sorted(expected_parts):
        if not counts.get(part):
            errors.append(f"source declares {part} material but parser found none")

    if not counts.get("majority") and not counts.get("opinion"):
        errors.append("source packet has no majority material")
    elif (
        counts.get("concurrence") or counts.get("dissent") or counts.get("separate")
    ) and not counts.get("majority"):
        errors.append("source has separate opinions but no explicit majority boundary")
    if set(counts) == {"opinion"}:
        # A source whose ingestion manifest declares exactly one sub-opinion
        # is a verified single writing: a single-opinion case has no part
        # boundaries to find, and demanding them refuses the most common
        # shape in the catalog (e.g. State v. Mosley, R.I. 2024).
        canonical_marker_count = len(CANONICAL_MARKER_RE.findall(text))
        if canonical_marker_count == 1:
            warnings.append(
                "single canonical sub-opinion; whole text is the opinion of the court"
            )
        else:
            warnings.append("source has no explicit opinion-part boundaries")
            if require_explicit:
                errors.append("source has no verifiable opinion-part boundaries")

    marker_text_found = any(
        CANONICAL_MARKER_RE.search(passage.get("text", ""))
        or EXTRACTOR_MARKER_RE.search(passage.get("text", ""))
        for passage in passages
    )
    if marker_text_found:
        errors.append("opinion-part marker leaked into passage text")

    return BoundaryAssessment(not errors, tuple(errors), tuple(warnings), counts)
