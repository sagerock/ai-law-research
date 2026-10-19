import asyncio
import datetime

import remote_conn


def test_row_matches_asyncpg_record_access():
    row = remote_conn._to_row({"keys": ["content", "content_hash"],
                               "values": ["text", {"__t": "d", "v": "2026-10-19"}]})
    text, digest = row
    assert text == "text" and digest == datetime.date(2026, 10, 19)
    assert row["content"] == "text" and row[1] == digest
    assert dict(row.items()) == {"content": "text", "content_hash": digest}


def test_fetchrow_none_supports_or_fallback(monkeypatch):
    conn = remote_conn.RemoteConnection()

    async def call(payload):
        return None

    monkeypatch.setattr(conn, "_call", call)
    text, digest = asyncio.run(conn.fetchrow("SELECT 1")) or (None, None)
    assert text is None and digest is None


def test_transaction_sends_one_batch(monkeypatch):
    conn = remote_conn.RemoteConnection()
    sent = []

    async def call(payload):
        sent.append(payload)

    monkeypatch.setattr(conn, "_call", call)

    async def work():
        async with conn.transaction():
            await conn.execute("UPDATE a SET x = $1", 1)
            await conn.executemany("INSERT INTO b VALUES ($1)", [(1,), (2,)])

    asyncio.run(work())
    assert sent == [{"op": "batch", "statements": [
        ["execute", "UPDATE a SET x = $1", [1]],
        ["executemany", "INSERT INTO b VALUES ($1)", [[1], [2]]],
    ]}]


def test_failed_transaction_sends_nothing(monkeypatch):
    conn = remote_conn.RemoteConnection()
    sent = []

    async def call(payload):
        sent.append(payload)

    monkeypatch.setattr(conn, "_call", call)

    async def work():
        async with conn.transaction():
            await conn.execute("UPDATE a SET x = 1")
            raise ValueError("boom")

    try:
        asyncio.run(work())
    except ValueError:
        pass
    assert sent == []
