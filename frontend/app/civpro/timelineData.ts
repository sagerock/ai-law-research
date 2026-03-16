export interface Rule {
  rule: string
  slug: string | null
  description: string
}

export interface Branch {
  label: string
  description: string
  rules: string[]
}

export interface KeyCase {
  name: string
  holding?: string
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
      { rule: 'Rule 11', slug: 'rule-11', description: 'Signing pleadings — certification of good faith basis' },
      { rule: '28 USC §1331', slug: null, description: 'Federal question jurisdiction' },
      { rule: '28 USC §1332', slug: null, description: 'Diversity jurisdiction ($75K+ amount in controversy)' },
      { rule: '28 USC §1367', slug: null, description: 'Supplemental jurisdiction' },
      { rule: '28 USC §1391', slug: null, description: 'Venue — proper district for filing' },
    ],
    concepts: [
      { name: 'Rule 11 "Stop and Think"', description: 'Before signing/filing, attorney must conduct inquiry reasonable under the circumstances. Objective negligence standard — good faith is no defense. Must certify: (1) no improper purpose, (2) legal contentions warranted or nonfrivolous argument for change, (3) factual contentions have evidentiary support, (4) denials warranted on evidence.' },
      { name: 'Rule 11 Sanctions', description: 'Two pathways: (1) Motion by opposing party with 21-day safe harbor to withdraw, (2) Sua sponte by court with no safe harbor. Cannot impose monetary sanctions on represented party for bad legal arguments (11(c)(5)) — that\'s the lawyer\'s responsibility.' },
      { name: 'Pre-Filing Investigation Standard', description: 'Amount of investigation depends on time available and probability more investigation will turn up important evidence (Szabo Food Service). National objective standard — no locality rule. If you lack expertise, must associate with a specialist or "bone up on the relevant law at every step."' },
    ],
    keyCases: [
      { name: 'Erie Railroad Co. v. Tompkins (1938)', holding: 'Federal courts sitting in diversity must apply state substantive law' },
      { name: 'International Shoe Co. v. Washington (1945)', holding: 'Personal jurisdiction requires minimum contacts with the forum state' },
      { name: 'World-Wide Volkswagen Corp. v. Woodson (1980)', holding: 'Foreseeability alone insufficient — defendant must purposefully avail itself of the forum' },
      { name: 'Hays v. Sony Corp.', holding: 'Attorney sanctioned $14,895 for filing claim based on abolished law with no pre-filing investigation. Objective negligence standard.' },
      { name: 'Hunter v. Earthgrains', holding: 'Sanctions vacated — arguing against controlling precedent was non-frivolous because circuit split existed and Supreme Court authority supported the position. Losing ≠ Rule 11 violation.' },
    ],
  },
  {
    id: 2,
    title: 'Filing & Service',
    subtitle: 'Commencing the action and notifying the defendant',
    rules: [
      { rule: 'Rule 3', slug: 'rule-3', description: 'Commencement of action — filing the complaint' },
      { rule: 'Rule 4', slug: 'rule-4', description: 'Summons — issuance and service of process' },
      { rule: 'Rule 4(k)', slug: 'rule-4', description: 'Territorial limits of effective service' },
      { rule: 'Rule 5', slug: 'rule-5', description: 'Service and filing of pleadings and papers' },
    ],
    keyCases: [
      { name: 'Mullane v. Central Hanover Bank & Trust Co. (1950)', holding: 'Notice must be reasonably calculated to inform interested parties — due process standard for service' },
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
      { rule: 'Rule 8(b)', slug: 'rule-8', description: 'Answer: admit, deny, or lack of knowledge (functions as denial). Failure to deny = admission' },
      { rule: 'Rule 8(c)', slug: 'rule-8', description: 'Affirmative defenses — must be pleaded or waived (statute of limitations, comparative negligence, etc.)' },
      { rule: 'Rule 8(d)', slug: 'rule-8', description: 'Pleading flexibility — alternative, hypothetical, and inconsistent claims permitted' },
      { rule: 'Rule 9(b)', slug: 'rule-9', description: 'Heightened pleading for fraud — must allege when, where, and how with specificity' },
      { rule: 'Rule 10', slug: 'rule-10', description: 'Form of pleadings — caption, numbered paragraphs, separate counts' },
      { rule: 'Rule 12', slug: 'rule-12', description: 'Defenses and objections — pre-answer motions to dismiss' },
      { rule: 'Rule 15', slug: 'rule-15', description: 'Amended and supplemental pleadings' },
      { rule: 'Rule 55', slug: 'rule-55', description: 'Default and default judgment — failure to respond within 21 days' },
    ],
    concepts: [
      { name: 'Pleading Standards Evolution', description: 'Common Law (hypertechnical) → Code Pleading (facts) → Notice Pleading (1938, give notice) → Plausibility Pleading (2007-2009, plausible facts). Conley\'s "no set of facts" standard retired by Twombly.' },
      { name: 'Twombly-Iqbal Two-Step Analysis', description: 'Step 1: Identify and discard conclusory allegations — "threadbare recitals of elements" get no presumption of truth. Step 2: Assess whether remaining well-pleaded facts plausibly state a claim. More than possible/conceivable, less than probable. Context-specific using "judicial experience and common sense."' },
      { name: 'The Catch-22 Problem', description: 'Plaintiffs need discovery to plead plausibly, but can\'t get discovery until they survive a motion to dismiss. Information asymmetry favors defendants who control the facts.' },
      { name: 'Rule 12(b) Defenses', description: '(1) Lack of subject matter jurisdiction, (2) Lack of personal jurisdiction, (3) Improper venue, (4) Insufficient process, (5) Insufficient service, (6) Failure to state a claim, (7) Failure to join party under Rule 19.' },
      { name: 'The Waiver Trap', description: 'Rule 12(g)(2): Must consolidate ALL available Rule 12 defenses in one motion. WAIVABLE (12(h)(1)): 12(b)(2)-(5), 12(e), 12(f) — waived if not in first motion or answer. CAN RAISE LATER (12(h)(2)): 12(b)(6), 12(b)(7) — through trial. NEVER WAIVED (12(h)(3)): 12(b)(1) subject matter jurisdiction — can be raised at any time, even on appeal.' },
      { name: 'Affirmative Defenses vs. Denials', description: '"Never went on property" = denial (contradicts allegation). "Had permission" = affirmative defense (admits entry, asserts additional fact). Key test: if defendant bears burden of proof → affirmative defense. Must be pleaded or waived — can\'t "lie behind a log" (Ingraham v. United States).' },
      { name: 'Amendments — Rule 15(a)', description: 'As of right: one amendment within 21 days after serving or 21 days after responsive pleading/Rule 12 motion. Otherwise: need consent or court leave — "freely give when justice so requires." Foman v. Davis factors: undue delay, bad faith, repeated failure to cure, undue prejudice, futility.' },
      { name: 'Relation Back — Rule 15(c)', description: 'Allows amendments after statute of limitations by "relating back" to original filing date. Same party/new claim: must arise from same transaction/occurrence. New defendant: must have received notice within 90 days (Rule 4(m)) and known action would have been brought against it "but for mistake in identity."' },
      { name: 'Default Judgment — Rule 55', description: 'Step 1: Entry of default by clerk when defendant fails to respond within 21 days. Step 2: Default judgment by clerk (limited) or court. Setting aside: different standards — entry of default = "good cause" (lower), default judgment = Rule 60(b) requirements (higher).' },
    ],
    keyCases: [
      { name: 'Conley v. Gibson (1957)', holding: 'Notice pleading era — complaint sufficient unless "beyond doubt plaintiff can prove no set of facts." Low threshold, retired by Twombly.' },
      { name: 'Bell Atlantic Corp. v. Twombly (2007)', holding: 'Must plead facts making claim "plausible on its face." Parallel conduct equally consistent with conspiracy or lawful behavior is insufficient.' },
      { name: 'Ashcroft v. Iqbal (2009)', holding: 'Applies Twombly plausibility to ALL civil actions, not just antitrust. Two-step: discard conclusory allegations, then assess plausibility.' },
      { name: 'Swanson v. Citibank (7th Cir. 2010)', holding: 'Plausibility ≠ probability. Ask "could this have happened," not "did it happen." Posner dissent favored strict reading.' },
      { name: 'Leatherman v. Tarrant County (1993)', holding: 'Courts cannot extend heightened pleading beyond categories listed in Rule 9(b).' },
      { name: 'Krupski v. Costa Crociere (2010)', holding: '"Mistake" inquiry focuses on what defendant knew, not plaintiff\'s diligence. Shared counsel = notice.' },
      { name: 'Foman v. Davis (1962)', holding: 'Standard for denying leave to amend: undue delay, bad faith, repeated failure to cure, undue prejudice, futility.' },
      { name: 'Hunter v. Serv-Tech, Inc.', holding: 'Filed 12(b)(5) motion, then tried to raise 12(b)(2) later — waived. "Reserving rights" in motion does not prevent waiver.' },
    ],
    branches: [
      {
        label: 'Case May End Here',
        description: 'Defendant moves to dismiss for failure to state a claim, lack of jurisdiction, or default',
        rules: ['Rule 12(b)(6)', 'Rule 12(c)', 'Rule 55'],
      },
    ],
  },
  {
    id: 4,
    title: 'Joinder & Parties',
    subtitle: 'Adding claims, parties, and third-party defendants',
    rules: [
      { rule: 'Rule 13(a)', slug: 'rule-13', description: 'Compulsory counterclaims — must assert or waived (same transaction/occurrence)' },
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
      { name: 'Hansberry v. Lee (1940)', holding: 'Due process requires adequate representation for class members to be bound by judgment' },
      { name: 'Wal-Mart Stores, Inc. v. Dukes (2011)', holding: 'Class must share common questions that generate common answers — individualized inquiries defeat commonality' },
      { name: 'King v. Blanton', holding: 'Equitable waiver of compulsory counterclaims — even if first case settled (not adjudicated), may still bar later lawsuit' },
    ],
  },
  {
    id: 5,
    title: 'Discovery',
    subtitle: 'Exchanging information and evidence between the parties',
    isWide: true,
    rules: [
      { rule: 'Rule 26', slug: 'rule-26', description: 'Duty to disclose; general discovery provisions; scope and proportionality' },
      { rule: 'Rule 26(b)(3)', slug: 'rule-26', description: 'Work product doctrine — materials prepared in anticipation of litigation' },
      { rule: 'Rule 26(b)(4)', slug: 'rule-26', description: 'Expert discovery — testifying vs. consulting experts' },
      { rule: 'Rule 26(c)', slug: 'rule-26', description: 'Protective orders — good cause required, must meet and confer first' },
      { rule: 'Rule 26(g)', slug: 'rule-26', description: 'Discovery\'s Rule 11 — must sign and certify all discovery papers' },
      { rule: 'Rule 30', slug: 'rule-30', description: 'Depositions by oral examination (10 max, 1 day/7 hours each)' },
      { rule: 'Rule 33', slug: 'rule-33', description: 'Interrogatories to parties (25 max, 30-day response, under oath)' },
      { rule: 'Rule 34', slug: 'rule-34', description: 'Production of documents, ESI, and tangible things' },
      { rule: 'Rule 35', slug: 'rule-35', description: 'Physical and mental examinations (court order + good cause required)' },
      { rule: 'Rule 36', slug: 'rule-36', description: 'Requests for admission (deemed admitted if no response in 30 days)' },
      { rule: 'Rule 37', slug: 'rule-37', description: 'Failure to make disclosures or cooperate; sanctions' },
      { rule: 'Rule 45', slug: 'rule-45', description: 'Subpoenas — compelling nonparty testimony and document production' },
    ],
    concepts: [
      { name: 'Scope — Three-Part Test', description: 'All three must be met: (1) Not privileged, (2) Relevant to claim/defense, (3) Proportional to needs of case. Discoverable ≠ admissible. Six proportionality factors (2015 amendment): importance of issues, amount in controversy, parties\' access to info, resources, importance of discovery in resolving issues, burden vs. benefit.' },
      { name: 'Privileges — Discovery "Full Stop"', description: 'Privileged info = discovery ends. Relevance and proportionality do not override valid privilege. Types: attorney-client, spousal, doctor-patient, psychotherapist (Jaffee v. Redmond), 5th Amendment, clergy-penitent. Privilege protects communications, not underlying facts. Must affirmatively assert + provide privilege log (Rule 26(b)(5)(A)).' },
      { name: 'Work Product Doctrine', description: 'Two tiers: Fact/ordinary work product (qualified — can overcome with substantial need + no equivalent). Opinion work product (near-absolute — mental impressions, conclusions, legal theories virtually never discoverable). "Anticipation of litigation" is the biggest battleground: specific claim (narrowest), primary purpose (majority), ad hoc/totality (broadest).' },
      { name: 'Expert Discovery Categories', description: 'Testifying experts (26(a)(2)(B)): broad mandatory disclosure with written report, can be deposed after report. Draft reports protected as work product. Consulting/non-testifying experts (26(b)(4)(D)): discovery ordinarily prohibited. Fact witness experts: only facts/opinions acquired in anticipation of litigation are protected.' },
      { name: 'ESI / E-Discovery', description: 'No duty to produce from sources not reasonably accessible due to undue burden/cost (26(b)(2)(B)). Litigation holds (Zubulake IV & V): once litigation reasonably anticipated, must suspend routine destruction. Predictive coding/TAR widely accepted. Attorney must understand e-discovery or associate with specialists.' },
      { name: 'Deposition Objection Rules', description: 'Form objections (compound, ambiguous, leading) must be made at deposition or permanently waived (32(d)(3)(B)). Substantive objections (relevance, hearsay) preserved until trial. Objections must be concise, non-argumentative, non-suggestive (30(d)(1)). Counsel may instruct not to answer only for privilege, court limitation, or Rule 30(d)(3) motion.' },
      { name: 'Sanctions Framework', description: 'Rule 37(a): motion to compel (must meet and confer first). Rule 37(b)(2)(A): graduated sanctions for violating court order — establish facts, prohibit evidence, strike pleadings, stay proceedings, dismiss, default judgment, contempt. Rule 37(c)(1): self-executing exclusion for failure to disclose (no motion needed). Rule 37(e): ESI spoliation — severe sanctions require intentional destruction.' },
      { name: 'Strategic Sequencing', description: 'Initial disclosures → Interrogatories (identify/locate) → Document requests (collect evidence) → Depositions (armed with documents, key witnesses last) → Requests for admissions (narrow issues for trial).' },
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
      { name: 'Hickman v. Taylor (1947)', holding: 'Foundation of work product doctrine — if attorneys must hand over everything, they stop writing things down, harming clients and justice.' },
      { name: 'Zubulake v. UBS Warburg LLC (2003)', holding: 'Litigation hold duties — once litigation reasonably anticipated, must suspend routine document destruction and counsel must oversee compliance.' },
      { name: 'Schlagenhauf v. Holder (1964)', holding: 'Rule 35 physical/mental exams require good cause and condition genuinely in controversy — not routine.' },
      { name: 'Chudasama v. Mazda Motor Corp.', holding: 'Resolve 12(b)(6) and narrow issues before compelling broad discovery. Default judgment sanctions excessive — graduated sanctions required.' },
    ],
  },
  {
    id: 6,
    title: 'Resolution Without Trial',
    subtitle: 'Voluntary dismissal, involuntary dismissal, and summary judgment',
    rules: [
      { rule: 'Rule 41(a)', slug: 'rule-41', description: 'Voluntary dismissal — by notice (before answer/MSJ), by stipulation, or by court order' },
      { rule: 'Rule 41(b)', slug: 'rule-41', description: 'Involuntary dismissal — failure to prosecute, failure to comply with Rules' },
      { rule: 'Rule 56', slug: 'rule-56', description: 'Summary judgment — no genuine dispute of material fact' },
    ],
    concepts: [
      { name: 'Voluntary Dismissal — Rule 41(a)', description: 'Without court order: by notice before defendant serves answer or MSJ — self-executing, automatically without prejudice. 12(b)(6) motion does not cut off this right. By stipulation: signed by all parties. By court order: required after answer/MSJ. Two-dismissal rule: second dismissal of same claim by notice or stipulation = on the merits, cannot refile.' },
      { name: 'Summary Judgment Standard', description: 'Court SHALL grant if (1) no genuine dispute as to any material fact AND (2) movant entitled to judgment as a matter of law. "Material" facts determined by substantive law (Anderson). Court must not resolve disputes, weigh evidence, assess credibility, or make factual determinations.' },
      { name: 'Movant\'s Burden', description: 'If movant has burden of proof at trial → must show no genuine dispute on each element. If non-movant has burden → can show non-movant lacks evidence on at least one dispositive element (Celotex "show me" motion).' },
      { name: 'Non-Movant\'s Burden', description: 'Once burden shifts: must go beyond pleadings — designate specific facts showing genuine dispute. Cannot rely solely on pleading allegations, "naked assertions," or hopes of cross-examination.' },
      { name: 'SJ / JMOL / RJMOL Relationship', description: 'Same standard (reasonable jury test) applied at three stages: Summary Judgment = before trial on written evidence. JMOL (Rule 50(a)) = during trial on presented evidence. Renewed JMOL (Rule 50(b)) = after verdict.' },
    ],
    keyCases: [
      { name: 'Celotex Corp. v. Catrett (1986)', holding: 'When non-movant bears trial burden, movant can prevail by showing non-movant lacks evidence on a dispositive element — the "show me" motion.' },
      { name: 'Anderson v. Liberty Lobby, Inc. (1986)', holding: '"Material" facts identified by substantive law. Only disputes affecting outcome under governing law are material.' },
      { name: 'Matsushita Electric v. Zenith Radio (1986)', holding: 'Non-movant must show more than "some metaphysical doubt" about material facts.' },
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
      { rule: 'Rule 16', slug: 'rule-16', description: 'Pretrial conferences; scheduling; management' },
      { rule: 'Rule 16(e)', slug: 'rule-16', description: 'Final pretrial order — supersedes the pleadings, modified only for "manifest injustice"' },
      { rule: 'Rule 38', slug: 'rule-38', description: 'Right to a jury trial — demand (waivable, must request)' },
      { rule: 'Rule 39', slug: 'rule-39', description: 'Trial by jury or by the court' },
      { rule: 'Rule 47', slug: 'rule-47', description: 'Selecting jurors (voir dire)' },
      { rule: 'Rule 49', slug: 'rule-49', description: 'Special verdicts; general verdict with interrogatories' },
      { rule: 'Rule 50(a)', slug: 'rule-50', description: 'Judgment as a matter of law (JMOL / directed verdict) — must specify issue, law, and facts' },
      { rule: 'Rule 51', slug: 'rule-51', description: 'Instructions to the jury — parties submit proposed instructions, objections on record' },
    ],
    concepts: [
      { name: 'Seventh Amendment Jury Right', description: 'Preserves right as existed in English courts in 1791. Only "suits at common law" (not equity/admiralty). Federal courts only — not incorporated to states via 14th Amendment. Common law (money damages) → jury. Equity (injunctions, specific performance) → judge. Waivable — must be demanded.' },
      { name: 'Law vs. Equity', description: 'Law (jury): assumpsit, trespass, ejectment, trover, mandamus, habeas corpus. Equity (judge): injunctions, specific performance, accounting, class actions, interpleader. Key test: seeking money damages = law = jury right. Labels don\'t control — "incidental legal issues" argument rejected (Dairy Queen).' },
      { name: 'Rule 16 Case Management', description: 'Scheduling order sets deadlines for amendments, motions, discovery — modification requires "good cause." Final pretrial order (16(e)) supersedes the pleadings — can only be modified to prevent "manifest injustice." Rule 16 does not authorize compelled stipulations.' },
      { name: 'JMOL — Rule 50(a)', description: 'After opposing party presents evidence: if no reasonable jury could find for non-movant → grant. View evidence in light most favorable to non-moving party. Court must not weigh evidence or make credibility determinations. Multiple 50(a) motions permitted — each preserves those specific issues for Rule 50(b) after verdict.' },
    ],
    keyCases: [
      { name: 'Dairy Queen, Inc. v. Wood', holding: 'Labels don\'t control jury rights. Contract debt claim is "undeniably legal" regardless of how pleaded. Legal claims go to jury first; judge bound by jury findings on common issues.' },
      { name: 'Beacon Theatres, Inc. v. Westover (1959)', holding: 'Right to jury trial on legal issues cannot be defeated by characterizing them as incidental to equitable claims.' },
      { name: 'Pennsylvania RR v. Chamberlain', holding: 'Incredible testimony alone cannot create a genuine factual dispute sufficient to defeat JMOL.' },
      { name: 'J.F. Edwards Construction Co. v. Anderson Safeway Guard Rail Corp.', holding: 'Rule 16 pretrial is informational, not coercive — cannot "club the parties into submission." Standing orders cannot exceed Rule 16\'s authority.' },
    ],
  },
  {
    id: 8,
    title: 'Post-Trial Motions',
    subtitle: 'Challenging the verdict or seeking a new trial',
    rules: [
      { rule: 'Rule 50(b)', slug: 'rule-50', description: 'Renewed JMOL (formerly JNOV) — within 28 days after judgment' },
      { rule: 'Rule 59', slug: 'rule-59', description: 'New trial; altering or amending a judgment — within 28 days' },
      { rule: 'Rule 60(b)', slug: 'rule-60', description: 'Relief from a judgment or order — extraordinary circumstances' },
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
      { rule: '28 USC §1291', slug: null, description: 'Final judgment rule — only final decisions (resolving all claims of all parties) are appealable' },
      { rule: '28 USC §1292', slug: null, description: 'Interlocutory appeals — immediate appeal of certain non-final orders (injunctions, etc.)' },
      { rule: 'Rule 54', slug: 'rule-54', description: 'Judgment; costs — defines "final judgment"' },
      { rule: 'Fed. R. App. P. 4', slug: null, description: 'Notice of appeal — strict 30-day deadline after entry of judgment' },
    ],
    concepts: [
      { name: 'Exceptions to Finality', description: 'Interlocutory appeals (§1292): orders involving injunctions. Collateral Order Doctrine (Cohen v. Beneficial Industrial Loan): must be (1) conclusive, (2) separate from merits, (3) effectively unreviewable on appeal from final judgment. Writ of Mandamus: extraordinary remedy. Permissive Interlocutory Appeal: district court certifies controlling question of law.' },
      { name: 'Standards of Appellate Review', description: 'Legal conclusions: de novo (fresh look). Factual findings: clear error (deferential). Jury verdicts: substantial evidence. Discretionary rulings: abuse of discretion. The standard determines how much deference the appellate court gives the trial court.' },
      { name: 'Appellate Court Options', description: 'Affirm, reverse, remand (send back for further proceedings), or modify the judgment.' },
    ],
    keyCases: [
      { name: 'Liberty Mutual Insurance Co. v. Wetzel (1976)', holding: 'Partial summary judgment on liability alone is not a final decision appealable under §1291.' },
      { name: 'Cohen v. Beneficial Industrial Loan Corp.', holding: 'Established the collateral order doctrine — narrow exception allowing appeal of orders that are conclusive, separate from the merits, and effectively unreviewable later.' },
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
      { name: 'Claim Preclusion (Res Judicata)', description: 'A final judgment on the merits bars suing again on the same claim. Three elements: (1) Final judgment on the merits, (2) Same claim — transactional test (same transaction or series of connected transactions), (3) Same parties or privies. Bars claims that were or could have been litigated.' },
      { name: 'Issue Preclusion (Collateral Estoppel)', description: 'Once a court decides an issue of fact or law necessary to its judgment, that issue cannot be re-litigated. Five elements: (1) Same issue, (2) Actually litigated and decided, (3) Necessary to the judgment, (4) Final judgment on the merits, (5) Party against whom preclusion is sought was party/privy to prior action.' },
      { name: 'Non-Mutual Collateral Estoppel', description: 'Defensive: new defendant uses prior plaintiff\'s loss against same plaintiff — generally allowed (plaintiff had full opportunity). Offensive: new plaintiff uses prior defendant\'s loss — discretionary, court weighs fairness (could encourage "wait-and-see"). Default/consent judgments don\'t satisfy "actually litigated" requirement.' },
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
