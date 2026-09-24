import asyncio

import pytest
from fastapi import HTTPException

import main


def test_force_regeneration_requires_admin():
    # force=true re-runs a paid Anthropic generation for a case that already has
    # a brief. Left unauthenticated it would be a way to drain the shared pool by
    # re-requesting the same case, so the gate must fire before any other work.
    with pytest.raises(HTTPException) as error:
        asyncio.run(main.summarize_case("10600062", force=True, authorization=None))
    assert error.value.status_code in (401, 403)


def test_force_gate_runs_before_touching_the_database():
    # db_pool is None here, so anything that reached a query would raise
    # AttributeError rather than HTTPException. This pins the ordering.
    assert main.db_pool is None
    with pytest.raises(HTTPException):
        asyncio.run(main.summarize_case("10600062", force=True, authorization="Bearer nonsense"))


def test_approved_candidate_without_legacy_summary_is_a_cache_hit(monkeypatch):
    class FakeConnection:
        def __init__(self):
            self.fetchrow_calls = 0

        async def fetchrow(self, query, *args):
            self.fetchrow_calls += 1
            if self.fetchrow_calls == 1:
                return None  # No ai_summaries row.
            return {"id": "626209"}  # Case exists.

        async def fetchval(self, query, *args):
            return True  # An approved Claude candidate exists.

        async def fetch(self, query, *args):
            return []

    class AcquireContext:
        def __init__(self, connection):
            self.connection = connection

        async def __aenter__(self):
            return self.connection

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    class FakePool:
        def __init__(self):
            self.connection = FakeConnection()

        def acquire(self):
            return AcquireContext(self.connection)

    async def no_user(_authorization):
        return None

    async def should_not_resolve_api_key(_user_id):
        raise AssertionError("a cache hit must not resolve a paid API key")

    async def cached_response(case_id, user):
        return {"case_id": case_id, "cached": True, "structured_candidates": [{}]}

    monkeypatch.setattr(main, "db_pool", FakePool())
    monkeypatch.setattr(main, "get_current_user", no_user)
    monkeypatch.setattr(main, "get_anthropic_api_key", should_not_resolve_api_key)
    monkeypatch.setattr(main, "get_case_summary", cached_response)

    result = asyncio.run(main.summarize_case("626209"))

    assert result["cached"] is True
    assert result["structured_candidates"] == [{}]
