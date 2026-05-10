"""Parameter resolution (§4.1) and feasibility checking (§4.2).

Resolution order:
1. country defaults to BE, profile_quality defaults to 'average'.
2. Each optional loan parameter falls back to the country profile if not user-supplied.
3. purchase_taxes estimated from profile if not provided.
4. total_acquisition_cost = property_price + purchase_taxes.
5. min_down_payment computed per taxes_financeable rule.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from .calculator import compute_emi, compute_monthly_insurance
from .config import (
    DEFAULT_COUNTRY,
    DEFAULT_LOAN_DURATION_MONTHS,
    DEFAULT_MAX_MONTHLY_PAYMENT,
    DEFAULT_QUALITY,
    SWEET_SPOT_OPPORTUNITY_COST_RATE,
    ZERO,
    ProfileQuality,
)
from .i18n import _
from .profiles import LtvRateTier, SessionProfileStore, get_profile


@dataclass
class UserInputs:
    """Raw user-supplied values.  None means 'not provided — use profile default'."""
    # Mandatory
    property_price: Decimal
    monthly_net_income: Decimal
    available_savings: Decimal
    # Optional property
    country: str | None = None
    profile_quality: ProfileQuality | None = None
    purchase_taxes: Decimal | None = None
    # Optional loan parameters
    annual_interest_rate: Decimal | None = None
    insurance_rate: Decimal | None = None
    min_down_payment_ratio: Decimal | None = None
    max_loan_duration_months: int | None = None
    fixed_loan_duration_months: int | None = None  # pin optimizer to exactly this duration
    # Optional buyer constraints
    max_debt_ratio: Decimal | None = None
    max_monthly_payment: Decimal | None = None
    preferred_down_payment: Decimal | None = None  # pin optimizer to exactly this amount
    # Optimization preference
    optimization_preference: str = "balanced"
    # Sweet-spot analysis benchmark
    opportunity_cost_rate: Decimal | None = None  # None → use config default


@dataclass(frozen=True)
class ResolvedParams:
    """Fully resolved simulation parameters, ready for optimization."""
    # Country / quality
    country: str
    profile_quality: ProfileQuality
    currency: str
    # Property
    property_price: Decimal
    purchase_taxes: Decimal
    total_acquisition_cost: Decimal
    taxes_financeable: bool
    # Loan parameters (resolved)
    annual_interest_rate: Decimal
    insurance_rate: Decimal
    min_down_payment_ratio: Decimal
    max_loan_duration_months: int
    fixed_loan_duration_months: int  # defaults to DEFAULT_LOAN_DURATION_MONTHS
    preferred_down_payment: Decimal | None  # None means free grid search
    # Buyer constraints (resolved)
    monthly_net_income: Decimal
    available_savings: Decimal
    max_debt_ratio: Decimal
    max_monthly_payment: Decimal
    min_down_payment: Decimal
    # LTV-based rate tiers (from static profile, ordered ascending ltv_max)
    ltv_rate_tiers: tuple[LtvRateTier, ...]
    # Preference
    optimization_preference: str
    # Sweet-spot opportunity cost (resolved from user input or config default)
    opportunity_cost_rate: Decimal
    # Provenance — 'user' or 'profile' for each optional param
    sources: dict[str, str] = field(default_factory=dict)

    def rate_for_ltv(self, ltv: Decimal) -> Decimal:
        """Effective annual rate for the given LTV (base rate + tier delta)."""
        for tier in self.ltv_rate_tiers:
            if ltv <= tier.ltv_max:
                return self.annual_interest_rate + tier.rate_delta
        if self.ltv_rate_tiers:
            return self.annual_interest_rate + self.ltv_rate_tiers[-1].rate_delta
        return self.annual_interest_rate


class InfeasibleError(Exception):
    """Raised when the buyer cannot afford any loan under the given constraints."""


def resolve(inputs: UserInputs, store: SessionProfileStore) -> ResolvedParams:
    """Resolve all parameters and return a fully-specified ResolvedParams."""
    sources: dict[str, str] = {}

    # --- Step 1: country & quality ---
    country = (inputs.country or DEFAULT_COUNTRY).upper()
    quality: ProfileQuality = inputs.profile_quality or DEFAULT_QUALITY
    # Validate country code (will raise ValueError if unknown)
    profile = get_profile(country)

    currency = str(store.get_field(country, "currency"))
    ltv_rate_tiers = profile.ltv_rate_tiers

    # --- Step 2: optional loan parameters ---
    def _resolve(user_val, profile_val, name: str):
        if user_val is not None:
            sources[name] = "user"
            return user_val
        sources[name] = "profile"
        return profile_val

    annual_interest_rate = _resolve(
        inputs.annual_interest_rate,
        store.get_annual_rate(country, quality),
        "annual_interest_rate",
    )
    insurance_rate = _resolve(
        inputs.insurance_rate,
        store.get_insurance_rate(country, quality),
        "insurance_rate",
    )
    min_down_payment_ratio = _resolve(
        inputs.min_down_payment_ratio,
        Decimal(str(store.get_field(country, "min_down_payment_ratio"))),
        "min_down_payment_ratio",
    )
    max_loan_duration_months = _resolve(
        inputs.max_loan_duration_months,
        int(store.get_field(country, "max_loan_duration_months")),
        "max_loan_duration_months",
    )
    max_debt_ratio = _resolve(
        inputs.max_debt_ratio,
        Decimal(str(store.get_field(country, "max_debt_ratio"))),
        "max_debt_ratio",
    )
    max_monthly_payment = _resolve(
        inputs.max_monthly_payment,
        DEFAULT_MAX_MONTHLY_PAYMENT,
        "max_monthly_payment",
    )

    # --- Step 3: fixed loan duration ---
    if inputs.fixed_loan_duration_months is not None:
        fixed_loan_duration_months = inputs.fixed_loan_duration_months
        sources["fixed_loan_duration_months"] = "user"
    else:
        fixed_loan_duration_months = DEFAULT_LOAN_DURATION_MONTHS
        sources["fixed_loan_duration_months"] = "default"

    # --- Step 4: preferred down payment ---
    if inputs.preferred_down_payment is not None:
        sources["preferred_down_payment"] = "user"

    # --- Step 5: purchase_taxes ---
    taxes_financeable = bool(store.get_field(country, "taxes_financeable"))
    if inputs.purchase_taxes is not None:
        purchase_taxes = inputs.purchase_taxes
        sources["purchase_taxes"] = "user"
    else:
        tax_rate = Decimal(str(store.get_field(country, "purchase_tax_rate")))
        purchase_taxes = (inputs.property_price * tax_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        sources["purchase_taxes"] = "profile"

    # --- Step 6: total acquisition cost ---
    total_acquisition_cost = inputs.property_price + purchase_taxes

    # --- Step 7: effective minimum down payment ---
    if not taxes_financeable:
        min_down_payment = max(
            purchase_taxes,
            total_acquisition_cost * min_down_payment_ratio,
        )
    else:
        min_down_payment = total_acquisition_cost * min_down_payment_ratio

    return ResolvedParams(
        country=country,
        profile_quality=quality,
        currency=currency,
        property_price=inputs.property_price,
        purchase_taxes=purchase_taxes,
        total_acquisition_cost=total_acquisition_cost,
        taxes_financeable=taxes_financeable,
        annual_interest_rate=annual_interest_rate,
        insurance_rate=insurance_rate,
        min_down_payment_ratio=min_down_payment_ratio,
        max_loan_duration_months=max_loan_duration_months,
        fixed_loan_duration_months=fixed_loan_duration_months,
        preferred_down_payment=inputs.preferred_down_payment,
        ltv_rate_tiers=ltv_rate_tiers,
        monthly_net_income=inputs.monthly_net_income,
        available_savings=inputs.available_savings,
        max_debt_ratio=max_debt_ratio,
        max_monthly_payment=max_monthly_payment,
        min_down_payment=min_down_payment,
        optimization_preference=inputs.optimization_preference,
        opportunity_cost_rate=(
            inputs.opportunity_cost_rate
            if inputs.opportunity_cost_rate is not None
            else SWEET_SPOT_OPPORTUNITY_COST_RATE
        ),
        sources=sources,
    )


def check_feasibility(params: ResolvedParams) -> None:
    """Raise InfeasibleError if the buyer cannot get any loan at all.

    Checks (per §4.2):
    1. available_savings >= min_down_payment
    2. income headroom is enough for at least the minimum possible payment
    3. required loan principal > 0
    """
    if params.available_savings < params.min_down_payment:
        raise InfeasibleError(_(
            "error.infeasible.savings",
            min_dp=f"{params.min_down_payment:,.2f}",
            currency=params.currency,
            savings=f"{params.available_savings:,.2f}",
        ))

    if params.preferred_down_payment is not None:
        if params.preferred_down_payment < params.min_down_payment:
            raise InfeasibleError(_(
                "error.infeasible.preferred_below_min",
                preferred=f"{params.preferred_down_payment:,.2f}",
                currency=params.currency,
                min_dp=f"{params.min_down_payment:,.2f}",
            ))
        if params.preferred_down_payment > params.available_savings:
            raise InfeasibleError(_(
                "error.infeasible.preferred_above_savings",
                preferred=f"{params.preferred_down_payment:,.2f}",
                currency=params.currency,
                savings=f"{params.available_savings:,.2f}",
            ))

    # Minimum possible monthly payment = smallest principal at longest duration.
    # Smallest principal = total_acquisition_cost - all available savings.
    min_principal = params.total_acquisition_cost - params.available_savings
    if min_principal <= ZERO:
        # Buyer can pay cash — loan is trivially feasible (loan = 0)
        return

    # Effective monthly cap = stricter of DTI limit and absolute payment cap.
    effective_cap = min(
        params.monthly_net_income * params.max_debt_ratio,
        params.max_monthly_payment,
    )

    min_ltv = min_principal / params.property_price
    best_emi = compute_emi(
        min_principal, params.rate_for_ltv(min_ltv), params.max_loan_duration_months
    )
    min_insurance = compute_monthly_insurance(min_principal, params.insurance_rate)
    min_payment = best_emi + min_insurance

    if min_payment > effective_cap:
        raise InfeasibleError(_(
            "error.infeasible.payment_too_high",
            principal=f"{min_principal:,.2f}",
            currency=params.currency,
            months=params.max_loan_duration_months,
            payment=f"{min_payment:,.2f}",
            cap=f"{effective_cap:,.2f}",
            dti_pct=f"{params.max_debt_ratio:.0%}",
            abs_cap=f"{params.max_monthly_payment:,.2f}",
        ))
