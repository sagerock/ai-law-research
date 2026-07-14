from opinion_passages import build_opinion_passages


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
