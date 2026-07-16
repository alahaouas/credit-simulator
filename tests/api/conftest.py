"""Shared fixtures for API tests that need a mocked Supabase client."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from api.db import get_db
from api.limiter import limiter
from api.main import app


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Clear slowapi's in-memory rate-limit counters before every test.

    Without this, tests sharing the same TestClient "IP" accumulate
    request counts across the whole test session and start tripping
    429s well before a minute of wall-clock time has passed.
    """
    limiter.reset()
    yield


USER_ID = "11111111-1111-1111-1111-111111111111"
SIM_ID = "22222222-2222-2222-2222-222222222222"
KEY_ID = "33333333-3333-3333-3333-333333333333"
BEARER = "Bearer test-token-abc"

BASE = {
    "property_price": "300000",
    "monthly_net_income": "4000",
    "available_savings": "80000",
}

SHARE_TOKEN = "test-share-token-abc123"

SAMPLE_SIM = {
    "id": SIM_ID,
    "user_id": USER_ID,
    "created_at": "2026-05-11T10:00:00+00:00",
    "inputs": {"property_price": "300000", "monthly_net_income": "4000", "available_savings": "80000"},
    "result": {"down_payment": "60000.00", "loan_principal": "268800.00"},
    "schedule": None,
    "name": "Brussels apartment",
    "tags": ["primary", "2026"],
    "share_token": None,
}

SAMPLE_SIM_WITH_TOKEN = {
    **SAMPLE_SIM,
    "share_token": SHARE_TOKEN,
}


def make_db_mock(
    *,
    rows: list[dict] | None = None,
    auth_fail: bool = False,
    invalid_token: bool = False,
    user_id: str = USER_ID,
) -> MagicMock:
    """Build a chained-call mock of the Supabase client used in tests.

    auth_fail=True       — auth backend raises (simulates service outage → 503)
    invalid_token=True   — auth backend returns no user (simulates bad/expired JWT → anonymous)
    """
    db = MagicMock()

    if auth_fail:
        db.auth.get_user.side_effect = Exception("auth backend unreachable")
    elif invalid_token:
        resp = MagicMock()
        resp.user = None
        db.auth.get_user.return_value = resp
    else:
        user = MagicMock()
        user.user.id = user_id
        db.auth.get_user.return_value = user

    execute_result = MagicMock()
    execute_result.data = rows if rows is not None else []

    # Fluent chain: every query builder method returns the same chain object
    # so any sequence of .select/.eq/.or_/.lt/.order/.limit/.update/... works.
    chain = MagicMock()
    for method in (
        "select", "eq", "or_", "lt", "order", "limit",
        "update", "delete", "upsert",
    ):
        getattr(chain, method).return_value = chain
    chain.execute.return_value = execute_result
    chain.insert.return_value.execute.return_value = MagicMock()

    db.table.return_value = chain

    return db


@pytest.fixture
def mock_db():
    db = make_db_mock()
    app.dependency_overrides[get_db] = lambda: db
    yield db
    app.dependency_overrides.clear()


@pytest.fixture
def mock_db_with_sim():
    db = make_db_mock(rows=[SAMPLE_SIM])
    app.dependency_overrides[get_db] = lambda: db
    yield db
    app.dependency_overrides.clear()


@pytest.fixture
def mock_db_with_token_sim():
    """Simulation that already has a share_token set."""
    db = make_db_mock(rows=[SAMPLE_SIM_WITH_TOKEN])
    app.dependency_overrides[get_db] = lambda: db
    yield db
    app.dependency_overrides.clear()


SAMPLE_KEY_ROW = {
    "id": KEY_ID,
    "name": "my-script",
    "key_prefix": "csim_ab12cd",
    "created_at": "2026-05-14T10:00:00+00:00",
    "last_used_at": None,
}


@pytest.fixture
def mock_db_with_key():
    db = make_db_mock(rows=[SAMPLE_KEY_ROW])
    app.dependency_overrides[get_db] = lambda: db
    yield db
    app.dependency_overrides.clear()
