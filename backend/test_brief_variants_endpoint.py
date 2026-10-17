import asyncio
import json

import pytest
from fastapi import HTTPException

import main
from test_brief_variants import detailed_brief, valid_candidate


class AcquireContext:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeConnection:
    def __init__(self, title="Dean Milk Co. v. City of Madison"):
        self.title = title
        self.executed = []

    async def fetchval(self, query, *args):
        return self.title

    async def execute(self, query, *args):
        self.executed.append(args)


class FakePool:
    def __init__(self, connection):
        self.connection = connection

    def acquire(self):
        return AcquireContext(self.connection)


def install(monkeypatch, connection, response, detailed=("claude", None)):
    async def variant_response(conn, case_id):
        return response() if callable(response) else response

    async def approved(conn, case_id):
        if detailed is None:
            return None
        return detailed[0], detailed[1] or detailed_brief()

    async def no_user(_authorization):
        return None

    monkeypatch.setattr(main, "db_pool", FakePool(connection))
    monkeypatch.setattr(main, "_brief_variant_response", variant_response)
    monkeypatch.setattr(main, "_approved_detailed_brief", approved)
    monkeypatch.setattr(main, "get_current_user", no_user)


def test_force_regeneration_requires_admin_before_database():
    assert main.db_pool is None
    with pytest.raises(HTTPException) as error:
        asyncio.run(main.generate_brief_variants("104847", force=True, authorization=None))
    assert error.value.status_code in (401, 403)


def test_cached_variant_never_resolves_a_paid_key(monkeypatch):
    install(monkeypatch, FakeConnection(), {"status": "ready", "simplified": {}, "bullets": []})

    async def should_not_resolve(_user_id):
        raise AssertionError("a cache hit must not resolve a paid API key")

    monkeypatch.setattr(main, "get_anthropic_api_key", should_not_resolve)
    assert asyncio.run(main.generate_brief_variants("104847"))["status"] == "ready"


def test_case_without_approved_brief_is_refused_before_any_spend(monkeypatch):
    install(monkeypatch, FakeConnection(), {"status": "unavailable"}, detailed=None)

    async def should_not_resolve(_user_id):
        raise AssertionError("no approved brief means nothing to rewrite")

    monkeypatch.setattr(main, "get_anthropic_api_key", should_not_resolve)
    with pytest.raises(HTTPException) as error:
        asyncio.run(main.generate_brief_variants("104847"))
    assert error.value.status_code == 409


def test_fidelity_problem_triggers_targeted_retry_then_publishes(monkeypatch):
    connection = FakeConnection()
    states = iter([{"status": "not_generated"}, {"status": "ready"}])
    install(monkeypatch, connection, lambda: next(states))

    replies = iter([
        json.dumps(valid_candidate()),
        json.dumps({"problems": [{"line": "simplified.dissent[0]", "severity": "wrong",
                                  "problem": "says the opposite"}]}),
        json.dumps(valid_candidate()),
        json.dumps({"problems": [{"line": "bullets[0]", "severity": "minor", "problem": "loose"}]}),
    ])
    sent = []

    class FakeResponse:
        status_code = 200

        def __init__(self, text):
            self.text = text

        def json(self):
            return {"content": [{"type": "text", "text": self.text}],
                    "usage": {"input_tokens": 100, "output_tokens": 50}}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, headers=None, json=None, timeout=None):
            sent.append(json)
            return FakeResponse(next(replies))

    async def site_key(_user_id):
        return "test-key", "byok"

    async def reserve(*args, **kwargs):
        return {"site_funded": False, "reference_id": "test"}

    async def settle(*args, **kwargs):
        return None

    async def log_usage(*args, **kwargs):
        return None

    monkeypatch.setattr(main, "get_anthropic_api_key", site_key)
    monkeypatch.setattr(main, "reserve_anthropic_request", reserve)
    monkeypatch.setattr(main, "settle_anthropic_request", settle)
    monkeypatch.setattr(main, "log_api_usage", log_usage)
    monkeypatch.setattr(main.httpx, "AsyncClient", FakeClient)

    result = asyncio.run(main.generate_brief_variants("104847"))

    assert result["status"] == "ready"
    assert [call["model"] for call in sent] == [
        main.BRIEF_VARIANT_MODEL, main.BRIEF_VARIANT_REVIEW_MODEL,
        main.BRIEF_VARIANT_MODEL, main.BRIEF_VARIANT_REVIEW_MODEL,
    ]
    retry_turn = sent[2]["messages"][-1]["content"]
    assert "simplified.dissent[0]: says the opposite" in retry_turn
    assert "Copy every other line unchanged" in retry_turn
    (row,) = connection.executed
    simplified = json.loads(row[3])
    assert simplified["holding"][0]["sources"] == ["op-h1", "op-h2"]
