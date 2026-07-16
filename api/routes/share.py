"""Share-token endpoints (Layer 6 A5).

POST   /api/simulations/{id}/share   – generate a share token (auth required)
DELETE /api/simulations/{id}/share   – revoke the share token (auth required)
GET    /api/share/{token}            – fetch a simulation by token (no auth)
"""
from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_user
from ..db import get_db

router = APIRouter()

SHARE_TOKEN_TTL = timedelta(days=30)


@router.post("/simulations/{sim_id}/share", summary="Generate a public share token")
def generate_share_token(
    sim_id: str,
    user_id: str = Depends(require_user),
    db=Depends(get_db),
) -> dict:
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    check = (
        db.table("simulations")
        .select("id,share_token,share_token_expires_at")
        .eq("id", sim_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not check.data:
        raise HTTPException(status_code=404, detail="Simulation not found")

    row = check.data[0]
    existing = row.get("share_token")
    expires_at = row.get("share_token_expires_at")
    if existing and (expires_at is None or _parse_iso(expires_at) > datetime.now(UTC)):
        return {"share_token": existing, "expires_at": expires_at}

    token = secrets.token_urlsafe(32)
    new_expiry = (datetime.now(UTC) + SHARE_TOKEN_TTL).isoformat()
    resp = (
        db.table("simulations")
        .update({"share_token": token, "share_token_expires_at": new_expiry})
        .eq("id", sim_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=500, detail="Failed to save share token")
    return {"share_token": token, "expires_at": new_expiry}


def _parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


@router.delete("/simulations/{sim_id}/share", status_code=204, summary="Revoke a share token")
def revoke_share_token(
    sim_id: str,
    user_id: str = Depends(require_user),
    db=Depends(get_db),
) -> None:
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    resp = (
        db.table("simulations")
        .update({"share_token": None, "share_token_expires_at": None})
        .eq("id", sim_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Simulation not found")


@router.get("/share/{token}", summary="Fetch a shared simulation (no auth required)")
def get_shared_simulation(
    token: str,
    db=Depends(get_db),
) -> dict:
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    resp = (
        db.table("simulations")
        .select("id,created_at,name,result,share_token_expires_at")
        .eq("share_token", token)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Shared simulation not found")

    row = resp.data[0]
    expires_at = row.pop("share_token_expires_at", None)
    if expires_at is not None and _parse_iso(expires_at) <= datetime.now(UTC):
        raise HTTPException(status_code=404, detail="Shared simulation not found")
    return row
