#!/home/sage/.venvs/lawdata/bin/python
"""Create internal case stubs for authority entries displayed by one casebook.

    python stub_casebook_citers.py <casebook_id>
"""
import asyncio
import sys

import asyncpg

import stub_citers


async def casebook_ids(casebook_id):
    conn = await asyncpg.connect(stub_citers.prod_url())
    try:
        rows = await conn.fetch(
            """SELECT case_id FROM casebook_cases
               WHERE casebook_id = $1 AND case_id ~ '^[0-9]+$'
               ORDER BY sort_order NULLS LAST, case_id""",
            casebook_id,
        )
        return [int(row["case_id"]) for row in rows]
    finally:
        await conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: stub_casebook_citers.py <casebook_id>")
        raise SystemExit(1)
    ids = asyncio.run(casebook_ids(int(sys.argv[1])))
    asyncio.run(stub_citers.run(ids))
