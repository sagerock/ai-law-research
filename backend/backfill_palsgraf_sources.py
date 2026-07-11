"""One-case pilot backfill for source-linked AI briefs."""

import asyncio
import math
import os
import re
from collections import Counter

import asyncpg
import boto3

from opinion_passages import build_opinion_passages


CASE_ID = "3602780"
QUERIES = {
    "facts": [
        "guards helped the passenger board and dislodged the package onto the rails",
        "fireworks when they fell exploded shock threw down scales at the other end of the platform many feet away",
    ],
    "issue": [
        "risk reasonably perceived defines duty to persons within the range of apprehension",
    ],
    "holding": [
        "conduct was not a wrong in relation to the plaintiff standing far away",
        "judgment reversed and complaint dismissed",
    ],
    "reasoning": [
        "risk reasonably perceived defines the duty to be obeyed and imports relation",
        "law of causation remote or proximate is foreign when no duty is owed",
        "due care is a duty to protect society not A B or C alone",
        "explosion direct cause substantial factor natural continuous sequence direct connection concussion smashed weighing machine",
    ],
}
WORD_RE = re.compile(r"[a-z][a-z'-]{2,}")


def cosine(left: str, right: str) -> float:
    a, b = Counter(WORD_RE.findall(left.lower())), Counter(WORD_RE.findall(right.lower()))
    numerator = sum(a[word] * b[word] for word in set(a) & set(b))
    denominator = math.sqrt(sum(value * value for value in a.values())) * math.sqrt(
        sum(value * value for value in b.values())
    )
    return numerator / denominator if denominator else 0


def read_s3_opinion() -> str:
    bucket = os.getenv("OPINIONS_BUCKET", "lawstudygroup-opinions")
    response = boto3.client("s3").get_object(Bucket=bucket, Key=f"opinions/{CASE_ID}.txt")
    return response["Body"].read().decode("utf-8")


async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        content = await conn.fetchval("SELECT content FROM cases WHERE id = $1", CASE_ID)
        if not content:
            content = await asyncio.to_thread(read_s3_opinion)
        content_hash, passages = build_opinion_passages(content)

        async with conn.transaction():
            await conn.execute("DELETE FROM opinion_passages WHERE case_id = $1", CASE_ID)
            await conn.executemany(
                """INSERT INTO opinion_passages
                   (case_id, content_hash, passage_id, ordinal, opinion_part, text)
                   VALUES ($1, $2, $3, $4, $5, $6)""",
                [
                    (CASE_ID, content_hash, passage["id"], passage["ordinal"],
                     passage["opinion_part"], passage["text"])
                    for passage in passages
                ],
            )
            for section, queries in QUERIES.items():
                for query in queries:
                    best = max(passages, key=lambda passage: cosine(query, passage["text"]))
                    score = cosine(query, best["text"])
                    await conn.execute(
                        """INSERT INTO summary_source_links
                           (case_id, section_key, content_hash, passage_id, confidence, method)
                           VALUES ($1, $2, $3, $4, $5, 'pilot-reviewed')
                           ON CONFLICT (case_id, section_key, content_hash, passage_id)
                           DO UPDATE SET confidence = GREATEST(summary_source_links.confidence, EXCLUDED.confidence)""",
                        CASE_ID, section, content_hash, best["id"], score,
                    )
                    print(section, best["id"], f"{score:.2f}", best["text"][:100])
        print(f"Stored {len(passages)} passages for {CASE_ID} ({content_hash[:12]})")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
