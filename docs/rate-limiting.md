# API rate limiting

`api/limiter.py` limits the compute-heavy endpoints (`/api/simulate` 20/min, `/api/simulate/all` and `/api/simulate/heatmap` 10/min, profile refresh 5/min) with slowapi. Two things decide whether it actually limits anyone:

- **Where the counters live.** On Vercel the API runs as serverless functions, many short-lived instances each with its own memory. In-memory counters would start from zero on every new instance, so they live in Redis (`RATE_LIMIT_STORAGE_URL`, falling back to `REDIS_URL`; an Upstash `rediss://` URL).
- **The bucket key.** If every request gets the same key, one busy client throttles everyone. If a client can choose its key, it escapes the limit.

## How the key is chosen

In order:

1. **`user:<id>`**: `optional_user` verified a Supabase JWT or an API key (it stores the id on `request.state.user_id`). Only routes that depend on `optional_user` see it: `/api/simulate` and `/api/simulate/all`.
2. **`ip:<TRUSTED_CLIENT_IP_HEADER>`**: on Vercel, `x-real-ip`. Vercel [overwrites `x-forwarded-for` / `x-real-ip`](https://vercel.com/docs/headers/request-headers) with the real client address, so a client cannot set it. A missing header is rejected (503). This mode also **requires** the Redis storage: without it, the limited endpoints answer 503.
3. **`ip:<X-Forwarded-For entry>`**: counted `TRUSTED_PROXY_HOPS` entries **from the right**, for a host behind a proxy chain that appends to the header (the old Render deployment needed `3`). Proxies append on the right, so a client can only add entries on the left.
4. **`ip:<peer>`**: no `X-Forwarded-For` at all (local dev, tests).

A request with `X-Forwarded-For` and neither of the settings above is **rejected with 503**, never keyed on the proxy's address. The log line says how many entries the header had (never the addresses), which is how `TRUSTED_PROXY_HOPS` is measured on a new host.

## Configuration on Vercel

| Variable | Value |
|---|---|
| `TRUSTED_CLIENT_IP_HEADER` | `x-real-ip` |
| `RATE_LIMIT_STORAGE_URL` (or `REDIS_URL` from the Upstash integration) | `rediss://default:<password>@<host>:6379` |

## History

- The limiter first keyed on the TCP peer. Behind Render's load balancer that was the balancer itself, so **all users shared one bucket**.
- A proxy-secret scheme followed (#256): the Next.js middleware forwarded the visitor's address to Render with a shared secret.
- It was removed when the API moved into the same Vercel project as the web app. The API now reads Vercel's own header directly.
