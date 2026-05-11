"""Tests for GET/DELETE /api/simulations (history endpoints).

Covers:
- 401 when unauthenticated
- 503 when auth header present but Supabase not configured
- List returns user's simulations
- Get returns a single simulation
- Get returns 404 for unknown / other-user simulation
- Delete removes a simulation
- Delete returns 404 for unknown simulation
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.db import get_db
from api.main import app
from tests.api.conftest import BEARER, SIM_ID, SAMPLE_SIM, make_db_mock

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
    def test_empty_history_returns_empty_list(self, mock_db):
        resp = client.get("/api/simulations", headers={"Authorization": BEARER})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_saved_simulations(self, mock_db_with_sim):
        resp = client.get("/api/simulations", headers={"Authorization": BEARER})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == SIM_ID

    def test_result_has_expected_fields(self, mock_db_with_sim):
        data = client.get("/api/simulations", headers={"Authorization": BEARER}).json()
        row = data[0]
        for field in ("id", "created_at", "inputs", "result"):
            assert field in row, f"missing field: {field}"


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
