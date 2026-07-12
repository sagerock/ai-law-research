import json
import unittest

from structured_briefs import (
    build_source_packet,
    parse_structured_response,
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

    def test_builds_stable_passages_and_packet(self):
        text = "First supported sentence.\nSecond supported sentence."
        first_hash, first_passages, selected = build_source_packet(text)
        second_hash, second_passages, _ = build_source_packet(text)
        self.assertEqual(first_hash, second_hash)
        self.assertEqual(first_passages, second_passages)
        self.assertEqual(selected, first_passages)
        self.assertTrue(all(passage["id"].startswith("op-") for passage in selected))

    def test_text_rendering_preserves_legacy_fallback(self):
        text = structured_summary_to_text(valid_summary())
        self.assertTrue(text.startswith("**📋 Facts**"))
        self.assertIn("**📏 Rule**", text)
        self.assertIn("**🎯 Significance**", text)
        self.assertNotIn("**🗣️ Dissent**", text)


if __name__ == "__main__":
    unittest.main()
