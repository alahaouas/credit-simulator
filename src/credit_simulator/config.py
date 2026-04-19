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

DEFAULT_LOAN_DURATION_MONTHS: int = 240  # 20 years

STEP_DOWN_PAYMENT = Decimal("1000")
STEP_DURATION: int = 12          # reserved for future duration grid-search
VALID_PREFERENCES: frozenset[str] = frozenset({
    "minimize_total_cost",
    "minimize_monthly_payment",
    "minimize_duration",
    "minimize_down_payment",
    "balanced",
})

# ── Sweet-spot analysis thresholds ───────────────────────────────────────────

SWEET_SPOT_LTV_TARGET = Decimal("0.80")   # LTV reference threshold (regulatory / bank threshold)
SWEET_SPOT_RESERVE_MONTHS: int = 6        # Months of income to keep in savings (emergency fund)
SWEET_SPOT_OPPORTUNITY_COST_RATE = Decimal("0.035")  # Annual benchmark return (e.g. savings / ETF)

# ── Calculator tuning ────────────────────────────────────────────────────────

APR_MAX_ITERATIONS: int = 100         # Newton-Raphson iterations for APR convergence
APR_TOLERANCE = Decimal("1E-12")      # Monthly-rate convergence tolerance
APR_PRECISION = Decimal("0.000001")   # Output precision for APR (6 decimal places)

# ── Fetcher tuning ────────────────────────────────────────────────────────────

FETCH_TIMEOUT_SECONDS: int = 10       # HTTP request timeout for online rate fetches

# ── Input validation bounds ──────────────────────────────────────────────────

MAX_MONETARY_VALUE = Decimal("1_000_000_000")   # 1 billion — sanity cap on amounts
MIN_LOAN_DURATION_MONTHS: int = 12              # minimum accepted loan duration

# ── Numeric convenience ───────────────────────────────────────────────────────

ZERO = Decimal("0")
CENT = Decimal("0.01")
