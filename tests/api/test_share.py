"""Tests for share-token endpoints (Layer 6 A5).

Covers:
- POST /api/simulations/{id}/share   — generate token (auth required)
- DELETE /api/simulations/{id}/share — revoke token (auth required)
- GET /api/share/{token}             — public fetch by token (no auth)
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from api.db import get_db
from api.main import app
from tests.api.conftest import BEARER, SHARE_TOKEN, SIM_ID, make_db_mock

client = TestClient(app)


# ---------------------------------------------------------------------------
# Generate share token  POST /api/simulations/{id}/share
# ---------------------------------------------------------------------------

class TestGenerateShareToken:
    def test_no_auth_returns_401(self):
        assert client.post(f"/api/simulations/{SIM_ID}/share").status_code == 401

    def test_without_supabase_returns_503(self):
        resp = client.post(f"/api/simulations/{SIM_ID}/share", headers={"Authorization": BEARER})
        assert resp.status_code == 503

    def test_generates_token_for_existing_sim(self, mock_db_with_sim):
        resp = client.post(f"/api/simulations/{SIM_ID}/share", headers={"Authorization": BEARER})
        assert resp.status_code == 200
        data = resp.json()
        assert "share_token" in data
        assert isinstance(data["share_token"], str)
        assert len(data["share_token"]) > 0

    def test_not_found_returns_404(self, mock_db):
        resp = client.post(f"/api/simulations/{SIM_ID}/share", headers={"Authorization": BEARER})
        assert resp.status_code == 404

    def test_not_found_response_has_detail(self, mock_db):
        resp = client.post(f"/api/simulations/{SIM_ID}/share", headers={"Authorization": BEARER})
        assert "detail" in resp.json()

    def test_idempotent_returns_existing_token(self, mock_db_with_token_sim):
        """Calling generate on a sim that already has a token returns the same token."""
        resp = client.post(f"/api/simulations/{SIM_ID}/share", headers={"Authorization": BEARER})
        assert resp.status_code == 200
        assert resp.json()["share_token"] == SHARE_TOKEN


# ---------------------------------------------------------------------------
# Revoke share token  DELETE /api/simulations/{id}/share
# ---------------------------------------------------------------------------

class TestRevokeShareToken:
    def test_no_auth_returns_401(self):
        assert client.delete(f"/api/simulations/{SIM_ID}/share").status_code == 401

    def test_without_supabase_returns_503(self):
        resp = client.delete(f"/api/simulations/{SIM_ID}/share", headers={"Authorization": BEARER})
        assert resp.status_code == 503

    def test_revoke_existing_returns_204(self, mock_db_with_sim):
        resp = client.delete(f"/api/simulations/{SIM_ID}/share", headers={"Authorization": BEARER})
        assert resp.status_code == 204

    def test_revoke_not_found_returns_404(self, mock_db):
        resp = client.delete(f"/api/simulations/{SIM_ID}/share", headers={"Authorization": BEARER})
        assert resp.status_code == 404

    def test_revoke_calls_update_on_simulations_table(self, mock_db_with_sim):
        client.delete(f"/api/simulations/{SIM_ID}/share", headers={"Authorization": BEARER})
        mock_db_with_sim.table.assert_called_with("simulations")


# ---------------------------------------------------------------------------
# Public fetch by token  GET /api/share/{token}
# ---------------------------------------------------------------------------

class TestGetSharedSimulation:
    def test_without_supabase_returns_503(self):
        # No dependency override — get_db returns None
        resp = client.get(f"/api/share/{SHARE_TOKEN}")
        assert resp.status_code == 503

    def test_returns_simulation_without_auth(self, mock_db_with_sim):
        """No Authorization header required."""
        resp = client.get(f"/api/share/{SHARE_TOKEN}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == SIM_ID

    def test_not_found_returns_404(self, mock_db):
        resp = client.get(f"/api/share/{SHARE_TOKEN}")
        assert resp.status_code == 404

    def test_not_found_has_detail(self, mock_db):
        resp = client.get(f"/api/share/{SHARE_TOKEN}")
        assert "detail" in resp.json()

    def test_response_has_expected_fields(self, mock_db_with_sim):
        data = client.get(f"/api/share/{SHARE_TOKEN}").json()
        for field in ("id", "created_at", "result"):
            assert field in data, f"missing field: {field}"

    def test_auth_header_not_required(self, mock_db_with_sim):
        """Explicitly verify no auth header is needed (public endpoint)."""
        resp = client.get(f"/api/share/{SHARE_TOKEN}")
        # Must succeed without Authorization header
        assert resp.status_code == 200
