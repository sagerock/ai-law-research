import unittest
from unittest.mock import AsyncMock

from opinion_loader import is_courtlistener_id, load_opinion_text


class OpinionLoaderTests(unittest.IsolatedAsyncioTestCase):
    async def test_postgres_precedes_other_sources(self):
        s3 = AsyncMock(return_value="s3")
        courtlistener = AsyncMock(return_value="courtlistener")
        result = await load_opinion_text("123", "postgres", s3, courtlistener)
        self.assertEqual((result.text, result.source), ("postgres", "postgres"))
        s3.assert_not_awaited()
        courtlistener.assert_not_awaited()

    async def test_s3_precedes_courtlistener(self):
        s3 = AsyncMock(return_value="s3")
        courtlistener = AsyncMock(return_value="courtlistener")
        result = await load_opinion_text("123", None, s3, courtlistener)
        self.assertEqual((result.text, result.source), ("s3", "s3"))
        courtlistener.assert_not_awaited()

    async def test_numeric_id_can_fall_back_to_courtlistener(self):
        result = await load_opinion_text(
            "123", None, AsyncMock(return_value=None), AsyncMock(return_value="courtlistener")
        )
        self.assertEqual((result.text, result.source), ("courtlistener", "courtlistener"))

    async def test_synthetic_id_never_reaches_courtlistener(self):
        courtlistener = AsyncMock(return_value="courtlistener")
        result = await load_opinion_text(
            "lexis-example-1996", None, AsyncMock(return_value=None), courtlistener
        )
        self.assertEqual((result.text, result.source), (None, None))
        courtlistener.assert_not_awaited()

    def test_courtlistener_id_requires_digits_only(self):
        self.assertTrue(is_courtlistener_id("687292"))
        self.assertFalse(is_courtlistener_id("lexis-example-1996"))
        self.assertFalse(is_courtlistener_id("687292-extra"))


if __name__ == "__main__":
    unittest.main()
