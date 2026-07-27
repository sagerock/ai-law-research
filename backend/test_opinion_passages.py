import hashlib

from opinion_passages import (
    PASSAGE_FORMAT_VERSION,
    assess_opinion_boundaries,
    build_opinion_passages,
    looks_hard_wrapped,
    unwrap_typeset_lines,
)


def test_passage_ids_survive_insertions_before_unchanged_text():
    original = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence. Sixth sentence."
    changed = "New sentence. " + original
    _, original_passages = build_opinion_passages(original)
    _, changed_passages = build_opinion_passages(changed)
    assert [p["id"] for p in original_passages] == [p["id"] for p in changed_passages[1:]]


def test_content_hash_changes_when_opinion_changes():
    first_hash, _ = build_opinion_passages("One sentence. Two sentence. Three sentence.")
    second_hash, _ = build_opinion_passages("One sentence. Different sentence. Three sentence.")
    assert first_hash != second_hash


def test_content_hash_is_namespaced_by_passage_format():
    text = "One sentence."
    content_hash, passages = build_opinion_passages(text)
    material = "\n".join(
        f'{p["ordinal"]}\0{p["id"]}\0{p["opinion_part"]}\0{p["text"]}' for p in passages
    )
    assert content_hash == hashlib.sha256(
        f"{PASSAGE_FORMAT_VERSION}\0{material}".encode("utf-8")
    ).hexdigest()
    assert content_hash != hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_content_hash_changes_when_boundaries_change():
    plain_hash, _ = build_opinion_passages("Majority sentence. Dissent sentence.")
    marked_hash, _ = build_opinion_passages(
        "=== Lead Opinion ===\nMajority sentence.\n=== Dissent ===\nDissent sentence."
    )
    assert plain_hash != marked_hash


def test_labels_majority_and_dissent():
    _, passages = build_opinion_passages(
        "[by Cardozo]\nOne. Two. Three.\n[Dissent by Andrews]\nFour. Five. Six."
    )
    assert [p["opinion_part"] for p in passages] == [
        "majority", "majority", "majority", "dissent", "dissent", "dissent"
    ]


def test_labels_concurrence_generically():
    _, passages = build_opinion_passages(
        "[by Smith]\nMajority sentence.\n[Concurrence by Jones]\nSeparate sentence."
    )
    assert [p["opinion_part"] for p in passages] == ["majority", "concurrence"]


def test_labels_wrapped_supreme_court_opinion_introductions():
    _, passages = build_opinion_passages(
        """Syllabus sentence.
Justice Thomas delivered the opinion of the Court.
Majority sentence.
Opinion of Barrett, J.
Majority conclusion.
Justice Barrett, concurring in part and concurring in
the judgment.
Concurrence sentence.
Kagan, J., dissenting
Concurrence conclusion.
Justice Kagan, with whom Justice Sotomayor and
Justice Jackson join, dissenting.
First dissent sentence.
Justice Jackson, dissenting.
Second dissent sentence."""
    )
    assert [(p["opinion_part"], p["text"]) for p in passages] == [
        ("opinion", "Syllabus sentence."),
        ("majority", "Majority sentence."),
        ("majority", "Opinion of Barrett, J."),
        ("majority", "Majority conclusion."),
        ("concurrence", "Concurrence sentence."),
        ("concurrence", "Kagan, J., dissenting"),
        ("concurrence", "Concurrence conclusion."),
        ("dissent", "First dissent sentence."),
        ("dissent", "Second dissent sentence."),
    ]


def test_dissent_reference_inside_opinion_does_not_change_part():
    _, passages = build_opinion_passages(
        "[by Smith]\nThe court cited an earlier view.\n(White, J., dissenting).\nThe majority continued."
    )
    assert {p["opinion_part"] for p in passages} == {"majority"}


def test_recognizes_title_only_chief_justice_marker():
    _, passages = build_opinion_passages(
        "The Chief Justice, dissenting.\nSeparate sentence."
    )
    assert [(p["opinion_part"], p["text"]) for p in passages] == [
        ("dissent", "Separate sentence.")
    ]


def test_labels_old_us_reports_headings_in_html():
    _, passages = build_opinion_passages(
        """<p>MR. JUSTICE BRENNAN delivered the opinion of the Court.</p>
<p>Majority sentence.</p>
<p>MR. JUSTICE STEWART, concurring.</p>
<p>Concurrence sentence.</p>
<p>MR. JUSTICE WHITE, dissenting.</p>
<p>Dissent sentence.</p>
<h2>NOTES</h2>
<p>Neutral footnote.</p>"""
    )
    assert [(p["opinion_part"], p["text"]) for p in passages] == [
        ("majority", "Majority sentence."),
        ("concurrence", "Concurrence sentence."),
        ("dissent", "Dissent sentence."),
        ("opinion", "Neutral footnote."),
    ]


def test_labels_circuit_court_headings():
    # Heading shapes from Stephens v. Miller, 13 F.3d 998 (7th Cir. 1994) (en banc)
    _, passages = build_opinion_passages(
        """MANION, Circuit Judge.
Majority sentence.
FLAUM, Circuit Judge, concurring.
Concurrence sentence.
ILANA DIAMOND ROVNER, Circuit Judge, concurring.
Second concurrence sentence.
CUMMINGS, Circuit Judge, joined by CUDAHY and MANION, Circuit Judges, dissenting.
First dissent sentence.
RIPPLE, Circuit Judge, dissenting.
Second dissent sentence."""
    )
    assert [(p["opinion_part"], p["text"]) for p in passages] == [
        ("majority", "Majority sentence."),
        ("concurrence", "Concurrence sentence."),
        ("concurrence", "Second concurrence sentence."),
        ("dissent", "First dissent sentence."),
        ("dissent", "Second dissent sentence."),
    ]


def test_labels_inline_circuit_headings_with_paragraph_numbers():
    # Numbered-paragraph reporter text flattens headings into the text flow.
    _, passages = build_opinion_passages(
        "MANION, Circuit Judge. Majority sentence. "
        "100 COFFEY, Circuit Judge, dissenting. Dissent sentence."
    )
    assert [(p["opinion_part"], p["text"]) for p in passages] == [
        ("majority", "Majority sentence."),
        ("dissent", "Dissent sentence."),
    ]


def test_labels_partial_dissent_as_dissent():
    _, passages = build_opinion_passages(
        "POSNER, Chief Judge.\nMajority sentence.\n"
        "EASTERBROOK, Circuit Judge, concurring in part and dissenting in part.\n"
        "Partial dissent sentence."
    )
    assert [(p["opinion_part"], p["text"]) for p in passages] == [
        ("majority", "Majority sentence."),
        ("dissent", "Partial dissent sentence."),
    ]


def test_labels_supreme_court_partial_dissent_conservatively_as_dissent():
    _, passages = build_opinion_passages(
        "Justice Smith delivered the opinion of the Court. Majority sentence. "
        "Justice Jones, concurring in part and dissenting in part. Mixed sentence."
    )
    assert [(p["opinion_part"], p["text"]) for p in passages] == [
        ("majority", "Majority sentence."),
        ("dissent", "Mixed sentence."),
    ]


def test_circuit_citation_strings_are_not_headings():
    # Mixed-case citation references and page cites must not flip the part.
    _, passages = build_opinion_passages(
        "MANION, Circuit Judge.\n"
        "See Cudahy, J., dissenting, at 1012-14. "
        "The court disagreed (Scalia, J., dissenting). "
        "Majority conclusion."
    )
    assert {p["opinion_part"] for p in passages} == {"majority"}


def test_vote_lines_are_not_headings():
    # End-of-opinion vote lines use finite verbs, not participles.
    _, passages = build_opinion_passages(
        "[by Cardozo]\nMajority sentence.\n"
        "POUND, LEHMAN and KELLOGG, JJ., concur with CARDOZO, Ch. J.\n"
        "ANDREWS, J., dissents in opinion in which CRANE and O'BRIEN, JJ., concur."
    )
    assert all(p["opinion_part"] == "majority" for p in passages)


def test_labels_state_court_parenthetical_dissent_heading():
    _, passages = build_opinion_passages(
        "[by Cardozo]\nMajority sentence.\nANDREWS, J. (dissenting).\nDissent sentence."
    )
    assert [(p["opinion_part"], p["text"]) for p in passages] == [
        ("majority", "Majority sentence."),
        ("dissent", "Dissent sentence."),
    ]


def test_labels_inline_old_us_reports_dissent_heading():
    _, passages = build_opinion_passages(
        "Justice Brown delivered the opinion of the Court. "
        "Majority conclusion. "
        "Mr. Justice Shiras dissenting, with whom concurred Mr. Justice Gray and Mr. Justice White. "
        "Dissent sentence."
    )
    assert [(p["opinion_part"], p["text"]) for p in passages] == [
        ("majority", "Majority conclusion."),
        ("dissent", "Dissent sentence."),
    ]


def test_labels_unqualified_separate_opinion_after_disposition_as_separate():
    # Chevron Oil Co. v. Huson, 404 U.S. 97, introduces Douglas's partial
    # dissent with only "MR. JUSTICE DOUGLAS." — no disposition word at all.
    # The type is unknowable from the text, so it must be labeled "separate"
    # (not guessed as concurrence): dissent claims may then characterize it
    # from content, while majority sections still cannot cite it.
    _, passages = build_opinion_passages(
        "Mr. Justice Stewart delivered the opinion of the Court. "
        "Majority conclusion. It is so ordered. Mr. Justice Douglas. "
        "Rodrigue does not require reversal. I would affirm the judgment."
    )
    assert [(p["opinion_part"], p["text"]) for p in passages] == [
        ("majority", "Majority conclusion."),
        ("majority", "It is so ordered."),
        ("separate", "Rodrigue does not require reversal."),
        ("separate", "I would affirm the judgment."),
    ]


def test_labels_for_the_court_heading_as_majority():
    # Rhode Island style: "Justice Goldberg, for the Court." (State v. Mosley)
    _, passages = build_opinion_passages(
        "Caption sentence.\n"
        "Justice Goldberg, for the Court. On the afternoon of August 13, 2014, "
        "the defendant was arrested."
    )
    assert [(p["opinion_part"], p["text"]) for p in passages] == [
        ("opinion", "Caption sentence."),
        ("majority", "On the afternoon of August 13, 2014, the defendant was arrested."),
    ]


def test_single_canonical_sub_opinion_passes_strict_preflight():
    # One combined sub-opinion, no separate writings: a verified single
    # writing must not be refused for lacking boundaries it never had.
    text = (
        '[[COURTLISTENER_SUBOPINION {"id":"1","type":"010combined","part":"opinion","author":null}]]\n'
        + "Body sentence. " * 300
    )
    _, passages = build_opinion_passages(text)
    assessment = assess_opinion_boundaries(text, passages, require_explicit=True)
    assert assessment.ok
    assert any("single canonical sub-opinion" in w for w in assessment.warnings)


def test_unmarked_all_opinion_source_still_fails_strict_preflight():
    text = "Unmarked opinion sentence. " * 120
    _, passages = build_opinion_passages(text)
    assessment = assess_opinion_boundaries(text, passages, require_explicit=True)
    assert not assessment.ok
    assert "source has no verifiable opinion-part boundaries" in assessment.errors


def test_labels_canonical_courtlistener_markers_and_assesses_expected_parts():
    text = (
        '[[COURTLISTENER_SUBOPINION {"id":"1","type":"020lead","part":"majority","author":"A"}]]\n'
        "Majority sentence.\n"
        '[[COURTLISTENER_SUBOPINION {"id":"2","type":"040dissent","part":"dissent","author":"B"}]]\n'
        "Dissent sentence."
    )
    _, passages = build_opinion_passages(text)
    assert [(p["opinion_part"], p["text"]) for p in passages] == [
        ("majority", "Majority sentence."),
        ("dissent", "Dissent sentence."),
    ]
    assessment = assess_opinion_boundaries(text, passages)
    assert assessment.ok
    assert assessment.part_counts == {"majority": 1, "dissent": 1}


def test_labels_extractor_markers_and_rejects_separate_only_source():
    text = "=== Dissent ===\nAndrews, J.\n(dissenting). Separate sentence."
    _, passages = build_opinion_passages(text)
    assert all(p["opinion_part"] == "dissent" for p in passages)
    assessment = assess_opinion_boundaries(text, passages)
    assert not assessment.ok
    assert "source packet has no majority material" in assessment.errors


def test_strict_preflight_rejects_fully_unclassified_source():
    text = "Unmarked opinion sentence. " * 120
    _, passages = build_opinion_passages(text)
    assessment = assess_opinion_boundaries(
        text, passages, min_chars=2500, require_explicit=True
    )
    assert not assessment.ok
    assert "source has no verifiable opinion-part boundaries" in assessment.errors


def test_preflight_rejects_neutral_preamble_before_dissent_only_source():
    text = "Case caption.\n=== Dissent ===\nSeparate reasoning. " * 120
    _, passages = build_opinion_passages(text)
    assessment = assess_opinion_boundaries(text, passages, require_explicit=True)
    assert not assessment.ok
    assert "source has separate opinions but no explicit majority boundary" in assessment.errors


def test_labels_colon_terminated_circuit_dissent_heading():
    _, passages = build_opinion_passages(
        "The motion is DENIED. GARWOOD, Circuit Judge, dissenting in part: "
        "Separate reasoning."
    )
    assert [(passage["opinion_part"], passage["text"]) for passage in passages] == [
        ("opinion", "The motion is DENIED."),
        ("dissent", "Separate reasoning."),
    ]


def typeset_page(body_lines, page=780, name="SMITH v. ARIZONA", label="Opinion of the Court"):
    """Render body lines the way a reporter's preliminary print stores them."""
    return "\f{:<4}{:>30}\n\n{:>50}\n\n".format(page, name, label) + "\n".join(body_lines)


def test_leaves_paragraph_per_line_sources_untouched():
    # The dominant catalog shape: one paragraph (or the whole opinion) per line.
    # Rejoining those would merge distinct paragraphs, so detection must decline
    # and segmentation must come out byte-identical.
    paragraphs = [
        "Justice Kagan delivered the opinion of the Court.",
        "The Confrontation Clause bars testimonial hearsay from an absent witness. " * 8,
        "We therefore vacate the judgment below and remand for further proceedings. " * 8,
    ] * 20
    text = "\n".join(paragraphs)
    assert not looks_hard_wrapped(text.split("\n"))
    assert unwrap_typeset_lines(text) == text


def test_detects_wrapping_only_in_typeset_sources():
    typeset = ["The Sixth Amendment's Confrontation Clause guarantees a crimi-"] * 60
    assert looks_hard_wrapped(typeset)
    # Too few lines to judge, whatever their shape.
    assert not looks_hard_wrapped(typeset[:10])
    # Wide lines are authored paragraphs, not typesetter output.
    assert not looks_hard_wrapped([line * 4 for line in typeset])


def test_rejoins_typesetter_wrapped_sentences_and_hyphenation():
    body = [
        "   Justice Kagan delivered the opinion of the Court.",
        "   The Sixth Amendment's Confrontation Clause guarantees a crimi-",
        "nal defendant the right to confront the witnesses against him, and",
        "that prohibition applies in full to forensic evidence offered by an",
        "absent analyst whose findings the State puts before the jury.",
    ]
    _, passages = build_opinion_passages(typeset_page(body * 12))
    texts = [p["text"] for p in passages]
    assert any("criminal defendant the right to confront" in text for text in texts)
    assert not any(text.endswith("-") for text in texts)
    assert all(p["opinion_part"] == "majority" for p in passages)


def test_drops_running_heads_watermarks_and_page_numbers():
    body = [
        "   The State does not escape the Confrontation Clause merely be-",
        "cause the records came in to explain an expert's basis.",
        "Page Proof Pending Publication",
        "   We vacate the judgment of the Arizona Court of Appeals and re-",
        "mand for further proceedings not inconsistent with this opinion.",
        "                                      -3-",
    ]
    _, passages = build_opinion_passages(typeset_page(body * 12, label="Syllabus"))
    texts = " ".join(p["text"] for p in passages)
    assert "Page Proof" not in texts
    assert "SMITH v. ARIZONA" not in texts
    assert "Syllabus" not in texts
    assert "-3-" not in texts
    assert "because the records came in" in texts


def test_page_break_carrying_body_text_keeps_the_text():
    # A page break lands mid-sentence as often as between paragraphs; the text
    # riding on it is content, not a running head, and must not be dropped.
    body = ["   Waters complied with the demand, and although he was not an"] * 40
    text = typeset_page(body) + "\n\feyewitness, he recalled hearing the victim exclaim."
    _, passages = build_opinion_passages(text)
    joined = " ".join(p["text"] for p in passages)
    assert "eyewitness, he recalled hearing the victim exclaim." in joined


def test_unwrapping_preserves_canonical_sub_opinion_markers():
    # Markers declare the opinion boundaries; joined into a paragraph they stop
    # matching and the source loses the parts it explicitly declares.
    marker = '[[COURTLISTENER_SUBOPINION {"id":"1","part":"majority"}]]'
    dissent = '[[COURTLISTENER_SUBOPINION {"id":"2","part":"dissent"}]]'
    body = ["   The judgment of the court of appeals is hereby affirmed in"] * 40
    text = marker + "\n" + typeset_page(body) + "\n" + dissent + "\n" + "\n".join(
        ["   I would reverse because the statements were plainly testi-", "monial."]
    )
    _, passages = build_opinion_passages(text)
    parts = {p["opinion_part"] for p in passages}
    assert parts == {"majority", "dissent"}
    assert any("testimonial." in p["text"] for p in passages)


def test_centered_section_label_does_not_swallow_the_writing_heading():
    # State v. Mosley shape: a centered "OPINION" label sits directly above the
    # heading. Joined into it ("OPINION Justice Goldberg, for the Court.") the
    # heading stops matching and the opinion loses its majority boundary.
    body = ["   the defendant was convicted on all four counts after a retrial"] * 40
    text = (
        "                                  OPINION\n\n"
        "      Justice Goldberg, for the Court. On the afternoon of August 13,\n"
        "2014, a gunman entered the barbershop and opened fire.\n\n"
        + "\n\n".join(body)
    )
    _, passages = build_opinion_passages(text)
    assert any(p["opinion_part"] == "majority" for p in passages)
    assert not any("for the Court" in p["text"] for p in passages)


def test_double_spaced_slip_opinion_rejoins_across_blank_lines():
    # Slip opinions are double-spaced, so blank lines are line spacing rather
    # than paragraph breaks and must not end a block.
    body = [
        "      Derek Winslow and the victim had an acrimonious relationship,",
        "leading Winslow to declare that he wanted the victim harmed, which in",
        "street parlance evidently meant that he wanted him killed outright.",
    ]
    text = "\n\n".join(body * 14)
    _, passages = build_opinion_passages(text)
    assert any(
        "acrimonious relationship, leading Winslow to declare" in p["text"]
        for p in passages
    )
