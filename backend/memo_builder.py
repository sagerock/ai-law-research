"""
Memo Workbench - research-memo project prompts and case-chart generation.

Deliberately NOT a memo writer. The tool collects a scenario (research question,
posture, jurisdiction), the record (transcripts and other documents), and the
authorities (uploaded case printouts or cases snapshotted from Tortwell), and
its generation step produces a CASE CHART: a per-authority helps/hurts analysis
with verbatim supporting passages. The Discussion is the student's work; the
chat and chart exist to sharpen it, not to replace it.

Builder contract (shared with affidavit_builder, dispatched by tool_type):
    build_memo_system_prompt(case_info, form_data, documents, library_docs,
                             generated_document=None) -> str
    build_memo_generation_prompt(case_info, form_data, documents,
                                 library_docs) -> tuple[str, str]
"""

import json
import re
from typing import Optional

# Reporter star pagination ("*493", "[**212]") is typography, not text: a quote
# is verbatim whether or not it carries the page marker the reporter printed
# mid-sentence. Same pattern opinion_passages strips at ingestion.
STAR_PAGE_RE = re.compile(r"\[?\*{1,2}\d{1,4}\]?(?!\d)")

# Documents whose text belongs to the factual record rather than the law.
RECORD_DOC_TYPES = {"assignment", "transcript", "evidence", "other"}
AUTHORITY_DOC_TYPES = {"case", "statute"}

MAX_DOC_CHARS = 40000  # per document, keeps a 6-8 document project inside budget


def _scenario_block(case_info: dict, form_data: dict) -> str:
    lines = ["## The assignment"]
    client = case_info.get("client_name") or "the client"
    posture = case_info.get("posture") or "unstated"
    lines.append(f"Client: {client} (our side: {posture})")
    if case_info.get("matter"):
        lines.append(f"Matter: {case_info['matter']}")
    if case_info.get("jurisdiction"):
        lines.append(f"Jurisdiction: {case_info['jurisdiction']}")
    question = case_info.get("research_question")
    lines.append(f"Research question: {question}" if question
                 else "Research question: NOT YET STATED - ask for it before analyzing.")
    if case_info.get("scope_notes"):
        lines.append(f"Scope limits from the assigning attorney: {case_info['scope_notes']}")
    if form_data.get("universe") == "closed":
        lines.append(
            "This is a CLOSED-UNIVERSE assignment: only the authorities in this project "
            "may be used. Never suggest, cite, or rely on any authority outside it."
        )
    return "\n".join(lines)


def _document_blocks(documents: list[tuple]) -> tuple[str, str, int]:
    """Split project documents into record and authority sections.

    Returns (record_block, authority_block, authority_count).
    """
    record, authorities = [], []
    for doc_id, doc_type, title, text in documents:
        text = (text or "")[:MAX_DOC_CHARS]
        block = f"### [{doc_type} #{doc_id}] {title}\n{text}"
        if doc_type in AUTHORITY_DOC_TYPES:
            authorities.append(block)
        else:
            record.append(block)
    record_block = "## The record\n" + ("\n\n".join(record) if record
                   else "(no record documents uploaded yet)")
    authority_block = "## The authorities\n" + ("\n\n".join(authorities) if authorities
                      else "(no authorities added yet - upload case printouts or link Tortwell cases)")
    return record_block, authority_block, len(authorities)


def build_memo_system_prompt(
    case_info: dict,
    form_data: dict,
    documents: list[tuple],
    library_docs: list[tuple],
    generated_document: Optional[str] = None,
) -> str:
    """System prompt for memo-project chat.

    Args:
        case_info: {client_name, matter, jurisdiction, posture, research_question, scope_notes}
        form_data: {universe: "closed"|"open", notes}
        documents: [(id, doc_type, title, extracted_text)] - doc_type "case"/"statute"
                   are authorities; everything else is the record
        library_docs: [(title, content)] - unused by memo for now, kept for contract parity
        generated_document: previously generated case chart JSON, if any
    """
    record_block, authority_block, _ = _document_blocks(documents)
    parts = [
        "You are the research assistant on a law-student office-memo project. Your job "
        "is to help the student understand their record and authorities: which cases help "
        "the client, which hurt, what facts distinguish them, and what is still missing "
        "from the record. Ground every statement about the law in a specific provided "
        "document, quoting it where the words matter. If the materials do not answer a "
        "question, say so plainly.",
        "You do not write the memo. If asked to draft the memo or a full Discussion "
        "section, decline in one sentence - the analysis is the student's work and most "
        "programs treat a drafted memo as an integrity violation - and offer what you do "
        "instead: testing an argument, comparing facts to a case, finding the passage "
        "that supports or undercuts a claim, or generating the case chart.",
        _scenario_block(case_info, form_data),
        record_block,
        authority_block,
    ]
    if generated_document:
        parts.append("## Current case chart\n" + generated_document[:12000])
    return "\n\n".join(parts)


CASE_CHART_SHAPE = {
    "issue_frame": "one-sentence statement of the disputed question, from the record",
    "authorities": [
        {
            "title": "case or statute name as it appears in the document",
            "citation": "citation as it appears in the document, or null",
            "source_doc": "the [doc_type #id] tag of the document analyzed",
            "side": "helps | hurts | mixed",
            "why": "2-3 sentences tying the authority's holding to our facts",
            "key_passages": [
                {"quote": "verbatim from the document", "use": "what this passage does for or against us"}
            ],
            "fact_comparison": [
                {"their_fact": "...", "our_fact": "from the record", "cuts": "for us | against us | neutral"}
            ],
            "how_to_use_or_distinguish": "the argumentative move, one or two sentences",
        }
    ],
    "record_gaps": ["facts the record does not establish that the analysis needs"],
    "suggested_order": ["authority titles, strongest ground first, with one clause of reasoning each"],
}


def build_memo_generation_prompt(
    case_info: dict,
    form_data: dict,
    documents: list[tuple],
    library_docs: list[tuple],
) -> tuple[str, str]:
    """Build system + user prompts for generating the case chart. Returns (system, user)."""
    system_prompt = build_memo_system_prompt(
        case_info=case_info,
        form_data=form_data,
        documents=documents,
        library_docs=library_docs,
    )
    _, _, authority_count = _document_blocks(documents)
    user_prompt = (
        "Produce the case chart for this project. Return ONLY a JSON object with exactly "
        "this shape:\n\n"
        + json.dumps(CASE_CHART_SHAPE, indent=2)
        + "\n\nRules:\n"
        f"- Cover every one of the {authority_count} authorities in the project - one entry each, "
        "no authority skipped and none invented.\n"
        "- Every quote must appear verbatim in the named source document.\n"
        "- side is judged from OUR client's posture as stated in the assignment.\n"
        "- fact_comparison rows must draw our_fact from the record documents, never from "
        "the authority or from outside knowledge.\n"
        "- Where an authority cuts both ways, use side \"mixed\" and let key_passages show "
        "both edges.\n"
        "- record_gaps is for genuinely missing facts, not strategy advice.\n"
        "- Honor the assignment's scope limits absolutely: if the assigning attorney "
        "excluded an issue (for example probable cause), do not argue it, rest a "
        "side judgment on it, or build a move around it - mention it only to note "
        "it is outside scope.\n"
        "- No text before or after the JSON."
    )
    return system_prompt, user_prompt


def parse_memo_chart(text: str) -> Optional[dict]:
    """Parse a generated case chart, tolerating a fenced code block. None if unparseable."""
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = candidate.split("\n", 1)[-1]
        if candidate.rstrip().endswith("```"):
            candidate = candidate.rstrip()[:-3]
    try:
        chart = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    if not isinstance(chart, dict) or "authorities" not in chart:
        return None
    return chart


def verify_chart_quotes(chart: dict, documents: list[tuple]) -> list[str]:
    """Return a problem string per quote that does not appear in its source document.

    The same discipline as the brief pipeline: a passage that is not verbatim in the
    source is not evidence. Whitespace is normalized on both sides before comparison.
    """
    def squash(value: str) -> str:
        # PDFs carry typographic quotes and dashes; models echo ASCII ones.
        value = (value or "").translate(str.maketrans({
            "\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'",
            "\u2013": "-", "\u2014": "-", "\u00a0": " ",
        }))
        value = STAR_PAGE_RE.sub(" ", value)
        return " ".join(value.split())

    texts_by_tag = {
        f"[{doc_type} #{doc_id}]": squash(text)
        for doc_id, doc_type, title, text in documents
    }
    all_text = " ".join(texts_by_tag.values())
    problems = []
    for authority in chart.get("authorities", []):
        source = authority.get("source_doc") or ""
        haystack = texts_by_tag.get(source, all_text)
        for passage in authority.get("key_passages", []):
            quote = squash(passage.get("quote", ""))
            if quote and quote not in haystack:
                problems.append(
                    f"{authority.get('title', '?')}: quote not found in {source or 'any document'}: "
                    f"\"{quote[:80]}...\""
                )
    return problems


def postprocess_generated(generated_text: str, documents: list[tuple]) -> dict:
    """Metadata to persist alongside a generated chart: parse + quote audit.

    Called by the generic generate endpoint when the builder defines it. The
    problems list travels in document_metadata so the chart carries its own
    audit; an unparseable chart is recorded rather than discarded.
    """
    chart = parse_memo_chart(generated_text)
    if chart is None:
        return {"chart_parsed": False, "quote_problems": []}
    problems = verify_chart_quotes(chart, documents)
    return {"chart_parsed": True, "quote_problems": problems}
