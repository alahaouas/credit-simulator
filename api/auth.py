"""FastAPI authentication dependencies.

Supports two auth schemes:
- Bearer <supabase_jwt>  — via Authorization header
- csim_<hex>            — API key via X-Api-Key header (E3)

Failure semantics (per the security-controls rule: a check that cannot resolve
its required context must reject, not silently fall back):
- Invalid / expired token              → return None  (request treated as anonymous)
- Auth backend reachable but rejecting → return None  (anonymous)
- Auth backend errored / unreachable   → HTTP 503     (never silent fallback)
"""
from __future__ import annotations

import contextlib
import hashlib
import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Header, HTTPException

from .db import get_db

logger = logging.getLogger(__name__)

# supabase-py / gotrue surface their auth-rejection errors via AuthApiError.
# If the import shape ever changes, AuthRejected falls back to a sentinel so
# the isinstance check is always safe.
try:
    from gotrue.errors import AuthApiError as _AuthRejected  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - defensive
    class _AuthRejected(Exception):
        pass

AuthRejected = _AuthRejected

_API_KEY_SALT = b"credit-simulator/api-key/v1"
_API_KEY_ITERATIONS = 600_000


def hash_api_key(key: str) -> str:
    """Deterministic PBKDF2-HMAC-SHA256 hash used for both storage and lookup."""
    digest = hashlib.pbkdf2_hmac(
        "sha256", key.encode(), _API_KEY_SALT, _API_KEY_ITERATIONS
    )
    return digest.hex()


def optional_user(
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header()] = None,
    db=Depends(get_db),
) -> str | None:
    """Return the authenticated user's UUID, or None for anonymous requests.

    Checks Bearer token first, then X-Api-Key.
    Raises 503 if auth material is provided but Supabase is not configured,
    or if the auth backend errors unexpectedly.
    """
    # --- Bearer token (Supabase JWT) ---
    if authorization is not None and authorization.startswith("Bearer "):
        if db is None:
            raise HTTPException(status_code=503, detail="Authentication service not configured")
        token = authorization.removeprefix("Bearer ")
        try:
            resp = db.auth.get_user(token)
        except AuthRejected:
            return None
        except Exception as exc:
            logger.warning("auth backend error verifying Bearer token: %s", exc)
            raise HTTPException(status_code=503, detail="Authentication service error") from exc
        if resp is None or resp.user is None:
            return None
        return str(resp.user.id)

    # --- API key ---
    if x_api_key is not None:
        if db is None:
            raise HTTPException(status_code=503, detail="Authentication service not configured")
        key_hash = hash_api_key(x_api_key)
        try:
            resp = (
                db.table("api_keys")
                .select("user_id,id")
                .eq("key_hash", key_hash)
                .execute()
            )
        except Exception as exc:
            logger.warning("auth backend error verifying API key: %s", exc)
            raise HTTPException(status_code=503, detail="Authentication service error") from exc
        if not resp.data:
            return None
        row = resp.data[0]
        with contextlib.suppress(Exception):
            db.table("api_keys").update(
                {"last_used_at": datetime.now(UTC).isoformat()}
            ).eq("id", row["id"]).execute()
        return str(row["user_id"])

    return None


def require_user(user_id: Annotated[str | None, Depends(optional_user)] = None) -> str:
    """Like optional_user but raises 401 when unauthenticated."""
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id
