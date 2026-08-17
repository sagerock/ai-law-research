import json

from memo_builder import (
    build_memo_generation_prompt,
    build_memo_system_prompt,
    parse_memo_chart,
    verify_chart_quotes,
)


CASE_INFO = {
    "client_name": "Terrell Jones",
    "posture": "plaintiff",
    "jurisdiction": "Ohio",
    "research_question": "Was the detention reasonable under R.C. 2935.041?",
    "scope_notes": "Reasonableness only; no other statutes.",
}
DOCUMENTS = [
    (1, "transcript", "Jones Deposition", "I was held for thirty minutes after the search."),
    (2, "case", "Mullins v. Rinks, Inc.", "There could be no reasonable apprehension of force."),
    (3, "case", "Isaiah v. Great Atlantic", "The officer took Isaiah by the elbow."),
]


def test_system_prompt_separates_record_from_authorities():
    prompt = build_memo_system_prompt(CASE_INFO, {"universe": "closed"}, DOCUMENTS, [])
    assert prompt.index("## The record") < prompt.index("Jones Deposition")
    assert prompt.index("## The authorities") < prompt.index("Mullins v. Rinks")
    assert "[transcript #1]" in prompt and "[case #2]" in prompt


def test_closed_universe_is_stated():
    prompt = build_memo_system_prompt(CASE_INFO, {"universe": "closed"}, DOCUMENTS, [])
    assert "CLOSED-UNIVERSE" in prompt
    open_prompt = build_memo_system_prompt(CASE_INFO, {"universe": "open"}, DOCUMENTS, [])
    assert "CLOSED-UNIVERSE" not in open_prompt


def test_system_prompt_declines_to_write_the_memo():
    prompt = build_memo_system_prompt(CASE_INFO, {}, DOCUMENTS, [])
    assert "You do not write the memo" in prompt


def test_missing_research_question_is_flagged():
    prompt = build_memo_system_prompt({}, {}, DOCUMENTS, [])
    assert "NOT YET STATED" in prompt


def test_generation_prompt_counts_authorities():
    system, user = build_memo_generation_prompt(CASE_INFO, {}, DOCUMENTS, [])
    assert "every one of the 2 authorities" in user
    assert "issue_frame" in user and "fact_comparison" in user


def test_parse_chart_accepts_fenced_json():
    chart = {"issue_frame": "x", "authorities": []}
    fenced = "```json\n" + json.dumps(chart) + "\n```"
    assert parse_memo_chart(fenced) == chart
    assert parse_memo_chart(json.dumps(chart)) == chart
    assert parse_memo_chart("not json") is None
    assert parse_memo_chart('{"no_authorities": true}') is None


def test_quote_verification_catches_invented_quotes():
    chart = {
        "authorities": [
            {
                "title": "Mullins",
                "source_doc": "[case #2]",
                "key_passages": [
                    {"quote": "no reasonable apprehension of force", "use": "helps"},
                    {"quote": "this sentence appears nowhere", "use": "hurts"},
                ],
            }
        ]
    }
    problems = verify_chart_quotes(chart, DOCUMENTS)
    assert len(problems) == 1
    assert "appears nowhere" in problems[0]


def test_quote_verification_normalizes_whitespace():
    chart = {
        "authorities": [
            {
                "title": "Isaiah",
                "source_doc": "[case #3]",
                "key_passages": [
                    {"quote": "took  Isaiah\nby the elbow", "use": "helps"},
                ],
            }
        ]
    }
    assert verify_chart_quotes(chart, DOCUMENTS) == []
