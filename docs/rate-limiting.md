# API rate limiting

`api/limiter.py` limits the compute-heavy endpoints (`/api/simulate` 20/min, `/api/simulate/all` and `/api/simulate/heatmap` 10/min, profile refresh 5/min) with an in-memory slowapi limiter. What matters is the **bucket key**: if every request gets the same key, one busy client throttles everyone.

## Why the key needed fixing

The key used to be the TCP peer address. On Render that peer is the load balancer, and uvicorn only trusts `X-Forwarded-For` from `127.0.0.1` by default, so **all users shared one bucket**. Simply trusting `X-Forwarded-For` would not work either: Render appends to a client-supplied value instead of replacing it, so the leftmost entry is whatever the client sent.

## How the key is chosen now

In order:

1. **`user:<id>`**: `optional_user` verified a Supabase JWT or an API key (it stores the id on `request.state.user_id`). Only routes that depend on `optional_user` see it: `/api/simulate` and `/api/simulate/all`.
2. **`ip:<X-Client-IP>`**: the request carries `X-Proxy-Secret` equal to `API_PROXY_SECRET`. The web app's middleware (`web/middleware.ts`) adds both headers when it proxies `/api/*` on Vercel, taking the address from `x-real-ip`, which Vercel overwrites to prevent spoofing. A wrong or unexpected secret is rejected with 403.
3. **`ip:<X-Forwarded-For entry>`**: counted `TRUSTED_PROXY_HOPS` entries **from the right**. Proxies append on the right, so a client can only add entries on the left and cannot pick its own key.
4. **`ip:<peer>`**: no `X-Forwarded-For` at all (local dev, tests).

A request that has `X-Forwarded-For` while `TRUSTED_PROXY_HOPS` is unset is **rejected with 503**, never keyed on the proxy's address. The log line says how many entries the header had (never the addresses).

## Configuration

| Where | Variable | Value |
|---|---|---|
| Render (API) | `API_PROXY_SECRET` | a long random string, e.g. `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| Vercel (web) | `API_PROXY_SECRET` | the same string (not `NEXT_PUBLIC_`: it must never reach the browser) |
| Vercel (web) | `BACKEND_URL` | the Render service URL; the middleware proxies to it |
| Render (API) | `TRUSTED_PROXY_HOPS` | number of proxies that append to `X-Forwarded-For` in front of the API, for calls that do not come through the web app |

### Choosing `TRUSTED_PROXY_HOPS`

Render does not document its proxy chain. Measure it once:

1. Deploy with `TRUSTED_PROXY_HOPS` unset.
2. Call the API directly, without sending any `X-Forwarded-For` yourself: `curl -X POST https://<api>/api/simulate/heatmap -H "Content-Type: application/json" -d '{"property_price":"300000","monthly_net_income":"4000","available_savings":"80000"}'`. It returns 503.
3. Render's logs show `X-Forwarded-For has N entries`. Set `TRUSTED_PROXY_HOPS=N`: with no client-supplied entries, all N were added by Render, and the leftmost of them is your address.

Until then, direct anonymous calls get 503; calls through the web app (secret header) and authenticated calls are unaffected.
