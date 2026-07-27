import asyncio
from datetime import date

import pytest
from fastapi import HTTPException

from ai_usage import (
    anthropic_call_cost,
    anthropic_reservation_cost,
    reserve_daily_ai_request,
    reserve_pool_funds,
    settle_pool_reservation_on_connection,
    settle_pool_reservation,
)


class AsyncContext:
    def __init__(self, value=None):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self, *, tier_row=None, pool_balance=0.0, reservation_amount=None):
        self.tier_row = tier_row
        self.pool_balance = pool_balance
        self.reservation_amount = reservation_amount
        self.executed = []
        self.events = []

    def transaction(self):
        return AsyncContext()

    async def execute(self, query, *args):
        self.executed.append((query, args))
        self.events.append(("execute", query, args))

    async def fetchrow(self, query, *args):
        self.events.append(("fetchrow", query, args))
        if "FROM user_tiers" in query:
            return self.tier_row
        if "FROM pool_ledger" in query:
            if "entry_type = 'ai_reservation'" in query:
                return ({"amount": self.reservation_amount}
                        if self.reservation_amount is not None else None)
            return {"balance": self.pool_balance}
        raise AssertionError(f"Unexpected query: {query}")

    async def fetchval(self, query, *args):
        self.events.append(("fetchval", query, args))
        return False


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

    settle_conn = FakeConnection(pool_balance=0.75, reservation_amount=-0.25)
    remaining = asyncio.run(
        settle_pool_reservation(FakePool(settle_conn), 0.07, "actual", "ref-1")
    )
    assert remaining == pytest.approx(0.93)
    assert any(args[0] == pytest.approx(0.18)
               for query, args in settle_conn.executed if "INSERT INTO pool_ledger" in query)


def test_pool_reservation_locks_before_reading_or_debiting_balance():
    conn = FakeConnection(pool_balance=1.00)

    asyncio.run(reserve_pool_funds(FakePool(conn), 0.25, "request", "ref-1"))

    lock_index = next(i for i, event in enumerate(conn.events)
                      if event[0] == "execute" and "pg_advisory_xact_lock" in event[1])
    balance_index = next(i for i, event in enumerate(conn.events)
                         if event[0] == "fetchrow" and "FROM pool_ledger" in event[1])
    debit_index = next(i for i, event in enumerate(conn.events)
                       if event[0] == "execute" and "INSERT INTO pool_ledger" in event[1])
    assert lock_index < balance_index < debit_index


def test_repeated_pool_reservation_reference_is_a_locked_noop():
    conn = FakeConnection(pool_balance=0.75, reservation_amount=-0.25)

    remaining = asyncio.run(
        reserve_pool_funds(FakePool(conn), 0.25, "retry", "ref-1")
    )

    assert remaining == pytest.approx(0.75)
    assert not any("INSERT INTO pool_ledger" in query for query, _ in conn.executed)


def test_anthropic_reservation_covers_worst_case_cache_write_and_output():
    reservation = anthropic_reservation_cost(10_000, 4_096, "claude-sonnet-4-6")
    worst_case = anthropic_call_cost(
        0,
        4_096,
        cache_write_tokens=10_000,
        model="claude-sonnet-4-6",
    )

    assert reservation == pytest.approx(worst_case)


@pytest.mark.parametrize("calculator", [
    lambda: anthropic_call_cost(1, 1, model="claude-future-9"),
    lambda: anthropic_reservation_cost(1, 1, "claude-future-9"),
])
def test_unknown_anthropic_models_fail_closed(calculator):
    with pytest.raises(ValueError, match="Unsupported Anthropic model"):
        calculator()


class LedgerTransaction:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        for lock in reversed(self.conn.held_locks):
            lock.release()
        self.conn.held_locks.clear()
        return False


class LedgerState:
    def __init__(self):
        self.rows = [{
            "amount": -0.25,
            "entry_type": "ai_reservation",
            "description": "reserved",
            "reference_id": "request-1",
        }]
        self.global_lock = asyncio.Lock()
        self.request_locks = {}


class LedgerConnection:
    def __init__(self, state):
        self.state = state
        self.held_locks = []

    def transaction(self):
        return LedgerTransaction(self)

    async def execute(self, query, *args):
        if "pg_advisory_xact_lock(hashtext" in query:
            lock = self.state.request_locks.setdefault(args[0], asyncio.Lock())
            await lock.acquire()
            self.held_locks.append(lock)
        elif "pg_advisory_xact_lock(1)" in query:
            await self.state.global_lock.acquire()
            self.held_locks.append(self.state.global_lock)
        elif "ai_reservation_adjustment" in query:
            self.state.rows.append({
                "amount": args[0], "entry_type": "ai_reservation_adjustment",
                "description": args[1], "reference_id": args[2],
            })
        elif "ai_reservation_finalized" in query:
            if not any(r["entry_type"] == "ai_reservation_finalized" and
                       r["reference_id"] == args[1] for r in self.state.rows):
                self.state.rows.append({
                    "amount": 0.0, "entry_type": "ai_reservation_finalized",
                    "description": args[0], "reference_id": args[1],
                })
        else:
            raise AssertionError(f"Unexpected execute: {query}")

    async def fetchval(self, query, *args):
        if "ai_reservation_finalized" in query:
            return any(r["entry_type"] == "ai_reservation_finalized" and
                       r["reference_id"] == args[0] for r in self.state.rows)
        raise AssertionError(f"Unexpected fetchval: {query}")

    async def fetchrow(self, query, *args):
        if "entry_type = 'ai_reservation'" in query:
            return next((r for r in self.state.rows
                         if r["entry_type"] == "ai_reservation" and
                         r["reference_id"] == args[0]), None)
        if "SUM(amount)" in query:
            return {"balance": sum(float(r["amount"]) for r in self.state.rows)}
        raise AssertionError(f"Unexpected fetchrow: {query}")


def test_zero_adjustment_still_closes_reservation_and_restart_retry_is_noop():
    async def scenario():
        state = LedgerState()
        conn = LedgerConnection(state)
        async with conn.transaction():
            await settle_pool_reservation_on_connection(
                conn, 0.25, "actual", "request-1"
            )
        first_rows = list(state.rows)
        retry_conn = LedgerConnection(state)
        async with retry_conn.transaction():
            await settle_pool_reservation_on_connection(
                retry_conn, 0.10, "retry", "request-1"
            )
        return first_rows, state.rows

    first_rows, final_rows = asyncio.run(scenario())
    assert [r["entry_type"] for r in first_rows].count("ai_reservation_finalized") == 1
    assert not any(r["entry_type"] == "ai_reservation_adjustment" for r in first_rows)
    assert final_rows == first_rows


def test_concurrent_settle_and_cancel_apply_exactly_one_terminal_transition():
    async def scenario():
        state = LedgerState()

        async def settle(actual, description):
            conn = LedgerConnection(state)
            async with conn.transaction():
                await settle_pool_reservation_on_connection(
                    conn, actual, description, "request-1"
                )

        await asyncio.gather(settle(0.07, "settle"), settle(0.0, "cancel"))
        return state.rows

    rows = asyncio.run(scenario())
    assert [r["entry_type"] for r in rows].count("ai_reservation_finalized") == 1
    adjustments = [r for r in rows if r["entry_type"] == "ai_reservation_adjustment"]
    assert len(adjustments) == 1
    assert any(adjustments[0]["amount"] == pytest.approx(value)
               for value in (0.18, 0.25))
