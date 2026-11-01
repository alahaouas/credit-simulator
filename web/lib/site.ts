// Absolute origin of the deployed site, used for metadataBase, canonicals,
// robots.txt and the sitemap.
//
// NEXT_PUBLIC_SITE_URL must be set on Vercel (Config, not Secret — the value is
// public and gets inlined into the bundle). The fallback is localhost on
// purpose: a wrong-but-plausible production guess would publish canonicals and
// a sitemap pointing at a domain nobody owns, which is worse than an obviously
// local URL that fails review at a glance.
export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000').replace(
  /\/+$/,
  ''
)

/** Paths that are crawlable and listed in the sitemap. */
export const PUBLIC_PATHS = ['/', '/simulate', '/rates', '/legal'] as const

/**
 * Paths excluded from search. Every one of them either needs a session (and so
 * redirects to /auth, which search engines record as a soft 404) or renders
 * per-request state from query parameters, which would generate unbounded
 * near-duplicate URLs.
 */
export const PRIVATE_PATHS = [
  '/auth',
  '/results',
  '/compare',
  '/history',
  '/preferences',
  '/settings',
  '/alerts',
  '/share',
] as const
