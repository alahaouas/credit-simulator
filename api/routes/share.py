"""Share-token endpoints (Layer 6 A5).

POST   /api/simulations/{id}/share   – generate a share token (auth required)
DELETE /api/simulations/{id}/share   – revoke the share token (auth required)
GET    /api/share/{token}            – fetch a simulation by token (no auth)
"""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_user
from ..db import get_db

router = APIRouter()


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
        .select("id,share_token")
        .eq("id", sim_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not check.data:
        raise HTTPException(status_code=404, detail="Simulation not found")

    existing = check.data[0].get("share_token")
    if existing:
        return {"share_token": existing}

    token = secrets.token_urlsafe(32)
    resp = (
        db.table("simulations")
        .update({"share_token": token})
        .eq("id", sim_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=500, detail="Failed to save share token")
    return {"share_token": token}


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
        .update({"share_token": None})
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
        .select("id,created_at,name,result")
        .eq("share_token", token)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Shared simulation not found")
    return resp.data[0]
