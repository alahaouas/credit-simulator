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
    monkeypatch.delenv("API_PROXY_SECRET", raising=False)
    monkeypatch.delenv("TRUSTED_PROXY_HOPS", raising=False)


class TestAuthenticatedUser:
    def test_verified_user_gets_own_bucket(self):
        assert client_key(_request(user_id="u-1")) == "user:u-1"

    def test_user_takes_precedence_over_forwarded_headers(self):
        request = _request({"X-Forwarded-For": "1.2.3.4"}, user_id="u-1")
        assert client_key(request) == "user:u-1"


class TestProxySecret:
    def test_matching_secret_uses_client_ip_header(self, monkeypatch):
        monkeypatch.setenv("API_PROXY_SECRET", "s3cret")
        request = _request({"X-Proxy-Secret": "s3cret", "X-Client-IP": "198.51.100.4"})
        assert client_key(request) == "ip:198.51.100.4"

    def test_wrong_secret_is_rejected(self, monkeypatch):
        monkeypatch.setenv("API_PROXY_SECRET", "s3cret")
        request = _request({"X-Proxy-Secret": "guess", "X-Client-IP": "198.51.100.4"})
        with pytest.raises(HTTPException) as exc:
            client_key(request)
        assert exc.value.status_code == 403

    def test_secret_sent_but_not_configured_is_rejected(self):
        request = _request({"X-Proxy-Secret": "anything", "X-Client-IP": "198.51.100.4"})
        with pytest.raises(HTTPException) as exc:
            client_key(request)
        assert exc.value.status_code == 403

    def test_missing_client_ip_is_rejected(self, monkeypatch):
        monkeypatch.setenv("API_PROXY_SECRET", "s3cret")
        with pytest.raises(HTTPException) as exc:
            client_key(_request({"X-Proxy-Secret": "s3cret"}))
        assert exc.value.status_code == 400

    def test_client_ip_header_ignored_without_secret(self, monkeypatch):
        monkeypatch.setenv("API_PROXY_SECRET", "s3cret")
        assert client_key(_request({"X-Client-IP": "198.51.100.4"})) == "ip:10.0.0.9"


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
