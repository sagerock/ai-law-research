export interface Rule {
  rule: string
  slug: string | null
  description: string
  timing?: string
}

export interface Branch {
  label: string
  description: string
  rules: string[]
}

export interface KeyCase {
  name: string
  holding?: string
  caseId?: string
}

export interface Concept {
  name: string
  description: string
}

export interface Stage {
  id: number
  title: string
  subtitle: string
  rules: Rule[]
  branches?: Branch[]
  keyCases?: KeyCase[]
  concepts?: Concept[]
  isWide?: boolean
  discoveryTools?: { name: string; description: string }[]
}

export const stages: Stage[] = [
  {
    id: 1,
    title: 'Pre-Filing',
    subtitle: 'Investigating the claim and choosing the right court',
    rules: [
      { rule: 'Rule 11', slug: 'rule-11', description: 'Signing pleadings — certification of good faith basis', timing: 'Applies to: every pleading, motion, and paper filed with the court. Does NOT apply to: discovery (Rule 37 governs instead) or oral arguments. Continuing duty — violation can occur by later advocating a position.' },
      { rule: '28 USC §1331', slug: null, description: 'Federal question jurisdiction' },
      { rule: '28 USC §1332', slug: null, description: 'Diversity jurisdiction ($75K+ amount in controversy)' },
      { rule: '28 USC §1367', slug: null, description: 'Supplemental jurisdiction' },
      { rule: '28 USC §1391', slug: null, description: 'Venue — proper district for filing' },
    ],
    concepts: [
      { name: 'Rule 11 "Stop and Think"', description: 'Before signing/filing, attorney must conduct inquiry reasonable under the circumstances. Objective negligence standard — good faith is no defense. Must certify: (1) no improper purpose, (2) legal contentions warranted or nonfrivolous argument for change, (3) factual contentions have evidentiary support, (4) denials warranted on evidence.' },
      { name: 'Rule 11(a) — Signature Requirement', description: 'At least one attorney of record must sign every pleading, motion, and paper. Court must strike unsigned paper unless promptly corrected.' },
      { name: 'Rule 11 Sanctions', description: 'Two pathways: (1) Motion by opposing party with 21-day safe harbor to withdraw (11(c)(2)), (2) Sua sponte by court with no safe harbor — cannot award attorney\'s fees, reserved for conduct "akin to contempt" (11(c)(3)). Cannot impose monetary sanctions on represented party for bad legal arguments (11(c)(5)) — that\'s the lawyer\'s responsibility. Sanctions must be "sufficient to deter" — no more (11(c)(4)).' },
      { name: 'Pre-Filing Investigation Standard', description: 'Amount of investigation depends on time available and probability more investigation will turn up important evidence (Szabo Food Service). National objective standard — no locality rule. If you lack expertise, must associate with a specialist or "bone up on the relevant law at every step."' },
      { name: 'Nonfrivolous Argument for Change — 11(b)(2)', description: 'Sources: circuit splits, Supreme Court dicta, dissenting opinions, law review articles, scholarly commentary, trends in other jurisdictions. En banc review exists as a legitimate mechanism for changing circuit law — arguing against controlling precedent is non-frivolous. Losing does NOT equal Rule 11 violation.' },
    ],
    keyCases: [
      { name: 'Erie Railroad Co. v. Tompkins (1938)', holding: 'Federal courts sitting in diversity must apply state substantive law', caseId: '103012' },
      { name: 'International Shoe Co. v. Washington (1945)', holding: 'Personal jurisdiction requires minimum contacts with the forum state', caseId: '104200' },
      { name: 'World-Wide Volkswagen Corp. v. Woodson (1980)', holding: 'Foreseeability alone insufficient — defendant must purposefully avail itself of the forum', caseId: '110170' },
      { name: 'Hays v. Sony Corp.', holding: 'Attorney sanctioned $14,895 for filing claim based on abolished law with no pre-filing investigation. Objective negligence standard.' },
      { name: 'Hunter v. Earthgrains', holding: 'Sanctions vacated — arguing against controlling precedent was non-frivolous because circuit split existed and Supreme Court authority supported the position. Losing ≠ Rule 11 violation.' },
      { name: 'Blue v. U.S. Dept. of Army', holding: 'Rule 11 must not chill advocacy for legal change — "If arguing against precedent were forbidden, the parties who brought Brown v. Board of Education might have been thought to have engaged in sanctionable conduct for pursuing claims in the face of Plessy v. Ferguson."' },
      { name: 'Wright v. Universal Maritime Service Corp. (1998)', holding: 'Supreme Court validated Hunter\'s legal theory after she filed but before sanctions were imposed — demonstrates arguing against controlling precedent can be vindicated.' },
    ],
  },
  {
    id: 2,
    title: 'Filing & Service',
    subtitle: 'Commencing the action and notifying the defendant',
    rules: [
      { rule: 'Rule 3', slug: 'rule-3', description: 'Commencement of action — filing the complaint' },
      { rule: 'Rule 4', slug: 'rule-4', description: 'Summons — issuance and service of process', timing: 'Must serve within 90 days of filing complaint (Rule 4(m)). If not served in time, court must dismiss without prejudice OR order service within a specified time if plaintiff shows good cause.' },
      { rule: 'Rule 4(k)', slug: 'rule-4', description: 'Territorial limits of effective service' },
      { rule: 'Rule 5', slug: 'rule-5', description: 'Service and filing of pleadings and papers' },
    ],
    keyCases: [
      { name: 'Mullane v. Central Hanover Bank & Trust Co. (1950)', holding: 'Notice must be reasonably calculated to inform interested parties — due process standard for service', caseId: '104786' },
    ],
  },
  {
    id: 3,
    title: 'Pleadings & Motions',
    subtitle: 'Complaint, answer, and early dispositive motions',
    isWide: true,
    rules: [
      { rule: 'Rule 7', slug: 'rule-7', description: 'Pleadings allowed — types of pleadings (complaint, answer, reply to counterclaim, etc.)' },
      { rule: 'Rule 8(a)', slug: 'rule-8', description: 'Complaint: (1) jurisdiction statement, (2) short/plain statement of claim, (3) demand for relief' },
      { rule: 'Rule 8(b)', slug: 'rule-8', description: 'Answer: admit, deny, or lack of knowledge (functions as denial). Failure to deny = admission', timing: 'Must file within 21 days after service of summons/complaint. Exception: 60 days if defendant timely returns waiver of service (Rule 12(a)(1)).' },
      { rule: 'Rule 8(c)', slug: 'rule-8', description: 'Affirmative defenses — must be pleaded or waived (statute of limitations, comparative negligence, etc.)' },
      { rule: 'Rule 8(d)', slug: 'rule-8', description: 'Pleading flexibility — alternative, hypothetical, and inconsistent claims permitted' },
      { rule: 'Rule 8(e)', slug: 'rule-8', description: 'Construction — pleadings "must be construed so as to do justice"' },
      { rule: 'Rule 9(b)', slug: 'rule-9', description: 'Heightened pleading for fraud — must allege when, where, and how with specificity', timing: 'Applies ONLY to fraud and mistake claims. Courts cannot extend heightened pleading to other categories (Leatherman v. Tarrant County). Malice, intent, and knowledge may still be alleged generally.' },
      { rule: 'Rule 10', slug: 'rule-10', description: 'Form of pleadings — caption (10(a)), numbered paragraphs, separate counts (10(b))' },
      { rule: 'Rule 12', slug: 'rule-12', description: 'Defenses and objections — pre-answer motions to dismiss', timing: 'Must file BEFORE the answer (or include in the answer). 12(b)(2)-(5) waived if not in first Rule 12 motion or answer. 12(b)(6) and 12(b)(7) can be raised through trial. 12(b)(1) subject matter jurisdiction can be raised at ANY time, even on appeal.' },
      { rule: 'Rule 12(e)', slug: 'rule-12', description: 'More Definite Statement — when complaint is "hopelessly vague" and defendant cannot reasonably prepare a response. Rarely granted.' },
      { rule: 'Rule 12(f)', slug: 'rule-12', description: 'Motion to Strike — remove inflammatory, improper, or irrelevant material from a pleading. Not a substitute for 12(b)(6).' },
      { rule: 'Rule 15', slug: 'rule-15', description: 'Amended and supplemental pleadings', timing: 'As of right (15(a)(1)): ONE TIME within 21 days after serving, or 21 days after a responsive pleading or Rule 12 motion — whichever is earlier. After that: need opposing party\'s written consent or court leave. During/after trial: Rule 15(b) allows amendment for issues tried by consent.' },
      { rule: 'Rule 55', slug: 'rule-55', description: 'Default and default judgment — failure to respond within 21 days', timing: 'Entry of default (55(a)): when defendant fails to plead or otherwise defend within 21 days. Default judgment (55(b)): only AFTER entry of default. Setting aside: entry of default requires "good cause" (lower bar); default judgment requires meeting Rule 60(b) (higher bar).' },
    ],
    concepts: [
      { name: 'Pleading Standards Evolution', description: 'Common Law (hypertechnical) → Code Pleading (facts) → Notice Pleading (1938, give notice) → Plausibility Pleading (2007-2009, plausible facts). Conley\'s "no set of facts" standard retired by Twombly.' },
      { name: 'Twombly-Iqbal Two-Step Analysis', description: 'Step 1: Identify and discard conclusory allegations — "threadbare recitals of elements" get no presumption of truth. Step 2: Assess whether remaining well-pleaded facts plausibly state a claim. More than possible/conceivable, less than probable. Context-specific using "judicial experience and common sense."' },
      { name: 'Competing Inferences Problem', description: 'When facts equally support innocent and guilty explanations, plaintiff must plead something more to make liability more plausible than the alternative. Parallel conduct equally consistent with conspiracy or lawful behavior = insufficient (Twombly).' },
      { name: 'The Catch-22 Problem', description: 'Plaintiffs need discovery to plead plausibly, but can\'t get discovery until they survive a motion to dismiss. Information asymmetry favors defendants who control the facts. Discovery doesn\'t begin until after 12(b)(6) is resolved.' },
      { name: 'Rule 12(b) Defenses', description: '(1) Lack of subject matter jurisdiction, (2) Lack of personal jurisdiction, (3) Improper venue, (4) Insufficient process, (5) Insufficient service, (6) Failure to state a claim, (7) Failure to join party under Rule 19.' },
      { name: 'The Waiver Trap', description: 'Rule 12(g)(2): Must consolidate ALL available Rule 12 defenses in one motion. WAIVABLE (12(h)(1)): 12(b)(2)-(5), 12(e), 12(f) — waived if not in first motion or answer. CAN RAISE LATER (12(h)(2)): 12(b)(6), 12(b)(7) — through trial. NEVER WAIVED (12(h)(3)): 12(b)(1) subject matter jurisdiction — can be raised at any time, even on appeal. "Reserving rights" in motion does NOT prevent waiver (Hunter v. Serv-Tech).' },
      { name: 'Rule 12(d) — Conversion to Summary Judgment', description: 'If court considers matters outside the pleadings on a 12(b)(6) or 12(c) motion, the motion converts to a Rule 56 summary judgment motion. All parties must be given reasonable opportunity to present pertinent material.' },
      { name: 'Affirmative Defenses vs. Denials', description: '"Never went on property" = denial (contradicts allegation). "Had permission" = affirmative defense (admits entry, asserts additional fact). Key test: if defendant bears burden of proof → affirmative defense. Must be pleaded or waived — can\'t "lie behind a log" (Ingraham v. United States). Vague laundry-list defenses ("laches, waiver, estoppel...") may be stricken as too general (Reis Robotics).' },
      { name: 'Amendments — Rule 15(a)', description: 'As of right: one amendment within 21 days after serving or 21 days after responsive pleading/Rule 12 motion. Otherwise: need consent or court leave — "freely give when justice so requires." Foman v. Davis factors: undue delay, bad faith, repeated failure to cure, undue prejudice, futility. Focus on prejudice (preparation prejudice, not merits) — Beeck v. Aqua Slide.' },
      { name: 'Relation Back — Rule 15(c)', description: 'Allows amendments after statute of limitations by "relating back" to original filing date. 15(c)(1)(A): state law may be more generous — one-way ratchet favoring amending party. Same party/new claim (15(c)(1)(B)): must arise from same transaction/occurrence. New defendant (15(c)(1)(C)): must have received notice within 90 days (Rule 4(m)) and known action would have been brought against it "but for mistake in identity." "Mistake" = about WHO you meant to sue (misnomer, wrong entity), NOT discovering a new wrongdoer.' },
      { name: 'Default Judgment — Rule 55', description: 'Step 1: Entry of default by clerk when defendant fails to respond within 21 days. Step 2: Default judgment by clerk (limited) or court. Setting aside (55(c)): different standards — entry of default = "good cause" (lower), default judgment = Rule 60(b) requirements (higher).' },
    ],
    keyCases: [
      { name: 'Conley v. Gibson (1957)', holding: 'Notice pleading era — complaint sufficient unless "beyond doubt plaintiff can prove no set of facts." Low threshold, retired by Twombly.', caseId: '105573' },
      { name: 'Bell Atlantic Corp. v. Twombly (2007)', holding: 'Must plead facts making claim "plausible on its face." Parallel conduct equally consistent with conspiracy or lawful behavior is insufficient.', caseId: '145730' },
      { name: 'Ashcroft v. Iqbal (2009)', holding: 'Applies Twombly plausibility to ALL civil actions, not just antitrust. Two-step: discard conclusory allegations, then assess plausibility.', caseId: '30747' },
      { name: 'Dioguardi v. Durning (2d Cir. 1944)', holding: 'Pro se barely comprehensible complaint sufficient under notice pleading — court identifies applicable law from alleged facts.' },
      { name: 'Swanson v. Citibank (7th Cir. 2010)', holding: 'Plausibility ≠ probability. Ask "could this have happened," not "did it happen." Posner dissent favored strict reading.' },
      { name: 'Leatherman v. Tarrant County (1993)', holding: 'Courts cannot extend heightened pleading beyond categories listed in Rule 9(b).' },
      { name: 'Krupski v. Costa Crociere (2010)', holding: '"Mistake" inquiry focuses on what defendant knew, not plaintiff\'s diligence. Shared counsel = notice.', caseId: '67602' },
      { name: 'Foman v. Davis (1962)', holding: 'Standard for denying leave to amend: undue delay, bad faith, repeated failure to cure, undue prejudice, futility.' },
      { name: 'Beeck v. Aqua Slide \'N\' Dive', holding: 'Liberal standard for granting leave to amend. Focus on prejudice (preparation prejudice, not merits) and futility.' },
      { name: 'Bonerb v. Richard J. Caron Foundation', holding: 'New claims related to original facts can relate back — defendant already on notice to preserve evidence.' },
      { name: 'Reis Robotics USA v. Concept Industries', holding: 'Motion to strike insufficient affirmative defenses: defenses that are really denials, vague laundry-list defenses too general, "reserving right to add defenses" not allowed.' },
      { name: 'Hunter v. Serv-Tech, Inc.', holding: 'Filed 12(b)(5) motion, then tried to raise 12(b)(2) later — waived. "Reserving rights" in motion does not prevent waiver.' },
      { name: 'Matos v. Nextran', holding: 'Illustrates Rules 12(e) and 12(f): complaint incorporated paragraphs by reference without separating claims; references to "illegal conduct" stricken as inflammatory.' },
    ],
    branches: [
      {
        label: 'Case May End Here',
        description: 'Defendant moves to dismiss for failure to state a claim, lack of jurisdiction, or default. Dismissal under 12(b)(6) is usually with leave to amend.',
        rules: ['Rule 12(b)(6)', 'Rule 12(c)', 'Rule 55'],
      },
    ],
  },
  {
    id: 4,
    title: 'Joinder & Parties',
    subtitle: 'Adding claims, parties, and third-party defendants',
    rules: [
      { rule: 'Rule 13(a)', slug: 'rule-13', description: 'Compulsory counterclaims — must assert or waived (same transaction/occurrence)', timing: 'Must be raised in the answer or it is WAIVED permanently. Even if first case settled (not adjudicated), may still bar later lawsuit (King v. Blanton — equitable waiver).' },
      { rule: 'Rule 13(b)', slug: 'rule-13', description: 'Permissive counterclaims — may assert any unrelated claim' },
      { rule: 'Rule 14', slug: 'rule-14', description: 'Third-party practice (impleader)' },
      { rule: 'Rule 18', slug: 'rule-18', description: 'Joinder of claims — permissive joinder of claims' },
      { rule: 'Rule 19', slug: 'rule-19', description: 'Required joinder of parties' },
      { rule: 'Rule 20', slug: 'rule-20', description: 'Permissive joinder of parties' },
      { rule: 'Rule 22', slug: 'rule-22', description: 'Interpleader' },
      { rule: 'Rule 23', slug: 'rule-23', description: 'Class actions' },
      { rule: 'Rule 24', slug: 'rule-24', description: 'Intervention' },
    ],
    concepts: [
      { name: 'Compulsory vs. Permissive Counterclaims', description: 'Compulsory (13(a)): arises from same transaction/occurrence — must assert or waived forever. Permissive (13(b)): any unrelated claim — may assert now or bring separately later. Counterclaim relief can exceed or differ from plaintiff\'s requested relief (13(c)).' },
    ],
    keyCases: [
      { name: 'Hansberry v. Lee (1940)', holding: 'Due process requires adequate representation for class members to be bound by judgment', caseId: '103379' },
      { name: 'Wal-Mart Stores, Inc. v. Dukes (2011)', holding: 'Class must share common questions that generate common answers — individualized inquiries defeat commonality', caseId: '78615' },
      { name: 'King v. Blanton', holding: 'Equitable waiver of compulsory counterclaims — even if first case settled (not adjudicated), may still bar later lawsuit' },
    ],
  },
  {
    id: 5,
    title: 'Discovery',
    subtitle: 'Exchanging information and evidence between the parties',
    isWide: true,
    rules: [
      { rule: 'Rule 1', slug: 'rule-1', description: '"Just, speedy, and inexpensive determination of every action" — foundational purpose underlying all discovery rules' },
      { rule: 'Rule 26', slug: 'rule-26', description: 'Duty to disclose; general discovery provisions; scope and proportionality', timing: 'Rule 26(f) conference ("Meet and Confer"): required at least 21 days before Rule 16(b) scheduling conference. Initial disclosures: within 14 days after 26(f) conference. Discovery cannot begin until AFTER the 26(f) conference (Rule 26(d)). Expert disclosures: at least 90 days before trial; rebuttal within 30 days (26(a)(2)(D)). Pretrial disclosures: at least 30 days before trial (26(a)(3)).' },
      { rule: 'Rule 26(b)(3)', slug: 'rule-26', description: 'Work product doctrine — materials prepared in anticipation of litigation', timing: 'Applies only to documents/tangible things prepared "in anticipation of litigation." Does NOT protect underlying facts — only the attorney\'s compilation and analysis. Any person can obtain their OWN prior statement without any special showing (26(b)(3)(C)).' },
      { rule: 'Rule 26(b)(4)', slug: 'rule-26', description: 'Expert discovery — testifying vs. consulting experts', timing: 'Testifying experts (26(a)(2)(B)): must disclose identity of ANY witness who may present expert testimony. Can be deposed only AFTER report is provided (26(b)(4)(A)). Summary disclosure (26(a)(2)(C)) for non-retained experts (treating physicians, employee experts). Consulting/non-testifying experts (26(b)(4)(D)): discovery ordinarily PROHIBITED except in exceptional circumstances. Draft expert reports protected as work product (26(b)(4)(B)).' },
      { rule: 'Rule 26(c)', slug: 'rule-26', description: 'Protective orders — good cause required, must meet and confer first' },
      { rule: 'Rule 26(g)', slug: 'rule-26', description: 'Discovery\'s Rule 11 — must sign and certify all discovery papers', timing: 'Applies ONLY to discovery papers (requests, responses, objections, disclosures). Regular Rule 11 does NOT apply to discovery — Rule 26(g) is the parallel enforcement mechanism. Certifies: completeness, consistency with rules, no improper purpose, not unreasonable or unduly burdensome.' },
      { rule: 'Rule 30', slug: 'rule-30', description: 'Depositions by oral examination (10 max, 1 day/7 hours each)', timing: 'Can depose parties AND nonparties (nonparties via Rule 45 subpoena). Leave required if: more than 10 depositions per side, deponent already deposed, or before Rule 26(d) discovery period. 30(b)(6) organizational depositions: name entity, describe matters, entity designates witness. Deponent has 30 days to review transcript and note changes (30(e)).' },
      { rule: 'Rule 33', slug: 'rule-33', description: 'Interrogatories to parties (25 max, 30-day response, under oath)', timing: 'Parties ONLY — cannot send to nonparties. 30-day response period. Corporate parties must furnish ALL info available to the organization including employees/agents/lawyers (33(b)(1)(B)). Contention interrogatories allowed but court may defer answer until after other discovery. Business records option (33(d)). "Continuing interrogatories" preamble invalid — cannot impose supplementation beyond Rule 26(e).' },
      { rule: 'Rule 34', slug: 'rule-34', description: 'Production of documents, ESI, and tangible things', timing: 'Parties only via Rule 34. Nonparties only via Rule 45 subpoena. No numerical limit. 30-day response period. Must describe items with reasonable particularity (34(b)). Must specify form for ESI production.' },
      { rule: 'Rule 35', slug: 'rule-35', description: 'Physical and mental examinations (court order + good cause required)', timing: 'Parties ONLY — cannot compel nonparty exams. Requires court order showing good cause AND that the physical/mental condition is genuinely in controversy. Examiner\'s report must be provided on request; requesting party waives privilege on same condition.' },
      { rule: 'Rule 36', slug: 'rule-36', description: 'Requests for admission (deemed admitted if no response in 30 days)', timing: 'Parties ONLY. If no response within 30 days — matter is CONCLUSIVELY established for the pending action (automatic, no motion needed). Cannot object solely because request presents a genuine issue for trial (36(a)(6)). Best used AFTER other discovery to authenticate documents and narrow issues for trial.' },
      { rule: 'Rule 37', slug: 'rule-37', description: 'Failure to make disclosures or cooperate; sanctions', timing: 'Motion to compel (37(a)): anytime during discovery, must meet and confer first. Self-executing exclusion (37(c)(1)): applies automatically when party fails to disclose — no motion needed. ESI spoliation (37(e)): applies when ESI lost because party failed to take reasonable preservation steps — severe sanctions (adverse inference, dismissal) require intentional destruction.' },
      { rule: 'Rule 45', slug: 'rule-45', description: 'Subpoenas — compelling nonparty testimony and document production', timing: 'Only mechanism for compelling nonparty cooperation. 100-mile rule (45(c)): compliance within 100 miles of nonparty\'s residence or workplace. Must tender 1 day\'s attendance fees and mileage when serving (45(b)). Contempt for failure to comply without adequate excuse (45(g)).' },
    ],
    concepts: [
      { name: 'Scope — Three-Part Test', description: 'All three must be met: (1) Not privileged, (2) Relevant to claim/defense, (3) Proportional to needs of case. Discoverable ≠ admissible. Six proportionality factors (2015 amendment): importance of issues, amount in controversy, parties\' access to info, resources, importance of discovery in resolving issues, burden vs. benefit.' },
      { name: 'Privileges — Discovery "Full Stop"', description: 'Privileged info = discovery ends. Relevance and proportionality do not override valid privilege. Types: attorney-client, spousal, doctor-patient, psychotherapist (Jaffee v. Redmond), 5th Amendment, clergy-penitent. Privilege protects communications, not underlying facts. Must affirmatively assert + provide privilege log (Rule 26(b)(5)(A)).' },
      { name: 'Work Product Doctrine', description: 'Two tiers: Fact/ordinary work product (qualified — can overcome with substantial need + no equivalent (26(b)(3)(A))). Opinion work product (near-absolute — mental impressions, conclusions, legal theories virtually never discoverable (26(b)(3)(B))). "Anticipation of litigation" is the biggest battleground: specific claim test (narrowest, Coastal States Gas), primary purpose (majority), ad hoc/totality (broadest, In re Sealed Case).' },
      { name: 'Expert Discovery Categories', description: 'Testifying experts (26(a)(2)(B)): broad mandatory disclosure with written report, can be deposed after report. Draft reports protected as work product. Consulting/non-testifying experts (26(b)(4)(D)): discovery ordinarily prohibited. "Consulted but not retained" experts: rule is silent — Advisory Committee says omission is intentional (protected), but alternative reading leaves them vulnerable to discovery. Fact witness experts: only facts/opinions acquired in anticipation of litigation are protected.' },
      { name: 'ESI / E-Discovery', description: 'No duty to produce from sources not reasonably accessible due to undue burden/cost (26(b)(2)(B)). Litigation holds (Zubulake IV & V): once litigation reasonably anticipated, must suspend routine destruction and counsel must oversee compliance. Predictive coding/TAR widely accepted. Attorney must understand e-discovery or associate with specialists (Waskul v. Washtenaw County).' },
      { name: 'Deposition Objection Rules', description: 'Form objections (compound, ambiguous, leading) must be made at deposition or permanently waived (32(d)(3)(B)). Substantive objections (relevance, hearsay) preserved until trial (32(d)(3)(A)). Objections must be concise, non-argumentative, non-suggestive (30(d)(1)). Counsel may instruct not to answer only for: (1) privilege, (2) court limitation, or (3) Rule 30(d)(3) motion to terminate. Answering after privilege objection effectively waives the privilege.' },
      { name: 'Spoliation', description: 'Destruction or alteration of evidence, or failure to preserve. Three elements: (1) obligation to preserve, (2) culpable state of mind, (3) relevance to claims/defenses. Common law spoliation: negligence can trigger sanctions. Rule 37(e) for ESI: severe sanctions (adverse inference, dismissal) require showing of intentional destruction.' },
      { name: 'Sanctions Framework', description: 'Rule 37(a): motion to compel (must meet and confer first). Rule 37(b)(2)(A) graduated sanctions for violating court order: (i) establish facts, (ii) prohibit evidence, (iii) strike pleadings, (iv) stay proceedings, (v) dismiss action, (vi) default judgment, (vii) contempt. Rule 37(c)(1): self-executing exclusion for failure to disclose (no motion needed). Boilerplate/general objections increasingly disfavored — may be stricken or sanctioned.' },
      { name: 'Strategic Sequencing', description: 'Initial disclosures → Interrogatories (identify/locate) → Document requests (collect evidence) → Depositions (armed with documents, key witnesses last) → Requests for admissions (narrow issues for trial). Zweifach detailed sequence: (1) required disclosures, (2) depose secondary witnesses, (3) initial document requests, (4) interrogatories, (5) depose adverse party, (6) follow-up requests to admit, (7) depose experts, (8) contention interrogatories, (9) final "clean up" requests.' },
      { name: 'De Bene Esse vs. Discovery Deposition', description: 'Discovery deposition: open-ended questioning for preview and impeachment — witness expected to testify live at trial. De bene esse deposition: substitute for live testimony when witness will be unavailable (illness, distance) — more guarded questioning because it IS the trial testimony.' },
      { name: 'Initial Disclosures Scope', description: 'Narrower than general discovery: only what disclosing party may use to support its OWN claims/defenses. NOT required to disclose witnesses whose testimony damages your case. NOT impeachment-only witnesses. Three ways to delay/avoid: (1) stipulation, (2) object during 26(f) conference, (3) move for court order. Self-help non-disclosure is NOT authorized.' },
    ],
    discoveryTools: [
      { name: 'Initial Disclosures', description: 'Rule 26(a)(1) — automatic exchange within 14 days after 26(f) conference. Witnesses, documents, damages, insurance. Narrower scope: only what disclosing party may use to support its own claims/defenses.' },
      { name: 'Interrogatories', description: 'Rule 33 — written questions to parties only (max 25). 30-day response under oath. Good for identifying witnesses/facts/documents. Business records option (33(d)). Contention interrogatories allowed.' },
      { name: 'Depositions', description: 'Rules 30/31 — parties and nonparties. 10 per side, 1 day/7 hours. Oral exam under oath, no judge present. 30(b)(6) organizational depositions — entity designates witness for named topics.' },
      { name: 'Document Requests', description: 'Rule 34 — documents, ESI, tangible things in possession, custody, or control. No numerical limit. 30-day response. Nonparties via Rule 45 subpoena only.' },
      { name: 'Physical/Mental Exams', description: 'Rule 35 — parties only, requires court order + good cause + condition in controversy (Schlagenhauf v. Holder). Examiner\'s report must be provided; requesting waives privilege on same condition.' },
      { name: 'Requests for Admission', description: 'Rule 36 — parties only. Deemed admitted if no response within 30 days — conclusively established for pending action. Used after other discovery to authenticate documents and narrow issues for trial.' },
    ],
    keyCases: [
      { name: 'Hickman v. Taylor (1947)', holding: 'Foundation of work product doctrine — if attorneys must hand over everything, they stop writing things down, harming clients and justice.', caseId: '104357' },
      { name: 'Zubulake v. UBS Warburg LLC (2003)', holding: 'Litigation hold duties — once litigation reasonably anticipated, must suspend routine document destruction and counsel must oversee compliance.', caseId: '2410862' },
      { name: 'Schlagenhauf v. Holder (1964)', holding: 'Rule 35 physical/mental exams require good cause and condition genuinely in controversy — not routine.', caseId: '106937' },
      { name: 'Chudasama v. Mazda Motor Corp.', holding: 'Resolve 12(b)(6) and narrow issues before compelling broad discovery. Default judgment sanctions excessive — graduated sanctions required.' },
      { name: 'Gaylord v. Homemakers', holding: 'Informal pre-filing investigation permissible. Rule 4.2 no-contact rule not violated when no lawsuit yet filed. Ethics violations do NOT trigger exclusionary rule — ethics rules govern lawyer discipline, not evidence admissibility.' },
    ],
  },
  {
    id: 6,
    title: 'Resolution Without Trial',
    subtitle: 'Voluntary dismissal, involuntary dismissal, and summary judgment',
    rules: [
      { rule: 'Rule 41(a)', slug: 'rule-41', description: 'Voluntary dismissal — by notice (before answer/MSJ), by stipulation, or by court order', timing: 'By notice (self-executing): ONLY before defendant serves answer or MSJ — a 12(b)(6) motion does NOT cut off this right (Bath & Kitchen). By stipulation: anytime, signed by all parties. By court order: required AFTER answer/MSJ. Two-dismissal rule: second dismissal of same claim by notice or stipulation = on the merits (court-ordered dismissal does NOT count toward this rule). Defendant can block dismissal under 41(a)(2) if defendant has counterclaim that cannot independently proceed.' },
      { rule: 'Rule 41(b)', slug: 'rule-41', description: 'Involuntary dismissal — failure to prosecute, failure to comply with Rules', timing: 'Can be raised anytime by defendant or court. Generally operates as adjudication ON THE MERITS. Exceptions (NOT on the merits): court order says otherwise, lack of jurisdiction, improper venue, failure to join necessary party.' },
      { rule: 'Rule 56', slug: 'rule-56', description: 'Summary judgment — no genuine dispute of material fact', timing: 'Can be filed anytime until 30 days after close of discovery (56(b)). If facts unavailable, court may defer and allow time for discovery (56(d)). Court can grant SJ sua sponte or for non-movant (56(f)). Evidence must be admissible — affidavits require personal knowledge, admissible facts, competent affiant (56(c)(4)). Bad faith affidavits → sanctions including contempt (56(h)).' },
    ],
    concepts: [
      { name: 'Summary Judgment Standard', description: 'Court SHALL grant if (1) no genuine dispute as to any material fact AND (2) movant entitled to judgment as a matter of law. "Material" facts determined by substantive law (Anderson). Court must not resolve disputes, weigh evidence, assess credibility, or make factual determinations.' },
      { name: 'Movant\'s Burden', description: 'If movant has burden of proof at trial → must show no genuine dispute on each element. If non-movant has burden → can show non-movant lacks evidence on at least one dispositive element (Celotex "show me" motion).' },
      { name: 'Non-Movant\'s Burden', description: 'Once burden shifts: must go beyond pleadings — designate specific facts showing genuine dispute. Cannot rely solely on pleading allegations, "naked assertions," or hopes of cross-examination (Slaven v. City of Salem). Self-serving declarations are not dismissed simply because they are self-serving (Haley v. Amazon).' },
      { name: 'Burden of Production vs. Persuasion', description: 'At SJ, court asks about burden of production (is there enough evidence for a rational factfinder to find for non-movant?), NOT burden of persuasion (which side\'s evidence is more convincing). Court does not weigh evidence or assess credibility — that is for trial.' },
      { name: 'SJ / JMOL / RJMOL Relationship', description: 'Same standard (reasonable jury test) applied at three stages: Summary Judgment = before trial on written evidence. JMOL (Rule 50(a)) = during trial on presented evidence. Renewed JMOL (Rule 50(b)) = after verdict. Standard of review on appeal: de novo for all three.' },
    ],
    keyCases: [
      { name: 'Celotex Corp. v. Catrett (1986)', holding: 'When non-movant bears trial burden, movant can prevail by showing non-movant lacks evidence on a dispositive element — the "show me" motion.', caseId: '111722' },
      { name: 'Anderson v. Liberty Lobby, Inc. (1986)', holding: '"Material" facts identified by substantive law. Only disputes affecting outcome under governing law are material.' },
      { name: 'Matsushita Electric v. Zenith Radio (1986)', holding: 'Non-movant must show more than "some metaphysical doubt" about material facts.' },
      { name: 'Palucki v. Sears', holding: '"Fair chance of verdict?" test — if non-movant\'s evidence gives a fair chance of a verdict, summary judgment is inappropriate.' },
      { name: 'Lopez-Gonzalez v. Municipality of Comerio', holding: '"A federal court is not a parking lot for stagnant cases." Involuntary dismissal for failure to prosecute.' },
    ],
    branches: [
      {
        label: 'Case May End Here',
        description: 'Voluntary/involuntary dismissal or court grants summary judgment on all claims — no trial needed',
        rules: ['Rule 41', 'Rule 56'],
      },
    ],
  },
  {
    id: 7,
    title: 'Pre-Trial Conference & Trial',
    subtitle: 'Final preparation, jury selection, and presentation of evidence',
    rules: [
      { rule: 'Rule 16', slug: 'rule-16', description: 'Pretrial conferences; scheduling; management', timing: 'Scheduling order issued early in the case. Rule 16(a) purposes: expediting disposition, establishing control, discouraging waste, improving trial quality, facilitating settlement. Modification of scheduling order requires "good cause" showing diligence, not just consent. Rule 16(f): sanctions for failure to appear, being unprepared, or disobeying orders.' },
      { rule: 'Rule 16(e)', slug: 'rule-16', description: 'Final pretrial order — supersedes the pleadings, modified only for "manifest injustice"', timing: 'Issued after the final pretrial conference. From this point, the pretrial order — not the pleadings — controls the case. Issues NOT in the final pretrial order may be excluded at trial. Four-factor test for modification (Davey v. Lockheed): (1) prejudice/surprise, (2) ability to cure, (3) disruption to orderly trial, (4) bad faith.' },
      { rule: 'Rule 38', slug: 'rule-38', description: 'Right to a jury trial — demand (waivable, must request)', timing: 'Must demand no later than 14 days after service of the last pleading directed to the issue. If not demanded, the right is WAIVED. Rule 38(a) preserves the right — Rule 2 merged law/equity but 38(a) ensures the merger expanded (not contracted) jury rights.' },
      { rule: 'Rule 39', slug: 'rule-39', description: 'Trial by jury or by the court' },
      { rule: 'Rule 47', slug: 'rule-47', description: 'Selecting jurors (voir dire)' },
      { rule: 'Rule 49', slug: 'rule-49', description: 'Special verdicts; general verdict with interrogatories' },
      { rule: 'Rule 50(a)', slug: 'rule-50', description: 'Judgment as a matter of law (JMOL / directed verdict) — must specify issue, law, and facts', timing: 'Can move ONLY after opposing party has been fully heard on the issue (usually after plaintiff rests). Multiple motions permitted — after plaintiff rests, after defendant rests, etc. Each motion preserves those specific issues for Rule 50(b) after verdict. CRITICAL: must make 50(a) to preserve right to file 50(b) on those same issues.' },
      { rule: 'Rule 51', slug: 'rule-51', description: 'Instructions to the jury — parties submit proposed instructions, objections on record' },
    ],
    concepts: [
      { name: 'Seventh Amendment — Two Clauses', description: '(1) Right to Jury Trial Clause: preserves jury right for "suits at common law" where value in controversy exceeds $20. (2) Reexamination Clause: no fact tried by a jury shall be otherwise reexamined in any court except according to rules of the common law. Federal courts only — NOT incorporated to states through 14th Amendment. Does not apply to criminal cases (6th Amendment covers those).' },
      { name: 'Law vs. Equity', description: 'Law (jury): assumpsit, trespass, ejectment, trover, mandamus, habeas corpus. Equity (judge): injunctions, specific performance, accounting, class actions, interpleader. Key test: seeking money damages = law = jury right. No adequate legal remedy = equity = judge decides. Labels don\'t control — "incidental legal issues" argument rejected (Dairy Queen). Legal claims go to jury first; judge bound by jury findings on common issues.' },
      { name: 'JMOL — Evidence Spectrum', description: 'Too little evidence → JMOL against the burden-bearer (directed verdict). Reasonable dispute → jury decides. Overwhelming evidence → JMOL for the burden-bearer. View evidence in light most favorable to non-moving party. Court must not weigh evidence or make credibility determinations.' },
      { name: 'Rule 16 Case Management', description: 'Rule 16(c): attorney must have authority to act on all matters; parties must be available for settlement discussions. Authority to discuss ≠ obligation to agree. Rule 16 is informational, not coercive — cannot "club the parties into submission" (J.F. Edwards). Standing orders cannot exceed Rule 16\'s authority (Rule 83).' },
    ],
    keyCases: [
      { name: 'Dairy Queen, Inc. v. Wood', holding: 'Labels don\'t control jury rights. Contract debt claim is "undeniably legal" regardless of how pleaded. Legal claims go to jury first; judge bound by jury findings on common issues.' },
      { name: 'Beacon Theatres, Inc. v. Westover (1959)', holding: 'Right to jury trial on legal issues cannot be defeated by characterizing them as incidental to equitable claims.', caseId: '105889' },
      { name: 'Pennsylvania RR v. Chamberlain', holding: 'Incredible testimony alone cannot create a genuine factual dispute sufficient to defeat JMOL.', caseId: '102040' },
      { name: 'J.F. Edwards Construction Co. v. Anderson Safeway Guard Rail Corp.', holding: 'Rule 16 pretrial is informational, not coercive — cannot "club the parties into submission." Standing orders cannot exceed Rule 16\'s authority.' },
      { name: 'Davey v. Lockheed Martin Corp.', holding: 'Four-factor test for modifying pretrial order: (1) prejudice/surprise, (2) ability to cure, (3) disruption to orderly trial, (4) bad faith.' },
    ],
  },
  {
    id: 8,
    title: 'Post-Trial Motions',
    subtitle: 'Challenging the verdict or seeking a new trial',
    rules: [
      { rule: 'Rule 50(b)', slug: 'rule-50', description: 'Renewed JMOL (formerly JNOV) — within 28 days after judgment', timing: 'Must file within 28 days after entry of judgment. PREREQUISITE: must have made Rule 50(a) motion on the SAME grounds during trial — cannot file 50(b) without prior 50(a). Cannot appeal denial of 50(a) without first filing 50(b). If granted on appeal, appellate court can reinstate the jury verdict. Standard of review: de novo.' },
      { rule: 'Rule 59', slug: 'rule-59', description: 'New trial; altering or amending a judgment — within 28 days', timing: 'Must file within 28 days after entry of judgment. Unlike SJ/JMOL, judge MAY weigh evidence and assess credibility. Does NOT require a prior motion during trial (unlike Rule 50(b)). Can be combined with a Rule 50(b) motion.' },
      { rule: 'Rule 60(b)', slug: 'rule-60', description: 'Relief from a judgment or order — extraordinary circumstances', timing: 'Must file within "reasonable time." For grounds (1)-(3) — mistake, new evidence, fraud — no more than 1 year after judgment. Ground (6) catch-all — no fixed deadline but requires extraordinary circumstances. Rule 60(b) is a "last resort" — do not use as substitute for appeal.' },
    ],
    concepts: [
      { name: 'Rule 50(b) Prerequisite', description: 'Must have made Rule 50(a) motion on the same grounds during trial — cannot make 50(b) without prior 50(a). Purpose: gives opposing party chance to cure, respects 7th Amendment Reexamination Clause, prevents sandbagging. Cannot appeal denial of 50(a) without filing 50(b).' },
      { name: 'New Trial Grounds — Rule 59', description: 'Errors of law, verdict against weight of evidence (judge may weigh evidence — unlike SJ/JMOL), excessive/inadequate damages, newly discovered evidence, juror misconduct, improper jury instructions. Error must be substantial enough to have prejudiced the moving party.' },
      { name: 'Relief from Judgment — Rule 60(b)', description: 'Six grounds: (1) mistake/inadvertence/excusable neglect, (2) newly discovered evidence, (3) fraud by opposing party, (4) judgment is void, (5) judgment satisfied/released, (6) any other reason — catch-all requiring extraordinary circumstances. Must file within reasonable time.' },
      { name: 'Impeachment of Verdict', description: 'FRE 606(b): jurors generally cannot testify about deliberations. Narrow exceptions: outside influences, extraneous prejudicial information, error in verdict form.' },
    ],
    keyCases: [
      { name: 'Neely v. Martin K. Eby Construction Co. (1967)', holding: 'Appellate court can grant RJMOL and reinstate jury verdict rather than ordering new trial.' },
    ],
  },
  {
    id: 9,
    title: 'Appeal',
    subtitle: 'Seeking review of the trial court\'s decision by a higher court',
    rules: [
      { rule: '28 USC §1291', slug: null, description: 'Final judgment rule — only final decisions (resolving all claims of all parties) are appealable', timing: 'Applies ONLY to "final decisions" — must resolve ALL claims of ALL parties. Partial summary judgment on liability alone is NOT final and NOT appealable (Liberty Mutual v. Wetzel). If any claim or party remains unresolved, no appeal under §1291.' },
      { rule: '28 USC §1292', slug: null, description: 'Interlocutory appeals — immediate appeal of certain non-final orders (injunctions, etc.)', timing: 'Available for: orders granting/refusing/modifying injunctions. Permissive interlocutory appeal: district court certifies controlling question of law + appellate court agrees to hear it. Collateral order doctrine (Cohen v. Beneficial Industrial Loan): must be (1) conclusive, (2) separate from merits, (3) effectively unreviewable later.' },
      { rule: 'Rule 54', slug: 'rule-54', description: 'Judgment; costs — defines "final judgment"' },
      { rule: 'Fed. R. App. P. 4', slug: null, description: 'Notice of appeal — strict 30-day deadline after entry of judgment', timing: 'STRICT 30-day deadline — jurisdictional, cannot be waived or extended (with very narrow exceptions). Clock starts from entry of judgment. Missing this deadline = no appeal, period.' },
    ],
    concepts: [
      { name: 'Exceptions to Finality', description: 'Interlocutory appeals (§1292): orders involving injunctions. Collateral Order Doctrine (Cohen): must be (1) conclusive (fully resolves the disputed question), (2) resolves important question completely separate from merits, (3) effectively unreviewable on appeal from final judgment. Writ of Mandamus: extraordinary remedy for clear abuse of discretion. Permissive Interlocutory Appeal: district court certifies controlling question of law.' },
      { name: 'Standards of Appellate Review', description: 'Legal conclusions: de novo (fresh look). Factual findings: clear error (deferential). Jury verdicts: substantial evidence. Discretionary rulings: abuse of discretion. The standard determines how much deference the appellate court gives the trial court.' },
      { name: 'Appellate Court Options', description: 'Affirm, reverse, remand (send back for further proceedings), or modify the judgment.' },
    ],
    keyCases: [
      { name: 'Liberty Mutual Insurance Co. v. Wetzel (1976)', holding: 'Partial summary judgment on liability alone is not a final decision appealable under §1291.', caseId: '109403' },
      { name: 'Cohen v. Beneficial Industrial Loan Corp.', holding: 'Established the collateral order doctrine — narrow exception allowing appeal of orders that are conclusive, separate from the merits, and effectively unreviewable later.', caseId: '104695' },
    ],
  },
  {
    id: 10,
    title: 'Claim & Issue Preclusion',
    subtitle: 'How final judgments prevent re-litigation of claims and issues',
    rules: [
      { rule: 'Rule 41(b)', slug: 'rule-41', description: 'Involuntary dismissals generally operate as adjudication on the merits (with exceptions)' },
    ],
    concepts: [
      { name: 'Claim Preclusion (Res Judicata)', description: 'A final judgment on the merits bars suing again on the same claim. Three elements: (1) Final judgment on the merits (Rule 41(b) involuntary dismissals usually qualify; voluntary 2nd dismissal = on the merits), (2) Same claim — transactional test (same transaction or series of connected transactions), (3) Same parties or privies. Bars claims that were or COULD HAVE BEEN litigated in the first action.' },
      { name: 'Issue Preclusion (Collateral Estoppel)', description: 'Once a court decides an issue of fact or law necessary to its judgment, that issue cannot be re-litigated. Five elements: (1) Same issue, (2) Actually litigated and decided, (3) Necessary to the judgment, (4) Final judgment on the merits, (5) Party against whom preclusion is sought was party/privy to prior action.' },
      { name: '"Actually Litigated" Requirement', description: 'Default judgments and consent judgments (settlements) do NOT satisfy the "actually litigated" requirement. Only claim preclusion (not issue preclusion) can arise from defaults/settlements, because the issues were never genuinely contested and decided.' },
      { name: 'Non-Mutual Collateral Estoppel', description: 'Defensive: new defendant uses prior plaintiff\'s loss against same plaintiff — generally allowed (plaintiff had full opportunity to litigate). Offensive: new plaintiff uses prior defendant\'s loss — discretionary, court weighs fairness (could encourage "wait-and-see"). Key exam distinction.' },
    ],
    keyCases: [],
  },
  {
    id: 11,
    title: 'Enforcement',
    subtitle: 'Collecting on the judgment after all appeals are exhausted',
    rules: [
      { rule: 'Rule 69', slug: 'rule-69', description: 'Execution — proceedings to enforce a money judgment' },
      { rule: 'Rule 70', slug: 'rule-70', description: 'Enforcing a judgment for a specific act' },
    ],
  },
]
