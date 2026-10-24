/* global process, URL */
/** @type {import('next').NextConfig} */
const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000'

const isDev = process.env.NODE_ENV !== 'production'

/** Origin of a configured URL, or '' when unset or malformed. */
function origin(url) {
  try {
    return url ? new URL(url).origin : ''
  } catch {
    return ''
  }
}

// The browser talks to Supabase directly; the API is same-origin (/api/*).
const connectSrc = ["'self'", origin(process.env.NEXT_PUBLIC_SUPABASE_URL)]
  .filter(Boolean)
  .join(' ')

const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ''}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  `connect-src ${connectSrc}`,
  "object-src 'none'",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join('; ')

// Applied to every response, including errors and redirects.
const securityHeaders = [
  { key: 'Content-Security-Policy', value: csp },
  { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
]

const nextConfig = {
  poweredByHeader: false,
  // Browsers must never receive .map files: they would expose the original TypeScript.
  productionBrowserSourceMaps: false,
  async headers() {
    return [{ source: '/:path*', headers: securityHeaders }]
  },
  experimental: {
    // Tree-shake package imports so webpack serializes smaller module chunks,
    // eliminating the "Serializing big strings" pack-cache warnings in dev.
    optimizePackageImports: ['recharts', '@supabase/supabase-js', '@supabase/ssr'],
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${BACKEND_URL}/api/:path*`,
      },
    ]
  },
}

export default nextConfig
