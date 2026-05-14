"""API-layer constants.

Domain constants live in `src/credit_simulator/config.py`; this module is the
single source of truth for values used by the FastAPI surface (request
validation, CORS, defaults, prefixes).
"""
from __future__ import annotations

from credit_simulator.config import DEFAULT_COUNTRY, DEFAULT_QUALITY

# Countries accepted by the API surface (mirrors the static profiles in
# credit_simulator.profiles).
SUPPORTED_COUNTRIES: frozenset[str] = frozenset(
    {"BE", "FR", "DE", "ES", "PT", "IT", "GB", "US"}
)

CURRENCY_DISPLAY_OPTIONS: frozenset[str] = frozenset({"symbol", "code"})

# E3 — API key surface
API_KEY_PREFIX = "csim_"
API_KEY_DISPLAY_PREFIX_LEN = 12  # chars of the full key shown back to users

# E1 — user preferences defaults
DEFAULT_USER_PREFERENCES: dict[str, str] = {
    "default_country": DEFAULT_COUNTRY,
    "default_optimization_preference": "balanced",
    "currency_display": "symbol",
}

# CORS — local dev origins always allowed. Production origins go in
# the ALLOWED_ORIGINS env var (comma-separated).
DEFAULT_CORS_ORIGINS: list[str] = [
    "http://localhost:3000",
    "http://localhost:5173",
]

__all__ = [
    "API_KEY_DISPLAY_PREFIX_LEN",
    "API_KEY_PREFIX",
    "CURRENCY_DISPLAY_OPTIONS",
    "DEFAULT_CORS_ORIGINS",
    "DEFAULT_COUNTRY",
    "DEFAULT_QUALITY",
    "DEFAULT_USER_PREFERENCES",
    "SUPPORTED_COUNTRIES",
]
