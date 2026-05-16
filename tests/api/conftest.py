"""Shared fixtures for API tests that need a mocked Supabase client."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from api.db import get_db
from api.main import app

USER_ID = "11111111-1111-1111-1111-111111111111"
SIM_ID = "22222222-2222-2222-2222-222222222222"
BEARER = "Bearer test-token-abc"

SAMPLE_SIM = {
    "id": SIM_ID,
    "user_id": USER_ID,
    "created_at": "2026-05-11T10:00:00+00:00",
    "inputs": {"property_price": "300000", "monthly_net_income": "4000", "available_savings": "80000"},
    "result": {"down_payment": "60000.00", "loan_principal": "268800.00"},
    "schedule": None,
    "name": "Brussels apartment",
    "tags": ["primary", "2026"],
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

    # select().eq().order().execute()  — list query
    (db.table.return_value
        .select.return_value
        .eq.return_value
        .order.return_value
        .execute.return_value) = execute_result

    # select().eq().eq().execute()  — get / delete query
    (db.table.return_value
        .select.return_value
        .eq.return_value
        .eq.return_value
        .execute.return_value) = execute_result

    # insert().execute()
    db.table.return_value.insert.return_value.execute.return_value = MagicMock()

    # delete().eq().eq().execute()
    (db.table.return_value
        .delete.return_value
        .eq.return_value
        .eq.return_value
        .execute.return_value) = execute_result

    # update().eq().eq().execute() — PATCH metadata (A1)
    (db.table.return_value
        .update.return_value
        .eq.return_value
        .eq.return_value
        .execute.return_value) = execute_result

    # select().eq().execute() — single-eq queries (stats, preferences GET, api_key lookup)
    (db.table.return_value
        .select.return_value
        .eq.return_value
        .execute.return_value) = execute_result

    # upsert().execute() — preferences PUT
    db.table.return_value.upsert.return_value.execute.return_value = execute_result

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
