"""Visitors get no live AI on the site key (Sage, 2026-10-19)."""

import asyncio

import pytest

import main


def _key(monkeypatch, user_key=None, site_key="site-key"):
    async def fake_user_key(user_id):
        return user_key

    monkeypatch.setattr(main, "get_user_api_key", fake_user_key)
    monkeypatch.setattr(main, "ANTHROPIC_API_KEY", site_key)


def test_anonymous_gets_403(monkeypatch):
    _key(monkeypatch)
    with pytest.raises(main.HTTPException) as exc:
        asyncio.run(main.get_anthropic_api_key(None))
    assert exc.value.status_code == 403
    assert exc.value.detail == main.LIVE_AI_OFF_DETAIL


def test_signed_in_reader_without_key_gets_403(monkeypatch):
    _key(monkeypatch)
    with pytest.raises(main.HTTPException) as exc:
        asyncio.run(main.get_anthropic_api_key({"id": "u1", "email": "student@example.edu"}))
    assert exc.value.status_code == 403


def test_byok_reader_uses_own_key(monkeypatch):
    _key(monkeypatch, user_key="sk-own")
    assert asyncio.run(main.get_anthropic_api_key({"id": "u1", "email": "s@x.edu"})) == (
        "sk-own", "byok")


def test_admin_uses_site_key(monkeypatch):
    _key(monkeypatch)
    assert asyncio.run(main.get_anthropic_api_key({"id": "a", "email": main.ADMIN_EMAIL})) == (
        "site-key", "site")


def test_admin_without_site_key_is_503(monkeypatch):
    _key(monkeypatch, site_key=None)
    with pytest.raises(main.HTTPException) as exc:
        asyncio.run(main.get_anthropic_api_key({"id": "a", "email": main.ADMIN_EMAIL}))
    assert exc.value.status_code == 503


@pytest.mark.parametrize("user", [None, {"id": "u1", "email": "s@x.edu"}])
def test_site_only_features_are_admin_only(monkeypatch, user):
    _key(monkeypatch)
    with pytest.raises(main.HTTPException) as exc:
        main.require_site_ai(user)
    assert exc.value.status_code == 403


def test_site_only_features_allow_admin(monkeypatch):
    _key(monkeypatch)
    main.require_site_ai({"id": "a", "email": main.ADMIN_EMAIL})


def test_mindmap_generate_refuses_visitor_before_any_call(monkeypatch):
    _key(monkeypatch)

    async def unexpected(*args, **kwargs):
        raise AssertionError("reservation must not run for a visitor")

    monkeypatch.setattr(main, "reserve_anthropic_request", unexpected)
    with pytest.raises(main.HTTPException) as exc:
        asyncio.run(main.generate_mindmap(
            main.MindmapGenerate(topic="Negligence"), user={"id": "u1", "email": "s@x.edu"}
        ))
    assert exc.value.status_code == 403


class _Conn:
    def __init__(self):
        self.rows = set()
        self.recent = 0

    async def fetchval(self, query, *args):
        if "FROM cases" in query:
            return True
        if "AND user_id = $2" in query:
            return (args[0], args[1]) in self.rows
        if "created_at > NOW()" in query:
            return self.recent
        if "COUNT(*) FROM brief_requests WHERE case_id" in query:
            return sum(1 for case, _ in self.rows if case == args[0])
        raise AssertionError(query)

    async def execute(self, query, *args):
        assert "INSERT INTO brief_requests" in query
        self.rows.add((args[0], args[1]))


class _Pool:
    def __init__(self, conn):
        self.conn = conn

    def acquire(self):
        conn = self.conn

        class Ctx:
            async def __aenter__(self):
                return conn

            async def __aexit__(self, *exc):
                return False

        return Ctx()


def test_brief_request_is_idempotent(monkeypatch):
    conn = _Conn()
    monkeypatch.setattr(main, "db_pool", _Pool(conn))
    user = {"id": "u1", "email": "s@x.edu"}
    first = asyncio.run(main.request_brief("case-1", user=user))
    again = asyncio.run(main.request_brief("case-1", user=user))
    other = asyncio.run(main.request_brief("case-1", user={"id": "u2", "email": "t@x.edu"}))
    assert first == {"requests": 1, "requested": True}
    assert again == {"requests": 1, "requested": True}
    assert other["requests"] == 2


def test_brief_request_daily_cap(monkeypatch):
    conn = _Conn()
    conn.recent = main.BRIEF_REQUESTS_PER_DAY
    monkeypatch.setattr(main, "db_pool", _Pool(conn))
    with pytest.raises(main.HTTPException) as exc:
        asyncio.run(main.request_brief("case-9", user={"id": "u1", "email": "s@x.edu"}))
    assert exc.value.status_code == 429
