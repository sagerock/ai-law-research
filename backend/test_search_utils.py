import unittest

from search_utils import case_title_terms


class CaseTitleTermsTests(unittest.TestCase):
    def test_abbreviated_caption_ignores_versus_and_punctuation(self):
        self.assertEqual(
            case_title_terms("United States v. Ince,"),
            ["united", "states", "ince"],
        )

    def test_terms_preserve_literal_party_name(self):
        self.assertEqual(case_title_terms("Ince"), ["ince"])

    def test_terms_are_deduplicated_and_bounded(self):
        self.assertEqual(case_title_terms("Alpha v Alpha Beta", limit=2), ["alpha", "beta"])


if __name__ == "__main__":
    unittest.main()
