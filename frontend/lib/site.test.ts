import { describe, expect, it } from 'vitest'
import nextConfig from '../next.config'
import { BRAND_NAME, CANONICAL_SITE_URL, LEGACY_HOST, SITE_TAGLINE, SITE_URL } from './site'

describe('site configuration', () => {
  it('uses Tortwell as the canonical brand', () => {
    expect(BRAND_NAME).toBe('Tortwell')
    expect(SITE_TAGLINE).toBe('Free law-school study tools, sourced to the opinion')
    expect(SITE_URL).toBe(CANONICAL_SITE_URL)
  })

  it('permanently redirects the legacy host while preserving the path', async () => {
    const redirects = await nextConfig.redirects?.()
    expect(redirects).toContainEqual({
      source: '/:path*',
      has: [{ type: 'host', value: LEGACY_HOST }],
      destination: `${CANONICAL_SITE_URL}/:path*`,
      permanent: true,
    })
    expect(redirects).toContainEqual({
      source: '/:path*',
      has: [{ type: 'host', value: 'www.tortwell.com' }],
      destination: `${CANONICAL_SITE_URL}/:path*`,
      permanent: true,
    })
  })
})
