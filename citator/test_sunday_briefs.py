from sunday_briefs import validate_candidate


def valid_candidate():
    text = " ".join(["supported"] * 70)
    return {
        "facts": [{"text": text, "sources": ["op-majority"]}],
        "issue": [{"text": text, "sources": ["op-majority"]}],
        "holding": [{"text": text, "sources": ["op-majority"]}],
        "rule": [{"text": text, "sources": ["op-majority"]}],
        "majority_reasoning": [{"text": text, "sources": ["op-majority"]}],
        "dissent": [],
        "significance": " ".join(["editorial"] * 70),
    }


PASSAGES = [
    {"passage_id": "op-majority", "opinion_part": "majority", "text": "Majority."},
    {"passage_id": "op-dissent", "opinion_part": "dissent", "text": "Dissent."},
]


def test_candidate_without_dissent_is_valid():
    assert validate_candidate(valid_candidate(), PASSAGES) == []


def test_majority_cannot_cite_dissent():
    candidate = valid_candidate()
    candidate["majority_reasoning"][0]["sources"] = ["op-dissent"]
    assert "majority_reasoning[0] cites dissent" in validate_candidate(candidate, PASSAGES)


def test_dissent_cannot_cite_majority():
    candidate = valid_candidate()
    candidate["dissent"] = [{"text": "separate view", "sources": ["op-majority"]}]
    assert "dissent[0] cites non-dissent passage" in validate_candidate(candidate, PASSAGES)


def test_unknown_source_is_rejected():
    candidate = valid_candidate()
    candidate["facts"][0]["sources"] = ["op-invented"]
    errors = validate_candidate(candidate, PASSAGES)
    assert any("unknown sources" in error for error in errors)
