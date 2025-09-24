#!/usr/bin/env python3
import asyncpg
import asyncio

async def reset():
    conn = await asyncpg.connect('postgresql://legal_user:legal_pass@localhost:5432/legal_research')
    await conn.execute('DROP TABLE IF EXISTS cases, courts, citations, test_cases CASCADE')
    await conn.close()
    print("Tables dropped")

asyncio.run(reset())