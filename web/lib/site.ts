// Absolute origin of the deployed site, used for metadataBase, canonicals,
// robots.txt and the sitemap.
//
// NEXT_PUBLIC_SITE_URL must be set on Vercel (Config, not Secret — the value is
// public and gets inlined into the bundle). The fallback is localhost on
// purpose: a wrong-but-plausible production guess would publish canonicals and
// a sitemap pointing at a domain nobody owns, which is worse than an obviously
// local URL that fails review at a glance.
const FALLBACK_SITE_URL = 'http://localhost:3000'

/**
 * `new URL(raw).origin` rather than the raw value: it drops a trailing slash, a
 * pasted path and a query string, so only scheme + host + port survive.
 *
 * The throw is deliberate — a malformed value must fail the build rather than
 * ship canonicals pointing nowhere. It names the variable because the likely
 * mistake is a value with no scheme (`example.com`), typed into the Vercel
 * dashboard, and `new URL` alone would fail the deploy with a bare
 * `TypeError: Invalid URL` pointing at app/layout.tsx.
 */
function resolveSiteUrl(raw: string): string {
  try {
    return new URL(raw).origin
  } catch {
    throw new Error(
      `NEXT_PUBLIC_SITE_URL is not a valid absolute URL: ${JSON.stringify(raw)}. ` +
        `Expected an origin with a scheme, e.g. https://example.com`
    )
  }
}

export const SITE_URL = resolveSiteUrl(process.env.NEXT_PUBLIC_SITE_URL || FALLBACK_SITE_URL)

// Both lists are checked against the filesystem by `npm run check:routes`, so a
// new route segment cannot quietly end up in neither.

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
