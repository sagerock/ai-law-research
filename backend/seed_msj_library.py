"""
Seed the MSJ library with original educational resources on summary judgment law and motion drafting.
These are original syntheses of well-established legal principles, not copies of any textbook.

Usage:
  python seed_msj_library.py

Requires DATABASE_URL environment variable.
"""

import asyncio
import os
import json
import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL")

LIBRARY_DOCS = [
    {
        "title": "Summary Judgment Legal Standard (FRCP Rule 56)",
        "doc_type": "standard",
        "jurisdiction": "federal",
        "content": """SUMMARY JUDGMENT LEGAL STANDARD

I. THE RULE 56 STANDARD

Summary judgment shall be granted when "there is no genuine dispute as to any material fact and the movant is entitled to judgment as a matter of law." Fed. R. Civ. P. 56(a).

This standard has three components:
1. No genuine dispute — The evidence must be so one-sided that no reasonable fact-finder could find for the non-movant.
2. Material fact — A fact is "material" if it could affect the outcome of the case under the governing substantive law. Only disputes about material facts preclude summary judgment.
3. Entitled to judgment as a matter of law — Once undisputed facts are established, the court applies the substantive law to determine whether the movant wins.

A dispute about the applicable law does NOT preclude summary judgment. Legal disputes are decided by judges, not juries. Summary judgment can be granted even when the legal question is novel or difficult.

II. BURDEN FRAMEWORK

The movant's burden depends on who bears the burden of proof at trial:

A. When the Movant Has the Trial Burden (e.g., Plaintiff Moving on Own Claim)
The movant must show that the evidence on every element of the claim is so strong that no reasonable fact-finder could decide against them. This is a heavy burden — the movant must essentially prove the case on paper.

B. When the Movant Does NOT Have the Trial Burden (e.g., Defendant Moving Against Plaintiff's Claim)
The movant has two options:

Option 1 — DISPROOF: Affirmatively disprove an essential element of the non-movant's claim with evidence. Example: Proving that no product made by the defendant was ever present at the plaintiff's workplace.

Option 2 — ABSENCE OF PROOF: Show that the non-movant lacks sufficient evidence to prove an essential element of their claim. The movant must identify specific portions of the record (depositions, interrogatory answers, admissions) demonstrating the absence of evidence — a bare assertion that the opponent "has no evidence" is insufficient and would convert summary judgment into "a tool for harassment." Celotex Corp. v. Catrett, 477 U.S. 317, 332 (1986).

III. BURDEN SHIFTING

Once the movant meets the initial burden, the burden shifts to the non-movant, who must:
- Identify specific facts in the record creating a genuine dispute
- Cannot rest on mere allegations or denials in the pleadings
- Must go beyond the pleadings and identify admissible evidence
- "An adverse party may not rest upon the mere allegations or denials of his pleading" — the response must set forth specific facts showing a genuine issue for trial

IV. THE "GENUINE" DISPUTE REQUIREMENT

A dispute is "genuine" if "the evidence is such that a reasonable jury could return a verdict for the nonmoving party." Anderson v. Liberty Lobby, Inc., 477 U.S. 242, 248 (1986).

Key principles:
- The court does NOT weigh evidence or assess credibility
- The court must draw all reasonable inferences in favor of the non-movant
- The court does not decide disputed facts — it determines whether a dispute exists
- The mere existence of some evidence is not enough; there must be enough for a reasonable fact-finder to rule for the non-movant
- The standard of proof matters: if the claim requires clear and convincing evidence, the summary judgment inquiry asks whether a reasonable jury could find by that standard

V. EVIDENCE ON SUMMARY JUDGMENT

A. What May Be Considered
Rule 56(c)(1)(A) lists: depositions, documents, electronically stored information, affidavits or declarations, stipulations, admissions, interrogatory answers, or other materials.

B. Admissibility Requirement
Evidence must be in a form that "would be admissible in evidence" at trial, or the proponent must show it can be reduced to admissible form. Rule 56(c)(2).

Key points on evidence:
- Hearsay is generally inadmissible (e.g., "I heard someone say...")
- Evidence must be based on personal knowledge
- Speculation is insufficient (e.g., "I guessed that...")
- Self-serving declarations ARE admissible if made on personal knowledge — bias and self-interest go to weight, which is for the jury, not the judge on summary judgment
- Affidavits/declarations are permitted even though the witness would need to testify live at trial — this exception keeps summary judgment "summary"
- Unsworn pleadings generally cannot serve as evidence for the party who filed them (they are promises, not proof)

C. The "Reducible to Admissible Form" Standard
Evidence need not be in trial-admissible form at the summary judgment stage, so long as it is clear the substance could be presented in admissible form at trial. For example, a witness's letter describing relevant facts may be considered if the witness could testify live to the same facts at trial.

VI. KEY SUPREME COURT TRILOGY

Three 1986 cases define modern summary judgment practice:

1. Celotex Corp. v. Catrett, 477 U.S. 317 (1986)
- Established that a defendant need not produce affirmative evidence negating the plaintiff's case
- The movant can point to the absence of evidence supporting the non-movant's claim
- But must do more than make a conclusory assertion — must identify portions of the record
- Plaintiff must then come forward with specific evidence or face judgment

2. Anderson v. Liberty Lobby, Inc., 477 U.S. 242 (1986)
- "Genuine" dispute means sufficient evidence for a reasonable jury to find for the non-movant
- The applicable standard of proof affects the summary judgment inquiry
- Summary judgment is not a "disfavored procedural shortcut" but an integral part of the Rules

3. Matsushita Electric Industrial Co. v. Zenith Radio Corp., 475 U.S. 574 (1986)
- The non-movant must show more than "some metaphysical doubt" about material facts
- Evidence must be significantly probative, not merely colorable
- Inferences drawn by the non-movant must be reasonable, not speculative

VII. PARTIAL SUMMARY JUDGMENT

Under Rule 56(a), a court may grant summary judgment on part of a claim or defense. This is useful to:
- Narrow the issues for trial
- Resolve undisputed elements while leaving genuinely disputed ones for the jury
- Eliminate meritless claims or defenses before trial

VIII. TIMING

A party may file a motion for summary judgment at any time until 30 days after the close of all discovery, unless the court orders otherwise or local rules specify a different deadline. Rule 56(b).

If the non-movant shows by affidavit or declaration that it cannot present facts essential to justify its opposition, the court may defer consideration, allow additional discovery, or deny the motion. Rule 56(d).
""",
        "metadata": {
            "description": "Comprehensive overview of Rule 56 summary judgment standards, burden framework, evidence requirements, and the Celotex trilogy.",
            "source": "Original synthesis of established federal civil procedure principles"
        }
    },
    {
        "title": "Motion for Summary Judgment: Structure & Drafting Guide",
        "doc_type": "template",
        "jurisdiction": None,  # Applies to all jurisdictions
        "content": """MOTION FOR SUMMARY JUDGMENT: STRUCTURE & DRAFTING GUIDE

This guide covers the standard components and drafting principles for a motion for summary judgment. Always check local rules for jurisdiction-specific requirements (especially page limits and formatting).

I. COMPONENTS OF A MOTION FOR SUMMARY JUDGMENT

A. Caption
The caption must include the court name, parties, and case number. Follow the format required by local rules.

B. Title
Identify who is filing and what relief is sought. Examples:
- "Defendant's Motion for Summary Judgment"
- "Plaintiff's Motion for Partial Summary Judgment on Count I (Breach of Contract)"
Keep the title as short as the situation allows while being specific enough to identify the motion.

C. Introduction / Opening
Answer the question: "What is this motion about?" In 1-2 paragraphs:
- State the relief sought
- Briefly explain what the case concerns
- Preview why summary judgment is appropriate
- Give the court enough context to understand how this motion fits the case

D. Statement of Undisputed Material Facts
This is critical and distinctive to summary judgment motions:
- Number each fact separately
- Each fact must cite to specific evidence in the record (depositions, affidavits, documents)
- Include only facts that are MATERIAL — facts that matter under the applicable substantive law
- State facts objectively; let the facts speak for themselves
- Many jurisdictions require a separate Statement of Undisputed Material Facts document
- The opposing party will typically file a response admitting or denying each numbered fact

Format example:
  1. On March 15, 2024, Plaintiff entered into a written agreement with Defendant. (Johnson Dep. 45:12-18, Ex. A.)
  2. The agreement required Plaintiff to deliver 500 units by June 1, 2024. (Agreement § 3.1, Ex. B.)
  3. Plaintiff did not deliver any units by June 1, 2024. (Johnson Dep. 67:3-8; Plaintiff's Resp. to Interrog. No. 5, Ex. C.)

E. Motion Standard
State the legal standard for summary judgment. For federal court:
"Summary judgment is appropriate when 'there is no genuine dispute as to any material fact and the movant is entitled to judgment as a matter of law.' Fed. R. Civ. P. 56(a). The movant bears the initial burden of demonstrating the absence of a genuine dispute of material fact. Celotex Corp. v. Catrett, 477 U.S. 317, 323 (1986). If the movant meets this burden, the burden shifts to the non-movant to identify specific facts showing a genuine dispute for trial. Anderson v. Liberty Lobby, Inc., 477 U.S. 242, 248 (1986)."
Cite binding authority from the applicable jurisdiction.

F. Argument
This is the centerpiece. Organize around the legal issues:

1. Provide a roadmap paragraph identifying the elements of the claim/defense and previewing which elements are at issue.

2. For each issue:
   a. State your conclusion (framed in case-specific terms)
   b. State and explain the governing legal rule
   c. Apply the rule to your undisputed facts
   d. Anticipate and address the opponent's best counterarguments
   e. Restate your conclusion

3. Show how the conclusions on each issue add up to the overall result.

Drafting principles:
- Every fact relied upon must appear in the Statement of Facts with record citations
- Every legal proposition must cite binding authority
- Expand or collapse legal analysis as needed — don't belabor settled points; develop contested ones
- Be direct and concise — trial judges are busy
- Avoid conclusory characterizations; state facts that lead to the desired inference
- Write persuasively without appearing to advocate — let the law and facts do the work

G. Conclusion / Prayer for Relief
State the specific relief sought. Preview the language you want in the court's order:
"For the foregoing reasons, Defendant respectfully requests that this Court grant summary judgment in Defendant's favor on all claims and enter judgment dismissing Plaintiff's Complaint with prejudice."

H. Signature Block and Certificate of Service

II. SUPPORTING EVIDENCE

Attach all evidence supporting each fact in the Statement of Undisputed Material Facts:
- Relevant deposition excerpts (include cover page, reporter's certification, and cited pages)
- Affidavits or declarations (must be made on personal knowledge, setting out facts that would be admissible)
- Documentary exhibits (contracts, emails, business records)
- Interrogatory answers and responses to requests for admission
- Each exhibit should be labeled and referenced in the motion

III. STRATEGIC CONSIDERATIONS

A. When to File
- When discovery produces case-ending evidence (e.g., opposing party's admission negating an element)
- When the case turns on a pure legal question with undisputed facts
- When partial summary judgment can narrow issues and encourage settlement
- Be realistic about chances — drafting a substantive motion is expensive

B. Common Pitfalls
- Failing to identify the applicable substantive law (you cannot analyze materiality without it)
- Making conclusory assertions instead of citing specific record evidence
- Relying on inadmissible evidence (hearsay, speculation, unauthenticated documents)
- Ignoring evidence favorable to the non-movant (courts draw inferences against movant)
- Overstating the record or mischaracterizing evidence
- Filing when genuine factual disputes clearly exist (wastes court resources and credibility)

C. Responding to Summary Judgment
When opposing a motion, the non-movant must:
- File a response to the Statement of Undisputed Facts (admitting or denying each, with citations)
- Identify specific evidence creating genuine disputes on material facts
- Cannot rest on pleading allegations alone
- May file a Rule 56(d) affidavit if more discovery is needed to respond
- Should identify all reasonable inferences favoring the non-movant's position

IV. LOCAL RULE CHECKLIST

Before filing, verify:
□ Page/word limit for the motion
□ Whether a separate Statement of Undisputed Material Facts is required
□ Format for citing evidence (exhibits, appendix, etc.)
□ Filing deadline relative to trial date or discovery close
□ Whether a proposed order must be submitted
□ Certificate of conference requirements (if any)
□ Whether the court requires or permits oral argument
""",
        "metadata": {
            "description": "Practical guide to drafting a motion for summary judgment: structure, components, evidence requirements, and strategic considerations.",
            "source": "Original synthesis of established legal writing and civil procedure principles"
        }
    },
    {
        "title": "Summary Judgment Checklist for Analysis",
        "doc_type": "standard",
        "jurisdiction": None,
        "content": """SUMMARY JUDGMENT ANALYSIS CHECKLIST

Use this checklist when preparing or opposing a motion for summary judgment.

STEP 1: IDENTIFY THE SUBSTANTIVE LAW
□ What cause of action or defense is at issue?
□ What are the elements that must be proved?
□ Who bears the burden of proof at trial on each element?
□ What is the standard of proof (preponderance, clear and convincing)?
□ What facts are "material" under this substantive law?

STEP 2: ANALYZE THE MOVANT'S BURDEN
□ Does the movant bear the burden of proof at trial?
  - If YES: Has the movant shown every element is undisputed in its favor?
  - If NO: Is the movant using the DISPROOF approach or the ABSENCE-OF-PROOF approach?
□ For DISPROOF: Has the movant produced affirmative evidence negating an element?
□ For ABSENCE OF PROOF: Has the movant identified specific record materials showing the non-movant lacks evidence on an element? (A bare assertion is insufficient.)

STEP 3: EVALUATE THE EVIDENCE
□ Is each piece of cited evidence admissible or reducible to admissible form?
□ Are affidavits/declarations based on personal knowledge?
□ Is any cited evidence hearsay, speculation, or lacking authentication?
□ Has the evidence been properly authenticated?
□ Are deposition excerpts cited to specific page and line numbers?

STEP 4: ANALYZE THE NON-MOVANT'S RESPONSE
□ Has the non-movant identified specific facts creating a genuine dispute?
□ Has the non-movant gone beyond mere pleading allegations?
□ Are the non-movant's cited facts material under the substantive law?
□ Are the inferences the non-movant draws reasonable (not speculative)?
□ Does the non-movant need additional discovery? (Rule 56(d) affidavit)

STEP 5: ASSESS GENUINE DISPUTE
□ Could a reasonable fact-finder decide for the non-movant based on the record?
□ Are all reasonable inferences drawn in favor of the non-movant?
□ Is the court improperly weighing evidence or assessing credibility?
□ Is there merely a "metaphysical doubt" or a genuine evidentiary dispute?

STEP 6: DETERMINE DISPOSITION
□ Grant in full — No genuine dispute on any material fact; movant entitled to judgment
□ Grant in part — Some claims/defenses resolved, others have genuine disputes
□ Deny — Genuine dispute of material fact exists on at least one material issue
□ Defer — Non-movant needs additional discovery under Rule 56(d)

COMMON TRAPS TO AVOID:
- Confusing immaterial factual disputes with material ones
- Treating a dispute about the law as a factual dispute
- Accepting pleading allegations as evidence
- Relying on inadmissible evidence
- Failing to identify which elements are actually contested
- Making the movant prove a negative when absence-of-proof approach applies
""",
        "metadata": {
            "description": "Step-by-step analytical checklist for evaluating or preparing a summary judgment motion.",
            "source": "Original synthesis of established civil procedure principles"
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
                """INSERT INTO msj_library (title, doc_type, jurisdiction, content, metadata, created_by)
                   VALUES ($1, $2, $3, $4, $5, 'system')
                   RETURNING id""",
                doc["title"],
                doc["doc_type"],
                doc.get("jurisdiction"),
                doc["content"],
                json.dumps(doc.get("metadata", {})),
            )
            print(f"  Created: {doc['title']} (id={row['id']})")
    finally:
        await conn.close()

    print("Done seeding MSJ library.")


if __name__ == "__main__":
    asyncio.run(seed_library())
