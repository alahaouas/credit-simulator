"""GET/PUT /api/preferences — user preferences (E1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import require_user
from ..constants import DEFAULT_USER_PREFERENCES
from ..db import get_db
from ..models import UserPreferencesModel

router = APIRouter()


@router.get("/preferences", summary="Get user preferences")
def get_preferences(
    user_id: str = Depends(require_user),
    db=Depends(get_db),
) -> dict:
    resp = (
        db.table("user_preferences")
        .select("default_country,default_optimization_preference,currency_display")
        .eq("user_id", user_id)
        .execute()
    )
    if resp.data:
        row = resp.data[0]
        return {k: row[k] for k in DEFAULT_USER_PREFERENCES}
    return dict(DEFAULT_USER_PREFERENCES)


@router.put("/preferences", summary="Update user preferences")
def update_preferences(
    body: UserPreferencesModel,
    user_id: str = Depends(require_user),
    db=Depends(get_db),
) -> dict:
    payload = {
        "user_id": user_id,
        "default_country": body.default_country,
        "default_optimization_preference": body.default_optimization_preference,
        "currency_display": body.currency_display,
    }
    db.table("user_preferences").upsert(payload).execute()
    return {k: v for k, v in payload.items() if k != "user_id"}
