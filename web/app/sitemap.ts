import type { MetadataRoute } from 'next'
import { PUBLIC_PATHS, SITE_URL } from '@/lib/site'

// Only the pages a visitor can reach without signing in. The private routes are
// listed in lib/site.ts and carry `robots: { index: false }` in their layouts.
//
// No `lastModified`: it is generated at build time, so every deploy would claim
// every page had just changed. A sitemap without lastmod is valid, and a crawler
// trusts an absent hint more than a wrong one.
export default function sitemap(): MetadataRoute.Sitemap {
  return PUBLIC_PATHS.map((path) => ({
    url: `${SITE_URL}${path}`,
    changeFrequency: path === '/rates' ? 'weekly' : 'monthly',
  }))
}
