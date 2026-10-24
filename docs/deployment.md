# Deployment Guide

## Architecture

```
Vercel (Next.js)  ──fetch──▶  Render (FastAPI)  ──supabase-py──▶  Supabase
```

Both services send security headers; the web CSP only allows the Supabase and API hosts set in `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_API_URL` at build time. See [security-headers.md](security-headers.md).

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

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon/public key |
| `BACKEND_URL` | Render service URL, e.g. `https://credit-simulator-api.onrender.com`. Read at build time by the `/api/*` rewrite in `next.config.mjs`. |

Leave `NEXT_PUBLIC_API_URL` unset in production. The browser then calls `/api/...` on the site's own origin and Next.js forwards it to `BACKEND_URL` server-side, so Render needs no CORS entry for the site, the CSP `connect-src` stays `'self'` + Supabase, and the Render URL is not in the browser bundle. Setting `NEXT_PUBLIC_API_URL` instead makes the browser call Render directly: add the site's origin to Render's `ALLOWED_ORIGINS` then, and the CSP picks the API origin up at build time.

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
NEXT_PUBLIC_API_URL=http://localhost:8000
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
