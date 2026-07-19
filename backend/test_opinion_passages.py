import hashlib

from opinion_passages import PASSAGE_FORMAT_VERSION, build_opinion_passages


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
    content_hash, _ = build_opinion_passages(text)
    assert content_hash == hashlib.sha256(
        f"{PASSAGE_FORMAT_VERSION}\0{text}".encode("utf-8")
    ).hexdigest()
    assert content_hash != hashlib.sha256(text.encode("utf-8")).hexdigest()


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
