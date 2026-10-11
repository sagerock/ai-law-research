import { describe, expect, it } from 'vitest'
import { groupDoctrines, hasDoctrine, type CaseTopic } from './collectionTopics'

const tag = (id: string, topic: string, topic_rank: number, sort_order: number, is_primary = false): CaseTopic => ({
  id, label: id.split(':')[1], topic, topic_rank, sort_order, is_primary,
})

const ripeness = tag('con-law:ripeness', 'Justiciability', 0, 5, true)
const mootness = tag('con-law:mootness', 'Justiciability', 0, 6)
const commerce = tag('con-law:commerce', 'Legislative Power', 1, 20, true)

describe('groupDoctrines', () => {
  it('groups by topic in taxonomy order and counts each doctrine', () => {
    const groups = groupDoctrines([
      { topics: [commerce] },
      { topics: [mootness, ripeness] },
      { topics: [ripeness] },
      {},
    ])
    expect(groups.map(g => g.topic)).toEqual(['Justiciability', 'Legislative Power'])
    expect(groups[0].doctrines.map(d => [d.label, d.count])).toEqual([['ripeness', 2], ['mootness', 1]])
  })

  it('returns nothing when no case is tagged', () => {
    expect(groupDoctrines([{ topics: [] }, {}])).toEqual([])
  })
})

describe('hasDoctrine', () => {
  it('matches primary and secondary tags', () => {
    expect(hasDoctrine({ topics: [ripeness, mootness] }, 'con-law:mootness')).toBe(true)
    expect(hasDoctrine({ topics: [ripeness] }, 'con-law:commerce')).toBe(false)
    expect(hasDoctrine({}, 'con-law:ripeness')).toBe(false)
  })
})
