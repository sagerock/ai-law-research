import asyncio
import inspect
import json
from datetime import date

import pytest
import httpx

import main


def test_done_event_is_built_only_after_durable_finalization():
    events = []

    async def finalize():
        events.append("assistant_persisted")
        await asyncio.sleep(0)
        events.append("api_usage_logged")
        await asyncio.sleep(0)
        events.append("pool_reconciled")

    event = asyncio.run(main.terminal_sse_event(finalize, {"type": "done"}))
    events.append(json.loads(event.removeprefix("data: ").strip())["type"])

    assert events == [
        "assistant_persisted",
        "api_usage_logged",
        "pool_reconciled",
        "done",
    ]


def test_done_event_is_not_built_when_finalization_fails():
    async def finalize():
        raise RuntimeError("database unavailable")

    with pytest.raises(RuntimeError, match="database unavailable"):
        asyncio.run(main.terminal_sse_event(finalize, {"type": "done"}))


def test_sse_business_usage_and_settlement_share_one_idempotent_transaction(monkeypatch):
    events = []
    state = {"finalized": False}

    class Transaction:
        async def __aenter__(self):
            conn.in_transaction = True
            events.append("transaction_enter")

        async def __aexit__(self, exc_type, exc, tb):
            events.append("transaction_exit")
            conn.in_transaction = False

    class Connection:
        in_transaction = False

        def transaction(self):
            return Transaction()

    conn = Connection()
    monkeypatch.setattr(main, "db_pool", ChatPool(conn))

    async def fake_lock(used_conn, reference_id):
        assert used_conn is conn and conn.in_transaction
        events.append("lock")
        return state["finalized"]

    async def fake_usage(used_conn, *args):
        assert used_conn is conn and conn.in_transaction
        events.append("usage")

    async def fake_settle(used_conn, *args, **kwargs):
        assert used_conn is conn and conn.in_transaction
        events.append("settle")
        state["finalized"] = True

    async def persist(used_conn):
        assert used_conn is conn and conn.in_transaction
        events.append("persist")

    monkeypatch.setattr(main, "lock_ai_request_on_connection", fake_lock)
    monkeypatch.setattr(main, "_record_api_usage", fake_usage)
    monkeypatch.setattr(main, "settle_pool_reservation_on_connection", fake_settle)
    reservation = {
        "reference_id": "request-1", "site_funded": True, "amount": 0.25,
    }

    async def finalize_twice():
        for _ in range(2):
            await main.finalize_anthropic_sse(
                reservation, 0.07, "case_ask", 10, 20, "site", "actual", persist
            )

    asyncio.run(finalize_twice())

    assert events == [
        "transaction_enter", "lock", "persist", "usage", "settle",
        "transaction_exit", "transaction_enter", "lock", "transaction_exit",
    ]


def test_site_reservation_uses_token_preflight_before_atomic_pool_debit(monkeypatch):
    events = []

    class FakeMessages:
        async def count_tokens(self, **kwargs):
            events.append(("count", kwargs))
            return type("Count", (), {"input_tokens": 10_000})()

    class FakeClient:
        def __init__(self, api_key):
            assert api_key == "site-key"
            self.messages = FakeMessages()

    async def fake_reserve(db_pool, amount, description, reference_id):
        events.append(("reserve", amount, description, reference_id))

    monkeypatch.setattr(main.anthropic, "AsyncAnthropic", FakeClient)
    monkeypatch.setattr(main, "reserve_pool_funds", fake_reserve)

    reservation = asyncio.run(main.reserve_anthropic_request(
        "site-key",
        "site",
        "claude-sonnet-4-6",
        4096,
        [{"role": "user", "content": "question"}],
        "test reservation",
    ))

    assert [event[0] for event in events] == ["count", "reserve"]
    assert events[1][1] == pytest.approx(0.09894)
    assert reservation["amount"] == pytest.approx(events[1][1])


def test_byok_skips_token_preflight_and_pool_reservation(monkeypatch):
    class UnexpectedClient:
        def __init__(self, api_key):
            raise AssertionError("BYOK must not use the site reservation path")

    monkeypatch.setattr(main.anthropic, "AsyncAnthropic", UnexpectedClient)

    reservation = asyncio.run(main.reserve_anthropic_request(
        "user-key",
        "byok",
        "claude-sonnet-4-6",
        4096,
        [{"role": "user", "content": "question"}],
        "test reservation",
    ))

    assert reservation["site_funded"] is False


def test_msj_cached_prompt_case_inputs_have_deterministic_ordering():
    assert "ORDER BY array_position($1::text[], c.id)" in main.MSJ_CORE_CASES_QUERY
    assert "ORDER BY pc.id, c.id" in main.MSJ_USER_CASES_QUERY


def test_persisted_unknown_model_override_fails_before_provider_work():
    with pytest.raises(main.HTTPException) as exc:
        main.validate_configured_anthropic_model("claude-future-9")

    assert exc.value.status_code == 500


def test_count_token_connection_failure_maps_to_503_without_reserving(monkeypatch):
    reserved = False

    class FailingMessages:
        async def count_tokens(self, **kwargs):
            request = httpx.Request("POST", "https://api.anthropic.com/v1/messages/count_tokens")
            raise main.anthropic.APIConnectionError(request=request)

    class FailingClient:
        def __init__(self, api_key):
            self.messages = FailingMessages()

    async def unexpected_reserve(*args, **kwargs):
        nonlocal reserved
        reserved = True

    monkeypatch.setattr(main.anthropic, "AsyncAnthropic", FailingClient)
    monkeypatch.setattr(main, "reserve_pool_funds", unexpected_reserve)

    with pytest.raises(main.HTTPException) as exc:
        asyncio.run(main.reserve_anthropic_request(
            "site-key", "site", "claude-sonnet-4-6", 100,
            [{"role": "user", "content": "question"}], "test",
        ))

    assert exc.value.status_code == 503
    assert reserved is False


def test_count_token_status_failure_maps_to_502(monkeypatch):
    class RejectedMessages:
        async def count_tokens(self, **kwargs):
            request = httpx.Request("POST", "https://api.anthropic.com/v1/messages/count_tokens")
            response = httpx.Response(429, request=request)
            raise main.anthropic.APIStatusError("rate limited", response=response, body={})

    class RejectedClient:
        def __init__(self, api_key):
            self.messages = RejectedMessages()

    monkeypatch.setattr(main.anthropic, "AsyncAnthropic", RejectedClient)

    with pytest.raises(main.HTTPException) as exc:
        asyncio.run(main.reserve_anthropic_request(
            "site-key", "site", "claude-sonnet-4-6", 100,
            [{"role": "user", "content": "question"}], "test",
        ))

    assert exc.value.status_code == 502


def test_provider_failure_refunds_connect_errors_and_audits_uncertain_reads(monkeypatch):
    events = []

    async def fake_cancel(reservation, description, *, conn=None):
        events.append(("cancel", description))

    async def fake_uncertain(db_pool, description, reference_id):
        events.append(("uncertain", description, reference_id))

    monkeypatch.setattr(main, "cancel_anthropic_request", fake_cancel)
    monkeypatch.setattr(main, "mark_pool_reservation_uncertain", fake_uncertain)
    reservation = {"reference_id": "request-1", "site_funded": True}
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")

    asyncio.run(main.handle_anthropic_provider_failure(
        reservation, httpx.ConnectError("connect", request=request), "connect"
    ))
    asyncio.run(main.handle_anthropic_provider_failure(
        reservation, httpx.ReadTimeout("read", request=request), "read"
    ))

    assert events[0] == ("cancel", "connect refund")
    assert events[1] == (
        "uncertain", "read; provider acceptance unknown", "request-1",
    )


@pytest.mark.parametrize("streaming_endpoint", [
    main.study_chat,
    main.case_ask_ai,
    main.session_respond,
    main.msj_chat,
    main.msj_generate_motion,
    main.tool_chat,
    main.tool_generate,
])
def test_migrated_provider_streams_audit_cancellation(streaming_endpoint):
    source = inspect.getsource(streaming_endpoint)
    assert "except asyncio.CancelledError" in source
    assert "audit_cancelled_anthropic_provider" in source


class AsyncContext:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, exc_type, exc, tb):
        return False


class ChatConnection:
    def __init__(self, kind):
        self.kind = kind
        self.executed = []

    async def execute(self, query, *args):
        self.executed.append((query, args))

    async def fetchrow(self, query, *args):
        if "FROM user_tiers" in query:
            return {
                "tier": "free", "messages_today": 0,
                "last_message_date": date.today(), "daily_limit": None,
                "model_override": None,
            }
        if "SELECT user_id FROM conversations" in query:
            return {"user_id": "user-1"}
        if "SELECT note_ids FROM conversations" in query:
            return {"note_ids": []}
        if "FROM outline_conversations" in query:
            return {
                "id": 1, "outline_id": 2, "user_id": "user-1", "mode": "ask",
                "subject": "Torts", "content": "Duty and breach",
            }
        if "SELECT id, title, content, court_id" in query:
            return {
                "id": "case-1", "title": "Example v. Example", "content": "Opinion",
                "court_id": "court", "decision_date": None,
            }
        if "SELECT summary FROM ai_summaries" in query:
            return None
        if "SELECT user_id, case_id FROM conversations" in query:
            return {"user_id": "user-1", "case_id": "case-1"}
        raise AssertionError(f"Unexpected fetchrow: {query}")

    async def fetch(self, query, *args):
        return []


class ChatPool:
    def __init__(self, conn):
        self.conn = conn

    def acquire(self):
        return AsyncContext(self.conn)


@pytest.mark.parametrize("kind", ["study", "outline", "case"])
@pytest.mark.parametrize("failure_status", [402, 503])
def test_preflight_failure_does_not_persist_pending_chat_turn(
    monkeypatch, kind, failure_status
):
    conn = ChatConnection(kind)
    monkeypatch.setattr(main, "db_pool", ChatPool(conn))

    async def no_user_key(user_id):
        return None

    async def reject_reservation(*args, **kwargs):
        raise main.HTTPException(status_code=failure_status, detail="preflight failed")

    monkeypatch.setattr(main, "get_user_api_key", no_user_key)
    monkeypatch.setattr(main, "ANTHROPIC_API_KEY", "site-key")
    monkeypatch.setattr(main, "reserve_anthropic_request", reject_reservation)
    monkeypatch.setattr(
        main, "load_opinion_text",
        lambda *args, **kwargs: asyncio.sleep(
            0, result=type("Opinion", (), {"text": "Opinion"})()
        ),
    )

    with pytest.raises(main.HTTPException) as exc:
        if kind == "study":
            asyncio.run(main.study_chat(
                main.ChatMessage(content="question", conversation_id=1),
                user={"id": "user-1"},
            ))
        elif kind == "outline":
            asyncio.run(main.outline_study_message(
                2, 1, main.OutlineStudyMessage(content="question"),
                user={"id": "user-1"},
            ))
        else:
            asyncio.run(main.case_ask_ai(
                "case-1", main.CaseAskMessage(content="question", conversation_id=1),
                user={"id": "user-1"},
            ))

    assert exc.value.status_code == failure_status
    assert not any("INSERT INTO messages" in query or
                   "INSERT INTO outline_conversation_messages" in query
                   for query, _ in conn.executed)
