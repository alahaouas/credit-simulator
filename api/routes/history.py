"""GET/DELETE /api/simulations — simulation history for authenticated users."""
from __future__ import annotations

import contextlib
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_user
from ..db import get_db

router = APIRouter()


@router.get("/simulations/stats", summary="Aggregate stats for the authenticated user's simulations")
def simulation_stats(
    user_id: str = Depends(require_user),
    db=Depends(get_db),
) -> dict:
    resp = (
        db.table("simulations")
        .select("result")
        .eq("user_id", user_id)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        return {
            "total_count": 0,
            "avg_monthly_installment": None,
            "avg_loan_duration_months": None,
            "total_principal": None,
            "avg_down_payment": None,
        }

    count = len(rows)
    total_installment = Decimal(0)
    total_duration = 0
    total_principal = Decimal(0)
    total_down_payment = Decimal(0)

    for row in rows:
        r = row.get("result") or {}
        with contextlib.suppress(Exception):
            total_installment += Decimal(str(r.get("plan", {}).get("monthly_installment") or 0))
        with contextlib.suppress(Exception):
            total_duration += int(r.get("loan_duration_months") or 0)
        with contextlib.suppress(Exception):
            total_principal += Decimal(str(r.get("loan_principal") or 0))
        with contextlib.suppress(Exception):
            total_down_payment += Decimal(str(r.get("down_payment") or 0))

    return {
        "total_count": count,
        "avg_monthly_installment": str(total_installment / count),
        "avg_loan_duration_months": total_duration // count,
        "total_principal": str(total_principal),
        "avg_down_payment": str(total_down_payment / count),
    }


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
