"""Tests for GET /api/profiles, GET /api/profiles/{country},
POST /api/profiles/{country}/refresh (C1), and
GET/POST/DELETE /api/alerts (C5).
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.db import get_db
from api.main import app
from tests.api.conftest import BEARER, make_db_mock

client = TestClient(app)

ALERT_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
SAMPLE_ALERT = {
    "id": ALERT_ID,
    "country": "FR",
    "target_rate": "0.030",
    "active": True,
    "created_at": "2026-05-17T09:00:00+00:00",
    "last_notified_at": None,
}


# ---------------------------------------------------------------------------
# C1 — GET /api/profiles
# ---------------------------------------------------------------------------

class TestListProfiles:
    def test_returns_all_countries(self):
        resp = client.get("/api/profiles")
        assert resp.status_code == 200
        body = resp.json()
        assert "profiles" in body
        assert set(body["profiles"].keys()) == {"BE", "FR", "DE", "ES", "IT", "PT", "GB", "US"}

    def test_profile_has_required_fields(self):
        profile = client.get("/api/profiles").json()["profiles"]["BE"]
        for field in (
            "code", "currency", "annual_rate_average", "annual_rate_best",
            "insurance_rate_average", "insurance_rate_best", "purchase_tax_rate",
            "taxes_financeable", "min_down_payment_ratio", "max_debt_ratio",
            "max_loan_duration_months", "ltv_rate_tiers",
        ):
            assert field in profile, f"missing field: {field}"

    def test_rate_fields_are_strings(self):
        profile = client.get("/api/profiles").json()["profiles"]["FR"]
        for field in ("annual_rate_average", "annual_rate_best", "purchase_tax_rate"):
            assert isinstance(profile[field], str)
            Decimal(profile[field])  # must parse as Decimal


class TestGetCountryProfile:
    def test_be_profile_returns_200(self):
        resp = client.get("/api/profiles/BE")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == "BE"
        assert body["currency"] == "EUR"

    def test_case_insensitive(self):
        assert client.get("/api/profiles/fr").status_code == 200
        assert client.get("/api/profiles/FR").status_code == 200

    def test_unknown_country_returns_404(self):
        assert client.get("/api/profiles/ZZ").status_code == 404

    def test_ltv_tiers_present(self):
        tiers = client.get("/api/profiles/BE").json()["ltv_rate_tiers"]
        assert len(tiers) > 0
        assert "ltv_max" in tiers[0]
        assert "rate_delta" in tiers[0]


# ---------------------------------------------------------------------------
# C3 — POST /api/profiles/{country}/refresh
# ---------------------------------------------------------------------------

class TestRefreshRate:
    def test_unknown_country_returns_404(self):
        assert client.post("/api/profiles/ZZ/refresh").status_code == 404

    def test_be_returns_422_no_source(self):
        resp = client.post("/api/profiles/BE/refresh")
        assert resp.status_code == 422
        assert "no online" in resp.json()["detail"].lower() or "manually" in resp.json()["detail"].lower()

    def test_fr_returns_rate(self):
        with patch("api.routes.profiles.fetch_rate", return_value=Decimal("0.0352")) as mock_fetch:
            mock_fetch.cache_clear = lambda: None
            resp = client.post("/api/profiles/FR/refresh")
        assert resp.status_code == 200
        body = resp.json()
        assert body["country"] == "FR"
        assert Decimal(body["annual_rate_average"]) == Decimal("0.0352")

    def test_fetch_error_returns_422(self):
        from credit_simulator.fetcher import FetchError

        def _fail(country: str):
            raise FetchError("network timeout")

        _fail.cache_clear = lambda: None  # type: ignore[attr-defined]
        with patch("api.routes.profiles.fetch_rate", _fail):
            resp = client.post("/api/profiles/FR/refresh")
        assert resp.status_code == 422
        assert "network timeout" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# C5 — GET/POST/DELETE /api/alerts
# ---------------------------------------------------------------------------

class TestAlertsRequiresAuth:
    def test_list_no_auth_returns_401(self):
        assert client.get("/api/alerts").status_code == 401

    def test_create_no_auth_returns_401(self):
        assert client.post("/api/alerts", json={"country": "FR", "target_rate": "0.03"}).status_code == 401

    def test_delete_no_auth_returns_401(self):
        assert client.delete(f"/api/alerts/{ALERT_ID}").status_code == 401

    def test_auth_without_supabase_returns_503(self):
        resp = client.get("/api/alerts", headers={"Authorization": BEARER})
        assert resp.status_code == 503


class TestListAlerts:
    def test_empty_list(self, mock_db):
        resp = client.get("/api/alerts", headers={"Authorization": BEARER})
        assert resp.status_code == 200
        assert resp.json()["alerts"] == []

    def test_returns_alerts(self):
        db = make_db_mock(rows=[SAMPLE_ALERT])
        app.dependency_overrides[get_db] = lambda: db
        try:
            resp = client.get("/api/alerts", headers={"Authorization": BEARER})
            assert resp.status_code == 200
            assert len(resp.json()["alerts"]) == 1
            assert resp.json()["alerts"][0]["country"] == "FR"
        finally:
            app.dependency_overrides.clear()


class TestCreateAlert:
    def test_valid_alert_returns_201(self, mock_db):
        resp = client.post(
            "/api/alerts",
            json={"country": "FR", "target_rate": "0.030"},
            headers={"Authorization": BEARER},
        )
        assert resp.status_code == 201

    def test_response_contains_country_and_rate(self, mock_db):
        resp = client.post(
            "/api/alerts",
            json={"country": "DE", "target_rate": "0.025"},
            headers={"Authorization": BEARER},
        )
        body = resp.json()
        assert body["country"] == "DE"
        assert body["target_rate"] == "0.025"
        assert body["active"] is True

    def test_invalid_country_returns_422(self, mock_db):
        resp = client.post(
            "/api/alerts",
            json={"country": "ZZ", "target_rate": "0.030"},
            headers={"Authorization": BEARER},
        )
        assert resp.status_code == 422

    def test_rate_above_1_returns_422(self, mock_db):
        resp = client.post(
            "/api/alerts",
            json={"country": "FR", "target_rate": "3.5"},
            headers={"Authorization": BEARER},
        )
        assert resp.status_code == 422

    def test_rate_zero_returns_422(self, mock_db):
        resp = client.post(
            "/api/alerts",
            json={"country": "FR", "target_rate": "0"},
            headers={"Authorization": BEARER},
        )
        assert resp.status_code == 422


class TestDeleteAlert:
    def test_delete_existing_returns_204(self):
        db = make_db_mock(rows=[SAMPLE_ALERT])
        app.dependency_overrides[get_db] = lambda: db
        try:
            resp = client.delete(f"/api/alerts/{ALERT_ID}", headers={"Authorization": BEARER})
            assert resp.status_code == 204
        finally:
            app.dependency_overrides.clear()

    def test_delete_nonexistent_returns_404(self, mock_db):
        resp = client.delete(f"/api/alerts/{ALERT_ID}", headers={"Authorization": BEARER})
        assert resp.status_code == 404
