"""Shared slowapi rate limiter for compute-heavy / external-call endpoints.

Per-process, in-memory limiter. Sufficient for a single-instance deployment;
a multi-instance deployment would need a shared backend (e.g. Redis) instead.

The bucket key (see docs/rate-limiting.md) is, in order:
1. ``user:<id>`` when ``optional_user`` verified a Supabase JWT or API key;
2. ``ip:<client>`` from ``X-Client-IP`` when the request carries the shared
   ``API_PROXY_SECRET`` (set by the web app's middleware on Vercel);
3. ``ip:<client>`` from ``X-Forwarded-For``, counted ``TRUSTED_PROXY_HOPS``
   entries from the right: proxies append on the right, so a client can only
   add entries on the left and cannot choose its own key;
4. ``ip:<peer>`` when there is no ``X-Forwarded-For`` at all (direct connection).

A proxied request that matches none of these is rejected rather than keyed on
the proxy's address: that shared key would put every user in one bucket.
"""

from __future__ import annotations

import hmac
import logging
import os

from fastapi import HTTPException, Request
from slowapi import Limiter

logger = logging.getLogger(__name__)

PROXY_SECRET_HEADER = "x-proxy-secret"
CLIENT_IP_HEADER = "x-client-ip"


def _trusted_proxy_hops() -> int | None:
    raw = os.environ.get("TRUSTED_PROXY_HOPS", "").strip()
    if not raw:
        return None
    try:
        hops = int(raw)
    except ValueError:
        hops = 0
    if hops < 1:
        # The value itself is not logged: a secret pasted into the wrong variable must not leak.
        logger.error("TRUSTED_PROXY_HOPS must be a positive integer")
        raise HTTPException(status_code=503, detail="Rate limiting is misconfigured")
    return hops


def client_key(request: Request) -> str:
    """Return the rate-limit bucket for this request, or raise when it cannot be trusted."""
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"

    secret = os.environ.get("API_PROXY_SECRET", "")
    sent = request.headers.get(PROXY_SECRET_HEADER)
    if sent is not None:
        if not secret or not hmac.compare_digest(sent.encode(), secret.encode()):
            raise HTTPException(status_code=403, detail="Invalid proxy credentials")
        client_ip = request.headers.get(CLIENT_IP_HEADER, "").strip()
        if not client_ip:
            raise HTTPException(status_code=400, detail="Missing client address from proxy")
        return f"ip:{client_ip}"

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded is None:
        peer = request.client.host if request.client else None
        if not peer:
            raise HTTPException(status_code=503, detail="Cannot determine client address")
        return f"ip:{peer}"

    entries = [entry.strip() for entry in forwarded.split(",") if entry.strip()]
    hops = _trusted_proxy_hops()
    if hops is None:
        # Entry count only, never the addresses: enough to choose TRUSTED_PROXY_HOPS.
        logger.warning(
            "rejecting proxied request: TRUSTED_PROXY_HOPS is unset "
            "(X-Forwarded-For has %d entries)",
            len(entries),
        )
        raise HTTPException(status_code=503, detail="Rate limiting is not configured")
    if len(entries) < hops:
        raise HTTPException(status_code=400, detail="Unexpected X-Forwarded-For")
    return f"ip:{entries[-hops]}"


limiter = Limiter(key_func=client_key)
