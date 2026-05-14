"""Tests for GET/PUT /api/preferences (Layer 6 E1).

Covers:
- 401 when unauthenticated
- GET returns hard-coded defaults when no row exists
- GET returns stored preferences
- PUT stores and returns preferences
- PUT with invalid country/preference/currency_display returns 422
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from api.db import get_db
from api.main import app
from tests.api.conftest import BEARER, USER_ID, make_db_mock

client = TestClient(app)

SAMPLE_PREFS = {
    "default_country": "FR",
    "default_optimization_preference": "minimize_total_cost",
    "currency_display": "code",
}


# ---------------------------------------------------------------------------
# Auth guards
# ---------------------------------------------------------------------------

class TestPreferencesRequiresAuth:
    def test_get_no_auth_returns_401(self):
        assert client.get("/api/preferences").status_code == 401

    def test_put_no_auth_returns_401(self):
        assert client.put("/api/preferences", json=SAMPLE_PREFS).status_code == 401

    def test_auth_without_supabase_returns_503(self):
        resp = client.get("/api/preferences", headers={"Authorization": BEARER})
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# GET /api/preferences
# ---------------------------------------------------------------------------

class TestGetPreferences:
    def test_returns_defaults_when_no_row(self, mock_db):
        resp = client.get("/api/preferences", headers={"Authorization": BEARER})
        assert resp.status_code == 200
        data = resp.json()
        assert data["default_country"] == "BE"
        assert data["default_optimization_preference"] == "balanced"
        assert data["currency_display"] == "symbol"

    def test_returns_stored_preferences(self):
        db = make_db_mock(rows=[{**SAMPLE_PREFS, "user_id": USER_ID}])
        app.dependency_overrides[get_db] = lambda: db
        try:
            resp = client.get("/api/preferences", headers={"Authorization": BEARER})
            assert resp.status_code == 200
            data = resp.json()
            assert data["default_country"] == "FR"
            assert data["default_optimization_preference"] == "minimize_total_cost"
            assert data["currency_display"] == "code"
        finally:
            app.dependency_overrides.clear()

    def test_response_has_all_fields(self, mock_db):
        data = client.get("/api/preferences", headers={"Authorization": BEARER}).json()
        for field in ("default_country", "default_optimization_preference", "currency_display"):
            assert field in data, f"missing field: {field}"


# ---------------------------------------------------------------------------
# PUT /api/preferences
# ---------------------------------------------------------------------------

class TestPutPreferences:
    def test_stores_and_returns_preferences(self, mock_db):
        resp = client.put(
            "/api/preferences",
            json=SAMPLE_PREFS,
            headers={"Authorization": BEARER},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["default_country"] == "FR"
        assert data["default_optimization_preference"] == "minimize_total_cost"
        assert data["currency_display"] == "code"

    def test_calls_upsert(self, mock_db):
        client.put("/api/preferences", json=SAMPLE_PREFS, headers={"Authorization": BEARER})
        mock_db.table.assert_called_with("user_preferences")
        mock_db.table.return_value.upsert.assert_called_once()

    def test_response_does_not_contain_user_id(self, mock_db):
        data = client.put(
            "/api/preferences", json=SAMPLE_PREFS, headers={"Authorization": BEARER}
        ).json()
        assert "user_id" not in data

    def test_invalid_country_returns_422(self, mock_db):
        body = {**SAMPLE_PREFS, "default_country": "XX"}
        resp = client.put("/api/preferences", json=body, headers={"Authorization": BEARER})
        assert resp.status_code == 422

    def test_invalid_optimization_preference_returns_422(self, mock_db):
        body = {**SAMPLE_PREFS, "default_optimization_preference": "maximize_luck"}
        resp = client.put("/api/preferences", json=body, headers={"Authorization": BEARER})
        assert resp.status_code == 422

    def test_invalid_currency_display_returns_422(self, mock_db):
        body = {**SAMPLE_PREFS, "currency_display": "emoji"}
        resp = client.put("/api/preferences", json=body, headers={"Authorization": BEARER})
        assert resp.status_code == 422

    def test_defaults_used_when_fields_omitted(self, mock_db):
        resp = client.put("/api/preferences", json={}, headers={"Authorization": BEARER})
        assert resp.status_code == 200
        data = resp.json()
        assert data["default_country"] == "BE"
        assert data["default_optimization_preference"] == "balanced"
        assert data["currency_display"] == "symbol"
