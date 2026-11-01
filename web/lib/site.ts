// Absolute origin of the deployed site, used for metadataBase, canonicals,
// robots.txt and the sitemap. Resolved from the first of:
//
//   1. NEXT_PUBLIC_SITE_URL — an explicit override, for a custom domain that is
//      not yet the project's primary one. Config, not Secret: Vercel refuses a
//      NEXT_PUBLIC_ secret, and the value is public anyway.
//   2. VERCEL_PROJECT_PRODUCTION_URL — set by Vercel on every deployment,
//      preview included, to the shortest production domain. So production is
//      correct with nothing configured, and a preview canonicalises to
//      production rather than to itself, which is the safe direction if
//      deployment protection is ever lifted.
//   3. http://localhost:3000 — local dev.
//
// The last resort is localhost rather than a plausible-looking domain on
// purpose: canonicals and a sitemap pointing at a domain nobody owns are far
// harder to notice than an obviously local URL that fails review at a glance.
//
// Both env vars are read on the server only (this module is imported by
// app/layout.tsx, app/robots.ts and app/sitemap.ts, all server). The Vercel one
// has no NEXT_PUBLIC_ prefix, so it is undefined in the browser —
// `npm run check:routes` fails if a 'use client' file ever imports this module,
// which would silently downgrade SITE_URL to localhost there.
const FALLBACK_SITE_URL = 'http://localhost:3000'

/**
 * Vercel's system variables are bare hosts with no scheme
 * (`credit-simulator-xyz.vercel.app`), so `new URL` would reject them as-is.
 */
function withScheme(host: string): string {
  return /^https?:\/\//.test(host) ? host : `https://${host}`
}

/** Requires "Automatically expose System Environment Variables" on the project. */
function vercelProductionUrl(): string | undefined {
  const host = process.env.VERCEL_PROJECT_PRODUCTION_URL
  return host ? withScheme(host) : undefined
}

/**
 * `new URL(raw).origin` rather than the raw value: it drops a trailing slash, a
 * pasted path and a query string, so only scheme + host + port survive.
 *
 * The throw is deliberate — a malformed value must fail the build rather than
 * ship canonicals pointing nowhere. It names the variable the value actually
 * came from, because the likely mistake is a value with no scheme
 * (`example.com`) typed into the Vercel dashboard, and `new URL` alone would
 * fail the deploy with a bare `TypeError: Invalid URL` pointing at
 * app/layout.tsx.
 */
function resolveSiteUrl(raw: string, source: string): string {
  try {
    return new URL(raw).origin
  } catch {
    throw new Error(
      `${source} is not a valid absolute URL: ${JSON.stringify(raw)}. ` +
        `Expected an origin with a scheme, e.g. https://example.com`
    )
  }
}

/** First source that supplies a value wins; the name travels with it, for the error. */
function siteUrlSource(): { raw: string; source: string } {
  const override = process.env.NEXT_PUBLIC_SITE_URL
  if (override) return { raw: override, source: 'NEXT_PUBLIC_SITE_URL' }

  const vercel = vercelProductionUrl()
  if (vercel) return { raw: vercel, source: 'VERCEL_PROJECT_PRODUCTION_URL' }

  return { raw: FALLBACK_SITE_URL, source: 'the built-in localhost fallback' }
}

const { raw, source } = siteUrlSource()

export const SITE_URL = resolveSiteUrl(raw, source)

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
