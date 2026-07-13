import asyncio
from datetime import date

import pytest
from fastapi import HTTPException

from ai_usage import reserve_daily_ai_request, reserve_pool_funds, settle_pool_reservation


class AsyncContext:
    def __init__(self, value=None):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self, *, tier_row=None, pool_balance=0.0):
        self.tier_row = tier_row
        self.pool_balance = pool_balance
        self.executed = []

    def transaction(self):
        return AsyncContext()

    async def execute(self, query, *args):
        self.executed.append((query, args))

    async def fetchrow(self, query, *args):
        if "FROM user_tiers" in query:
            return self.tier_row
        if "FROM pool_ledger" in query:
            return {"balance": self.pool_balance}
        raise AssertionError(f"Unexpected query: {query}")


class FakePool:
    def __init__(self, connection):
        self.connection = connection
        self.acquire_count = 0

    def acquire(self):
        self.acquire_count += 1
        return AsyncContext(self.connection)


def test_daily_reservation_rejects_anonymous_before_database_access():
    pool = FakePool(FakeConnection())

    with pytest.raises(HTTPException) as exc:
        asyncio.run(reserve_daily_ai_request(pool, "", is_byok=False))

    assert exc.value.status_code == 401
    assert pool.acquire_count == 0


def test_daily_reservation_rejects_exhausted_quota_without_incrementing():
    conn = FakeConnection(tier_row={
        "tier": "free",
        "messages_today": 15,
        "last_message_date": date.today(),
        "daily_limit": None,
    })

    with pytest.raises(HTTPException) as exc:
        asyncio.run(reserve_daily_ai_request(FakePool(conn), "user-1", is_byok=False))

    assert exc.value.status_code == 429
    assert not any("INSERT INTO user_tiers" in query for query, _ in conn.executed)


def test_daily_reservation_is_consumed_before_provider_work():
    conn = FakeConnection(tier_row={
        "tier": "free",
        "messages_today": 2,
        "last_message_date": date.today(),
        "daily_limit": None,
    })

    result = asyncio.run(reserve_daily_ai_request(FakePool(conn), "user-1", is_byok=False))

    assert result == {"daily_limit": 15, "messages_remaining": 12}
    assert any("INSERT INTO user_tiers" in query for query, _ in conn.executed)


def test_pool_reservation_rejects_insufficient_funds_without_ledger_write():
    conn = FakeConnection(pool_balance=0.04)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(reserve_pool_funds(FakePool(conn), 0.25, "request", "ref-1"))

    assert exc.value.status_code == 402
    assert not any("INSERT INTO pool_ledger" in query for query, _ in conn.executed)


def test_pool_reservation_and_settlement_never_overdraw():
    reserve_conn = FakeConnection(pool_balance=1.00)
    remaining = asyncio.run(
        reserve_pool_funds(FakePool(reserve_conn), 0.25, "request", "ref-1")
    )
    assert remaining == pytest.approx(0.75)
    assert any(args[0] == -0.25 for query, args in reserve_conn.executed if "INSERT INTO pool_ledger" in query)

    settle_conn = FakeConnection(pool_balance=0.75)
    remaining = asyncio.run(
        settle_pool_reservation(FakePool(settle_conn), 0.25, 0.07, "actual", "ref-1")
    )
    assert remaining == pytest.approx(0.93)
    assert any(args[0] == pytest.approx(0.18)
               for query, args in settle_conn.executed if "INSERT INTO pool_ledger" in query)
