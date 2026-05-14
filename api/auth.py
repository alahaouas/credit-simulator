"""FastAPI authentication dependencies.

Supports two auth schemes:
- Bearer <supabase_jwt>  — via Authorization header
- csim_<hex>            — API key via X-Api-Key header (E3)
"""
from __future__ import annotations

import contextlib
import hashlib
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Header, HTTPException

from .db import get_db


def optional_user(
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header()] = None,
    db=Depends(get_db),
) -> str | None:
    """Return the authenticated user's UUID, or None for anonymous requests.

    Checks Bearer token first, then X-Api-Key.
    Raises 503 if auth material is provided but Supabase is not configured.
    """
    # --- Bearer token (Supabase JWT) ---
    if authorization is not None and authorization.startswith("Bearer "):
        if db is None:
            raise HTTPException(status_code=503, detail="Authentication service not configured")
        token = authorization.removeprefix("Bearer ")
        try:
            resp = db.auth.get_user(token)
            if resp.user is None:
                return None
            return str(resp.user.id)
        except Exception:
            return None

    # --- API key ---
    if x_api_key is not None:
        if db is None:
            raise HTTPException(status_code=503, detail="Authentication service not configured")
        key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
        try:
            resp = (
                db.table("api_keys")
                .select("user_id,id")
                .eq("key_hash", key_hash)
                .execute()
            )
            if not resp.data:
                return None
            row = resp.data[0]
            with contextlib.suppress(Exception):
                db.table("api_keys").update(
                    {"last_used_at": datetime.now(UTC).isoformat()}
                ).eq("id", row["id"]).execute()
            return str(row["user_id"])
        except Exception:
            return None

    return None


def require_user(user_id: Annotated[str | None, Depends(optional_user)] = None) -> str:
    """Like optional_user but raises 401 when unauthenticated."""
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id
