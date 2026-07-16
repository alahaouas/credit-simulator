"""Pydantic request/response models for the Credit Simulator API.

Monetary and rate fields are typed as str so that JSON numbers (IEEE-754
floats) never silently truncate financial precision.  Validators confirm
that each value parses as a valid Decimal before it reaches the domain layer.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, field_validator

from credit_simulator.config import MIN_LOAN_DURATION_MONTHS, VALID_PREFERENCES

from .constants import CURRENCY_DISPLAY_OPTIONS, SUPPORTED_COUNTRIES

MAX_LOAN_DURATION_MONTHS = 600  # 50 years — matches the CLI's own sanity cap


class UserPreferencesModel(BaseModel):
    """Body model for PUT /api/preferences (E1)."""

    default_country: str = "BE"
    default_optimization_preference: str = "balanced"
    currency_display: str = "symbol"

    @field_validator("default_country", mode="before")
    @classmethod
    def validate_country(cls, v: object) -> str:
        s = str(v).upper()
        if s not in SUPPORTED_COUNTRIES:
            raise ValueError(f"unsupported country '{v}'; must be one of {sorted(SUPPORTED_COUNTRIES)}")
        return s

    @field_validator("default_optimization_preference", mode="before")
    @classmethod
    def validate_pref(cls, v: object) -> str:
        if v not in VALID_PREFERENCES:
            raise ValueError(
                f"optimization_preference must be one of {sorted(VALID_PREFERENCES)}, got {v!r}"
            )
        return str(v)

    @field_validator("currency_display", mode="before")
    @classmethod
    def validate_currency_display(cls, v: object) -> str:
        if v not in CURRENCY_DISPLAY_OPTIONS:
            raise ValueError(f"currency_display must be 'symbol' or 'code', got {v!r}")
        return str(v)


class SimulationMetaUpdate(BaseModel):
    """Body model for PATCH /api/simulations/{id} (A1 — naming & tagging).

    Both fields are optional; only fields present in the request are applied.
    Sending ``name: null`` (or an empty/whitespace string) clears the name.
    """

    name: str | None = None
    tags: list[str] | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        if len(s) > 120:
            raise ValueError("name must be 120 characters or fewer")
        return s or None

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v: object) -> list[str] | None:
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError("tags must be a list of strings")
        cleaned: list[str] = []
        for tag in v:
            s = str(tag).strip()
            if not s:
                continue
            if len(s) > 40:
                raise ValueError("each tag must be 40 characters or fewer")
            if s not in cleaned:
                cleaned.append(s)
        if len(cleaned) > 20:
            raise ValueError("a simulation can have at most 20 tags")
        return cleaned


class SimulateRequest(BaseModel):
    # --- Mandatory ---
    property_price: str
    monthly_net_income: str
    available_savings: str

    # --- Optional property ---
    country: str | None = None
    profile_quality: str | None = None

    # --- Optional overrides (all monetary / rate fields as str) ---
    purchase_taxes: str | None = None
    annual_interest_rate: str | None = None
    insurance_rate: str | None = None
    min_down_payment_ratio: str | None = None
    max_loan_duration_months: int | None = None
    fixed_loan_duration_months: int | None = None

    # --- Optional buyer constraints ---
    max_debt_ratio: str | None = None
    max_monthly_payment: str | None = None
    preferred_down_payment: str | None = None

    # --- Optimization ---
    optimization_preference: str = "balanced"
    opportunity_cost_rate: str | None = None

    # --- Response shaping ---
    include_schedule: bool = False
    include_sweet_spot: bool = True

    # --- Validators ---

    @field_validator("property_price", "monthly_net_income", "available_savings", mode="before")
    @classmethod
    def validate_positive_decimal(cls, v: object) -> str:
        if v is None:
            raise ValueError("field is required")
        try:
            d = Decimal(str(v))
        except InvalidOperation as err:
            raise ValueError(f"cannot parse {v!r} as a decimal number") from err
        if d <= 0:
            raise ValueError(f"must be > 0, got {v!r}")
        return str(v)

    @field_validator(
        "purchase_taxes",
        "annual_interest_rate",
        "insurance_rate",
        "min_down_payment_ratio",
        "max_debt_ratio",
        "max_monthly_payment",
        "preferred_down_payment",
        "opportunity_cost_rate",
        mode="before",
    )
    @classmethod
    def validate_optional_decimal(cls, v: object) -> str | None:
        if v is None:
            return None
        try:
            d = Decimal(str(v))
        except InvalidOperation as err:
            raise ValueError(f"cannot parse {v!r} as a decimal number") from err
        if d < 0:
            raise ValueError(f"must be >= 0, got {v!r}")
        return str(v)

    @field_validator("max_loan_duration_months", "fixed_loan_duration_months", mode="before")
    @classmethod
    def validate_loan_duration_months(cls, v: object) -> int | None:
        if v is None:
            return None
        try:
            i = int(v)
        except (TypeError, ValueError) as err:
            raise ValueError(f"cannot parse {v!r} as an integer") from err
        if not (MIN_LOAN_DURATION_MONTHS <= i <= MAX_LOAN_DURATION_MONTHS):
            raise ValueError(
                f"must be between {MIN_LOAN_DURATION_MONTHS} and {MAX_LOAN_DURATION_MONTHS}, got {i}"
            )
        return i

    @field_validator("profile_quality", mode="before")
    @classmethod
    def validate_profile_quality(cls, v: object) -> str | None:
        if v is None:
            return None
        if v not in ("average", "best"):
            raise ValueError(f"profile_quality must be 'average' or 'best', got {v!r}")
        return str(v)

    @field_validator("optimization_preference", mode="before")
    @classmethod
    def validate_optimization_preference(cls, v: object) -> str:
        if v not in VALID_PREFERENCES:
            raise ValueError(
                f"optimization_preference must be one of "
                f"{sorted(VALID_PREFERENCES)}, got {v!r}"
            )
        return str(v)
