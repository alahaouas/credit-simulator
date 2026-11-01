import type { MetadataRoute } from 'next'
import { PRIVATE_PATHS, SITE_URL } from '@/lib/site'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      // Disallow matches by prefix, so '/auth' covers '/auth' and '/auth/callback'.
      // /api/* is the FastAPI service (routed by the root vercel.json), including its
      // OpenAPI docs: nothing there is a search result.
      disallow: ['/api/', ...PRIVATE_PATHS],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  }
}
