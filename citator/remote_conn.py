"""An asyncpg-shaped connection that runs each query through `railway ssh`.

The production database has had no public address since the 2026-10-07 audit, so
`sunday_briefs.py` can no longer open it directly. `connect()` returns this proxy:
reads make one round trip each (about 1.3 s), and a `transaction()` block buffers
its writes and sends them as one remote transaction when the block exits. Reads are
not allowed inside a transaction block (nothing in the brief pipeline needs them).

Set DIRECT_DATABASE_URL to use a real asyncpg connection instead (local testing).
"""

from __future__ import annotations

import asyncio
import datetime
import decimal
import os

import railway_db

_SNIPPET = '''
import datetime, decimal

def _enc(v):
    if isinstance(v, datetime.datetime):
        return {"__t": "dt", "v": v.isoformat()}
    if isinstance(v, datetime.date):
        return {"__t": "d", "v": v.isoformat()}
    if isinstance(v, decimal.Decimal):
        return {"__t": "dec", "v": str(v)}
    if isinstance(v, (list, tuple)):
        return [_enc(x) for x in v]
    if isinstance(v, dict):
        return {k: _enc(x) for k, x in v.items()}
    return v

def _row(r):
    return None if r is None else {"keys": list(r.keys()), "values": _enc(list(r.values()))}

async def job(conn, payload):
    op = payload["op"]
    if op == "batch":
        async with conn.transaction():
            for kind, sql, args in payload["statements"]:
                if kind == "execute":
                    await conn.execute(sql, *args)
                else:
                    await conn.executemany(sql, [tuple(a) for a in args])
        return None
    sql, args = payload["sql"], payload["args"]
    if op == "fetch":
        return [_row(r) for r in await conn.fetch(sql, *args)]
    if op == "fetchrow":
        return _row(await conn.fetchrow(sql, *args))
    if op == "fetchval":
        return _enc(await conn.fetchval(sql, *args))
    if op == "execute":
        return await conn.execute(sql, *args)
    raise ValueError(op)
'''


def _dec(value):
    if isinstance(value, list):
        return [_dec(x) for x in value]
    if isinstance(value, dict):
        tag = value.get("__t")
        if tag == "dt":
            return datetime.datetime.fromisoformat(value["v"])
        if tag == "d":
            return datetime.date.fromisoformat(value["v"])
        if tag == "dec":
            return decimal.Decimal(value["v"])
        return {k: _dec(x) for k, x in value.items()}
    return value


def _args(args):
    def plain(v):
        if isinstance(v, (datetime.date, datetime.datetime)):
            raise TypeError("pass dates to the remote connection as ISO strings")
        if isinstance(v, (list, tuple)):
            return [plain(x) for x in v]
        return v
    return [plain(a) for a in args]


class Row:
    """Record stand-in: key and index access; iterating yields values, like asyncpg."""

    def __init__(self, keys, values):
        self._keys = list(keys)
        self._values = list(values)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._values[self._keys.index(key)]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def keys(self):
        return list(self._keys)

    def values(self):
        return list(self._values)

    def items(self):
        return list(zip(self._keys, self._values))

    def get(self, key, default=None):
        return self[key] if key in self._keys else default


def _to_row(raw):
    return None if raw is None else Row(raw["keys"], _dec(raw["values"]))


class _Transaction:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        if self.conn._batch is not None:
            raise RuntimeError("nested transactions are not supported")
        self.conn._batch = []
        return self

    async def __aexit__(self, exc_type, exc, tb):
        statements, self.conn._batch = self.conn._batch, None
        if exc_type is None and statements:
            await self.conn._call({"op": "batch", "statements": statements})
        return False


class RemoteConnection:
    def __init__(self):
        self._batch = None

    async def _call(self, payload):
        return await asyncio.to_thread(railway_db.run, _SNIPPET, payload, 600)

    async def _read(self, op, sql, args):
        if self._batch is not None:
            raise RuntimeError("reads inside a remote transaction block are not supported")
        return await self._call({"op": op, "sql": sql, "args": _args(args)})

    async def fetch(self, sql, *args):
        return [_to_row(r) for r in await self._read("fetch", sql, args)]

    async def fetchrow(self, sql, *args):
        return _to_row(await self._read("fetchrow", sql, args))

    async def fetchval(self, sql, *args):
        return _dec(await self._read("fetchval", sql, args))

    async def execute(self, sql, *args):
        if self._batch is not None:
            self._batch.append(["execute", sql, _args(args)])
            return None
        return await self._call({"op": "execute", "sql": sql, "args": _args(args)})

    async def executemany(self, sql, rows):
        rows = [_args(r) for r in rows]
        if self._batch is not None:
            self._batch.append(["executemany", sql, rows])
            return None
        await self._call({"op": "batch", "statements": [["executemany", sql, rows]]})

    def transaction(self):
        return _Transaction(self)

    async def close(self):
        return None


async def connect():
    url = os.getenv("DIRECT_DATABASE_URL")
    if url:
        import asyncpg
        return await asyncpg.connect(url)
    return RemoteConnection()
