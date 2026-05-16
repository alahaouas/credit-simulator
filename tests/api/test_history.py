"""Tests for GET/DELETE /api/simulations (history endpoints) and
GET /api/simulations/stats (E4).

Covers:
- 401 when unauthenticated
- 503 when auth header present but Supabase not configured
- List returns user's simulations
- Get returns a single simulation
- Get returns 404 for unknown / other-user simulation
- Delete removes a simulation
- Delete returns 404 for unknown simulation
- Stats: zeros when empty, aggregates when populated, requires auth
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from api.db import get_db
from api.main import app
from tests.api.conftest import BEARER, SAMPLE_SIM, SIM_ID, make_db_mock

client = TestClient(app)


# ---------------------------------------------------------------------------
# Unauthenticated — all endpoints require auth
# ---------------------------------------------------------------------------

class TestHistoryRequiresAuth:
    def test_list_no_auth_returns_401(self):
        assert client.get("/api/simulations").status_code == 401

    def test_get_no_auth_returns_401(self):
        assert client.get(f"/api/simulations/{SIM_ID}").status_code == 401

    def test_delete_no_auth_returns_401(self):
        assert client.delete(f"/api/simulations/{SIM_ID}").status_code == 401

    def test_auth_header_without_supabase_returns_503(self):
        # No dependency override → get_db returns None
        resp = client.get("/api/simulations", headers={"Authorization": BEARER})
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# List simulations
# ---------------------------------------------------------------------------

class TestListSimulations:
    def test_empty_history_returns_empty_items(self, mock_db):
        resp = client.get("/api/simulations", headers={"Authorization": BEARER})
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["next_cursor"] is None

    def test_returns_saved_simulations(self, mock_db_with_sim):
        resp = client.get("/api/simulations", headers={"Authorization": BEARER})
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 1
        assert body["items"][0]["id"] == SIM_ID

    def test_result_has_expected_fields(self, mock_db_with_sim):
        body = client.get("/api/simulations", headers={"Authorization": BEARER}).json()
        row = body["items"][0]
        for field in ("id", "created_at", "inputs", "result"):
            assert field in row, f"missing field: {field}"

    def test_response_envelope_has_next_cursor_key(self, mock_db_with_sim):
        body = client.get("/api/simulations", headers={"Authorization": BEARER}).json()
        assert "next_cursor" in body

    def test_search_param_accepted(self, mock_db_with_sim):
        resp = client.get(
            "/api/simulations?search=brussels",
            headers={"Authorization": BEARER},
        )
        assert resp.status_code == 200

    def test_cursor_param_accepted(self, mock_db_with_sim):
        resp = client.get(
            "/api/simulations?cursor=2026-01-01T00:00:00+00:00",
            headers={"Authorization": BEARER},
        )
        assert resp.status_code == 200

    def test_limit_param_accepted(self, mock_db_with_sim):
        resp = client.get(
            "/api/simulations?limit=5",
            headers={"Authorization": BEARER},
        )
        assert resp.status_code == 200

    def test_limit_too_large_returns_422(self, mock_db):
        resp = client.get(
            "/api/simulations?limit=999",
            headers={"Authorization": BEARER},
        )
        assert resp.status_code == 422

    def test_search_too_long_returns_422(self, mock_db):
        resp = client.get(
            f"/api/simulations?search={'x' * 101}",
            headers={"Authorization": BEARER},
        )
        assert resp.status_code == 422

    def test_next_cursor_set_when_more_pages_exist(self):
        # Return limit+1 rows; backend should set next_cursor and trim to limit
        rows = [
            {**SAMPLE_SIM, "id": f"id-{i}", "created_at": f"2026-01-{i+1:02d}T00:00:00+00:00"}
            for i in range(6)
        ]
        db = make_db_mock(rows=rows)
        app.dependency_overrides[get_db] = lambda: db
        try:
            body = client.get(
                "/api/simulations?limit=5",
                headers={"Authorization": BEARER},
            ).json()
            assert len(body["items"]) == 5
            assert body["next_cursor"] is not None
        finally:
            app.dependency_overrides.clear()

    def test_no_next_cursor_on_last_page(self, mock_db_with_sim):
        body = client.get(
            "/api/simulations?limit=20",
            headers={"Authorization": BEARER},
        ).json()
        assert body["next_cursor"] is None


# ---------------------------------------------------------------------------
# Get single simulation
# ---------------------------------------------------------------------------

class TestGetSimulation:
    def test_returns_simulation(self, mock_db_with_sim):
        resp = client.get(f"/api/simulations/{SIM_ID}", headers={"Authorization": BEARER})
        assert resp.status_code == 200
        assert resp.json()["id"] == SIM_ID

    def test_not_found_returns_404(self, mock_db):
        resp = client.get(f"/api/simulations/{SIM_ID}", headers={"Authorization": BEARER})
        assert resp.status_code == 404

    def test_404_response_has_detail(self, mock_db):
        resp = client.get(f"/api/simulations/{SIM_ID}", headers={"Authorization": BEARER})
        assert "detail" in resp.json()


# ---------------------------------------------------------------------------
# Delete simulation
# ---------------------------------------------------------------------------

class TestDeleteSimulation:
    def test_delete_existing_returns_204(self, mock_db_with_sim):
        resp = client.delete(f"/api/simulations/{SIM_ID}", headers={"Authorization": BEARER})
        assert resp.status_code == 204

    def test_delete_nonexistent_returns_404(self, mock_db):
        resp = client.delete(f"/api/simulations/{SIM_ID}", headers={"Authorization": BEARER})
        assert resp.status_code == 404

    def test_delete_calls_db(self, mock_db_with_sim):
        client.delete(f"/api/simulations/{SIM_ID}", headers={"Authorization": BEARER})
        mock_db_with_sim.table.assert_called_with("simulations")


# ---------------------------------------------------------------------------
# Update simulation metadata — name & tags (A1)
# ---------------------------------------------------------------------------

class TestUpdateSimulationMeta:
    def test_patch_no_auth_returns_401(self):
        resp = client.patch(f"/api/simulations/{SIM_ID}", json={"name": "x"})
        assert resp.status_code == 401

    def test_patch_without_supabase_returns_503(self):
        resp = client.patch(
            f"/api/simulations/{SIM_ID}", json={"name": "x"},
            headers={"Authorization": BEARER},
        )
        assert resp.status_code == 503

    def test_rename_existing_returns_200(self, mock_db_with_sim):
        resp = client.patch(
            f"/api/simulations/{SIM_ID}", json={"name": "Brussels apartment"},
            headers={"Authorization": BEARER},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == SIM_ID

    def test_update_tags(self, mock_db_with_sim):
        resp = client.patch(
            f"/api/simulations/{SIM_ID}", json={"tags": ["primary", "2026"]},
            headers={"Authorization": BEARER},
        )
        assert resp.status_code == 200

    def test_patch_nonexistent_returns_404(self, mock_db):
        resp = client.patch(
            f"/api/simulations/{SIM_ID}", json={"name": "x"},
            headers={"Authorization": BEARER},
        )
        assert resp.status_code == 404

    def test_empty_body_returns_400(self, mock_db_with_sim):
        resp = client.patch(
            f"/api/simulations/{SIM_ID}", json={},
            headers={"Authorization": BEARER},
        )
        assert resp.status_code == 400

    def test_name_too_long_returns_422(self, mock_db_with_sim):
        resp = client.patch(
            f"/api/simulations/{SIM_ID}", json={"name": "x" * 121},
            headers={"Authorization": BEARER},
        )
        assert resp.status_code == 422

    def test_too_many_tags_returns_422(self, mock_db_with_sim):
        resp = client.patch(
            f"/api/simulations/{SIM_ID}", json={"tags": [f"t{i}" for i in range(21)]},
            headers={"Authorization": BEARER},
        )
        assert resp.status_code == 422

    def test_patch_uses_update_on_simulations_table(self, mock_db_with_sim):
        client.patch(
            f"/api/simulations/{SIM_ID}", json={"name": "x"},
            headers={"Authorization": BEARER},
        )
        mock_db_with_sim.table.assert_called_with("simulations")


# ---------------------------------------------------------------------------
# Simulation stats (E4)
# ---------------------------------------------------------------------------

_SIM_WITH_RESULT = {
    "result": {
        "loan_duration_months": 240,
        "loan_principal": "268800.00",
        "down_payment": "60000.00",
        "plan": {"monthly_installment": "1500.00"},
    }
}


class TestSimulationStats:
    def test_stats_no_auth_returns_401(self):
        assert client.get("/api/simulations/stats").status_code == 401

    def test_stats_without_supabase_returns_503(self):
        resp = client.get("/api/simulations/stats", headers={"Authorization": BEARER})
        assert resp.status_code == 503

    def test_stats_empty_history(self, mock_db):
        resp = client.get("/api/simulations/stats", headers={"Authorization": BEARER})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 0
        for field in ("avg_monthly_installment", "avg_loan_duration_months",
                      "total_principal", "avg_down_payment"):
            assert data[field] is None

    def test_stats_with_simulations(self):
        db = make_db_mock(rows=[_SIM_WITH_RESULT, _SIM_WITH_RESULT])
        app.dependency_overrides[get_db] = lambda: db
        try:
            resp = client.get("/api/simulations/stats", headers={"Authorization": BEARER})
            assert resp.status_code == 200
            data = resp.json()
            assert data["total_count"] == 2
            assert data["avg_loan_duration_months"] == 240
            assert data["avg_monthly_installment"] == "1500.00"
            assert data["total_principal"] == "537600.00"
            assert data["avg_down_payment"] == "60000.00"
        finally:
            app.dependency_overrides.clear()

    def test_stats_has_all_fields(self):
        db = make_db_mock(rows=[_SIM_WITH_RESULT])
        app.dependency_overrides[get_db] = lambda: db
        try:
            data = client.get("/api/simulations/stats", headers={"Authorization": BEARER}).json()
            for field in ("total_count", "avg_monthly_installment", "avg_loan_duration_months",
                          "total_principal", "avg_down_payment"):
                assert field in data, f"missing field: {field}"
        finally:
            app.dependency_overrides.clear()
