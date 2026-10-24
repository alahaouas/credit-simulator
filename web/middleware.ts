import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

/**
 * Proxies /api/* to the FastAPI backend with the caller's address, so the API's rate
 * limiter has one bucket per visitor instead of one for the whole site. Vercel overwrites
 * x-forwarded-for / x-real-ip with the real client address, so they cannot be spoofed
 * here; the shared secret proves to the API that the address came from this proxy.
 * Without API_PROXY_SECRET or BACKEND_URL, the plain rewrite in next.config.mjs applies.
 */
function proxyApi(request: NextRequest): NextResponse | null {
  const secret = process.env.API_PROXY_SECRET
  const backend = process.env.BACKEND_URL
  if (!secret || !backend) return null

  const clientIp =
    request.headers.get('x-real-ip') ??
    request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ??
    ''
  const headers = new Headers(request.headers)
  // The site's Host would make Render's router look for a service by that name.
  headers.delete('host')
  headers.set('x-proxy-secret', secret)
  headers.set('x-client-ip', clientIp)

  const target = new URL(request.nextUrl.pathname + request.nextUrl.search, backend)
  return NextResponse.rewrite(target, { request: { headers } })
}

export async function middleware(request: NextRequest) {
  if (request.nextUrl.pathname.startsWith('/api/')) {
    return proxyApi(request) ?? NextResponse.next()
  }

  let response = NextResponse.next({ request })

  if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    return response
  }

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    {
      global: {
        fetch: (url, init) =>
          fetch(url, init).catch(() => new Response(null, { status: 503 })),
      },
      cookies: {
        getAll() { return request.cookies.getAll() },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value))
          response = NextResponse.next({ request })
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  await supabase.auth.getUser().catch(() => {})
  return response
}

// Run only on /api (proxy above) and on routes that need a fresh Supabase session
// cookie. Public pages (`/`, `/simulate`, `/results`) read auth state client-side
// and don't need middleware overhead on every request.
export const config = {
  matcher: [
    '/api/:path*',
    '/auth/:path*',
    '/history/:path*',
    '/preferences/:path*',
    '/settings/:path*',
  ],
}
