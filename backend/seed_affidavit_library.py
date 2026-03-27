"""
Seed the library with educational resources on affidavit drafting.
These are original syntheses of well-established legal principles.

Usage:
  python seed_affidavit_library.py

Requires DATABASE_URL environment variable.
"""

import asyncio
import os
import json
import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL")

LIBRARY_DOCS = [
    {
        "title": "Affidavit Legal Standards (Federal & Ohio)",
        "doc_type": "standard",
        "jurisdiction": "federal",
        "tool_type": "affidavit",
        "content": """AFFIDAVIT LEGAL STANDARDS

I. FEDERAL REQUIREMENTS — FRCP 56(c)(4)

An affidavit or declaration used to support or oppose a motion "must be made on personal knowledge, set out facts that would be admissible in evidence, and show that the affiant or declarant is competent to testify on the matters stated." Fed. R. Civ. P. 56(c)(4).

Three Requirements:
1. PERSONAL KNOWLEDGE — The affiant must have firsthand knowledge of the facts stated. This means the affiant personally observed, experienced, or participated in the events described. Information obtained solely from others (hearsay) generally does not satisfy the personal knowledge requirement.

2. ADMISSIBLE EVIDENCE — The facts set forth must be of a type that would be admissible in evidence at trial. This does not mean the affidavit itself must be in admissible form, but the content must be reducible to admissible evidence. Lujan v. National Wildlife Federation, 497 U.S. 871, 888 (1990).

3. COMPETENCY — The affiant must be competent to testify to the matters stated. The affidavit must affirmatively demonstrate this competency by explaining the affiant's relationship to the facts.

II. OHIO REQUIREMENTS — Civ.R. 56(E)

Ohio's standard mirrors the federal rule: "Supporting and opposing affidavits shall be made on personal knowledge, shall set forth such facts as would be admissible in evidence, and shall show affirmatively that the affiant is competent to testify to the matters stated in the affidavit." Ohio Civ.R. 56(E).

Under Dresher v. Burt, 75 Ohio St.3d 280, 293 (1996), the Ohio Supreme Court held that the moving party bears an initial burden of informing the trial court of the basis for the motion and identifying those portions of the record that demonstrate the absence of a genuine issue of material fact. Affidavits are one of the materials specifically identified in Civ.R. 56(C) as proper evidentiary support.

III. 28 U.S.C. § 1746 — UNSWORN DECLARATIONS

In federal practice, an unsworn declaration may be used instead of a traditional sworn affidavit if it includes the statement: "I declare (or certify, verify, or state) under penalty of perjury that the foregoing is true and correct. Executed on [date]."

This is particularly useful when a notary public is not readily available. The declaration has the same force and effect as an affidavit.

IV. SANCTIONS — FRCP 56(h)

If the court is satisfied that an affidavit is submitted in bad faith or solely for delay, the court may order the submitting party to pay the reasonable expenses, including attorney's fees. After notice and a reasonable time to respond, the court may also hold the offending party or attorney in contempt. Fed. R. Civ. P. 56(h).

V. EVIDENCE RULES APPLICABLE TO AFFIDAVITS

A. Hearsay: Affidavits must not contain hearsay unless a recognized exception applies. Fed. R. Evid. 802. Common exceptions relevant to affidavits:
   - Business records (Fed. R. Evid. 803(6))
   - Present sense impression (Fed. R. Evid. 803(1))
   - Excited utterance (Fed. R. Evid. 803(2))
   - Opposing party statements (Fed. R. Evid. 801(d)(2))

B. Opinion testimony: Lay witnesses may offer opinions under Fed. R. Evid. 701 only if rationally based on their perception and helpful to determining a fact in issue.

C. Self-serving affidavits: A party's own affidavit based on personal knowledge is admissible and may create a genuine issue of material fact, even if "self-serving." S.E.C. v. Contreras, 398 F.3d 1289, 1294 (11th Cir. 2005). However, conclusory or vague allegations will not suffice.
""",
        "metadata": {
            "description": "Comprehensive legal standards for affidavits under federal and Ohio law.",
            "source": "Original synthesis of established evidence and civil procedure principles"
        }
    },
    {
        "title": "Affidavit Structure & Drafting Guide",
        "doc_type": "template",
        "jurisdiction": "federal",
        "tool_type": "affidavit",
        "content": """AFFIDAVIT STRUCTURE AND DRAFTING GUIDE

I. REQUIRED COMPONENTS

A. Caption
- Full case caption matching the court filing
- Case number and court name

B. Title
- "AFFIDAVIT OF [FULL NAME OF AFFIANT]"
- Centered, bold

C. Opening / Identity Paragraph
- Affiant's full legal name
- Age (if relevant to competency)
- Residence or place of business
- Must establish that affiant is of legal age and competent to make the affidavit

D. Competency / Personal Knowledge Paragraph
- HOW the affiant knows the facts stated
- Relationship to the case, the parties, or the events
- Employment, position, or role that gives them knowledge
- Example: "I am employed by ZAMR Corp. as a warehouse supervisor. In my capacity as supervisor, I have personal knowledge of the company's employee policies, work schedules, and the events described below."

E. Numbered Factual Paragraphs
- Group related facts into coherent narrative paragraphs
- A single paragraph may cover multiple related facts on the same topic
- Must be based on personal knowledge
- Specific: dates, times, locations, names, amounts
- Declarative first-person statements: "I observed..." "I was present when..."
- Do NOT argue legal conclusions: Say "The light was red" not "The defendant was negligent"

F. Closing Paragraph
- "I have read this affidavit and the statements contained herein are true and correct to the best of my knowledge and belief."
- OR: "Further affiant sayeth naught." (traditional closing)

G. Signature Line
- Affiant's signature line with printed name below
- Date

H. Jurat (Notary Block) — if sworn affidavit:
   STATE OF _________ )
                      ) ss:
   COUNTY OF ________ )

   Subscribed and sworn to before me this ___ day of __________, ____.

   _________________________
   Notary Public
   My commission expires: _________

I. Alternative: 28 U.S.C. § 1746 Declaration
   Instead of notarization, end with:
   "I declare under penalty of perjury that the foregoing is true and correct.
    Executed on [date]."

II. DRAFTING BEST PRACTICES

A. Be Specific, Not General
   BAD: "The employee often left work early."
   GOOD: "On March 5, 2024, I personally observed Hayes leave the ZAMR Corp. warehouse at 2:15 p.m., approximately two hours and forty-five minutes before the end of his scheduled 5:00 p.m. shift."

B. Establish Knowledge Foundation First
   Before stating facts about a topic, explain how you know. If you supervised someone, state that before describing their behavior.

C. Group Related Facts
   Each paragraph should address a single topic or theme. Multiple related facts may appear in one paragraph. This follows the standard practice shown in Writing for Litigation (Appendix P).

D. Avoid Legal Conclusions
   BAD: "Hayes was acting outside the scope of his employment."
   GOOD: "Hayes's assigned delivery route for March 5, 2024 was to proceed directly from the warehouse at 123 Industrial Blvd. to the client at 456 Commerce Drive, a route that does not pass through the intersection of Main and Oak where the accident occurred."

E. Avoid Hearsay
   BAD: "Jones told me that Hayes was texting while driving."
   GOOD: "I personally observed Hayes using his cellular phone while operating the delivery van on February 28, 2024."

F. Use Active Voice
   BAD: "The delivery was supposed to be made by Hayes."
   GOOD: "I assigned Hayes to make the delivery to ABC Corp. on March 5, 2024."

G. Cross-Reference Records When Available
   "As reflected in the ZAMR Corp. delivery log for March 5, 2024, which I maintain in the ordinary course of business, Hayes's assigned route was..."

III. COMMON PITFALLS

1. Conclusory statements — stating conclusions without underlying facts
2. Hearsay — repeating what others said without an exception
3. Opinion testimony — offering opinions beyond lay witness capacity
4. Lack of personal knowledge foundation — not explaining HOW you know
5. Multiple facts per paragraph — makes it hard to address specific disputes
6. Argumentative language — this is an affidavit, not a brief
7. Vague time references — "around that time" vs. "at approximately 3:15 p.m."
8. Failure to attach exhibits — if referencing documents, attach them

IV. N.D. OHIO LOCAL RULES

Under the Local Civil Rules for the Northern District of Ohio:
- L.R. 7.1: All motions must include a brief in support. Affidavits are filed as exhibits to the motion.
- L.R. 56.1: Requires a "Statement of Material Facts" with citations to evidence. Each fact should be supported by specific citations to affidavits, depositions, or other evidence.
- Affidavits should be filed as separate documents attached to the motion, not embedded within the brief.
""",
        "metadata": {
            "description": "Practical guide for structuring and drafting affidavits with examples and pitfalls.",
            "source": "Original synthesis of legal writing principles and court requirements"
        }
    },
    {
        "title": "Affidavit Drafting Checklist",
        "doc_type": "standard",
        "jurisdiction": "federal",
        "tool_type": "affidavit",
        "content": """AFFIDAVIT DRAFTING CHECKLIST

Use this checklist to verify your affidavit before filing:

FOUNDATION
[ ] Affiant's full legal name is stated
[ ] Affiant's competency to testify is established
[ ] Affiant's personal knowledge basis is explained
[ ] Affiant's relationship to the case/parties is clear

CONTENT
[ ] Each paragraph groups related facts on a common topic
[ ] Every fact is based on personal knowledge (not hearsay)
[ ] Facts are specific: dates, times, locations, names
[ ] No legal conclusions or argumentative statements
[ ] No opinions beyond lay witness capacity
[ ] First person, active voice throughout
[ ] Facts are stated in admissible form
[ ] Cross-references to attached exhibits where appropriate

FORMAT
[ ] Caption matches the court filing
[ ] Title: "AFFIDAVIT OF [FULL NAME]" centered and bold
[ ] Paragraphs are numbered sequentially
[ ] Double-spaced, 12pt Times New Roman, 1-inch margins
[ ] Signature line with printed name
[ ] Jurat/notary block OR 28 U.S.C. § 1746 declaration
[ ] Date of execution

CLOSING
[ ] Closing paragraph affirming truth of statements
[ ] All referenced exhibits are attached
[ ] Affidavit is consistent with deposition testimony (if any)
[ ] No contradictions with prior sworn statements

OHIO / N.D. OHIO SPECIFIC
[ ] Complies with Ohio Civ.R. 56(E) requirements
[ ] Filed as separate exhibit per L.R. 56.1
[ ] Supports specific numbered facts in Statement of Material Facts
""",
        "metadata": {
            "description": "Step-by-step checklist for reviewing affidavits before submission.",
            "source": "Original synthesis of affidavit requirements and best practices"
        }
    },
]


async def seed_library():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        for doc in LIBRARY_DOCS:
            # Check if already exists by title
            existing = await conn.fetchrow(
                "SELECT id FROM msj_library WHERE title = $1", doc["title"]
            )
            if existing:
                print(f"  Already exists: {doc['title']} (id={existing['id']})")
                continue

            row = await conn.fetchrow(
                """INSERT INTO msj_library (title, doc_type, jurisdiction, content, metadata, tool_type, created_by)
                   VALUES ($1, $2, $3, $4, $5, $6, 'system')
                   RETURNING id""",
                doc["title"],
                doc["doc_type"],
                doc.get("jurisdiction"),
                doc["content"],
                json.dumps(doc.get("metadata", {})),
                doc.get("tool_type", "affidavit"),
            )
            print(f"  Created: {doc['title']} (id={row['id']})")
    finally:
        await conn.close()

    print("Done seeding affidavit library.")


if __name__ == "__main__":
    asyncio.run(seed_library())
