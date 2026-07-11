import hashlib
import re


ABBREVIATIONS = ("Mrs.", "Mr.", "Ms.", "Dr.", "Ch. J.", "J.", "Co.", "R.R.", "U.S.")


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
    normalized = normalize_opinion_text(text)
    content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    labeled = text.replace("[by Cardozo]", "\nMAJORITY\n").replace(
        "[Dissent by Andrews]", "\nDISSENT\n"
    )
    opinion_part = "opinion"
    sentences: list[tuple[str, str]] = []
    for block in labeled.splitlines():
        block = block.strip()
        if not block:
            continue
        if block in {"MAJORITY", "DISSENT"}:
            opinion_part = block.lower()
            continue
        sentences.extend((opinion_part, sentence) for sentence in split_sentences(block))

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
