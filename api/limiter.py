"""Shared slowapi rate limiter for compute-heavy / external-call endpoints.

Counters live in ``RATE_LIMIT_STORAGE_URL`` (falling back to ``REDIS_URL``), e.g. an
Upstash Redis ``rediss://`` URL. On Vercel the API runs as serverless functions: many
short-lived instances, each with its own memory, so in-memory counters would barely
limit anything. Without a storage URL the counters stay in memory, which is only
right for local dev and tests (see docs/rate-limiting.md).

The bucket key is, in order:
1. ``user:<id>`` when ``optional_user`` verified a Supabase JWT or API key;
2. ``ip:<value>`` of ``TRUSTED_CLIENT_IP_HEADER`` (``x-real-ip`` on Vercel, which
   overwrites it with the real client address so a client cannot set it);
3. ``ip:<entry>`` of ``X-Forwarded-For`` counted ``TRUSTED_PROXY_HOPS`` from the
   right, for hosts behind a proxy chain that appends to it;
4. ``ip:<peer>`` when there is no ``X-Forwarded-For`` at all (direct connection).

Anything that cannot be resolved is rejected rather than keyed on a shared value
(a proxy's address), which would put every user in one bucket.
"""

from __future__ import annotations

import logging
import os

from fastapi import HTTPException, Request
from slowapi import Limiter

logger = logging.getLogger(__name__)


def _storage_uri() -> str | None:
    return (
        os.environ.get("RATE_LIMIT_STORAGE_URL", "").strip()
        or os.environ.get("REDIS_URL", "").strip()
        or None
    )


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

    header = os.environ.get("TRUSTED_CLIENT_IP_HEADER", "").strip().lower()
    if header:
        if _storage_uri() is None:
            # A trusted platform header means a multi-instance host: per-instance
            # memory would let every new instance start from zero.
            logger.error("TRUSTED_CLIENT_IP_HEADER is set but no rate-limit storage is configured")
            raise HTTPException(status_code=503, detail="Rate limiting is not configured")
        client_ip = request.headers.get(header, "").split(",")[0].strip()
        if not client_ip:
            raise HTTPException(status_code=503, detail="Cannot determine client address")
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


limiter = Limiter(key_func=client_key, storage_uri=_storage_uri() or "memory://")
