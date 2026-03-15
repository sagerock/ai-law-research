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

export interface Stage {
  id: number
  title: string
  subtitle: string
  rules: Rule[]
  branches?: Branch[]
  keyCases?: string[]
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
    keyCases: [
      'Erie Railroad Co. v. Tompkins (1938)',
      'International Shoe Co. v. Washington (1945)',
      'World-Wide Volkswagen Corp. v. Woodson (1980)',
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
      'Mullane v. Central Hanover Bank & Trust Co. (1950)',
    ],
  },
  {
    id: 3,
    title: 'Pleadings & Motions',
    subtitle: 'Complaint, answer, and early dispositive motions',
    rules: [
      { rule: 'Rule 7', slug: 'rule-7', description: 'Pleadings allowed — types of pleadings' },
      { rule: 'Rule 8', slug: 'rule-8', description: 'General rules of pleading — claim, defense, denials' },
      { rule: 'Rule 9', slug: 'rule-9', description: 'Pleading special matters (fraud, mistake, conditions)' },
      { rule: 'Rule 10', slug: 'rule-10', description: 'Form of pleadings — caption, paragraphs, exhibits' },
      { rule: 'Rule 12', slug: 'rule-12', description: 'Defenses and objections — pre-answer motions' },
      { rule: 'Rule 15', slug: 'rule-15', description: 'Amended and supplemental pleadings' },
    ],
    keyCases: [
      'Bell Atlantic Corp. v. Twombly (2007)',
      'Ashcroft v. Iqbal (2009)',
      'Conley v. Gibson (1957)',
    ],
    branches: [
      {
        label: 'Case May End Here',
        description: 'Defendant moves to dismiss for failure to state a claim or lack of jurisdiction',
        rules: ['Rule 12(b)(6)', 'Rule 12(c)'],
      },
    ],
  },
  {
    id: 4,
    title: 'Joinder & Parties',
    subtitle: 'Adding claims, parties, and third-party defendants',
    rules: [
      { rule: 'Rule 13', slug: 'rule-13', description: 'Counterclaims and crossclaims' },
      { rule: 'Rule 14', slug: 'rule-14', description: 'Third-party practice (impleader)' },
      { rule: 'Rule 18', slug: 'rule-18', description: 'Joinder of claims — permissive joinder of claims' },
      { rule: 'Rule 19', slug: 'rule-19', description: 'Required joinder of parties' },
      { rule: 'Rule 20', slug: 'rule-20', description: 'Permissive joinder of parties' },
      { rule: 'Rule 22', slug: 'rule-22', description: 'Interpleader' },
      { rule: 'Rule 23', slug: 'rule-23', description: 'Class actions' },
      { rule: 'Rule 24', slug: 'rule-24', description: 'Intervention' },
    ],
    keyCases: [
      'Hansberry v. Lee (1940)',
      'Wal-Mart Stores, Inc. v. Dukes (2011)',
    ],
  },
  {
    id: 5,
    title: 'Discovery',
    subtitle: 'Exchanging information and evidence between the parties',
    isWide: true,
    rules: [
      { rule: 'Rule 26', slug: 'rule-26', description: 'Duty to disclose; general discovery provisions' },
      { rule: 'Rule 30', slug: 'rule-30', description: 'Depositions by oral examination' },
      { rule: 'Rule 31', slug: 'rule-31', description: 'Depositions by written questions' },
      { rule: 'Rule 33', slug: 'rule-33', description: 'Interrogatories to parties' },
      { rule: 'Rule 34', slug: 'rule-34', description: 'Production of documents and tangible things' },
      { rule: 'Rule 35', slug: 'rule-35', description: 'Physical and mental examinations' },
      { rule: 'Rule 36', slug: 'rule-36', description: 'Requests for admission' },
      { rule: 'Rule 37', slug: 'rule-37', description: 'Failure to make disclosures or to cooperate; sanctions' },
    ],
    discoveryTools: [
      { name: 'Initial Disclosures', description: 'Rule 26(a) — automatic exchange of witness lists, documents, damages, insurance' },
      { name: 'Interrogatories', description: 'Rule 33 — written questions answered under oath (max 25)' },
      { name: 'Depositions', description: 'Rules 30/31 — oral or written testimony under oath' },
      { name: 'Document Requests', description: 'Rule 34 — production of documents, ESI, and tangible things' },
      { name: 'Physical/Mental Exams', description: 'Rule 35 — court-ordered examination when condition is in controversy' },
      { name: 'Requests for Admission', description: 'Rule 36 — ask opposing party to admit facts or document authenticity' },
    ],
    keyCases: [
      'Hickman v. Taylor (1947)',
      'Zubulake v. UBS Warburg LLC (2003)',
    ],
  },
  {
    id: 6,
    title: 'Summary Judgment',
    subtitle: 'Deciding the case without trial when no genuine dispute of material fact exists',
    rules: [
      { rule: 'Rule 56', slug: 'rule-56', description: 'Summary judgment — no genuine dispute of material fact' },
    ],
    keyCases: [
      'Celotex Corp. v. Catrett (1986)',
      'Anderson v. Liberty Lobby, Inc. (1986)',
      'Matsushita Electric Industrial Co. v. Zenith Radio Corp. (1986)',
    ],
    branches: [
      {
        label: 'Case May End Here',
        description: 'Court grants summary judgment on all claims — no trial needed',
        rules: ['Rule 56'],
      },
    ],
  },
  {
    id: 7,
    title: 'Pre-Trial Conference & Trial',
    subtitle: 'Final preparation, jury selection, and presentation of evidence',
    rules: [
      { rule: 'Rule 16', slug: 'rule-16', description: 'Pretrial conferences; scheduling; management' },
      { rule: 'Rule 38', slug: 'rule-38', description: 'Right to a jury trial — demand' },
      { rule: 'Rule 39', slug: 'rule-39', description: 'Trial by jury or by the court' },
      { rule: 'Rule 47', slug: 'rule-47', description: 'Selecting jurors (voir dire)' },
      { rule: 'Rule 48', slug: 'rule-48', description: 'Number of jurors; verdict; polling' },
      { rule: 'Rule 49', slug: 'rule-49', description: 'Special verdicts; general verdict with interrogatories' },
      { rule: 'Rule 50', slug: 'rule-50', description: 'Judgment as a matter of law (directed verdict / JMOL)' },
      { rule: 'Rule 51', slug: 'rule-51', description: 'Instructions to the jury' },
    ],
    keyCases: [
      'Beacon Theatres, Inc. v. Westover (1959)',
    ],
  },
  {
    id: 8,
    title: 'Post-Trial Motions',
    subtitle: 'Challenging the verdict or seeking a new trial',
    rules: [
      { rule: 'Rule 50(b)', slug: 'rule-50', description: 'Renewed judgment as a matter of law (JNOV)' },
      { rule: 'Rule 59', slug: 'rule-59', description: 'New trial; altering or amending a judgment' },
      { rule: 'Rule 60', slug: 'rule-60', description: 'Relief from a judgment or order' },
    ],
    keyCases: [
      'Neely v. Martin K. Eby Construction Co. (1967)',
    ],
  },
  {
    id: 9,
    title: 'Appeal',
    subtitle: 'Seeking review of the trial court\'s decision by a higher court',
    rules: [
      { rule: '28 USC §1291', slug: null, description: 'Final decision rule — courts of appeals have jurisdiction over final decisions' },
      { rule: '28 USC §1292', slug: null, description: 'Interlocutory appeals — immediate appeal of certain non-final orders' },
      { rule: 'Rule 54', slug: 'rule-54', description: 'Judgment; costs — defines "final judgment"' },
    ],
    keyCases: [
      'Liberty Mutual Insurance Co. v. Wetzel (1976)',
    ],
  },
  {
    id: 10,
    title: 'Enforcement',
    subtitle: 'Collecting on the judgment after all appeals are exhausted',
    rules: [
      { rule: 'Rule 69', slug: 'rule-69', description: 'Execution — proceedings to enforce a money judgment' },
      { rule: 'Rule 70', slug: 'rule-70', description: 'Enforcing a judgment for a specific act' },
    ],
  },
]
