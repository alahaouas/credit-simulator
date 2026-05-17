"""GET/POST/DELETE /api/alerts — rate alert management (C5)."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from ..auth import require_user
from ..constants import SUPPORTED_COUNTRIES
from ..db import get_db

router = APIRouter()


class RateAlertCreate(BaseModel):
    country: str
    target_rate: str  # decimal fraction e.g. "0.030" for 3.0%

    @field_validator("country", mode="before")
    @classmethod
    def validate_country(cls, v: object) -> str:
        s = str(v).upper()
        if s not in SUPPORTED_COUNTRIES:
            raise ValueError(f"unsupported country '{v}'; must be one of {sorted(SUPPORTED_COUNTRIES)}")
        return s

    @field_validator("target_rate", mode="before")
    @classmethod
    def validate_rate(cls, v: object) -> str:
        try:
            d = Decimal(str(v))
        except InvalidOperation as err:
            raise ValueError(f"cannot parse {v!r} as a decimal") from err
        if not (Decimal("0") < d < Decimal("1")):
            raise ValueError(
                "target_rate must be a decimal fraction between 0 and 1 (e.g. 0.035 for 3.5%)"
            )
        return str(d)


@router.get("/alerts", summary="List the user's rate alerts")
def list_alerts(user_id: str = Depends(require_user), db=Depends(get_db)) -> dict:
    res = (
        db.table("rate_alerts")
        .select("id, country, target_rate, active, created_at, last_notified_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return {"alerts": res.data or []}


@router.post("/alerts", status_code=201, summary="Create a rate alert")
def create_alert(
    body: RateAlertCreate,
    user_id: str = Depends(require_user),
    db=Depends(get_db),
) -> dict:
    payload = {"user_id": user_id, "country": body.country, "target_rate": body.target_rate}
    res = db.table("rate_alerts").insert(payload).execute()
    row = res.data[0] if isinstance(getattr(res, "data", None), list) and res.data else {}
    return {
        "id": row.get("id", "") if isinstance(row, dict) else "",
        "country": body.country,
        "target_rate": body.target_rate,
        "active": True,
        "created_at": row.get("created_at", "") if isinstance(row, dict) else "",
        "last_notified_at": None,
    }


@router.delete("/alerts/{alert_id}", status_code=204, summary="Delete a rate alert")
def delete_alert(
    alert_id: str,
    user_id: str = Depends(require_user),
    db=Depends(get_db),
) -> None:
    res = (
        db.table("rate_alerts")
        .delete()
        .eq("id", alert_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Alert not found.")
