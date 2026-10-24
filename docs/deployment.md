# Deployment Guide

## Architecture

One Vercel project with two [Services](https://vercel.com/docs/services) (beta), declared in the root `vercel.json`:

```
                       ┌── /api/*  ──▶  api  (FastAPI, Python functions) ──supabase-py──▶  Supabase
browser ──▶  Vercel  ──┤
                       └── /*      ──▶  web  (Next.js)
```

- The browser calls `/api/...` on the site's own origin: no CORS, and the CSP `connect-src` stays `'self'` + Supabase.
- The API receives the original path (`/api/simulate`), so its routes keep their `/api` prefix.
- No always-on server: functions start in about a second when idle, instead of Render's free-tier sleep of 50 s or more.
- Rate-limit counters live in Redis (Upstash), because each function instance has its own memory. See [rate-limiting.md](rate-limiting.md).

Both services send security headers. See [security-headers.md](security-headers.md).

---

## 1. Vercel project

### Settings

- **Root Directory**: `.` (the repository root, where `vercel.json` declares the services). Not `web`.
- **Framework Preset**: Services (detected from `vercel.json`).
- `web/vercel.json` only applies when `web` is the Root Directory; with Services it is not used for routing.

### Python entrypoint and dependencies

- `[tool.vercel] entrypoint = "api.vercel:app"` in `pyproject.toml`, repeated in `vercel.json`. `api/vercel.py` puts `src/` on the import path, then imports `api.main:app`.
- The API's runtime packages (`fastapi`, `supabase`, `slowapi`, `redis`) are in `[project].dependencies`, because Vercel installs those; its docs do not say it installs optional extras. The `web` extra only holds `uvicorn`, for running the API locally.

### Environment variables

| Variable | Vercel type | Used by | Value |
|---|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | **Config** | web | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | **Config** | web | Supabase publishable (or legacy anon) key |
| `SUPABASE_URL` | Secret | api | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Secret | api | Supabase **secret key** (`sb_secret_...`), bypasses RLS. Scope it to the `api` service if the dashboard offers service-level variables. |
| `RATE_LIMIT_STORAGE_URL` | Secret | api | Upstash Redis URL (`rediss://...`). `REDIS_URL` is read as a fallback, which is the name the Upstash integration creates. |
| `TRUSTED_CLIENT_IP_HEADER` | Secret | api | `x-real-ip`: Vercel overwrites it with the real client address |
| `ALLOWED_ORIGINS` | Secret | api | optional, only for browser apps on other origins calling the API |

- Vercel refuses a `NEXT_PUBLIC_` variable of type *Secret* ("Remove the public framework prefix..."). Those names are inlined into the browser bundle, so they must be type **Config**. Both Supabase values above are public by design (RLS protects the data). Never give a `NEXT_PUBLIC_` name to anything secret.
- Leave `BACKEND_URL` unset on Vercel: it only feeds the local-dev `/api` rewrite in `next.config.mjs`.
- **Supabase's Vercel integration** creates names the app does not read (`NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`), plus `POSTGRES_*`, `SUPABASE_JWT_SECRET` and `SUPABASE_SECRET_KEY`. Keep only the variables in the table: the database password and the JWT signing secret must not sit in the project. If the integration keeps re-adding them, disconnect it.
- Environment-variable changes take effect on the next deployment.

### Rate-limit storage (Upstash Redis)

1. Vercel → **Storage** (or Marketplace) → **Upstash for Redis** → create a database on the free plan, in a region close to the functions (Frankfurt), and connect it to the project.
2. The integration adds `REDIS_URL` (and REST variables the API does not use). If it is named differently, copy its `rediss://` URL into `RATE_LIMIT_STORAGE_URL`.
3. With `TRUSTED_CLIENT_IP_HEADER` set and no storage URL, the rate-limited endpoints answer **503** instead of falling back to per-instance memory.

### After the first deploy

- Add the deployment URL to Supabase → Authentication → URL Configuration (Site URL and redirect URLs), see [supabase-setup.md](supabase-setup.md).
- Check `/api/docs` and run a simulation from the site.

---

## 2. Local dev

API (from the repo root):

```bash
pip install -e ".[dev,web]"
python -m uvicorn api.main:app --reload     # http://localhost:8000
```

Requires `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in the environment (or `api/.env`). Without `RATE_LIMIT_STORAGE_URL` and `TRUSTED_CLIENT_IP_HEADER`, the limiter keeps counters in memory and keys on the peer address, which is right for one local process.

Web:

```bash
cd web
npm install
npm run dev        # http://localhost:3000, /api/* is rewritten to BACKEND_URL (default http://localhost:8000)
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

## 4. Render (retired)

The API used to run on Render (`render.yaml`, free plan). The free instance slept after inactivity and took 50 s or more to wake, which is why it moved to Vercel. `render.yaml` is kept until the Vercel cut-over is verified, then deleted with the Render service.

---

## 5. Post-deployment checklist

- [ ] Vercel Root Directory is `.` and both services built.
- [ ] Upstash Redis connected; `RATE_LIMIT_STORAGE_URL` (or `REDIS_URL`) and `TRUSTED_CLIENT_IP_HEADER=x-real-ip` set.
- [ ] The Vercel URL is in Supabase Auth → URL Configuration → Redirect URLs.
- [ ] `/api/docs` loads on the site's own domain.
- [ ] A simulation runs end-to-end, and the 11th heatmap call within a minute returns 429.
