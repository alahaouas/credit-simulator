"""FastAPI authentication dependencies."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException

from .db import get_db


def optional_user(
    authorization: Annotated[str | None, Header()] = None,
    db=Depends(get_db),
) -> str | None:
    """Return the authenticated user's UUID, or None for anonymous requests.

    Raises 503 if an Authorization header is provided but Supabase is not configured.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        return None
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


def require_user(user_id: Annotated[str | None, Depends(optional_user)] = None) -> str:
    """Like optional_user but raises 401 when unauthenticated."""
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id
