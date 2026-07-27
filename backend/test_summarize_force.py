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
