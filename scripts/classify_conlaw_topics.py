#!/usr/bin/env python3
"""Group a Constitutional Law casebook's cases by doctrine, using Tortwell's own taxonomy.

The chapter labels written here are Tortwell's independent doctrinal organization of
public-domain Supreme Court cases. No casebook's table of contents, chapter numbering,
page references, or arrangement is read or reproduced: the only inputs are the case name,
citation, and decision date already stored in our database.

The default mode is a read-only classification report. Use --apply only after the report
looks right; the write is a single transaction and is idempotent.

Example:
    python3 scripts/classify_conlaw_topics.py --casebook-id 1499
    python3 scripts/classify_conlaw_topics.py --casebook-id 1499 --apply
"""

from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
import json
import os
from pathlib import Path
import sys

import anthropic
import asyncpg
from dotenv import load_dotenv


MODEL = "claude-opus-5"
BATCH_SIZE = 25

# Tortwell's doctrinal taxonomy for Constitutional Law. The order is the sequence the
# doctrine is conventionally taught in — structure of government before individual
# rights — and drives the order the groups render in on the textbook page.
TOPICS: list[str] = [
    "Judicial Power and Justiciability",
    "Federal Legislative Power",
    "Federal Executive Power and Separation of Powers",
    "Federalism and Limits on State Power",
    "The Reconstruction Amendments and State Action",
    "Economic Liberties, Takings, and the Contracts Clause",
    "Substantive Due Process and Privacy",
    "Equal Protection",
    "Procedural Due Process",
    "Freedom of Speech and the Press",
    "Freedom of Association and Assembly",
    "The Religion Clauses",
    "Other Individual Rights",
]
TOPIC_RANK = {topic: rank for rank, topic in enumerate(TOPICS)}

SYSTEM_PROMPT = """You classify United States Supreme Court cases by constitutional doctrine \
for a free study site used by law students.

For each case you are given, pick the single topic from the provided list that best \
describes the doctrine the case is principally taught for in a Constitutional Law course. \
Judge by the case's own holding, not by where any particular casebook places it.

Rules:
- Choose exactly one topic per case, using the exact topic string from the list.
- When a case touches several doctrines, pick the one it is canonically assigned to. \
Lochner is substantive due process; Katzenbach v. McClung is federal legislative power; \
Shelby County is the Reconstruction Amendments.
- "Freedom of Association and Assembly" is only for cases whose holding turns on a right \
of association or assembly (NAACP v. Alabama, Roberts v. United States Jaycees). Compelled \
speech, expressive conduct, and press cases belong under "Freedom of Speech and the Press."
- "Other Individual Rights" is for rights cases that fit none of the earlier topics \
(for example the Second Amendment, or criminal-procedure rights reached on incorporation \
grounds). Use it sparingly.
- Also give 2 to 4 short concept tags naming the specific doctrines at issue \
(for example "dormant commerce clause", "strict scrutiny", "public forum"). Lowercase, \
no citations."""

RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "classifications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "case_name": {"type": "string"},
                    "topic": {"type": "string", "enum": TOPICS},
                    "concepts": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["index", "case_name", "topic", "concepts"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["classifications"],
    "additionalProperties": False,
}


async def load_cases(conn: asyncpg.Connection, casebook_id: int) -> list[asyncpg.Record]:
    return await conn.fetch(
        """
        SELECT cc.case_id, cc.case_name_in_book, cc.citation_in_book,
               c.decision_date, cc.chapter, cc.legal_concepts, cc.sort_order
        FROM casebook_cases cc
        JOIN cases c ON c.id = cc.case_id
        WHERE cc.casebook_id = $1
        ORDER BY cc.case_name_in_book
        """,
        casebook_id,
    )


def batch_prompt(rows: list[asyncpg.Record]) -> str:
    lines = []
    for index, row in enumerate(rows, start=1):
        year = row["decision_date"].year if row["decision_date"] else "n.d."
        lines.append(
            f"{index}. {row['case_name_in_book']}, {row['citation_in_book']} ({year})"
        )
    listing = "\n".join(lines)
    return (
        f"There are {len(rows)} cases below. Classify every one of them: return exactly "
        f"{len(rows)} entries, in the order given, echoing each case's number as `index` "
        "and its name as `case_name`. Do not stop early or summarize.\n\n"
        f"Topics:\n" + "\n".join(f"- {t}" for t in TOPICS) + f"\n\nCases:\n{listing}"
    )


NAME_STOP_WORDS = {
    "and", "association", "board", "city", "commission", "committee", "company",
    "county", "department", "district", "employees", "inc", "law", "of", "school",
    "state", "states", "the", "town", "united", "university", "village",
}


def name_tokens(name: str) -> set[str]:
    tokens = {t.strip(".,()'\"").lower() for t in name.split()}
    return {t for t in tokens if len(t) > 2 and t not in NAME_STOP_WORDS and not t.isdigit()}


def names_agree(echoed: str, expected: str) -> bool:
    """Guard against a batch coming back misaligned.

    What the model echoes is a paraphrase: sometimes the whole listing line with the
    citation appended, sometimes a long institutional caption shortened to how the case
    is actually cited ("Janus v. AFSCME"). Neither an exact match nor a similarity score
    survives that. Sharing a distinctive party name does, and combined with the in-order
    index echo it is enough to catch two cases being swapped.
    """
    return bool(name_tokens(echoed) & name_tokens(expected))


TOPIC_BY_FOLDED = {topic.lower(): topic for topic in TOPICS}


def canonical_topic(topic: str) -> str:
    """Map a returned topic back onto the taxonomy's own spelling.

    The schema pins the topic to an enum, but the model still title-cases connecting
    words ("Freedom Of Speech And The Press"), which would otherwise land those cases
    under a topic key the report and the sort order don't know about.
    """
    folded = " ".join(topic.split()).lower()
    if folded not in TOPIC_BY_FOLDED:
        raise RuntimeError(f"Topic outside the taxonomy: {topic!r}")
    return TOPIC_BY_FOLDED[folded]


def classify_batch(client: anthropic.Anthropic, rows: list[asyncpg.Record]) -> list[dict]:
    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        output_config={
            "effort": "medium",
            "format": {"type": "json_schema", "schema": RESULT_SCHEMA},
        },
        messages=[{"role": "user", "content": batch_prompt(rows)}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Classification refused: {response.stop_details}")
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)["classifications"]


def classify_with_split(
    client: anthropic.Anthropic, rows: list[asyncpg.Record], label: int
) -> list[dict]:
    """Classify a batch, halving it if the model returns the wrong number of entries.

    The model occasionally answers a long list with a single entry. Splitting recovers
    those without re-running the cases that already came back correctly, and the indices
    are rewritten so the caller still sees one entry per row in the original order.
    """
    entries = classify_batch(client, rows)
    if len(entries) == len(rows):
        return entries
    if len(rows) == 1:
        raise RuntimeError(f"Case at {label} returned {len(entries)} entries")

    print(
        f"    batch at {label} returned {len(entries)} of {len(rows)}; splitting",
        file=sys.stderr,
    )
    middle = len(rows) // 2
    first = classify_with_split(client, rows[:middle], label)
    second = classify_with_split(client, rows[middle:], label + middle)
    for offset, entry in enumerate(second, start=middle + 1):
        entry["index"] = offset
    return first + second


def classify_all(rows: list[asyncpg.Record]) -> dict[str, dict]:
    """Return {case_id: {"topic": str, "concepts": list[str]}} for every case.

    Case IDs are text in this schema, so they stay strings throughout — including
    as the keys of the cache file, which must round-trip to the same set.
    """
    client = anthropic.Anthropic()
    by_case: dict[str, dict] = {}

    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]
        print(
            f"  classifying {start + 1}-{start + len(batch)} of {len(rows)}...",
            file=sys.stderr,
        )
        entries = classify_with_split(client, batch, start + 1)
        for entry in entries:
            index = int(entry["index"])
            if not 1 <= index <= len(batch):
                raise RuntimeError(f"Batch at {start + 1} returned out-of-range index {index}")
            row = batch[index - 1]
            if not names_agree(entry["case_name"], row["case_name_in_book"]):
                raise RuntimeError(
                    f"Index {index} in batch at {start + 1} echoed "
                    f"{entry['case_name']!r} for {row['case_name_in_book']!r}"
                )
            concepts = [c.strip().lower() for c in entry["concepts"] if c.strip()]
            by_case[row["case_id"]] = {
                "topic": canonical_topic(entry["topic"]),
                "concepts": concepts[:4],
            }

    missing = {row["case_id"] for row in rows} - by_case.keys()
    if missing:
        raise RuntimeError(f"{len(missing)} cases were never classified: {sorted(missing)}")
    return by_case


def load_cached(path: Path | None, rows: list[asyncpg.Record]) -> dict[str, dict] | None:
    """Reuse a saved classification, but only if it covers exactly this set of cases."""
    if not path or not path.exists():
        return None
    cached = {
        case_id: {**value, "topic": canonical_topic(value["topic"])}
        for case_id, value in json.loads(path.read_text()).items()
    }
    if cached.keys() != {row["case_id"] for row in rows}:
        print(f"{path} does not match this casebook's cases; reclassifying", file=sys.stderr)
        return None
    return cached


def plan_updates(
    rows: list[asyncpg.Record], classified: dict[str, dict]
) -> list[tuple[str, str, list[str], int]]:
    """Build the (case_id, topic, concepts, sort_order) rows to write.

    sort_order is topic rank * 1000 plus the case's alphabetical position within its
    topic, so the page renders the groups in doctrinal order and each group alphabetically.
    """
    grouped: dict[str, list[asyncpg.Record]] = defaultdict(list)
    for row in rows:
        grouped[classified[row["case_id"]]["topic"]].append(row)

    unknown = sorted(set(grouped) - set(TOPICS))
    if unknown:
        raise RuntimeError(f"Model returned topics outside the taxonomy: {unknown}")

    updates = []
    for topic in TOPICS:
        members = sorted(grouped.get(topic, []), key=lambda r: r["case_name_in_book"])
        for position, row in enumerate(members):
            sort_order = TOPIC_RANK[topic] * 1000 + position
            updates.append(
                (row["case_id"], topic, classified[row["case_id"]]["concepts"], sort_order)
            )

    if len(updates) != len(rows):
        raise RuntimeError(f"Planned {len(updates)} updates for {len(rows)} cases")
    return updates


def print_report(
    rows: list[asyncpg.Record],
    classified: dict[str, dict],
    updates: list[tuple[str, str, list[str], int]],
) -> None:
    by_id = {row["case_id"]: row for row in rows}
    grouped: dict[str, list[asyncpg.Record]] = defaultdict(list)
    for case_id, topic, _concepts, _sort in updates:
        grouped[topic].append(by_id[case_id])

    print()
    for topic in TOPICS:
        members = grouped.get(topic, [])
        print(f"{topic} — {len(members)}")
        for row in members:
            concepts = ", ".join(classified[row["case_id"]]["concepts"])
            print(f"    {row['case_name_in_book']} ({row['citation_in_book']}) [{concepts}]")
        print()

    changed = sum(
        1
        for case_id, topic, concepts, sort_order in updates
        if by_id[case_id]["chapter"] != topic
        or list(by_id[case_id]["legal_concepts"] or []) != concepts
        or by_id[case_id]["sort_order"] != sort_order
    )
    print(f"{len(updates)} cases across {sum(1 for t in TOPICS if grouped.get(t))} topics; "
          f"{changed} rows would change.")


async def apply_updates(
    conn: asyncpg.Connection,
    casebook_id: int,
    updates: list[tuple[str, str, list[str], int]],
) -> None:
    async with conn.transaction():
        for case_id, topic, concepts, sort_order in updates:
            await conn.execute(
                """
                UPDATE casebook_cases
                SET chapter = $3, legal_concepts = $4, sort_order = $5,
                    updated_at = NOW()
                WHERE casebook_id = $1 AND case_id = $2
                """,
                casebook_id,
                case_id,
                topic,
                concepts,
                sort_order,
            )


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--casebook-id", type=int, required=True)
    parser.add_argument("--apply", action="store_true", help="write the classification")
    parser.add_argument(
        "--cache",
        type=Path,
        help="JSON file to read the classification from, or write it to after a run",
    )
    parser.add_argument(
        "--database-url-var",
        default="PROD_DATABASE_URL",
        help="environment variable holding the connection string",
    )
    args = parser.parse_args()

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    database_url = os.getenv(args.database_url_var)
    if not database_url:
        print(f"{args.database_url_var} is not set", file=sys.stderr)
        return 1
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set", file=sys.stderr)
        return 1

    conn = await asyncpg.connect(database_url)
    try:
        rows = await load_cases(conn, args.casebook_id)
        if not rows:
            print(f"Casebook {args.casebook_id} has no linked cases", file=sys.stderr)
            return 1
        print(f"Loaded {len(rows)} cases from casebook {args.casebook_id}", file=sys.stderr)

        classified = load_cached(args.cache, rows)
        if classified is None:
            classified = classify_all(rows)
            if args.cache:
                args.cache.write_text(
                    json.dumps(classified, indent=2)
                )
                print(f"Cached classification to {args.cache}", file=sys.stderr)
        else:
            print(f"Reusing cached classification from {args.cache}", file=sys.stderr)

        updates = plan_updates(rows, classified)
        print_report(rows, classified, updates)

        if not args.apply:
            print("\nDry run. Re-run with --apply to write.")
            return 0

        await apply_updates(conn, args.casebook_id, updates)
        print(f"\nApplied {len(updates)} classifications to casebook {args.casebook_id}.")
        print("The textbook detail cache expires on its own TTL; a redeploy clears it now.")
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
