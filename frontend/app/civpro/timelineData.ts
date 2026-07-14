import outline from '@/content/outlines/civil-procedure.json'

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
  // 'doctrine' sections (PJ, SMJ, Erie, venue) belong to the outline but not
  // to the chronological litigation timeline; undefined means process stage.
  kind?: string
  rules: Rule[]
  branches?: Branch[]
  keyCases?: KeyCase[]
  concepts?: Concept[]
  isWide?: boolean
  discoveryTools?: { name: string; description: string }[]
}

export const stages = (outline.sections as Stage[]).filter(
  (s) => s.kind !== 'doctrine'
)
