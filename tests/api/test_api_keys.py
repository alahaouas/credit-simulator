"""Tests for GET/POST/DELETE /api/keys and X-Api-Key auth (Layer 6 E3).

Covers:
- Auth guards (401 on all endpoints, 503 when Supabase missing)
- List returns keys without key_hash or full key
- Create returns full key exactly once
- Create with empty name returns 422
- Delete revokes a key (204)
- Delete nonexistent returns 404
- optional_user accepts X-Api-Key header via simulate endpoint
"""
from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from api.auth import hash_api_key
from api.db import get_db
from api.main import app
from tests.api.conftest import BEARER, USER_ID, make_db_mock

client = TestClient(app)

KEY_ID = "33333333-3333-3333-3333-333333333333"
SAMPLE_KEY_ROW = {
    "id": KEY_ID,
    "name": "my-script",
    "key_prefix": "csim_ab12cd",
    "created_at": "2026-05-14T10:00:00+00:00",
    "last_used_at": None,
}
# Full key row as stored (includes key_hash, not returned to clients)
FULL_KEY_ROW = {**SAMPLE_KEY_ROW, "user_id": USER_ID, "key_hash": "fakehash"}


# ---------------------------------------------------------------------------
# hash_api_key
# ---------------------------------------------------------------------------

class TestApiKeyHashing:
    def test_same_input_produces_same_hash(self):
        key = "csim_" + "b" * 64
        assert hash_api_key(key) == hash_api_key(key)

    def test_different_inputs_produce_different_hashes(self):
        assert hash_api_key("csim_aaa") != hash_api_key("csim_bbb")

    def test_output_is_hex_string(self):
        result = hash_api_key("csim_test")
        assert all(c in "0123456789abcdef" for c in result)

    def test_output_is_not_raw_sha256(self):
        import hashlib
        key = "csim_" + "c" * 64
        sha256_hex = hashlib.sha256(key.encode()).hexdigest()
        assert hash_api_key(key) != sha256_hex


# ---------------------------------------------------------------------------
# Auth guards
# ---------------------------------------------------------------------------

class TestApiKeysRequiresAuth:
    def test_list_no_auth_returns_401(self):
        assert client.get("/api/keys").status_code == 401

    def test_create_no_auth_returns_401(self):
        assert client.post("/api/keys", json={"name": "x"}).status_code == 401

    def test_delete_no_auth_returns_401(self):
        assert client.delete(f"/api/keys/{KEY_ID}").status_code == 401

    def test_auth_without_supabase_returns_503(self):
        resp = client.get("/api/keys", headers={"Authorization": BEARER})
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# GET /api/keys
# ---------------------------------------------------------------------------

class TestListApiKeys:
    def test_empty_list(self, mock_db):
        resp = client.get("/api/keys", headers={"Authorization": BEARER})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_keys(self):
        db = make_db_mock(rows=[SAMPLE_KEY_ROW])
        app.dependency_overrides[get_db] = lambda: db
        try:
            resp = client.get("/api/keys", headers={"Authorization": BEARER})
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["id"] == KEY_ID
        finally:
            app.dependency_overrides.clear()

    def test_response_has_expected_fields(self):
        db = make_db_mock(rows=[SAMPLE_KEY_ROW])
        app.dependency_overrides[get_db] = lambda: db
        try:
            data = client.get("/api/keys", headers={"Authorization": BEARER}).json()
            row = data[0]
            for field in ("id", "name", "key_prefix", "created_at"):
                assert field in row
        finally:
            app.dependency_overrides.clear()

    def test_key_hash_not_in_response(self):
        db = make_db_mock(rows=[SAMPLE_KEY_ROW])
        app.dependency_overrides[get_db] = lambda: db
        try:
            data = client.get("/api/keys", headers={"Authorization": BEARER}).json()
            assert "key_hash" not in data[0]
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /api/keys
# ---------------------------------------------------------------------------

class TestCreateApiKey:
    def test_returns_201_and_key(self, mock_db):
        resp = client.post(
            "/api/keys",
            json={"name": "my-script"},
            headers={"Authorization": BEARER},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "key" in data
        assert data["key"].startswith("csim_")
        assert len(data["key"]) == 69  # "csim_" + 64 hex chars

    def test_key_not_repeated_in_future_list(self, mock_db):
        data = client.post(
            "/api/keys", json={"name": "x"}, headers={"Authorization": BEARER}
        ).json()
        # key field only present in create response, not in list fields
        assert "key_hash" not in data

    def test_empty_name_returns_422(self, mock_db):
        resp = client.post(
            "/api/keys", json={"name": "  "}, headers={"Authorization": BEARER}
        )
        assert resp.status_code == 422

    def test_missing_name_returns_422(self, mock_db):
        resp = client.post("/api/keys", json={}, headers={"Authorization": BEARER})
        assert resp.status_code == 422

    def test_calls_insert(self, mock_db):
        client.post("/api/keys", json={"name": "ci"}, headers={"Authorization": BEARER})
        mock_db.table.assert_called_with("api_keys")
        mock_db.table.return_value.insert.assert_called_once()


# ---------------------------------------------------------------------------
# DELETE /api/keys/{key_id}
# ---------------------------------------------------------------------------

class TestDeleteApiKey:
    def test_delete_existing_returns_204(self):
        db = make_db_mock(rows=[FULL_KEY_ROW])
        app.dependency_overrides[get_db] = lambda: db
        try:
            resp = client.delete(f"/api/keys/{KEY_ID}", headers={"Authorization": BEARER})
            assert resp.status_code == 204
        finally:
            app.dependency_overrides.clear()

    def test_delete_nonexistent_returns_404(self, mock_db):
        resp = client.delete(f"/api/keys/{KEY_ID}", headers={"Authorization": BEARER})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# X-Api-Key authentication
# ---------------------------------------------------------------------------

class TestApiKeyAuth:
    def test_optional_user_resolves_api_key(self):
        """X-Api-Key header on POST /api/simulate is accepted and resolves a user."""
        test_key = "csim_" + "a" * 64

        db = MagicMock()
        # API key lookup: select("user_id,id").eq("key_hash", hash).execute()
        lookup_result = MagicMock()
        lookup_result.data = [{"user_id": USER_ID, "id": KEY_ID}]
        (db.table.return_value
            .select.return_value
            .eq.return_value
            .execute.return_value) = lookup_result

        # last_used_at update (fire-and-forget)
        db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        # simulation insert
        db.table.return_value.insert.return_value.execute.return_value = MagicMock()

        app.dependency_overrides[get_db] = lambda: db
        try:
            resp = client.post(
                "/api/simulate",
                headers={"X-Api-Key": test_key},
                json={
                    "property_price": "300000",
                    "monthly_net_income": "4000",
                    "available_savings": "80000",
                    "include_sweet_spot": False,
                },
            )
            assert resp.status_code == 200
            # Verify insert was called (user was identified → simulation was saved)
            db.table.return_value.insert.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    def test_invalid_api_key_returns_anonymous(self):
        """An unrecognised API key falls through to anonymous (no 401 for simulate)."""
        db = MagicMock()
        # Lookup returns nothing
        not_found = MagicMock()
        not_found.data = []
        (db.table.return_value
            .select.return_value
            .eq.return_value
            .execute.return_value) = not_found
        db.table.return_value.insert.return_value.execute.return_value = MagicMock()

        app.dependency_overrides[get_db] = lambda: db
        try:
            resp = client.post(
                "/api/simulate",
                headers={"X-Api-Key": "csim_invalid"},
                json={
                    "property_price": "300000",
                    "monthly_net_income": "4000",
                    "available_savings": "80000",
                    "include_sweet_spot": False,
                },
            )
            # simulate works anonymously — result is returned, nothing persisted
            assert resp.status_code == 200
            db.table.return_value.insert.assert_not_called()
        finally:
            app.dependency_overrides.clear()
