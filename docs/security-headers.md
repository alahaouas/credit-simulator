# Security headers and source protection

## Web (Next.js, `web/next.config.mjs`)

Every response, including errors and redirects, carries:

| Header | Value |
|---|---|
| `Content-Security-Policy` | `default-src 'self'`; scripts and styles from `'self'` plus `'unsafe-inline'` (Next.js hydration scripts, inline styles); `connect-src` = `'self'` + the origin of `NEXT_PUBLIC_SUPABASE_URL` (the API is same-origin under `/api`); `frame-ancestors 'none'`, `object-src 'none'`, `base-uri` and `form-action 'self'` |
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | camera, microphone and geolocation disabled |

`connect-src` is built **at build time** from the two `NEXT_PUBLIC_*` variables. If the browser must reach another host (a new API URL, a second Supabase project, an analytics endpoint), add it there, or the request is blocked and the feature fails with only a console error. After a deploy, check the browser console for `Content Security Policy` errors.

`productionBrowserSourceMaps: false` and `poweredByHeader: false` are set explicitly: browsers never receive `.map` files, so the original TypeScript is not served.

## API (FastAPI, `api/main.py`)

A middleware adds `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` and `Referrer-Policy: no-referrer` to every response, including CORS preflight and error responses (`tests/api/test_main.py::TestSecurityHeaders`). There is deliberately no CSP on the API: it serves JSON, and `/api/docs` loads Swagger UI from a CDN.

## Licence and legal notice

- `LICENSE`: proprietary, CODYNAMICS SRL. The repository is public, so the code is readable; the licence is what forbids copying and reuse.
- `pyproject.toml` carries `Private :: Do Not Upload`, so PyPI rejects any upload of the package.
- `/legal` shows the publisher's identity from `web/lib/company.ts`; every page links to it from the footer.
- `web/THIRD-PARTY-NOTICES.md` lists the open-source packages shipped by the web app. Regenerate it after a dependency change: `node ../scripts/generate-third-party-notices.cjs "Credit Simulator"` from `web/`.
