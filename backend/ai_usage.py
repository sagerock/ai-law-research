"""Atomic quota and community-pool reservations for paid AI requests."""

from __future__ import annotations

from datetime import date

from fastapi import HTTPException


POOL_EMPTY_DETAIL = "Community AI pool is empty. Donate to refill it!"
DAILY_LIMIT_DETAIL = (
    "You've reached today's free limit. Add your own API key for unlimited use, "
    "or come back tomorrow."
)


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
    amount = abs(float(amount))
    if amount <= 0:
        raise ValueError("Pool reservation amount must be positive")

    async with db_pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(1)")
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


async def settle_pool_reservation(
    db_pool,
    reserved_amount: float,
    actual_amount: float,
    description: str,
    reference_id: str | None,
) -> float:
    """Reconcile a reservation to actual cost without allowing an overdraft."""
    reserved_amount = abs(float(reserved_amount))
    actual_amount = max(0.0, float(actual_amount))
    adjustment = reserved_amount - actual_amount

    async with db_pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(1)")
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
            return balance + adjustment


async def cancel_pool_reservation(
    db_pool,
    reserved_amount: float,
    description: str,
    reference_id: str | None,
) -> float:
    """Refund an unused reservation in full."""
    return await settle_pool_reservation(
        db_pool,
        reserved_amount,
        0.0,
        description,
        reference_id,
    )
