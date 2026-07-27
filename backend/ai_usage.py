"""Atomic quota and community-pool reservations for paid AI requests."""

from __future__ import annotations

from datetime import date

from fastapi import HTTPException


POOL_EMPTY_DETAIL = "Community AI pool is empty. Donate to refill it!"
DAILY_LIMIT_DETAIL = (
    "You've reached today's free limit. Add your own API key for unlimited use, "
    "or come back tomorrow."
)

ANTHROPIC_MODEL_PRICING = {
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "claude-sonnet-4-5-20250929": (3.00, 15.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-8": (5.00, 25.00),
}


def anthropic_call_cost(
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
    model: str = "claude-sonnet-4-6",
) -> float:
    """Price one Anthropic Messages call, including prompt-cache activity."""
    try:
        input_rate, output_rate = ANTHROPIC_MODEL_PRICING[model]
    except KeyError as exc:
        raise ValueError(f"Unsupported Anthropic model: {model}") from exc
    return (
        input_tokens * input_rate
        + output_tokens * output_rate
        + cache_read_tokens * input_rate * 0.10
        + cache_write_tokens * input_rate * 1.25
    ) / 1_000_000


def anthropic_reservation_cost(input_tokens: int, max_output_tokens: int, model: str) -> float:
    """Return a safe upper bound after an Anthropic token-count preflight.

    Treating every counted input token as a cache write covers the most expensive
    possible input path; the request's max_tokens value bounds output cost.
    """
    try:
        input_rate, output_rate = ANTHROPIC_MODEL_PRICING[model]
    except KeyError as exc:
        raise ValueError(f"Unsupported Anthropic model: {model}") from exc
    return (
        input_tokens * input_rate * 1.25
        + max_output_tokens * output_rate
    ) / 1_000_000


def _effective_daily_limit(tier_row, *, is_byok: bool) -> int | None:
    if is_byok:
        return None
    if tier_row and tier_row["daily_limit"] is not None:
        return int(tier_row["daily_limit"])
    if tier_row and tier_row["tier"] == "pro":
        return None
    return 15


async def reserve_daily_ai_request(db_pool, user_id: str, *, is_byok: bool) -> dict:
    """Atomically consume one daily AI request for a signed-in user.

    The per-user advisory lock prevents two concurrent requests from both observing
    the same remaining allowance. BYOK and pro users are unlimited, but their usage
    is still counted for visibility and abuse monitoring.
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    async with db_pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(hashtext($1))", f"ai-quota:{user_id}")
            row = await conn.fetchrow(
                """SELECT tier, messages_today, last_message_date, daily_limit
                   FROM user_tiers WHERE user_id = $1""",
                user_id,
            )

            messages_today = 0
            if row and row["last_message_date"] == date.today():
                messages_today = int(row["messages_today"] or 0)
            daily_limit = _effective_daily_limit(row, is_byok=is_byok)
            if daily_limit is not None and messages_today >= daily_limit:
                raise HTTPException(status_code=429, detail=DAILY_LIMIT_DETAIL)

            await conn.execute(
                """INSERT INTO user_tiers (user_id, messages_today, last_message_date, updated_at)
                   VALUES ($1, 1, CURRENT_DATE, NOW())
                   ON CONFLICT (user_id) DO UPDATE SET
                       messages_today = CASE
                           WHEN user_tiers.last_message_date = CURRENT_DATE
                           THEN user_tiers.messages_today + 1
                           ELSE 1
                       END,
                       last_message_date = CURRENT_DATE,
                       updated_at = NOW()""",
                user_id,
            )

    return {
        "daily_limit": daily_limit,
        "messages_remaining": None if daily_limit is None else daily_limit - messages_today - 1,
    }


async def release_daily_ai_request(db_pool, user_id: str) -> None:
    """Return a reserved request when no paid provider completed successfully."""
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(hashtext($1))", f"ai-quota:{user_id}")
            await conn.execute(
                """UPDATE user_tiers
                   SET messages_today = GREATEST(messages_today - 1, 0), updated_at = NOW()
                   WHERE user_id = $1 AND last_message_date = CURRENT_DATE""",
                user_id,
            )


async def reserve_pool_funds(
    db_pool,
    amount: float,
    description: str,
    reference_id: str | None,
    *,
    entry_type: str = "ai_reservation",
) -> float:
    """Atomically reserve community-pool funds and return the remaining balance."""
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            return await reserve_pool_funds_on_connection(
                conn, amount, description, reference_id, entry_type=entry_type
            )


async def reserve_pool_funds_on_connection(
    conn,
    amount: float,
    description: str,
    reference_id: str | None,
    *,
    entry_type: str = "ai_reservation",
) -> float:
    """Reserve funds using the caller's transaction connection."""
    amount = abs(float(amount))
    if amount <= 0:
        raise ValueError("Pool reservation amount must be positive")

    await conn.execute("SELECT pg_advisory_xact_lock(1)")
    if entry_type == "ai_reservation" and reference_id:
        existing = await conn.fetchrow(
            """SELECT amount FROM pool_ledger
               WHERE reference_id = $1 AND entry_type = 'ai_reservation'
               ORDER BY id LIMIT 1""",
            reference_id,
        )
        if existing:
            row = await conn.fetchrow(
                "SELECT COALESCE(SUM(amount), 0) AS balance FROM pool_ledger"
            )
            return float(row["balance"])
    row = await conn.fetchrow("SELECT COALESCE(SUM(amount), 0) AS balance FROM pool_ledger")
    balance = float(row["balance"])
    if balance < amount:
        raise HTTPException(status_code=402, detail=POOL_EMPTY_DETAIL)
    await conn.execute(
        """INSERT INTO pool_ledger
           (amount, entry_type, description, reference_id, created_by)
           VALUES ($1, $2, $3, $4, 'system')""",
        -amount,
        entry_type,
        description,
        reference_id,
    )
    return balance - amount


async def lock_ai_request_on_connection(conn, reference_id: str) -> bool:
    """Serialize one request and report whether it was already finalized."""
    await conn.execute(
        "SELECT pg_advisory_xact_lock(hashtext($1))",
        f"ai-request:{reference_id}",
    )
    return bool(await conn.fetchval(
        """SELECT EXISTS(
               SELECT 1 FROM pool_ledger
               WHERE reference_id = $1 AND entry_type = 'ai_reservation_finalized'
           )""",
        reference_id,
    ))


async def mark_ai_request_finalized_on_connection(
    conn, reference_id: str, description: str
) -> None:
    """Write the durable terminal marker for a non-pool-funded request."""
    await conn.execute(
        """INSERT INTO pool_ledger
           (amount, entry_type, description, reference_id, created_by)
           VALUES (0, 'ai_reservation_finalized', $1, $2, 'system')
           ON CONFLICT (reference_id)
               WHERE entry_type = 'ai_reservation_finalized' AND reference_id IS NOT NULL
           DO NOTHING""",
        description,
        reference_id,
    )


async def settle_pool_reservation(
    db_pool,
    actual_amount: float,
    description: str,
    reference_id: str,
) -> float:
    """Idempotently reconcile a reservation to actual cost."""
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            return await settle_pool_reservation_on_connection(
                conn, actual_amount, description, reference_id
            )


async def settle_pool_reservation_on_connection(
    conn,
    actual_amount: float,
    description: str,
    reference_id: str,
    *,
    request_locked: bool = False,
) -> float:
    """Reconcile on the caller's transaction; repeated calls are safe no-ops."""
    if not request_locked and await lock_ai_request_on_connection(conn, reference_id):
        row = await conn.fetchrow("SELECT COALESCE(SUM(amount), 0) AS balance FROM pool_ledger")
        return float(row["balance"])

    await conn.execute("SELECT pg_advisory_xact_lock(1)")
    if request_locked and await conn.fetchval(
        """SELECT EXISTS(
               SELECT 1 FROM pool_ledger
               WHERE reference_id = $1 AND entry_type = 'ai_reservation_finalized'
           )""",
        reference_id,
    ):
        row = await conn.fetchrow("SELECT COALESCE(SUM(amount), 0) AS balance FROM pool_ledger")
        return float(row["balance"])

    reservation = await conn.fetchrow(
        """SELECT amount FROM pool_ledger
           WHERE reference_id = $1 AND entry_type = 'ai_reservation'
           ORDER BY id LIMIT 1""",
        reference_id,
    )
    if not reservation:
        raise ValueError(f"Pool reservation not found: {reference_id}")

    reserved_amount = abs(float(reservation["amount"]))
    actual_amount = max(0.0, float(actual_amount))
    adjustment = reserved_amount - actual_amount
    row = await conn.fetchrow("SELECT COALESCE(SUM(amount), 0) AS balance FROM pool_ledger")
    balance = float(row["balance"])
    if adjustment < 0 and balance < -adjustment:
        raise HTTPException(status_code=402, detail=POOL_EMPTY_DETAIL)
    if abs(adjustment) > 0.0000001:
        await conn.execute(
            """INSERT INTO pool_ledger
               (amount, entry_type, description, reference_id, created_by)
               VALUES ($1, 'ai_reservation_adjustment', $2, $3, 'system')""",
            adjustment,
            description,
            reference_id,
        )
    await mark_ai_request_finalized_on_connection(conn, reference_id, description)
    return balance + adjustment


async def cancel_pool_reservation(
    db_pool,
    description: str,
    reference_id: str,
) -> float:
    """Refund an unused reservation in full."""
    return await settle_pool_reservation(
        db_pool,
        0.0,
        description,
        reference_id,
    )


async def mark_pool_reservation_uncertain(
    db_pool, description: str, reference_id: str
) -> None:
    """Audit an uncertain provider outcome while retaining its reservation."""
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            await mark_pool_reservation_uncertain_on_connection(
                conn, description, reference_id
            )


async def mark_pool_reservation_uncertain_on_connection(
    conn, description: str, reference_id: str
) -> None:
    await conn.execute(
        """INSERT INTO pool_ledger
           (amount, entry_type, description, reference_id, created_by)
           VALUES (0, 'ai_reservation_uncertain', $1, $2, 'system')
           ON CONFLICT (reference_id)
               WHERE entry_type = 'ai_reservation_uncertain' AND reference_id IS NOT NULL
           DO NOTHING""",
        description,
        reference_id,
    )
