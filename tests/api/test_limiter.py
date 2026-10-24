"""Tests for api/limiter.py — the rate-limit bucket key.

The key must never collapse onto a shared value (a proxy's address): that would
put every user in one bucket. Untrustworthy or unconfigured cases must raise.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from api.limiter import client_key


def _request(
    headers: dict[str, str] | None = None, client=("10.0.0.9", 443), user_id=None
) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/simulate",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "client": client,
    }
    request = Request(scope)
    if user_id is not None:
        request.state.user_id = user_id
    return request


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in (
        "TRUSTED_CLIENT_IP_HEADER",
        "TRUSTED_PROXY_HOPS",
        "RATE_LIMIT_STORAGE_URL",
        "REDIS_URL",
    ):
        monkeypatch.delenv(name, raising=False)


class TestAuthenticatedUser:
    def test_verified_user_gets_own_bucket(self):
        assert client_key(_request(user_id="u-1")) == "user:u-1"

    def test_user_takes_precedence_over_forwarded_headers(self):
        request = _request({"X-Forwarded-For": "1.2.3.4"}, user_id="u-1")
        assert client_key(request) == "user:u-1"


class TestTrustedClientIpHeader:
    """Vercel: x-real-ip is set by the platform, and a shared counter store is required."""

    @pytest.fixture
    def on_vercel(self, monkeypatch):
        monkeypatch.setenv("TRUSTED_CLIENT_IP_HEADER", "x-real-ip")
        monkeypatch.setenv("RATE_LIMIT_STORAGE_URL", "rediss://example:6379")

    def test_uses_the_trusted_header(self, on_vercel):
        assert client_key(_request({"X-Real-IP": "198.51.100.4"})) == "ip:198.51.100.4"

    def test_trusted_header_wins_over_forwarded_for(self, on_vercel):
        request = _request({"X-Real-IP": "198.51.100.4", "X-Forwarded-For": "6.6.6.6"})
        assert client_key(request) == "ip:198.51.100.4"

    def test_missing_trusted_header_is_rejected(self, on_vercel):
        with pytest.raises(HTTPException) as exc:
            client_key(_request())
        assert exc.value.status_code == 503

    def test_redis_url_counts_as_storage(self, monkeypatch):
        monkeypatch.setenv("TRUSTED_CLIENT_IP_HEADER", "x-real-ip")
        monkeypatch.setenv("REDIS_URL", "rediss://example:6379")
        assert client_key(_request({"X-Real-IP": "198.51.100.4"})) == "ip:198.51.100.4"

    def test_without_shared_storage_is_rejected(self, monkeypatch):
        monkeypatch.setenv("TRUSTED_CLIENT_IP_HEADER", "x-real-ip")
        with pytest.raises(HTTPException) as exc:
            client_key(_request({"X-Real-IP": "198.51.100.4"}))
        assert exc.value.status_code == 503

    def test_header_is_ignored_unless_configured(self):
        assert client_key(_request({"X-Real-IP": "198.51.100.4"})) == "ip:10.0.0.9"


class TestForwardedFor:
    def test_counts_trusted_hops_from_the_right(self, monkeypatch):
        monkeypatch.setenv("TRUSTED_PROXY_HOPS", "1")
        assert client_key(_request({"X-Forwarded-For": "203.0.113.7"})) == "ip:203.0.113.7"

    def test_spoofed_left_entries_are_ignored(self, monkeypatch):
        monkeypatch.setenv("TRUSTED_PROXY_HOPS", "1")
        request = _request({"X-Forwarded-For": "6.6.6.6, 203.0.113.7"})
        assert client_key(request) == "ip:203.0.113.7"

    def test_two_hops(self, monkeypatch):
        monkeypatch.setenv("TRUSTED_PROXY_HOPS", "2")
        request = _request({"X-Forwarded-For": "6.6.6.6, 203.0.113.7, 10.1.1.1"})
        assert client_key(request) == "ip:203.0.113.7"

    def test_unconfigured_hops_rejects_instead_of_sharing_the_proxy_key(self):
        with pytest.raises(HTTPException) as exc:
            client_key(_request({"X-Forwarded-For": "203.0.113.7"}))
        assert exc.value.status_code == 503

    def test_fewer_entries_than_hops_is_rejected(self, monkeypatch):
        monkeypatch.setenv("TRUSTED_PROXY_HOPS", "3")
        with pytest.raises(HTTPException) as exc:
            client_key(_request({"X-Forwarded-For": "203.0.113.7"}))
        assert exc.value.status_code == 400

    @pytest.mark.parametrize("value", ["0", "-1", "two"])
    def test_invalid_hops_is_rejected(self, monkeypatch, value):
        monkeypatch.setenv("TRUSTED_PROXY_HOPS", value)
        with pytest.raises(HTTPException) as exc:
            client_key(_request({"X-Forwarded-For": "203.0.113.7"}))
        assert exc.value.status_code == 503


class TestOptionalUserFeedsTheKey:
    def test_verified_bearer_sets_request_state(self):
        from unittest.mock import MagicMock  # noqa: PLC0415

        from api.auth import optional_user  # noqa: PLC0415

        db = MagicMock()
        db.auth.get_user.return_value.user.id = "u-42"
        request = _request()
        assert optional_user(request, authorization="Bearer t", x_api_key=None, db=db) == "u-42"
        assert client_key(request) == "user:u-42"

    def test_anonymous_leaves_no_user_on_state(self):
        from api.auth import optional_user  # noqa: PLC0415

        request = _request()
        assert optional_user(request, authorization=None, x_api_key=None, db=None) is None
        assert client_key(request) == "ip:10.0.0.9"


class TestDirectConnection:
    def test_no_forwarded_header_uses_peer(self):
        assert client_key(_request()) == "ip:10.0.0.9"

    def test_no_peer_is_rejected(self):
        with pytest.raises(HTTPException) as exc:
            client_key(_request(client=None))
        assert exc.value.status_code == 503
