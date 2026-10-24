"""Tests for api/main.py — CORS origin configuration."""
from __future__ import annotations

import sys
from unittest.mock import patch


def _reload_app(env: dict[str, str]):
    """Reload api.main with a patched environment to re-evaluate module-level CORS setup."""
    with patch.dict("os.environ", env, clear=False):
        # Force re-import so module-level _origins is recomputed
        for mod in list(sys.modules):
            if mod.startswith("api"):
                del sys.modules[mod]
        import api.main  # noqa: PLC0415
        return api.main._origins


class TestCorsOrigins:
    def test_default_origins_always_present(self):
        origins = _reload_app({})
        assert "http://localhost:3000" in origins
        assert "http://localhost:5173" in origins

    def test_allowed_origins_env_adds_extra_origin(self):
        origins = _reload_app({"ALLOWED_ORIGINS": "https://myapp.vercel.app"})
        assert any(o == "https://myapp.vercel.app" for o in origins)

    def test_allowed_origins_env_supports_multiple_comma_separated(self):
        origins = _reload_app({"ALLOWED_ORIGINS": "https://a.example.com,https://b.example.com"})
        assert any(o == "https://a.example.com" for o in origins)
        assert any(o == "https://b.example.com" for o in origins)

    def test_allowed_origins_strips_whitespace(self):
        origins = _reload_app({"ALLOWED_ORIGINS": " https://a.example.com , https://b.example.com "})
        assert any(o == "https://a.example.com" for o in origins)
        assert any(o == "https://b.example.com" for o in origins)

    def test_empty_allowed_origins_does_not_add_blank_entry(self):
        origins = _reload_app({"ALLOWED_ORIGINS": ""})
        assert "" not in origins
        assert all(o.startswith("http") for o in origins)

    def test_defaults_not_duplicated_when_env_is_empty(self):
        origins = _reload_app({"ALLOWED_ORIGINS": ""})
        assert origins.count("http://localhost:3000") == 1


class TestSecurityHeaders:
    """Every response path carries the same security headers: success, error and CORS preflight."""

    def _client(self):
        from fastapi.testclient import TestClient  # noqa: PLC0415

        import api.main  # noqa: PLC0415

        return TestClient(api.main.app), api.main.SECURITY_HEADERS

    def _assert_headers(self, response, expected):
        for name, value in expected.items():
            assert response.headers.get(name) == value, name

    def test_success_response(self):
        client, expected = self._client()
        response = client.get("/api/profiles")
        assert response.status_code == 200
        self._assert_headers(response, expected)

    def test_not_found_response(self):
        client, expected = self._client()
        response = client.get("/api/does-not-exist")
        assert response.status_code == 404
        self._assert_headers(response, expected)

    def test_cors_preflight_response(self):
        client, expected = self._client()
        response = client.options(
            "/api/profiles",
            headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
        )
        assert response.status_code == 200
        self._assert_headers(response, expected)
