"""
Affidavit Builder - prompt engineering and document generation for affidavits.

Handles:
- System prompt construction with affidavit-specific rules
- Generation prompt for drafting affidavits
- DOCX export with proper affidavit formatting (jurat/notary block)
"""

from typing import Optional
from docx_utils import (
    truncate_text, budget_documents, build_anti_hallucination_rules,
    build_case_info_section, build_documents_section, build_library_section,
    setup_legal_docx, add_educational_disclaimer, build_caption_table,
    add_centered_para, add_formatted_run, add_jurat_block,
    render_markdown_to_docx, save_docx_to_bytes, add_signature_block,
    ensure_docx_imports, Inches, Pt, WD_ALIGN_PARAGRAPH,
    MAX_DOCUMENT_TOKENS, CHARS_PER_TOKEN,
)


def build_affidavit_system_prompt(
    case_info: dict,
    form_data: dict,
    documents: list[tuple],
    library_docs: list[tuple],
    generated_document: Optional[str] = None,
) -> str:
    """
    Build the system prompt for affidavit chat interactions.

    Args:
        case_info: {plaintiff, defendant, court, jurisdiction, case_number, representing_side, judge}
        form_data: {affiant_info: {...}, attestable_facts: [...]}
        documents: [(id, doc_type, title, extracted_text)]
        library_docs: [(title, content)]
        generated_document: Previously generated affidavit text (if any)
    """
    parts = []

    # Role and core rules
    parts.append("""You are a law school educational assistant helping a student draft an Affidavit in support of a motion.

""" + build_anti_hallucination_rules("affidavit"))

    # Affidavit-specific rules
    parts.append("""

AFFIDAVIT-SPECIFIC RULES:
1. Every statement in the affidavit MUST be based on the affiant's PERSONAL KNOWLEDGE. Under Fed. R. Civ. P. 56(c)(4), "[a]n affidavit or declaration used to support or oppose a motion must be made on personal knowledge, set out facts that would be admissible in evidence, and show that the affiant or declarant is competent to testify on the matters stated."
2. Do NOT include legal conclusions, opinions, or argumentative statements. An affidavit contains FACTS, not legal arguments.
3. Do NOT include hearsay — statements about what someone else said — unless a hearsay exception clearly applies and you identify it.
4. Group related facts into coherent narrative paragraphs. A single paragraph may contain multiple related facts as long as they share a common topic or theme and are all based on personal knowledge.
5. Facts must be stated in a form that would be admissible in evidence at trial.
6. The affidavit must establish the affiant's competency: who they are, how they have personal knowledge of the facts stated.
7. Under Ohio Civ.R. 56(E), supporting affidavits "shall be made on personal knowledge, shall set forth such facts as would be admissible in evidence, and shall show affirmatively that the affiant is competent to testify to the matters stated in the affidavit."
8. If using 28 U.S.C. § 1746 unsworn declaration format, the affiant must include the statement: "I declare (or certify, verify, or state) under penalty of perjury that the foregoing is true and correct. Executed on [date]."
9. When referencing facts from depositions or discovery, the affidavit must restate them as the affiant's own personal knowledge — not merely repeat what a document says.""")

    # Case information
    parts.append(build_case_info_section(case_info))

    # Affiant information
    affiant_info = form_data.get("affiant_info", {})
    if affiant_info and any(affiant_info.values()):
        parts.append("\n\n--- AFFIANT INFORMATION ---")
        if affiant_info.get("name"):
            parts.append(f"Name: {affiant_info['name']}")
        if affiant_info.get("title"):
            parts.append(f"Title/Role: {affiant_info['title']}")
        if affiant_info.get("relationship_to_case"):
            parts.append(f"Relationship to Case: {affiant_info['relationship_to_case']}")
        if affiant_info.get("employer"):
            parts.append(f"Employer: {affiant_info['employer']}")
        if affiant_info.get("knowledge_basis"):
            parts.append(f"Basis of Knowledge: {affiant_info['knowledge_basis']}")

    # Facts the affiant can attest to
    attestable_facts = form_data.get("attestable_facts", [])
    if attestable_facts:
        parts.append("\n\n--- FACTS AFFIANT CAN ATTEST TO ---")
        parts.append("These are facts the student has identified that the affiant has personal knowledge of:")
        for fact in attestable_facts:
            num = fact.get("fact_number", "?")
            text = fact.get("text", "")
            basis = fact.get("knowledge_basis", "")
            basis_detail = fact.get("knowledge_basis_detail", "")
            source_info = ""
            if basis:
                source_info = f" [Basis: {basis}"
                if basis_detail:
                    source_info += f" — {basis_detail}"
                source_info += "]"
            source_ids = fact.get("source_doc_ids", [])
            if source_ids:
                refs = ", ".join(f"Doc #{sid}" for sid in source_ids)
                source_info += f" ({refs})"
            parts.append(f"{num}. {text}{source_info}")

    # Uploaded documents
    parts.append(build_documents_section(documents))

    # Library resources
    parts.append("\n\n--- APPROVED SOURCES ---")
    parts.append(build_library_section(library_docs))

    # Previously generated affidavit
    if generated_document:
        parts.append(f"\n\n--- PREVIOUSLY GENERATED AFFIDAVIT DRAFT ---\n{truncate_text(generated_document, 30000)}")

    return "\n".join(parts)


def build_affidavit_generation_prompt(
    case_info: dict,
    form_data: dict,
    documents: list[tuple],
    library_docs: list[tuple],
) -> tuple[str, str]:
    """
    Build system + user prompts for generating a full affidavit.
    Returns (system_prompt, user_prompt).
    """
    system_prompt = build_affidavit_system_prompt(
        case_info=case_info,
        form_data=form_data,
        documents=documents,
        library_docs=library_docs,
    )

    affiant_info = form_data.get("affiant_info", {})
    affiant_name = affiant_info.get("name", "[Affiant Name]")
    affiant_title = affiant_info.get("title", "")
    affiant_relationship = affiant_info.get("relationship_to_case", "")
    plaintiff = case_info.get("plaintiff", "[Plaintiff]")
    defendant = case_info.get("defendant", "[Defendant]")
    court = case_info.get("court", "[Court]")
    case_number = case_info.get("case_number", "[Case No.]")
    representing = case_info.get("representing_side", "plaintiff")

    # Determine motion purpose for the title
    if representing == "plaintiff":
        motion_purpose = f"In Support of Plaintiff's Motion for Summary Judgment"
    else:
        motion_purpose = f"In Support of Defendant's Motion for Summary Judgment"

    user_prompt = f"""Generate the body of an AFFIDAVIT OF {affiant_name.upper()} {motion_purpose} in {plaintiff} v. {defendant}, Case No. {case_number}, in {court}.

DO NOT generate the caption, affidavit title, venue block, jurat/notary block, or signature line — those are built separately. Generate ONLY the numbered paragraphs of the affidavit body.

Follow this model closely (from Writing for Litigation, Appendix P):

## Paragraph 1: Identity and Competency
State affiant's full name, that they are over the age of twenty-one, have never been convicted of a felony, are otherwise qualified to make this affidavit, and have personal knowledge of the facts stated. Example: "My name is [Name]. I am over the age of twenty-one, have never been convicted of a felony, and am otherwise qualified to make this affidavit. I have personal knowledge of the facts stated in this affidavit."

## Paragraph 2: Role and Basis of Knowledge
Establish the affiant's role and explain HOW they have personal knowledge. {f'The affiant is: {affiant_title}. ' if affiant_title else ''}{f'Relationship to case: {affiant_relationship}.' if affiant_relationship else ''}Describe their position, duties, or connection to the events that gives them firsthand knowledge.

## Remaining Paragraphs: Factual Statements
- Group related facts into coherent narrative paragraphs. A single paragraph may cover multiple related facts on the same topic, as long as all are based on personal knowledge.
- Begin each paragraph with its number (e.g., "3.", "4.", "5.").
- Use plain declarative sentences in first person ("I", "my", "me"). Do NOT begin with "Affiant states that."
- Be specific: use dates, times, locations, names, and amounts.
- Where the affiant is describing company procedures, policies, or business operations they oversee, explain them in detail.
- Use the facts from the FACTS AFFIANT CAN ATTEST TO section above.

## Final Paragraph
End with a simple denial or affirmation as appropriate, or omit if not needed.

IMPORTANT FORMATTING RULES:
- Number every paragraph sequentially (1., 2., 3., etc.)
- Use first person throughout
- State only FACTS, never legal conclusions or arguments
- Be specific with dates, times, locations, and names
- NEVER use em dashes (—) or en dashes (–). Use commas, semicolons, or parentheses instead.
- Do NOT fabricate any facts — use ONLY facts from the uploaded documents and the identified attestable facts
- This is for educational purposes only

Generate the affidavit body now."""

    return system_prompt, user_prompt


def generate_affidavit_docx(case_info: dict, form_data: dict, affidavit_text: str) -> bytes:
    """
    Generate a DOCX file from the affidavit text with proper formatting.
    Returns the DOCX as bytes.
    """
    ensure_docx_imports()

    # Strip em/en dashes
    affidavit_text = affidavit_text.replace("—", ", ").replace("–", "-")

    doc = setup_legal_docx()

    affiant_info = form_data.get("affiant_info", {})
    affiant_name = affiant_info.get("name", "[Affiant Name]")
    representing = case_info.get("representing_side", "plaintiff")
    plaintiff = case_info.get("plaintiff", "[Plaintiff]")
    defendant = case_info.get("defendant", "[Defendant]")
    movant = plaintiff if representing == "plaintiff" else defendant
    state = case_info.get("jurisdiction_state", "Ohio")
    county = case_info.get("county", "___________")

    # Educational disclaimer
    add_educational_disclaimer(doc, "top")

    # Caption — use § style (per Writing for Litigation textbook)
    _build_section_symbol_caption(doc, case_info)

    # Affidavit title with purpose
    if representing == "plaintiff":
        purpose = f"In Support of Plaintiff's Motion for Summary Judgment"
    else:
        purpose = f"In Support of Defendant's Motion for Summary Judgment"
    add_centered_para(doc, f"Affidavit of {affiant_name} {purpose}", bold=True, size=12)
    doc.add_paragraph()

    # Venue block (State / County with § symbols) before the body
    _add_venue_block(doc, state, county)
    doc.add_paragraph()

    # Parse and render the AI-generated affidavit body
    content_lines = affidavit_text.split("\n")

    # Skip lines that look like AI-generated title/caption until we hit substance
    start_idx = 0
    for i, line in enumerate(content_lines):
        stripped = line.strip().lower()
        if any(kw in stripped for kw in ["1.", "i,", "my name", "i am", "## identity", "## factual", "## paragraph"]):
            start_idx = i
            break
        if line.strip().startswith("#") and not any(kw in stripped for kw in ["caption", "affidavit of", "court"]):
            start_idx = i
            break
    else:
        start_idx = 0

    _render_affidavit_content(doc, content_lines[start_idx:])

    # Signature line for affiant (right-aligned, per textbook)
    doc.add_paragraph()
    doc.add_paragraph()

    sig = doc.add_paragraph()
    sig.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    sig.paragraph_format.space_after = Pt(0)
    r = sig.add_run("_________________________________")
    r.font.name = "Times New Roman"
    r.font.size = Pt(12)

    name_p = doc.add_paragraph()
    name_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    name_p.paragraph_format.space_after = Pt(0)
    r = name_p.add_run(affiant_name)
    r.font.name = "Times New Roman"
    r.font.size = Pt(12)

    if affiant_info.get("title"):
        title_p = doc.add_paragraph()
        title_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        title_p.paragraph_format.space_after = Pt(0)
        r = title_p.add_run(affiant_info["title"])
        r.font.name = "Times New Roman"
        r.font.size = Pt(12)

    # Jurat / Notary block — simple style per Writing for Litigation textbook
    doc.add_paragraph()
    _add_simple_jurat(doc, state)

    # Bottom disclaimer
    add_educational_disclaimer(doc, "bottom")

    return save_docx_to_bytes(doc)


def _build_section_symbol_caption(doc, case_info: dict):
    """Build caption using § symbols (per Writing for Litigation textbook style)."""
    ensure_docx_imports()
    from docx_utils import set_cell_text, WD_TABLE_ALIGNMENT

    court = case_info.get("court", "[United States District Court]")
    plaintiff = case_info.get("plaintiff", "[Plaintiff]")
    defendant = case_info.get("defendant", "[Defendant]")
    case_number = case_info.get("case_number", "[Case No.]")

    # Court name
    add_centered_para(doc, court, bold=False, size=12)
    doc.add_paragraph()

    # Caption table with § symbols
    caption_table = doc.add_table(rows=5, cols=3)
    caption_table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Remove all borders
    from docx_utils import qn
    for row in caption_table.rows:
        for cell in row.cells:
            tc = cell._tc
            tcPr = tc.get_or_add_tcPr()
            tcBorders = tcPr.makeelement(qn('w:tcBorders'), {})
            for border_name in ['top', 'left', 'bottom', 'right']:
                border = tcBorders.makeelement(qn(f'w:{border_name}'), {
                    qn('w:val'): 'none', qn('w:sz'): '0', qn('w:space'): '0', qn('w:color'): 'auto'
                })
                tcBorders.append(border)
            tcPr.append(tcBorders)

    # Set column widths
    from docx_utils import Inches
    for row in caption_table.rows:
        row.cells[0].width = Inches(3.0)
        row.cells[1].width = Inches(0.5)
        row.cells[2].width = Inches(3.0)

    # Fill in caption with § style
    set_cell_text(caption_table.cell(0, 0), f"{plaintiff},", bold=True)
    set_cell_text(caption_table.cell(0, 1), "\u00A7", bold=False)
    set_cell_text(caption_table.cell(0, 2), f"Civil Action No. {case_number}", bold=False)

    set_cell_text(caption_table.cell(1, 0), "          Plaintiff", bold=False)
    set_cell_text(caption_table.cell(1, 1), "\u00A7", bold=False)
    set_cell_text(caption_table.cell(1, 2), "", bold=False)

    set_cell_text(caption_table.cell(2, 0), "v.", bold=False)
    set_cell_text(caption_table.cell(2, 1), "\u00A7", bold=False)
    set_cell_text(caption_table.cell(2, 2), "", bold=False)

    set_cell_text(caption_table.cell(3, 0), f"{defendant},", bold=True)
    set_cell_text(caption_table.cell(3, 1), "\u00A7", bold=False)
    set_cell_text(caption_table.cell(3, 2), "", bold=False)

    set_cell_text(caption_table.cell(4, 0), "          Defendant", bold=False)
    set_cell_text(caption_table.cell(4, 1), "\u00A7", bold=False)
    set_cell_text(caption_table.cell(4, 2), "", bold=False)

    doc.add_paragraph()


def _add_venue_block(doc, state: str = "Ohio", county: str = "___________"):
    """Add State/County venue block with § symbols before the affidavit body."""
    ensure_docx_imports()

    p1 = doc.add_paragraph()
    p1.paragraph_format.space_after = Pt(0)
    p1.paragraph_format.line_spacing = 1.15
    r = p1.add_run(f"State of {state} \u00A7")
    r.font.name = "Times New Roman"
    r.font.size = Pt(12)

    p2 = doc.add_paragraph()
    p2.paragraph_format.space_after = Pt(0)
    p2.paragraph_format.space_before = Pt(0)
    p2.paragraph_format.line_spacing = 1.15
    r = p2.add_run(f"                        \u00A7")
    r.font.name = "Times New Roman"
    r.font.size = Pt(12)

    p3 = doc.add_paragraph()
    p3.paragraph_format.space_after = Pt(0)
    p3.paragraph_format.space_before = Pt(0)
    p3.paragraph_format.line_spacing = 1.15
    r = p3.add_run(f"County of {county} \u00A7")
    r.font.name = "Times New Roman"
    r.font.size = Pt(12)


def _add_simple_jurat(doc, state: str = "Ohio"):
    """Add simple jurat/notary block matching Writing for Litigation textbook style."""
    ensure_docx_imports()

    # "Signed and sworn before me..." line
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Inches(0.5)
    r = p.add_run(
        f"Signed and sworn before me, a notary public for the "
        f"state of {state}, on __________________, ________."
    )
    r.font.name = "Times New Roman"
    r.font.size = Pt(12)

    doc.add_paragraph()

    # Notary signature line (right-aligned)
    sig = doc.add_paragraph()
    sig.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    sig.paragraph_format.space_after = Pt(0)
    r = sig.add_run("_________________________________")
    r.font.name = "Times New Roman"
    r.font.size = Pt(12)

    # Printed name
    name_p = doc.add_paragraph()
    name_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    name_p.paragraph_format.space_after = Pt(0)
    r = name_p.add_run("Printed Name: ___________________")
    r.font.name = "Times New Roman"
    r.font.size = Pt(12)

    # Commission expiration
    exp_p = doc.add_paragraph()
    exp_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = exp_p.add_run("My commission expires: ___________")
    r.font.name = "Times New Roman"
    r.font.size = Pt(12)


def _render_affidavit_content(doc, lines: list[str]):
    """
    Render affidavit body into DOCX. Similar to render_markdown_to_docx but
    optimized for affidavit style (numbered paragraphs, no centered headings).
    """
    ensure_docx_imports()
    import re

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Section headings in affidavit are informational (not rendered centered)
        if stripped.startswith("## "):
            # Skip section headings like "## Identity and Competency" — they're structural
            # hints for the AI, not part of the final document
            continue

        if stripped.startswith("### ") or stripped.startswith("# "):
            continue

        # Bold-only line — skip (structural hint)
        if stripped.startswith("**") and stripped.endswith("**") and stripped.count("**") == 2:
            continue

        # Numbered paragraphs (the core of the affidavit)
        num_match = re.match(r'^(\d+)\.\s+(.+)', stripped)
        if num_match:
            p = doc.add_paragraph()
            p.paragraph_format.first_line_indent = Inches(0.5)
            add_formatted_run(p, f"{num_match.group(1)}. {num_match.group(2)}")
            continue

        # Regular text paragraph
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Inches(0.5)
        add_formatted_run(p, stripped)
