"""Tests for POST /api/simulate.

Covers:
- Happy-path response structure and field types
- Schedule and sweet-spot inclusion flags
- Financial consistency of the returned plan
- Input validation errors (missing fields, bad decimals, bad preference)
- Domain errors (infeasible inputs, unknown country)
- Optional parameter handling (country, profile_quality, fixed_duration)
- Auth: anonymous simulate works; authenticated simulate persists to DB
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

BASE = {
    "property_price": "300000",
    "monthly_net_income": "4000",
    "available_savings": "80000",
}


# ---------------------------------------------------------------------------
# Happy path — structure
# ---------------------------------------------------------------------------

class TestSimulateHappyPath:
    def test_returns_200(self):
        resp = client.post("/api/simulate", json=BASE)
        assert resp.status_code == 200

    def test_response_has_required_top_level_keys(self):
        data = client.post("/api/simulate", json=BASE).json()
        assert set(data.keys()) >= {"result", "sweet_spot", "schedule"}

    def test_result_has_required_fields(self):
        result = client.post("/api/simulate", json=BASE).json()["result"]
        for field in (
            "down_payment", "loan_principal", "loan_duration_months",
            "plan", "ltv_ratio", "country", "currency",
        ):
            assert field in result, f"missing field: {field}"

    def test_plan_has_required_fields(self):
        plan = client.post("/api/simulate", json=BASE).json()["result"]["plan"]
        for field in (
            "monthly_emi", "monthly_insurance", "monthly_installment",
            "total_interest_paid", "total_cost_of_credit", "effective_annual_rate",
        ):
            assert field in plan, f"missing plan field: {field}"

    def test_decimal_fields_serialised_as_strings(self):
        """No float leakage — every Decimal must arrive as a JSON string."""
        result = client.post("/api/simulate", json=BASE).json()["result"]
        for field in ("down_payment", "loan_principal", "ltv_ratio"):
            assert isinstance(result[field], str), f"{field!r} is not a string"
        plan = result["plan"]
        for field in ("monthly_emi", "monthly_insurance", "monthly_installment"):
            assert isinstance(plan[field], str), f"plan.{field!r} is not a string"

    def test_country_defaults_to_be(self):
        result = client.post("/api/simulate", json=BASE).json()["result"]
        assert result["country"] == "BE"
        assert result["currency"] == "EUR"


# ---------------------------------------------------------------------------
# Schedule option
# ---------------------------------------------------------------------------

class TestScheduleOption:
    def test_schedule_excluded_by_default(self):
        assert client.post("/api/simulate", json=BASE).json()["schedule"] is None

    def test_schedule_included_when_requested(self):
        data = client.post("/api/simulate", json={**BASE, "include_schedule": True}).json()
        assert data["schedule"] is not None
        assert isinstance(data["schedule"], list)
        assert len(data["schedule"]) > 0

    def test_schedule_row_structure(self):
        data = client.post("/api/simulate", json={**BASE, "include_schedule": True}).json()
        row = data["schedule"][0]
        for field in (
            "period", "opening_balance", "monthly_installment",
            "principal_component", "interest_component",
            "insurance_component", "closing_balance",
        ):
            assert field in row, f"missing schedule field: {field}"

    def test_schedule_first_period_is_1(self):
        data = client.post("/api/simulate", json={**BASE, "include_schedule": True}).json()
        assert data["schedule"][0]["period"] == 1

    def test_schedule_row_decimals_are_strings(self):
        data = client.post("/api/simulate", json={**BASE, "include_schedule": True}).json()
        row = data["schedule"][0]
        for field in ("opening_balance", "monthly_installment", "closing_balance"):
            assert isinstance(row[field], str), f"schedule row {field!r} is not a string"

    def test_schedule_length_matches_duration(self):
        payload = {**BASE, "fixed_loan_duration_months": 276, "include_schedule": True}
        data = client.post("/api/simulate", json=payload).json()
        assert len(data["schedule"]) == 276


# ---------------------------------------------------------------------------
# Sweet-spot option
# ---------------------------------------------------------------------------

class TestSweetSpotOption:
    def test_sweet_spot_included_by_default(self):
        data = client.post("/api/simulate", json=BASE).json()
        assert data["sweet_spot"] is not None

    def test_sweet_spot_excluded_when_not_requested(self):
        data = client.post("/api/simulate", json={**BASE, "include_sweet_spot": False}).json()
        assert data["sweet_spot"] is None

    def test_sweet_spot_has_milestones(self):
        sweet = client.post("/api/simulate", json=BASE).json()["sweet_spot"]
        assert "milestones" in sweet
        assert len(sweet["milestones"]) > 0


# ---------------------------------------------------------------------------
# Financial consistency
# ---------------------------------------------------------------------------

class TestFinancialConsistency:
    def test_monthly_installment_equals_emi_plus_insurance(self):
        plan = client.post("/api/simulate", json=BASE).json()["result"]["plan"]
        emi = Decimal(plan["monthly_emi"])
        ins = Decimal(plan["monthly_insurance"])
        installment = Decimal(plan["monthly_installment"])
        assert abs(installment - (emi + ins)) <= Decimal("0.01")

    def test_loan_principal_plus_down_payment_equals_acquisition_cost(self):
        result = client.post("/api/simulate", json=BASE).json()["result"]
        dp = Decimal(result["down_payment"])
        principal = Decimal(result["loan_principal"])
        acq = Decimal(result["total_acquisition_cost"])
        assert abs(dp + principal - acq) <= Decimal("0.01")

    def test_ltv_ratio_is_principal_over_property_price(self):
        result = client.post("/api/simulate", json=BASE).json()["result"]
        principal = Decimal(result["loan_principal"])
        price = Decimal(result["property_price"])
        ltv = Decimal(result["ltv_ratio"])
        expected = (principal / price).quantize(Decimal("0.0001"))
        assert ltv == expected


# ---------------------------------------------------------------------------
# Optional parameters
# ---------------------------------------------------------------------------

class TestOptionalParameters:
    def test_best_profile_quality_yields_lower_or_equal_rate(self):
        rate_avg = Decimal(
            client.post("/api/simulate", json=BASE).json()["result"]["plan"]["annual_interest_rate"]
        )
        rate_best = Decimal(
            client.post("/api/simulate", json={**BASE, "profile_quality": "best"})
            .json()["result"]["plan"]["annual_interest_rate"]
        )
        assert rate_best <= rate_avg

    def test_fixed_duration_is_honoured(self):
        result = client.post(
            "/api/simulate", json={**BASE, "fixed_loan_duration_months": 276}
        ).json()["result"]
        assert result["loan_duration_months"] == 276

    def test_country_gb_is_supported(self):
        resp = client.post("/api/simulate", json={**BASE, "country": "GB"})
        assert resp.status_code == 200
        assert resp.json()["result"]["country"] == "GB"

    def test_minimize_monthly_payment_preference(self):
        resp = client.post(
            "/api/simulate",
            json={**BASE, "optimization_preference": "minimize_monthly_payment"},
        )
        assert resp.status_code == 200

    def test_preferred_down_payment_is_used(self):
        result = client.post(
            "/api/simulate", json={**BASE, "preferred_down_payment": "70000"}
        ).json()["result"]
        assert Decimal(result["down_payment"]) == Decimal("70000")


# ---------------------------------------------------------------------------
# Input validation errors
# ---------------------------------------------------------------------------

class TestValidationErrors:
    def test_missing_mandatory_field_returns_422(self):
        payload = {"property_price": "300000", "monthly_net_income": "4000"}
        assert client.post("/api/simulate", json=payload).status_code == 422

    def test_zero_property_price_returns_422(self):
        assert client.post("/api/simulate", json={**BASE, "property_price": "0"}).status_code == 422

    def test_negative_savings_returns_422(self):
        assert client.post("/api/simulate", json={**BASE, "available_savings": "-1000"}).status_code == 422

    def test_non_numeric_price_returns_422(self):
        assert client.post("/api/simulate", json={**BASE, "property_price": "abc"}).status_code == 422

    def test_invalid_profile_quality_returns_422(self):
        assert (
            client.post("/api/simulate", json={**BASE, "profile_quality": "premium"}).status_code
            == 422
        )

    def test_invalid_optimization_preference_returns_422(self):
        assert (
            client.post("/api/simulate", json={**BASE, "optimization_preference": "bogus"}).status_code
            == 422
        )


# ---------------------------------------------------------------------------
# Domain errors
# ---------------------------------------------------------------------------

class TestDomainErrors:
    def test_unknown_country_returns_422(self):
        assert client.post("/api/simulate", json={**BASE, "country": "XX"}).status_code == 422

    def test_infeasible_savings_returns_422(self):
        payload = {
            "property_price": "500000",
            "monthly_net_income": "1000",
            "available_savings": "1000",
        }
        resp = client.post("/api/simulate", json=payload)
        assert resp.status_code == 422

    def test_infeasible_response_contains_detail(self):
        payload = {
            "property_price": "500000",
            "monthly_net_income": "1000",
            "available_savings": "1000",
        }
        resp = client.post("/api/simulate", json=payload)
        assert "detail" in resp.json()


# ---------------------------------------------------------------------------
# Auth integration — simulate + persistence
# ---------------------------------------------------------------------------

class TestSimulateWithAuth:
    def test_anonymous_simulate_still_returns_200(self):
        resp = client.post("/api/simulate", json=BASE)
        assert resp.status_code == 200

    def test_authenticated_simulate_returns_200(self, mock_db):
        from tests.api.conftest import BEARER
        resp = client.post("/api/simulate", json=BASE, headers={"Authorization": BEARER})
        assert resp.status_code == 200

    def test_authenticated_simulate_saves_to_db(self, mock_db):
        from tests.api.conftest import BEARER
        client.post("/api/simulate", json=BASE, headers={"Authorization": BEARER})
        mock_db.table.assert_called_with("simulations")
        mock_db.table.return_value.insert.assert_called_once()

    def test_invalid_token_treated_as_anonymous(self, mock_db):
        from tests.api.conftest import make_db_mock
        from api.db import get_db
        from api.main import app
        db = make_db_mock(invalid_token=True)
        app.dependency_overrides[get_db] = lambda: db
        try:
            resp = client.post("/api/simulate", json=BASE, headers={"Authorization": "Bearer bad"})
            assert resp.status_code == 200
            db.table.return_value.insert.assert_not_called()
        finally:
            app.dependency_overrides.clear()

    def test_auth_backend_error_returns_503(self):
        """Per security-controls rule: auth check that can't resolve must reject."""
        from tests.api.conftest import make_db_mock
        from api.db import get_db
        from api.main import app
        db = make_db_mock(auth_fail=True)
        app.dependency_overrides[get_db] = lambda: db
        try:
            resp = client.post(
                "/api/simulate", json=BASE, headers={"Authorization": "Bearer anything"}
            )
            assert resp.status_code == 503
        finally:
            app.dependency_overrides.clear()

    def test_auth_header_without_supabase_returns_503(self):
        # No override → get_db returns None → 503
        resp = client.post(
            "/api/simulate", json=BASE,
            headers={"Authorization": "Bearer some-token"},
        )
        assert resp.status_code == 503
