#!/usr/bin/env python3
"""Apply the human semantic review gate to the 10-case source-link pilot."""

import asyncio
import os

import asyncpg


REJECTED = {
    "84759": "Marbury: majority-reasoning claims cite incomplete passages for ministerial duty, mandamus, and executive control.",
    "104357": "Hickman: rule overstates mental-impression protection and several claims have incomplete source linkage.",
    "107082": "Griswold: majority reasoning conflates Douglas's analysis with the Ninth Amendment concurrence.",
    "107024": "Hanna: facts overstate Massachusetts service law and a rule claim lacks support in its assigned passages.",
    "118144": "Glucksberg: historical and procedural claims are not fully supported by their assigned passages.",
}


async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        async with conn.transaction():
            for case_id, reason in REJECTED.items():
                content_hash = await conn.fetchval(
                    """SELECT content_hash FROM structured_summary_candidates
                       WHERE case_id = $1 AND provider = 'claude'""",
                    case_id,
                )
                await conn.execute(
                    """INSERT INTO structured_summary_failures
                       (case_id, provider, content_hash, stage, error)
                       VALUES ($1, 'claude', $2, 'semantic_review', $3)""",
                    case_id, content_hash, reason,
                )
                await conn.execute(
                    "DELETE FROM structured_summary_candidates WHERE case_id = $1 AND provider = 'claude'",
                    case_id,
                )
                print(f"rejected={case_id}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
