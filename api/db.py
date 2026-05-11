"""Supabase client dependency."""
from __future__ import annotations

import os

from supabase import Client, create_client


def get_db() -> Client | None:
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        return None
    return create_client(url, key)
