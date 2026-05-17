"""GET /api/profiles — country profile endpoints (C1)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from credit_simulator.profiles import SUPPORTED_COUNTRIES, get_profile

from ..serializers import to_json_safe

router = APIRouter()


@router.get("/profiles", summary="List supported country codes")
def list_profiles() -> dict:
    """Return a sorted list of all supported country codes."""
    return {"countries": sorted(SUPPORTED_COUNTRIES)}


@router.get("/profiles/{country}", summary="Get country profile")
def get_country_profile(country: str) -> dict:
    """Return the full country profile for *country* (case-insensitive).

    Includes market-driven rates (average and best quality), regulatory
    constraints, LTV rate tiers, and the currency code.

    All ``Decimal`` fields are serialized as strings.
    """
    try:
        profile = get_profile(country.upper())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return to_json_safe(profile)
