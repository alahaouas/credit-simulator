"""Application-wide constants and configuration defaults.

All tuneable defaults live here so there is a single place to adjust them.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

# ── Type aliases ──────────────────────────────────────────────────────────────

ProfileQuality = Literal["average", "best"]

# ── Country / profile defaults ────────────────────────────────────────────────

DEFAULT_COUNTRY: str = "BE"
DEFAULT_QUALITY: ProfileQuality = "average"

# ── Buyer constraint defaults ─────────────────────────────────────────────────

DEFAULT_MAX_MONTHLY_PAYMENT = Decimal("2200")

# ── Optimizer search parameters ───────────────────────────────────────────────

STEP_DOWN_PAYMENT = Decimal("1000")
STEP_DURATION: int = 12
VALID_PREFERENCES: frozenset[str] = frozenset({
    "minimize_total_cost",
    "minimize_monthly_payment",
    "minimize_duration",
    "minimize_down_payment",
    "balanced",
})

# ── Numeric convenience ───────────────────────────────────────────────────────

ZERO = Decimal("0")
CENT = Decimal("0.01")
