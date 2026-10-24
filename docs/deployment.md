# Deployment Guide

## Architecture

```
Vercel (Next.js)  ──fetch──▶  Render (FastAPI)  ──supabase-py──▶  Supabase
```

Both services send security headers; the web CSP only allows the Supabase host set in `NEXT_PUBLIC_SUPABASE_URL` at build time; the browser reaches the API on the site's own origin (`/api/*`). See [security-headers.md](security-headers.md).

---

## 1. FastAPI on Render

### One-time setup

1. Connect the GitHub repo to [render.com](https://render.com).
2. Create a new **Web Service** — Render will detect `render.yaml` automatically.
3. Set the following environment variables in the Render dashboard:

| Variable | Description |
|---|---|
| `SUPABASE_URL` | Project URL from Supabase dashboard → Settings → API |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (keep secret — server-side only) |
| `ALLOWED_ORIGINS` | Comma-separated list of allowed frontend origins, e.g. `https://your-app.vercel.app` |
| `API_PROXY_SECRET` | Shared secret with the Vercel project (same value there); lets the rate limiter trust the client address the web app forwards. See [rate-limiting.md](rate-limiting.md). |
| `TRUSTED_PROXY_HOPS` | Proxies in front of the API that append to `X-Forwarded-For`; measure it as described in [rate-limiting.md](rate-limiting.md). Unset = direct anonymous calls get 503. |

4. Deploy. The service URL will be `https://credit-simulator-api.onrender.com` (or similar).

### Local dev

```bash
# from repo root
pip install -e ".[web]"
python -m uvicorn api.main:app --reload
```

Requires `api/.env`:
```
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service_role_key>
```

---

## 2. Next.js on Vercel

### One-time setup

1. Import the GitHub repo in the [Vercel dashboard](https://vercel.com/new). Vercel detects two services (it reads `render.yaml`) and offers a multi-service project: choose **Import single project** on `web` instead. The API stays on Render, and the suggested multi-service `vercel.json` would route every path, pages included, to the API.
2. Check that **Root Directory** is `web` and the framework is Next.js.
3. Add the environment variables in the dashboard, for Production and Preview. `web/vercel.json` holds build settings only: its old `@secret` references were removed because Vercel retired Secrets.

| Variable | Vercel type | Description |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | **Config** | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | **Config** | Supabase publishable (or legacy anon) key |
| `BACKEND_URL` | Secret | Render service URL, e.g. `https://credit-simulator-api.onrender.com`, no trailing slash. `web/middleware.ts` proxies `/api/*` to it (the `next.config.mjs` rewrite is the fallback when `API_PROXY_SECRET` is unset). |
| `API_PROXY_SECRET` | Secret | Same random value as on Render. The middleware sends it with the visitor's address so the API rate-limits per visitor; see [rate-limiting.md](rate-limiting.md). Never `NEXT_PUBLIC_`. |

Vercel refuses a `NEXT_PUBLIC_` variable of type *Secret* ("Remove the public framework prefix..."): those names are inlined into the browser bundle, so they must be type **Config**. Both Supabase values above are public by design (RLS protects the data). Never give a `NEXT_PUBLIC_` name to anything secret.

**Supabase's Vercel integration** creates other names than the app reads: `SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (the code reads `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`), plus `POSTGRES_*` and `SUPABASE_JWT_SECRET`. The web app uses none of them. Add the two names above yourself, check that `SUPABASE_URL` points at the existing project (not a new empty one the integration created), and delete the unused `POSTGRES_*` and `SUPABASE_JWT_SECRET`: the database password and the JWT signing secret do not belong in the web project.

The browser always calls `/api/...` on the site's own origin; Next.js forwards it to `BACKEND_URL` server-side. Render needs no CORS entry for the site, the CSP `connect-src` stays `'self'` + Supabase, and the Render URL is not in the browser bundle.

4. Deploy. Vercel reads `web/vercel.json` for build settings.
5. Add the deployment URL to Supabase → Authentication → URL Configuration (Site URL and redirect URLs), see [supabase-setup.md](supabase-setup.md).

### Local dev

```bash
cd web
npm install
npm run dev        # http://localhost:3000
```

Requires `web/.env.local`:
```
NEXT_PUBLIC_SUPABASE_URL=https://<project>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon_key>
```

---

## 3. Supabase

- Single project used for both local dev and production.
- Auth: magic-link email (no OAuth configured).
- Schema managed via `supabase/migrations/`. Apply with `supabase db push`.
- See [supabase-setup.md](supabase-setup.md) for initial setup steps.

---

## 4. Post-deployment checklist

- [ ] Set `ALLOWED_ORIGINS` on Render to include the Vercel URL.
- [ ] Add the Vercel URL to Supabase Auth → URL Configuration → Redirect URLs.
- [ ] Verify `/api/docs` is reachable on the Render URL.
- [ ] Run a simulation end-to-end through the production frontend.
