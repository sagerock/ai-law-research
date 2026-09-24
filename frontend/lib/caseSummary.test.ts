import { describe, expect, it } from 'vitest'

import { hasDisplayableBrief } from './caseSummary'

describe('hasDisplayableBrief', () => {
  it('accepts an approved structured candidate without a legacy summary', () => {
    expect(hasDisplayableBrief({
      summary: null,
      structured_candidates: [{ provider: 'claude' }],
    })).toBe(true)
  })

  it('accepts a legacy summary and rejects an empty payload', () => {
    expect(hasDisplayableBrief({ summary: 'Legacy brief.' })).toBe(true)
    expect(hasDisplayableBrief({ summary: null, structured_candidates: [] })).toBe(false)
  })
})
