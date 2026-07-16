"""Shared slowapi rate limiter for compute-heavy / external-call endpoints.

Per-process, in-memory limiter keyed by client IP. Sufficient for a
single-instance deployment; a multi-instance deployment would need a
shared backend (e.g. Redis) instead.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
