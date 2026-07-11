import { describe, expect, it } from 'vitest'
import { sanitizeLegalHtml } from './sanitizeHtml'

describe('sanitizeLegalHtml', () => {
  it('retains legal formatting and tables', () => {
    const html = '<p><strong>Holding:</strong> affirmed.</p><table><tr><th scope="col">Rule</th></tr></table>'
    expect(sanitizeLegalHtml(html)).toBe(html)
  })

  it('removes scripts, event handlers, styles, and embedded content', () => {
    const result = sanitizeLegalHtml(
      '<script>alert(1)</script><p onclick="steal()" style="display:none">Text</p><iframe src="https://evil.test"></iframe>',
    )
    expect(result).toBe('<p>Text</p>')
  })

  it('removes unsafe URL schemes', () => {
    const result = sanitizeLegalHtml(
      '<a href="javascript:alert(1)">bad</a><img src="data:image/svg+xml,evil"><a href="https://lawstudygroup.com">safe</a>',
    )
    expect(result).toBe('<a>bad</a><img /><a href="https://lawstudygroup.com">safe</a>')
  })

  it('styles search highlights without retaining supplied classes', () => {
    const result = sanitizeLegalHtml('<em class="attacker">match</em>', {
      highlightSearchTerms: true,
    })
    expect(result).toContain('class="font-semibold text-sage-700')
    expect(result).not.toContain('attacker')
  })
})
