import copy
import json
import unittest

from brief_variants import (
    attach_sources,
    build_fidelity_prompt,
    parse_fidelity_response,
    build_variant_prompt,
    parse_variant_response,
    source_digest,
    validate_variants,
)


def detailed_brief(with_dissent=True):
    return {
        "facts": [{"text": "A city barred milk pasteurized far away.", "sources": ["op-f1"]}],
        "issue": [{"text": "Whether the ordinance discriminates.", "sources": ["op-i1"]}],
        "holding": [
            {"text": "The five-mile rule is invalid; reversed.", "sources": ["op-h1"]},
            {"text": "The twenty-five-mile rule is vacated and remanded.", "sources": ["op-h2"]},
        ],
        "rule": [{"text": "Discrimination fails if alternatives exist.", "sources": ["op-r1"]}],
        "majority_reasoning": [{"text": "Alternatives exist.", "sources": ["op-m1", "op-m2"]}],
        "dissent": [{"text": "The record shows no exclusion.", "sources": ["op-d1"]}] if with_dissent else [],
        "significance": "Foundational.",
    }


def valid_candidate(with_dissent=True):
    candidate = {
        "simplified": {
            "facts": [{"text": "Madison kept out far-away milk.", "from": ["facts[0]"]}],
            "issue": [{"text": "Can a city do that?", "from": ["issue[0]"]}],
            "holding": [{"text": "No. The 5-mile rule falls and the 25-mile part goes back.",
                         "from": ["holding[0]", "holding[1]"]}],
            "rule": [{"text": "Treating outsiders worse fails if another way works.", "from": ["rule[0]"]}],
            "majority_reasoning": [{"text": "Other ways existed.", "from": ["majority_reasoning[0]"]}],
            "dissent": [{"text": "Dean could have complied.", "from": ["dissent[0]"]}] if with_dissent else [],
        },
        "bullets": [
            {"label": "Holding", "text": "The 5-mile rule is unconstitutional.", "from": ["holding[0]"]},
            {"label": "Rule", "text": "Discrimination fails if alternatives exist.", "from": ["rule[0]"]},
            {"label": "Outcome", "text": "Reversed; 25-mile part vacated and remanded.",
             "from": ["holding[0]", "holding[1]"]},
        ],
    }
    if with_dissent:
        candidate["bullets"].append(
            {"label": "Dissent", "text": "Dean could have complied.", "from": ["dissent[0]"]}
        )
    return candidate


class BriefVariantTests(unittest.TestCase):
    def test_valid_candidate_passes(self):
        self.assertEqual(validate_variants(valid_candidate(), detailed_brief()), [])
        self.assertEqual(validate_variants(valid_candidate(False), detailed_brief(False)), [])

    def test_dropped_detailed_claim_is_rejected(self):
        candidate = valid_candidate()
        candidate["simplified"]["holding"][0]["from"] = ["holding[0]"]
        errors = validate_variants(candidate, detailed_brief())
        self.assertIn("simplified.holding drops detailed claims: holding[1]", errors)

    def test_supporting_sections_need_only_one_line(self):
        brief = detailed_brief()
        brief["facts"].append({"text": "Its milk was Grade A.", "sources": ["op-f2"]})
        self.assertEqual(validate_variants(valid_candidate(), brief), [])
        candidate = valid_candidate()
        candidate["simplified"]["facts"] = []
        self.assertIn("simplified.facts needs at least one line", validate_variants(candidate, brief))

    def test_fidelity_parser_takes_final_answer(self):
        text = ('{"problems": [{"line": "x", "problem": "borderline"}]}\n'
                'Wait, reconsidering.\n```json\n{"problems": []}\n```')
        self.assertEqual(parse_fidelity_response(text), [])
        self.assertEqual(
            parse_fidelity_response('{"problems": [{"line": "simplified.dissent[0]", "problem": "garbled"}]}'),
            ["simplified.dissent[0]: garbled"],
        )
        minor = '{"problems": [{"line": "x", "severity": "minor", "problem": "loose"}]}'
        self.assertEqual(parse_fidelity_response(minor), [])

    def test_fidelity_prompt_pairs_lines_with_cited_claims(self):
        prompt = build_fidelity_prompt("Dean Milk", detailed_brief(), valid_candidate())
        self.assertIn("bullets[2] (Outcome): Reversed; 25-mile part vacated and remanded.", prompt)
        self.assertIn("holding[1]: The twenty-five-mile rule is vacated and remanded.", prompt)

    def test_cross_section_reference_is_rejected(self):
        candidate = valid_candidate()
        candidate["simplified"]["majority_reasoning"][0]["from"] = ["dissent[0]"]
        errors = validate_variants(candidate, detailed_brief())
        self.assertTrue(any("from another section" in error for error in errors))

    def test_bullet_cannot_cite_dissent_for_majority_label(self):
        candidate = valid_candidate()
        candidate["bullets"][0]["from"] = ["dissent[0]"]
        errors = validate_variants(candidate, detailed_brief())
        self.assertIn("bullets[0] (Holding) cannot cite 'dissent[0]'", errors)

    def test_unknown_reference_is_rejected(self):
        candidate = valid_candidate()
        candidate["simplified"]["facts"][0]["from"] = ["facts[3]"]
        errors = validate_variants(candidate, detailed_brief())
        self.assertIn("simplified.facts[0] cites unknown claim 'facts[3]'", errors)

    def test_required_bullets_and_dissent_consistency(self):
        candidate = valid_candidate()
        candidate["bullets"] = [b for b in candidate["bullets"] if b["label"] not in ("Outcome", "Dissent")]
        errors = validate_variants(candidate, detailed_brief())
        self.assertIn("bullets need a Outcome bullet", errors)
        self.assertIn("bullets need a Dissent bullet", errors)

        no_dissent = valid_candidate(False)
        no_dissent["simplified"]["dissent"] = [{"text": "Invented.", "from": ["holding[0]"]}]
        errors = validate_variants(no_dissent, detailed_brief(False))
        self.assertIn("simplified.dissent must be empty; the detailed brief has none", errors)

    def test_length_limits(self):
        candidate = valid_candidate()
        candidate["simplified"]["facts"][0]["text"] = " ".join(["word"] * 401)
        candidate["bullets"][0]["text"] = " ".join(["word"] * 41)
        errors = validate_variants(candidate, detailed_brief())
        self.assertTrue(any(e.startswith("simplified is") and e.endswith("the limit is 400") for e in errors))
        self.assertIn("bullets[0] exceeds 40 words", errors)

    def test_attach_sources_derives_passages_from_references(self):
        published = attach_sources(valid_candidate(), detailed_brief())
        self.assertEqual(published["simplified"]["holding"][0]["sources"], ["op-h1", "op-h2"])
        self.assertEqual(published["simplified"]["majority_reasoning"][0]["sources"], ["op-m1", "op-m2"])
        self.assertEqual(published["bullets"][2]["sources"], ["op-h1", "op-h2"])

    def test_digest_tracks_brief_changes(self):
        brief = detailed_brief()
        changed = copy.deepcopy(brief)
        changed["holding"][1]["text"] = "Different."
        self.assertEqual(source_digest(brief), source_digest(copy.deepcopy(brief)))
        self.assertNotEqual(source_digest(brief), source_digest(changed))

    def test_prompt_numbers_claims_and_states_dissent_rule(self):
        prompt = build_variant_prompt("Dean Milk", detailed_brief())
        self.assertIn("[holding[1]] The twenty-five-mile rule is vacated and remanded.", prompt)
        self.assertIn('one "Dissent" bullet', prompt)
        self.assertIn('"dissent" must be []', build_variant_prompt("X", detailed_brief(False)))

    def test_parses_fenced_json(self):
        encoded = json.dumps(valid_candidate())
        self.assertEqual(parse_variant_response(f"```json\n{encoded}\n```"), valid_candidate())


if __name__ == "__main__":
    unittest.main()
