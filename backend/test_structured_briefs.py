import json
import unittest

from structured_briefs import (
    build_source_packet,
    has_majority_source_material,
    parse_structured_response,
    repair_unknown_sources,
    structured_summary_to_text,
    validate_structured_summary,
)


def valid_summary():
    claim = " ".join(["supported"] * 70)
    return {
        "facts": [{"text": claim, "sources": ["op-majority"]}],
        "issue": [{"text": claim, "sources": ["op-majority"]}],
        "holding": [{"text": claim, "sources": ["op-majority"]}],
        "rule": [{"text": claim, "sources": ["op-majority"]}],
        "majority_reasoning": [{"text": claim, "sources": ["op-majority"]}],
        "dissent": [],
        "significance": " ".join(["editorial"] * 70),
    }


class StructuredBriefTests(unittest.TestCase):
    passages = [{"id": "op-majority", "opinion_part": "opinion", "text": "Supported."}]

    def test_parses_plain_and_fenced_json(self):
        value = valid_summary()
        encoded = json.dumps(value)
        self.assertEqual(parse_structured_response(encoded), value)
        self.assertEqual(parse_structured_response(f"```json\n{encoded}\n```"), value)

    def test_rejects_unknown_source(self):
        value = valid_summary()
        value["facts"][0]["sources"] = ["op-invented"]
        errors = validate_structured_summary(value, self.passages)
        self.assertTrue(any("unknown sources" in error for error in errors))

    def test_repairs_source_id_with_extra_trailing_character(self):
        passages = [{"id": "op-050f959b963a1792", "opinion_part": "opinion", "text": "S."}]
        value = valid_summary()
        for section in value:
            if isinstance(value[section], list):
                for claim in value[section]:
                    claim["sources"] = ["op-050f959b963a1792"]
        value["rule"][0]["sources"] = ["op-050f959b963a17925"]
        repair_unknown_sources(value, passages)
        self.assertEqual(value["rule"][0]["sources"], ["op-050f959b963a1792"])
        self.assertEqual(validate_structured_summary(value, passages), [])

    def test_repairs_truncated_source_id(self):
        passages = [{"id": "op-abcdef0123456789", "opinion_part": "opinion", "text": "S."}]
        value = valid_summary()
        value["facts"][0]["sources"] = ["op-abcdef012345678"]
        repair_unknown_sources(value, passages)
        self.assertEqual(value["facts"][0]["sources"], ["op-abcdef0123456789"])

    def test_leaves_ambiguous_and_unmatched_sources_alone(self):
        passages = [
            {"id": "op-aa11", "opinion_part": "opinion", "text": "S."},
            {"id": "op-aa12", "opinion_part": "opinion", "text": "S."},
        ]
        value = valid_summary()
        value["facts"][0]["sources"] = ["op-aa1"]      # prefix of two known IDs
        value["issue"][0]["sources"] = ["op-zz99"]     # matches nothing
        repair_unknown_sources(value, passages)
        self.assertEqual(value["facts"][0]["sources"], ["op-aa1"])
        self.assertEqual(value["issue"][0]["sources"], ["op-zz99"])

    def test_builds_stable_passages_and_packet(self):
        text = "First supported sentence.\nSecond supported sentence."
        first_hash, first_passages, selected = build_source_packet(text)
        second_hash, second_passages, _ = build_source_packet(text)
        self.assertEqual(first_hash, second_hash)
        self.assertEqual(first_passages, second_passages)
        self.assertEqual(selected, first_passages)
        self.assertTrue(all(passage["id"].startswith("op-") for passage in selected))

    def test_requires_majority_source_material(self):
        self.assertFalse(has_majority_source_material([
            {"opinion_part": "concurrence"},
            {"opinion_part": "dissent"},
        ]))
        self.assertTrue(has_majority_source_material([{"opinion_part": "opinion"}]))
        self.assertTrue(has_majority_source_material([{"opinion_part": "majority"}]))

    def test_majority_reasoning_rejects_concurrence_source(self):
        value = valid_summary()
        value["majority_reasoning"][0]["sources"] = ["op-concurrence"]
        passages = self.passages + [
            {"id": "op-concurrence", "opinion_part": "concurrence", "text": "Separate."}
        ]
        errors = validate_structured_summary(value, passages)
        self.assertIn("majority_reasoning[0] cites non-majority passage", errors)

    def test_text_rendering_preserves_legacy_fallback(self):
        text = structured_summary_to_text(valid_summary())
        self.assertTrue(text.startswith("**📋 Facts**"))
        self.assertIn("**📏 Rule**", text)
        self.assertIn("**🎯 Significance**", text)
        self.assertNotIn("**🗣️ Dissent**", text)


if __name__ == "__main__":
    unittest.main()
