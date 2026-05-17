"""Tests for GET /api/profiles and GET /api/profiles/{country}."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_list_profiles_returns_sorted_country_codes():
    resp = client.get("/api/profiles")
    assert resp.status_code == 200
    data = resp.json()
    assert "countries" in data
    countries = data["countries"]
    assert sorted(countries) == countries
    assert "BE" in countries
    assert "FR" in countries
    assert "US" in countries


def test_list_profiles_contains_all_supported_countries():
    from credit_simulator.profiles import SUPPORTED_COUNTRIES
    resp = client.get("/api/profiles")
    assert resp.status_code == 200
    assert set(resp.json()["countries"]) == SUPPORTED_COUNTRIES


def test_get_profile_be_structure():
    resp = client.get("/api/profiles/BE")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == "BE"
    assert data["currency"] == "EUR"
    # Market-driven fields present
    assert "annual_rate_average" in data
    assert "annual_rate_best" in data
    assert "insurance_rate_average" in data
    assert "insurance_rate_best" in data
    # Regulatory fields present
    assert "purchase_tax_rate" in data
    assert "taxes_financeable" in data
    assert "min_down_payment_ratio" in data
    assert "max_debt_ratio" in data
    assert "max_loan_duration_months" in data
    # LTV tiers present
    assert isinstance(data["ltv_rate_tiers"], list)
    assert len(data["ltv_rate_tiers"]) > 0


def test_get_profile_decimal_fields_are_strings():
    resp = client.get("/api/profiles/FR")
    assert resp.status_code == 200
    data = resp.json()
    for field in ("annual_rate_average", "annual_rate_best", "purchase_tax_rate",
                  "min_down_payment_ratio", "max_debt_ratio"):
        assert isinstance(data[field], str), f"{field} should be a string"


def test_get_profile_ltv_tiers_have_correct_keys():
    resp = client.get("/api/profiles/DE")
    assert resp.status_code == 200
    for tier in resp.json()["ltv_rate_tiers"]:
        assert "ltv_max" in tier
        assert "rate_delta" in tier
        assert isinstance(tier["ltv_max"], str)
        assert isinstance(tier["rate_delta"], str)


def test_get_profile_case_insensitive():
    resp_upper = client.get("/api/profiles/GB")
    resp_lower = client.get("/api/profiles/gb")
    assert resp_upper.status_code == 200
    assert resp_lower.status_code == 200
    assert resp_upper.json() == resp_lower.json()


def test_get_profile_unknown_country_returns_404():
    resp = client.get("/api/profiles/XX")
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_get_profile_us_currency_is_usd():
    resp = client.get("/api/profiles/US")
    assert resp.status_code == 200
    assert resp.json()["currency"] == "USD"


def test_get_profile_gb_currency_is_gbp():
    resp = client.get("/api/profiles/GB")
    assert resp.status_code == 200
    assert resp.json()["currency"] == "GBP"


@pytest.mark.parametrize("country", ["BE", "FR", "ES", "DE", "PT", "IT", "GB", "US"])
def test_all_profiles_reachable(country: str):
    resp = client.get(f"/api/profiles/{country}")
    assert resp.status_code == 200
    assert resp.json()["code"] == country
