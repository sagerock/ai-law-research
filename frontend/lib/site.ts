export const BRAND_NAME = 'Tortwell'
export const SITE_TAGLINE = 'Free law-school study tools, sourced to the opinion'
export const CANONICAL_SITE_URL = 'https://tortwell.com'
export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || CANONICAL_SITE_URL).replace(/\/$/, '')
export const LEGACY_HOST = 'lawstudygroup.com'

// Default social share (Open Graph / Twitter) image. Lives in frontend/public.
// Shared across every page because Next.js replaces the whole `openGraph` object
// in child segments rather than deep-merging it — any page that sets its own
// openGraph must re-include this image or it gets none.
export const SOCIAL_IMAGE_PATH = '/tortwell-social-featured.png'
export const SOCIAL_IMAGE = {
  url: SOCIAL_IMAGE_PATH,
  width: 1200,
  height: 627,
  alt: `${BRAND_NAME} — ${SITE_TAGLINE}`,
}
