/* global process */
/** @type {import('next').NextConfig} */
const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000'

const nextConfig = {
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
