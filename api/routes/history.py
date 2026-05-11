"""GET/DELETE /api/simulations — simulation history for authenticated users."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_user
from ..db import get_db

router = APIRouter()


@router.get("/simulations", summary="List saved simulations")
def list_simulations(
    user_id: str = Depends(require_user),
    db=Depends(get_db),
) -> list[dict]:
    resp = (
        db.table("simulations")
        .select("id,created_at,inputs,result")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return resp.data or []


@router.get("/simulations/{sim_id}", summary="Get a saved simulation")
def get_simulation(
    sim_id: str,
    user_id: str = Depends(require_user),
    db=Depends(get_db),
) -> dict:
    resp = (
        db.table("simulations")
        .select("*")
        .eq("id", sim_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return resp.data[0]


@router.delete("/simulations/{sim_id}", status_code=204, summary="Delete a saved simulation")
def delete_simulation(
    sim_id: str,
    user_id: str = Depends(require_user),
    db=Depends(get_db),
) -> None:
    resp = (
        db.table("simulations")
        .delete()
        .eq("id", sim_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Simulation not found")
