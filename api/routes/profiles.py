"""GET /api/profiles, GET /api/profiles/{country}, POST /api/profiles/{country}/refresh (C1, C3)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from credit_simulator.fetcher import FetchError, fetch_rate
from credit_simulator.profiles import SUPPORTED_COUNTRIES, get_profile

router = APIRouter()


def _profile_to_dict(profile) -> dict:
    return {
        "code": profile.code,
        "currency": profile.currency,
        "annual_rate_average": str(profile.annual_rate_average),
        "annual_rate_best": str(profile.annual_rate_best),
        "insurance_rate_average": str(profile.insurance_rate_average),
        "insurance_rate_best": str(profile.insurance_rate_best),
        "purchase_tax_rate": str(profile.purchase_tax_rate),
        "taxes_financeable": profile.taxes_financeable,
        "min_down_payment_ratio": str(profile.min_down_payment_ratio),
        "max_debt_ratio": str(profile.max_debt_ratio),
        "max_loan_duration_months": profile.max_loan_duration_months,
        "last_updated_date": profile.last_updated_date,
        "ltv_rate_tiers": [
            {"ltv_max": str(t.ltv_max), "rate_delta": str(t.rate_delta)}
            for t in profile.ltv_rate_tiers
        ],
    }


@router.get("/profiles", summary="List all country profiles")
def list_profiles() -> dict:
    profiles = {code: _profile_to_dict(get_profile(code)) for code in sorted(SUPPORTED_COUNTRIES)}
    return {"profiles": profiles}


@router.get("/profiles/{country}", summary="Get a single country profile")
def get_country_profile(country: str) -> dict:
    try:
        profile = get_profile(country.upper())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _profile_to_dict(profile)


@router.post("/profiles/{country}/refresh", summary="Fetch the latest live mortgage rate for a country")
def refresh_country_rate(country: str) -> dict:
    """Fetch the current average annual rate from the relevant online source.

    Supported: FR, DE, ES, IT, PT (ECB) | GB (Bank of England) | US (FRED).
    BE has no reliable online source and returns 422.
    """
    code = country.upper()
    if code not in SUPPORTED_COUNTRIES:
        raise HTTPException(status_code=404, detail=f"Unsupported country '{code}'.")
    fetch_rate.cache_clear()
    try:
        rate = fetch_rate(code)
    except FetchError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"country": code, "annual_rate_average": str(rate)}
