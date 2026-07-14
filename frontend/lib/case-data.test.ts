import { describe, expect, it } from 'vitest'
import { caseYear } from './case-data'

describe('caseYear', () => {
  it('keeps date-only values in their UTC year', () => {
    expect(caseYear('1938-01-01')).toBe('1938')
  })

  it('returns an empty value for missing or invalid dates', () => {
    expect(caseYear()).toBe('')
    expect(caseYear('not-a-date')).toBe('')
  })
})
