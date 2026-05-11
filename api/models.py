"""Pydantic request model for the Credit Simulator API.

Monetary and rate fields are typed as str so that JSON numbers (IEEE-754
floats) never silently truncate financial precision.  Validators confirm
that each value parses as a valid Decimal before it reaches the domain layer.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, field_validator

from credit_simulator.config import VALID_PREFERENCES


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
        except InvalidOperation:
            raise ValueError(f"cannot parse {v!r} as a decimal number")
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
        except InvalidOperation:
            raise ValueError(f"cannot parse {v!r} as a decimal number")
        if d < 0:
            raise ValueError(f"must be >= 0, got {v!r}")
        return str(v)

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
