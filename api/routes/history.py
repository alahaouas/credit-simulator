"""GET/DELETE /api/simulations — simulation history for authenticated users."""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import require_user
from ..db import get_db
from ..models import SimulationMetaUpdate

router = APIRouter()


def _to_decimal(value: object) -> Decimal:
    if value is None:
        return Decimal(0)
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal(0)


def _to_int(value: object) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


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
        plan = r.get("plan") or {}
        total_installment += _to_decimal(plan.get("monthly_installment"))
        total_duration += _to_int(r.get("loan_duration_months"))
        total_principal += _to_decimal(r.get("loan_principal"))
        total_down_payment += _to_decimal(r.get("down_payment"))

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
    search: str | None = Query(None, max_length=100),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    safe = re.sub(r"[%{},]", "", search.strip()) if search else None
    query = (
        db.table("simulations")
        .select("id,created_at,inputs,result,name,tags")
        .eq("user_id", user_id)
    )
    if safe:
        query = query.or_(f"name.ilike.%{safe}%,tags.cs.{{{safe}}}")
    if cursor:
        query = query.lt("created_at", cursor)
    resp = query.order("created_at", desc=True).limit(limit + 1).execute()
    rows = list(resp.data or [])
    if len(rows) > limit:
        next_cursor = rows[limit - 1]["created_at"]
        rows = rows[:limit]
    else:
        next_cursor = None
    return {"items": rows, "next_cursor": next_cursor}


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


@router.patch("/simulations/{sim_id}", summary="Rename or re-tag a saved simulation")
def update_simulation_meta(
    sim_id: str,
    meta: SimulationMetaUpdate,
    user_id: str = Depends(require_user),
    db=Depends(get_db),
) -> dict:
    patch: dict = {}
    if "name" in meta.model_fields_set:
        patch["name"] = meta.name
    if "tags" in meta.model_fields_set:
        patch["tags"] = meta.tags or []
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")

    resp = (
        db.table("simulations")
        .update(patch)
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
