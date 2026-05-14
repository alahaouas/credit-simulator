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
        assert "https://myapp.vercel.app" in origins

    def test_allowed_origins_env_supports_multiple_comma_separated(self):
        origins = _reload_app({"ALLOWED_ORIGINS": "https://a.example.com,https://b.example.com"})
        assert "https://a.example.com" in origins
        assert "https://b.example.com" in origins

    def test_allowed_origins_strips_whitespace(self):
        origins = _reload_app({"ALLOWED_ORIGINS": " https://a.example.com , https://b.example.com "})
        assert "https://a.example.com" in origins
        assert "https://b.example.com" in origins

    def test_empty_allowed_origins_does_not_add_blank_entry(self):
        origins = _reload_app({"ALLOWED_ORIGINS": ""})
        assert "" not in origins
        assert all(o.startswith("http") for o in origins)

    def test_defaults_not_duplicated_when_env_is_empty(self):
        origins = _reload_app({"ALLOWED_ORIGINS": ""})
        assert origins.count("http://localhost:3000") == 1
