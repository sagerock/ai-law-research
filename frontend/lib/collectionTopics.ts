export interface CaseTopic {
  id: string
  label: string
  topic: string
  topic_rank: number
  sort_order: number
  is_primary: boolean
}

export interface DoctrineCount {
  id: string
  label: string
  sort_order: number
  count: number
}

export interface TopicGroup {
  topic: string
  topic_rank: number
  doctrines: DoctrineCount[]
}

/** Doctrines present in a collection, grouped under their topic in taxonomy order. */
export function groupDoctrines(cases: { topics?: CaseTopic[] }[]): TopicGroup[] {
  const groups = new Map<string, TopicGroup>()
  const counts = new Map<string, DoctrineCount>()
  for (const c of cases) {
    for (const t of c.topics ?? []) {
      let group = groups.get(t.topic)
      if (!group) {
        group = { topic: t.topic, topic_rank: t.topic_rank, doctrines: [] }
        groups.set(t.topic, group)
      }
      let doctrine = counts.get(t.id)
      if (!doctrine) {
        doctrine = { id: t.id, label: t.label, sort_order: t.sort_order, count: 0 }
        counts.set(t.id, doctrine)
        group.doctrines.push(doctrine)
      }
      doctrine.count += 1
    }
  }
  return [...groups.values()]
    .sort((a, b) => a.topic_rank - b.topic_rank)
    .map(g => ({ ...g, doctrines: [...g.doctrines].sort((a, b) => a.sort_order - b.sort_order) }))
}

export function hasDoctrine(c: { topics?: CaseTopic[] }, doctrineId: string): boolean {
  return (c.topics ?? []).some(t => t.id === doctrineId)
}
