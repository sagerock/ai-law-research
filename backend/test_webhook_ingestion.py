import asyncio
from unittest.mock import AsyncMock, patch

import webhooks


class FakeConnection:
    def __init__(self, existing_content=None):
        self.existing_content = existing_content
        self.closed = False
        self.executed = []

    async def fetchval(self, query, *args):
        if "SELECT content FROM cases" in query:
            return self.existing_content
        if "SELECT id FROM courts" in query:
            return 7
        raise AssertionError(query)

    async def execute(self, query, *args):
        self.executed.append((query, args))
        return "INSERT 0 1"

    async def close(self):
        self.closed = True


def test_webhook_delivery_is_persisted_before_background_hydration():
    connection = FakeConnection()
    result = {
        "cluster_id": 123,
        "caseName": "Example v. Example",
        "court_id": "scotus",
        "dateFiled": "2026-01-01",
        "citation": ["1 U.S. 1"],
        "absolute_url": "/opinion/123/example/",
    }
    with patch.object(webhooks.asyncpg, "connect", new=AsyncMock(return_value=connection)):
        asyncio.run(webhooks.persist_new_case_stubs([result]))

    assert connection.closed
    assert len(connection.executed) == 1
    query, args = connection.executed[0]
    assert "ON CONFLICT (id) DO NOTHING" in query
    assert args[0] == "123"


def test_webhook_releases_database_connection_while_hydrating_stub():
    lookup = FakeConnection(existing_content=None)
    writer = FakeConnection()
    connections = iter([lookup, writer])

    async def connect(_database_url):
        return next(connections)

    async def fetch_opinion(_case_id):
        assert lookup.closed
        assert not writer.executed
        return "Canonical majority opinion. " * 20

    result = {
        "cluster_id": 123,
        "caseName": "Example v. Example",
        "court_id": "scotus",
        "dateFiled": "2026-01-01",
        "citation": ["1 U.S. 1"],
        "absolute_url": "/opinion/123/example/",
    }
    with patch.object(webhooks.asyncpg, "connect", side_effect=connect), patch.object(
        webhooks, "fetch_opinion_text", side_effect=fetch_opinion
    ):
        asyncio.run(webhooks.process_new_cases([result], "delivery-1"))

    assert writer.closed
    assert len(writer.executed) == 1
    query, args = writer.executed[0]
    assert "ON CONFLICT (id) DO UPDATE" in query
    assert args[0] == "123"
    assert args[5].startswith("Canonical majority opinion")


def test_webhook_skips_case_that_already_has_real_opinion_text():
    lookup = FakeConnection(existing_content="Existing opinion. " * 20)

    with patch.object(webhooks.asyncpg, "connect", new=AsyncMock(return_value=lookup)), patch.object(
        webhooks, "fetch_opinion_text", new=AsyncMock()
    ) as fetch:
        asyncio.run(webhooks.process_new_cases([{"cluster_id": 123}], "delivery-2"))

    assert lookup.closed
    fetch.assert_not_awaited()
